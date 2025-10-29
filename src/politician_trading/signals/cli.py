"""
CLI for politician trading signal generation
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich import box
from datetime import datetime
import logging

from politician_trading.signals.signal_generator import SignalGenerator
from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def main():
    """Politician Trading Signal Generator"""
    pass


@main.command()
@click.option("--days", default=30, help="Look back period in days")
@click.option("--min-confidence", default=0.6, help="Minimum confidence threshold")
@click.option("--fetch-market-data/--no-market-data", default=True, help="Fetch market data")
@click.option("--output", type=click.Choice(["table", "json"]), default="table", help="Output format")
def generate(days, min_confidence, fetch_market_data, output):
    """Generate trading signals from politician trading data"""
    asyncio.run(_generate_signals(days, min_confidence, fetch_market_data, output))


async def _generate_signals(days, min_confidence, fetch_market_data, output):
    """Internal async function to generate signals"""
    console.print(f"[bold cyan]Generating signals from last {days} days...[/]")

    try:
        # Initialize database client
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)

        # Fetch recent disclosures
        console.print("[yellow]Fetching politician trading disclosures...[/]")
        cutoff_date = datetime.utcnow()
        from datetime import timedelta
        cutoff_date = cutoff_date - timedelta(days=days)

        # Query disclosures
        query = db.client.table("trading_disclosures").select("*")
        query = query.gte("transaction_date", cutoff_date.isoformat())
        query = query.order("transaction_date", desc=True)

        response = query.execute()
        disclosures = response.data

        if not disclosures:
            console.print("[red]No disclosures found in the specified period[/]")
            return

        console.print(f"[green]Found {len(disclosures)} disclosures[/]")

        # Group by ticker
        disclosures_by_ticker = {}
        for d in disclosures:
            ticker = d.get("asset_ticker")
            if ticker:
                if ticker not in disclosures_by_ticker:
                    disclosures_by_ticker[ticker] = []
                disclosures_by_ticker[ticker].append(d)

        console.print(f"[green]Analyzing {len(disclosures_by_ticker)} unique tickers[/]")

        # Generate signals
        generator = SignalGenerator(
            model_version="v1.0",
            use_ml=False,  # Use heuristics for now
            confidence_threshold=min_confidence,
        )

        signals = generator.generate_signals(disclosures_by_ticker, fetch_market_data)

        if not signals:
            console.print("[yellow]No signals generated meeting confidence threshold[/]")
            return

        # Sort by confidence
        signals.sort(key=lambda s: s.confidence_score, reverse=True)

        # Output signals
        if output == "table":
            _display_signals_table(signals)
        else:
            _display_signals_json(signals)

        # Save signals to database
        console.print("[yellow]Saving signals to database...[/]")
        await _save_signals(db, signals)
        console.print("[green]Signals saved successfully![/]")

    except Exception as e:
        console.print(f"[red]Error generating signals: {e}[/]")
        logger.exception("Signal generation error")
        raise


def _display_signals_table(signals):
    """Display signals in a table format"""
    table = Table(title="Trading Signals", box=box.ROUNDED)

    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Signal", style="bold")
    table.add_column("Strength", style="magenta")
    table.add_column("Confidence", justify="right")
    table.add_column("Politicians", justify="right")
    table.add_column("B/S Ratio", justify="right")
    table.add_column("Target Price", justify="right")

    for signal in signals:
        # Color-code signal type
        if signal.signal_type.value in ["buy", "strong_buy"]:
            signal_color = "green"
        elif signal.signal_type.value in ["sell", "strong_sell"]:
            signal_color = "red"
        else:
            signal_color = "yellow"

        signal_text = f"[{signal_color}]{signal.signal_type.value.upper()}[/]"

        table.add_row(
            signal.ticker,
            signal_text,
            signal.signal_strength.value,
            f"{signal.confidence_score:.1%}",
            str(signal.politician_activity_count),
            f"{signal.buy_sell_ratio:.2f}",
            f"${signal.target_price:.2f}" if signal.target_price else "N/A",
        )

    console.print(table)


def _display_signals_json(signals):
    """Display signals in JSON format"""
    import json

    signals_data = []
    for signal in signals:
        signals_data.append({
            "ticker": signal.ticker,
            "signal_type": signal.signal_type.value,
            "signal_strength": signal.signal_strength.value,
            "confidence_score": signal.confidence_score,
            "politician_activity_count": signal.politician_activity_count,
            "buy_sell_ratio": signal.buy_sell_ratio,
            "target_price": float(signal.target_price) if signal.target_price else None,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
            "generated_at": signal.generated_at.isoformat(),
        })

    console.print(json.dumps(signals_data, indent=2))


async def _save_signals(db: SupabaseClient, signals):
    """Save signals to database"""
    for signal in signals:
        try:
            data = {
                "ticker": signal.ticker,
                "asset_name": signal.asset_name,
                "signal_type": signal.signal_type.value,
                "signal_strength": signal.signal_strength.value,
                "confidence_score": signal.confidence_score,
                "target_price": float(signal.target_price) if signal.target_price else None,
                "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
                "take_profit": float(signal.take_profit) if signal.take_profit else None,
                "generated_at": signal.generated_at.isoformat(),
                "valid_until": signal.valid_until.isoformat() if signal.valid_until else None,
                "model_version": signal.model_version,
                "politician_activity_count": signal.politician_activity_count,
                "total_transaction_volume": float(signal.total_transaction_volume) if signal.total_transaction_volume else None,
                "buy_sell_ratio": signal.buy_sell_ratio,
                "features": signal.features,
                "disclosure_ids": signal.disclosure_ids,
                "is_active": signal.is_active,
                "notes": signal.notes,
            }

            db.client.table("trading_signals").insert(data).execute()
        except Exception as e:
            logger.error(f"Error saving signal for {signal.ticker}: {e}")


@main.command()
@click.option("--days", default=7, help="Show signals from last N days")
def list(days):
    """List active trading signals"""
    asyncio.run(_list_signals(days))


async def _list_signals(days):
    """Internal async function to list signals"""
    try:
        # Initialize database client
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)

        # Fetch recent signals
        from datetime import timedelta
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

        # Convert to TradingSignal objects for display
        from src.models import TradingSignal, SignalType, SignalStrength
        from decimal import Decimal

        signals = []
        for data in signals_data:
            signal = TradingSignal(
                ticker=data["ticker"],
                asset_name=data.get("asset_name", ""),
                signal_type=SignalType(data["signal_type"]),
                signal_strength=SignalStrength(data["signal_strength"]),
                confidence_score=data["confidence_score"],
                target_price=Decimal(str(data["target_price"])) if data.get("target_price") else None,
                politician_activity_count=data.get("politician_activity_count", 0),
                buy_sell_ratio=data.get("buy_sell_ratio", 0.0),
            )
            signals.append(signal)

        _display_signals_table(signals)

    except Exception as e:
        console.print(f"[red]Error listing signals: {e}[/]")
        logger.exception("Signal listing error")


if __name__ == "__main__":
    main()
