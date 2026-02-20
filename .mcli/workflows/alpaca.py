#!/usr/bin/env python3
# @description: Alpaca trading account management
# @version: 1.0.0
# @group: workflows

"""
Alpaca command group for mcli.

Manages the Alpaca paper/live trading account via the alpaca-account
Supabase Edge Function. All API calls proxy through the edge function
since Alpaca credentials are stored as Supabase secrets.
"""
import os
import subprocess
from pathlib import Path

import click
import httpx

from mcli.lib.logger.logger import get_logger

logger = get_logger()

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://uljsqvwkomdrlnofmlad.supabase.co"
)
EDGE_FUNCTION = "alpaca-account"


def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)


def get_supabase_key() -> str | None:
    """Get Supabase service role key."""
    load_env()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        try:
            result = subprocess.run(
                ["lsh", "get", "SUPABASE_SERVICE_ROLE_KEY"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                key = result.stdout.strip()
        except FileNotFoundError:
            pass
    return key


def call_edge_function(action: str, extra_params: dict | None = None) -> dict:
    """Call the alpaca-account Supabase edge function."""
    key = get_supabase_key()
    if not key:
        click.echo(click.style("Error: No Supabase service role key found", fg="red"))
        click.echo("Set SUPABASE_SERVICE_ROLE_KEY or configure lsh")
        raise SystemExit(1)

    url = f"{SUPABASE_URL}/functions/v1/{EDGE_FUNCTION}"
    payload = {"action": action}
    if extra_params:
        payload.update(extra_params)

    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        data = resp.json()
        if not data.get("success", False):
            error = data.get("error", "Unknown error")
            click.echo(click.style(f"API Error: {error}", fg="red"))
            raise SystemExit(1)
        return data
    except httpx.HTTPError as e:
        click.echo(click.style(f"HTTP Error: {e}", fg="red"))
        raise SystemExit(1)


def format_currency(value: float) -> str:
    """Format a number as USD currency."""
    if value < 0:
        return click.style(f"-${abs(value):,.2f}", fg="red")
    return click.style(f"${value:,.2f}", fg="green")


def format_pct(value: float) -> str:
    """Format a number as a percentage."""
    pct = value * 100
    color = "green" if pct >= 0 else "red"
    return click.style(f"{pct:+.2f}%", fg=color)


@click.group()
def cli():
    """Alpaca trading account management."""
    pass


@cli.command()
def account():
    """Show Alpaca account summary."""
    data = call_edge_function("get-account")
    acct = data.get("account", {})

    click.echo(click.style("\n  Alpaca Account Summary", bold=True))
    click.echo(f"  {'─' * 40}")
    click.echo(f"  Status:           {acct.get('status', 'N/A')}")
    click.echo(f"  Trading Mode:     {data.get('tradingMode', 'N/A')}")
    click.echo(f"  Portfolio Value:   {format_currency(acct.get('portfolio_value', 0))}")
    click.echo(f"  Equity:           {format_currency(acct.get('equity', 0))}")
    click.echo(f"  Cash:             {format_currency(acct.get('cash', 0))}")
    click.echo(f"  Buying Power:     {format_currency(acct.get('buying_power', 0))}")
    click.echo(f"  Long Market Value: {format_currency(acct.get('long_market_value', 0))}")
    click.echo(f"  Short Market Value:{format_currency(acct.get('short_market_value', 0))}")
    click.echo(f"  {'─' * 40}")

    flags = []
    if acct.get("pattern_day_trader"):
        flags.append("PDT")
    if acct.get("trading_blocked"):
        flags.append("TRADING BLOCKED")
    if acct.get("account_blocked"):
        flags.append("ACCOUNT BLOCKED")
    if flags:
        click.echo(f"  Flags:            {click.style(', '.join(flags), fg='yellow')}")
    click.echo()


@cli.command()
@click.option("--side", type=click.Choice(["all", "long", "short"]), default="all",
              help="Filter by position side")
def positions(side):
    """List all Alpaca positions."""
    data = call_edge_function("get-positions")
    positions_list = data.get("positions", [])

    if side != "all":
        positions_list = [p for p in positions_list if p.get("side") == side]

    if not positions_list:
        click.echo(f"\n  No {side} positions found.\n")
        return

    # Sort by absolute market value descending
    positions_list.sort(key=lambda p: abs(p.get("market_value", 0)), reverse=True)

    total_value = sum(p.get("market_value", 0) for p in positions_list)
    total_pl = sum(p.get("unrealized_pl", 0) for p in positions_list)
    shorts = [p for p in positions_list if p.get("side") == "short"]
    longs = [p for p in positions_list if p.get("side") == "long"]

    click.echo(click.style(f"\n  Alpaca Positions ({len(positions_list)} total)", bold=True))
    click.echo(f"  Long: {len(longs)}  |  Short: {len(shorts)}  |  P&L: {format_currency(total_pl)}")
    click.echo(f"  {'─' * 85}")
    click.echo(f"  {'Symbol':<8} {'Side':<6} {'Qty':>8} {'Entry':>10} {'Current':>10} {'Market Value':>14} {'Unrealized P&L':>16}")
    click.echo(f"  {'─' * 85}")

    for p in positions_list:
        sym = p.get("symbol", "?")
        s = p.get("side", "?")
        qty = p.get("qty", 0)
        entry = p.get("avg_entry_price", 0)
        current = p.get("current_price", 0)
        mv = p.get("market_value", 0)
        pl = p.get("unrealized_pl", 0)

        side_color = "green" if s == "long" else "red"
        pl_color = "green" if pl >= 0 else "red"

        click.echo(
            f"  {sym:<8} "
            f"{click.style(s, fg=side_color):<15} "
            f"{qty:>8.0f} "
            f"{entry:>10.2f} "
            f"{current:>10.2f} "
            f"{'${:,.2f}'.format(abs(mv)):>14} "
            f"{click.style('${:,.2f}'.format(pl), fg=pl_color):>25}"
        )

    click.echo(f"  {'─' * 85}")
    click.echo(f"  {'Total':<8} {'':6} {'':>8} {'':>10} {'':>10} "
               f"{'${:,.2f}'.format(abs(total_value)):>14} "
               f"{format_currency(total_pl):>25}")
    click.echo()


@cli.command("close-position")
@click.argument("symbol")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def close_position(symbol, yes):
    """Close a specific position by symbol."""
    symbol = symbol.upper()

    if not yes:
        click.confirm(f"Close position in {symbol}?", abort=True)

    data = call_edge_function("close-position", {"symbol": symbol})
    order = data.get("order", {})
    click.echo(click.style(f"\n  Position {symbol} close order submitted", fg="green"))
    click.echo(f"  Order ID: {order.get('id', 'N/A')}")
    click.echo(f"  Side: {order.get('side', 'N/A')}")
    click.echo(f"  Qty: {order.get('qty', 'N/A')}")
    click.echo(f"  Status: {order.get('status', 'N/A')}")
    click.echo()


@cli.command("close-shorts")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def close_shorts(yes):
    """Close all short positions."""
    # First show what would be closed
    pos_data = call_edge_function("get-positions")
    positions_list = pos_data.get("positions", [])
    shorts = [p for p in positions_list if p.get("side") == "short"]

    if not shorts:
        click.echo(click.style("\n  No short positions found.\n", fg="green"))
        return

    total_value = sum(abs(p.get("market_value", 0)) for p in shorts)
    click.echo(click.style(f"\n  Found {len(shorts)} short positions (${total_value:,.2f})", bold=True))
    for p in shorts:
        click.echo(f"    {p['symbol']:<8} qty={p['qty']:>8.0f}  value=${abs(p['market_value']):>12,.2f}")

    if not yes:
        click.confirm(f"\n  Close all {len(shorts)} short positions?", abort=True)

    data = call_edge_function("close-all-shorts")
    results = data.get("results", [])
    closed = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    click.echo(click.style(f"\n  Closed {len(closed)}/{len(results)} short positions", fg="green"))
    if failed:
        click.echo(click.style(f"  Failed: {len(failed)}", fg="red"))
        for f in failed:
            click.echo(f"    {f['symbol']}: {f.get('error', 'unknown')}")
    click.echo()


@cli.command()
@click.option("--status", type=click.Choice(["all", "open", "closed", "filled"]),
              default="all", help="Filter by order status")
@click.option("--limit", default=20, help="Number of orders to show")
def orders(status, limit):
    """Show recent Alpaca orders."""
    data = call_edge_function("get-orders", {"status": status, "limit": limit})
    orders_list = data.get("orders", [])

    if not orders_list:
        click.echo(f"\n  No {status} orders found.\n")
        return

    click.echo(click.style(f"\n  Recent Orders ({len(orders_list)})", bold=True))
    click.echo(f"  {'─' * 90}")
    click.echo(f"  {'Symbol':<8} {'Side':<6} {'Type':<8} {'Qty':>6} {'Filled':>6} {'Price':>10} {'Status':<12} {'Submitted'}")
    click.echo(f"  {'─' * 90}")

    for o in orders_list:
        sym = o.get("symbol", "?")
        side = o.get("side", "?")
        otype = o.get("type", "?")
        qty = o.get("qty", "0")
        filled = o.get("filled_qty", "0")
        price = o.get("filled_avg_price") or "-"
        if price != "-":
            price = f"${float(price):,.2f}"
        ostatus = o.get("status", "?")
        submitted = (o.get("submitted_at") or "")[:19]

        side_color = "green" if side == "buy" else "red"
        status_color = "green" if ostatus == "filled" else ("yellow" if ostatus in ("new", "partially_filled", "accepted") else "white")

        click.echo(
            f"  {sym:<8} "
            f"{click.style(side, fg=side_color):<15} "
            f"{otype:<8} "
            f"{qty:>6} "
            f"{filled:>6} "
            f"{price:>10} "
            f"{click.style(ostatus, fg=status_color):<21} "
            f"{submitted}"
        )

    click.echo(f"  {'─' * 90}\n")


@cli.command()
def health():
    """Check Alpaca API health and circuit breaker status."""
    data = call_edge_function("health-check")

    healthy = data.get("healthy", False)
    latency = data.get("latency", 0)
    cb = data.get("circuitBreaker", {})

    status_icon = click.style("HEALTHY", fg="green") if healthy else click.style("UNHEALTHY", fg="red")

    click.echo(click.style("\n  Alpaca API Health", bold=True))
    click.echo(f"  {'─' * 40}")
    click.echo(f"  Status:          {status_icon}")
    click.echo(f"  Latency:         {latency}ms")
    click.echo(f"  Trading Mode:    {data.get('tradingMode', 'N/A')}")
    click.echo(f"  Circuit Breaker: {cb.get('state', 'N/A')}")
    click.echo(f"  Failures:        {cb.get('failures', 0)}")
    click.echo(f"  Last Success:    {cb.get('lastSuccess', 'N/A')}")
    click.echo()
