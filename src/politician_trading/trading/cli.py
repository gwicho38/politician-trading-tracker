"""
CLI for politician trading execution
"""

import click
import asyncio
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from decimal import Decimal
import os
import logging

from politician_trading.trading.alpaca_client import AlpacaTradingClient
from politician_trading.trading.risk_manager import RiskManager
from politician_trading.trading.strategy import TradingStrategy
from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from src.models import TradingSignal, SignalType, SignalStrength

console = Console()
logger = logging.getLogger(__name__)


def get_alpaca_client(paper: bool = True) -> AlpacaTradingClient:
    """Get Alpaca client from environment variables."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        console.print("[red]Error: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set[/]")
        raise click.Abort()

    return AlpacaTradingClient(api_key=api_key, secret_key=secret_key, paper=paper)


@click.group()
def main():
    """Politician Trading - Automated Trading CLI"""
    pass


@main.command()
@click.option("--live", is_flag=True, help="Use live trading (default: paper)")
def account(live):
    """Show account information"""
    try:
        client = get_alpaca_client(paper=not live)
        account_info = client.get_account()

        mode = "LIVE TRADING" if live else "PAPER TRADING"
        panel = Panel.fit(
            f"""
[bold]Account ID:[/] {account_info['account_id']}
[bold]Status:[/] {account_info['status']}
[bold]Portfolio Value:[/] ${account_info['portfolio_value']:,.2f}
[bold]Cash:[/] ${account_info['cash']:,.2f}
[bold]Buying Power:[/] ${account_info['buying_power']:,.2f}
[bold]Equity:[/] ${account_info['equity']:,.2f}

[bold]Long Market Value:[/] ${account_info['long_market_value']:,.2f}
[bold]Short Market Value:[/] ${account_info['short_market_value']:,.2f}

[bold]Pattern Day Trader:[/] {account_info['pattern_day_trader']}
[bold]Trading Blocked:[/] {account_info['trading_blocked']}
            """.strip(),
            title=f"[bold cyan]{mode}[/]",
            border_style="cyan",
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@main.command()
@click.option("--live", is_flag=True, help="Use live trading (default: paper)")
def positions(live):
    """Show open positions"""
    try:
        client = get_alpaca_client(paper=not live)
        positions = client.get_positions()

        if not positions:
            console.print("[yellow]No open positions[/]")
            return

        table = Table(title="Open Positions", box=box.ROUNDED)
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Side", style="magenta")
        table.add_column("Quantity", justify="right")
        table.add_column("Avg Entry", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Market Value", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")

        for pos in positions:
            pl_color = "green" if pos.unrealized_pl >= 0 else "red"

            table.add_row(
                pos.ticker,
                pos.side,
                str(pos.quantity),
                f"${pos.avg_entry_price:.2f}",
                f"${pos.current_price:.2f}",
                f"${pos.market_value:.2f}",
                f"[{pl_color}]${pos.unrealized_pl:.2f}[/]",
                f"[{pl_color}]{pos.unrealized_pl_pct:.2f}%[/]",
            )

        console.print(table)

        # Summary
        total_value = sum(p.market_value for p in positions)
        total_pl = sum(p.unrealized_pl for p in positions)
        pl_color = "green" if total_pl >= 0 else "red"

        console.print(f"\n[bold]Total Market Value:[/] ${total_value:,.2f}")
        console.print(f"[bold]Total Unrealized P&L:[/] [{pl_color}]${total_pl:,.2f}[/]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@main.command()
@click.option("--days", default=7, help="Look back period in days")
@click.option("--live", is_flag=True, help="Use live trading (default: paper)")
@click.option("--auto", is_flag=True, help="Auto-execute trades")
@click.option("--dry-run", is_flag=True, default=True, help="Dry run (no execution)")
def trade(days, live, auto, dry_run):
    """Execute trades based on signals"""
    asyncio.run(_execute_trades(days, live, auto, dry_run))


async def _execute_trades(days, live, auto, dry_run):
    """Internal async function to execute trades"""
    mode = "LIVE" if live else "PAPER"
    console.print(f"[bold cyan]Trading Mode: {mode}[/]")

    if not dry_run and not auto:
        console.print("[red]Error: --auto flag required to execute real trades[/]")
        return

    if live and not dry_run:
        if not click.confirm("⚠️  WARNING: This will execute LIVE trades with real money. Continue?"):
            console.print("[yellow]Aborted[/]")
            return

    try:
        # Get Alpaca client
        alpaca_client = get_alpaca_client(paper=not live)

        # Initialize risk manager
        risk_manager = RiskManager(
            max_position_size_pct=10.0,
            max_portfolio_risk_pct=2.0,
            max_total_exposure_pct=80.0,
            max_positions=20,
            min_confidence=0.65,
        )

        # Initialize strategy
        strategy = TradingStrategy(
            alpaca_client=alpaca_client,
            risk_manager=risk_manager,
            auto_execute=auto and not dry_run,
        )

        # Get signals from database
        console.print(f"[yellow]Fetching signals from last {days} days...[/]")
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)

        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = db.client.table("trading_signals").select("*")
        query = query.eq("is_active", True)
        query = query.gte("generated_at", cutoff_date.isoformat())
        query = query.order("confidence_score", desc=True)

        response = query.execute()
        signals_data = response.data

        if not signals_data:
            console.print("[yellow]No active signals found[/]")
            return

        # Convert to TradingSignal objects
        signals = []
        for data in signals_data:
            signal = TradingSignal(
                id=data["id"],
                ticker=data["ticker"],
                asset_name=data.get("asset_name", ""),
                signal_type=SignalType(data["signal_type"]),
                signal_strength=SignalStrength(data["signal_strength"]),
                confidence_score=data["confidence_score"],
                target_price=Decimal(str(data["target_price"])) if data.get("target_price") else None,
                stop_loss=Decimal(str(data["stop_loss"])) if data.get("stop_loss") else None,
                take_profit=Decimal(str(data["take_profit"])) if data.get("take_profit") else None,
                politician_activity_count=data.get("politician_activity_count", 0),
                buy_sell_ratio=data.get("buy_sell_ratio", 0.0),
                features=data.get("features", {}),
            )
            signals.append(signal)

        console.print(f"[green]Found {len(signals)} signals[/]")

        # Evaluate signals
        console.print("[yellow]Evaluating signals...[/]")
        recommendations = strategy.evaluate_signals(signals, dry_run=dry_run)

        if not recommendations:
            console.print("[yellow]No trades recommended[/]")
            return

        # Display recommendations
        table = Table(title="Trade Recommendations", box=box.ROUNDED)
        table.add_column("Ticker", style="cyan")
        table.add_column("Signal", style="bold")
        table.add_column("Confidence", justify="right")
        table.add_column("Shares", justify="right")
        table.add_column("Cost", justify="right")
        table.add_column("Status", style="magenta")
        table.add_column("Reason")

        for rec in recommendations:
            signal_color = "green" if rec["signal"] in ["buy", "strong_buy"] else "red"
            status_color = "green" if rec.get("executed") else "yellow"

            table.add_row(
                rec["ticker"],
                f"[{signal_color}]{rec['signal'].upper()}[/]",
                f"{rec['confidence']:.1%}",
                str(rec.get("shares", "N/A")),
                f"${rec.get('estimated_cost', 0):,.2f}",
                f"[{status_color}]{'EXECUTED' if rec.get('executed') else 'PENDING'}[/]",
                rec.get("reason", ""),
            )

        console.print(table)

        if dry_run:
            console.print("\n[bold yellow]DRY RUN - No trades executed[/]")
        elif auto:
            executed_count = sum(1 for r in recommendations if r.get("executed"))
            console.print(f"\n[bold green]Executed {executed_count} trades[/]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        logger.exception("Trading error")
        raise


@main.command()
@click.option("--live", is_flag=True, help="Use live trading (default: paper)")
def monitor(live):
    """Monitor positions and execute risk management"""
    try:
        # Get Alpaca client
        alpaca_client = get_alpaca_client(paper=not live)

        # Initialize risk manager
        risk_manager = RiskManager()

        # Initialize strategy
        strategy = TradingStrategy(
            alpaca_client=alpaca_client,
            risk_manager=risk_manager,
            auto_execute=False,  # Don't auto-close positions without confirmation
        )

        # Monitor positions
        console.print("[yellow]Monitoring positions...[/]")
        actions = strategy.monitor_positions()

        if not actions:
            console.print("[green]All positions within risk parameters[/]")
        else:
            table = Table(title="Risk Management Actions", box=box.ROUNDED)
            table.add_column("Ticker", style="cyan")
            table.add_column("Action", style="bold")
            table.add_column("Reason")
            table.add_column("Executed", style="magenta")

            for action in actions:
                table.add_row(
                    action["ticker"],
                    action["action"].upper(),
                    action["reason"],
                    "YES" if action.get("executed") else "NO",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@main.command()
@click.option("--live", is_flag=True, help="Use live trading (default: paper)")
def portfolio(live):
    """Show portfolio summary with risk metrics"""
    try:
        # Get Alpaca client
        alpaca_client = get_alpaca_client(paper=not live)

        # Initialize risk manager
        risk_manager = RiskManager()

        # Initialize strategy
        strategy = TradingStrategy(
            alpaca_client=alpaca_client,
            risk_manager=risk_manager,
        )

        # Get portfolio summary
        summary = strategy.get_portfolio_summary()

        # Display portfolio info
        mode = "LIVE TRADING" if live else "PAPER TRADING"
        portfolio_info = f"""
[bold]Portfolio Value:[/] ${summary['portfolio']['value']:,.2f}
[bold]Cash:[/] ${summary['portfolio']['cash']:,.2f}
[bold]Buying Power:[/] ${summary['portfolio']['buying_power']:,.2f}

[bold]Open Positions:[/] {summary['positions']['open']}
[bold]Long Positions:[/] {summary['positions']['long']}
[bold]Short Positions:[/] {summary['positions']['short']}
        """.strip()

        console.print(Panel.fit(portfolio_info, title=f"[bold cyan]{mode}[/]", border_style="cyan"))

        # Display risk metrics
        risk_metrics = summary['risk_metrics']
        risk_info = f"""
[bold]Total Exposure:[/] ${risk_metrics['total_exposure']:,.2f} ({risk_metrics['exposure_pct']:.1f}%)
[bold]Unrealized P&L:[/] ${risk_metrics['total_unrealized_pl']:,.2f} ({risk_metrics['unrealized_pl_pct']:.1f}%)
[bold]Largest Position:[/] ${risk_metrics['largest_position_value']:,.2f} ({risk_metrics['largest_position_pct']:.1f}%)
[bold]Win Rate:[/] {risk_metrics['win_rate']:.1f}% ({risk_metrics['winning_positions']}/{risk_metrics['total_positions']})
[bold]Cash %:[/] {risk_metrics['cash_pct']:.1f}%
        """.strip()

        console.print(Panel.fit(risk_info, title="[bold yellow]Risk Metrics[/]", border_style="yellow"))

        # Display positions
        if summary['positions_detail']:
            table = Table(title="Position Details", box=box.ROUNDED)
            table.add_column("Ticker", style="cyan")
            table.add_column("Qty", justify="right")
            table.add_column("Entry", justify="right")
            table.add_column("Current", justify="right")
            table.add_column("Value", justify="right")
            table.add_column("P&L", justify="right")
            table.add_column("P&L %", justify="right")

            for pos in summary['positions_detail']:
                pl_color = "green" if pos['unrealized_pl'] >= 0 else "red"

                table.add_row(
                    pos['ticker'],
                    str(pos['quantity']),
                    f"${pos['avg_entry_price']:.2f}",
                    f"${pos['current_price']:.2f}",
                    f"${pos['market_value']:,.2f}",
                    f"[{pl_color}]${pos['unrealized_pl']:,.2f}[/]",
                    f"[{pl_color}]{pos['unrealized_pl_pct']:.2f}%[/]",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@main.command()
@click.argument("ticker")
@click.argument("quantity", type=int)
@click.option("--side", type=click.Choice(["buy", "sell"]), required=True)
@click.option("--order-type", type=click.Choice(["market", "limit"]), default="market")
@click.option("--limit-price", type=float, help="Limit price for limit orders")
@click.option("--live", is_flag=True, help="Use live trading (default: paper)")
def order(ticker, quantity, side, order_type, limit_price, live):
    """Place a manual order"""
    try:
        mode = "LIVE" if live else "PAPER"
        console.print(f"[bold cyan]Trading Mode: {mode}[/]")

        if live:
            if not click.confirm(f"⚠️  Execute {side.upper()} {quantity} {ticker} in LIVE account?"):
                console.print("[yellow]Aborted[/]")
                return

        client = get_alpaca_client(paper=not live)

        if order_type == "market":
            order = client.place_market_order(ticker, quantity, side)
            console.print(f"[green]Market order placed: {order.alpaca_order_id}[/]")
        elif order_type == "limit":
            if not limit_price:
                console.print("[red]Error: --limit-price required for limit orders[/]")
                return
            order = client.place_limit_order(ticker, quantity, side, Decimal(str(limit_price)))
            console.print(f"[green]Limit order placed: {order.alpaca_order_id}[/]")

        console.print(f"[bold]Order ID:[/] {order.alpaca_order_id}")
        console.print(f"[bold]Status:[/] {order.status.value}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


if __name__ == "__main__":
    main()
