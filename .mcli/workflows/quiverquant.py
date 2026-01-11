#!/usr/bin/env python3
# @description: QuiverQuant API commands
# @version: 1.0.0
# @group: workflows

"""
QuiverQuant command group for mcli.

Commands for interacting with QuiverQuant congressional trading API.
"""
import click
import httpx
import subprocess
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table

console = Console()

# API Configuration
QUIVERQUANT_API_URL = "https://api.quiverquant.com/beta/live/congresstrading"


def get_api_key() -> Optional[str]:
    """Get QuiverQuant API key from lsh."""
    try:
        result = subprocess.run(
            ["lsh", "get", "QUIVERQUANT_API_KEY"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


@click.group(name="quiverquant")
def app():
    """
    QuiverQuant congressional trading API commands.

    Test connection and fetch trading data from QuiverQuant.
    """
    pass


@app.command("test")
def test_connection():
    """
    Test connection to QuiverQuant API.

    Example: mcli run quiverquant test
    """
    api_key = get_api_key()

    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found in lsh[/red]")
        console.print("Set it with: lsh set QUIVERQUANT_API_KEY <your_key>")
        raise SystemExit(1)

    console.print(f"[cyan]Testing QuiverQuant API connection...[/cyan]")
    console.print(f"[dim]API Key: {api_key[:8]}...{api_key[-4:]}[/dim]")

    try:
        response = httpx.get(
            QUIVERQUANT_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            },
            timeout=30.0,
            params={"pagesize": 1}  # Just get 1 record to test
        )

        if response.status_code == 200:
            data = response.json()
            record_count = len(data) if isinstance(data, list) else 0
            console.print(f"[green]Success: API connection works[/green]")
            console.print(f"  Response: {record_count} record(s)")
            if record_count > 0 and isinstance(data, list):
                sample = data[0]
                console.print(f"  Sample fields: {list(sample.keys())[:5]}...")
        elif response.status_code == 401:
            console.print(f"[red]Error: Unauthorized (401)[/red]")
            console.print("  API key may be invalid or expired")
            raise SystemExit(1)
        elif response.status_code == 403:
            console.print(f"[red]Error: Forbidden (403)[/red]")
            console.print("  API access denied - check subscription")
            raise SystemExit(1)
        else:
            console.print(f"[red]Error: HTTP {response.status_code}[/red]")
            console.print(f"  Response: {response.text[:200]}")
            raise SystemExit(1)

    except httpx.TimeoutException:
        console.print("[red]Error: Request timed out[/red]")
        raise SystemExit(1)
    except httpx.RequestError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("fetch")
@click.option("--limit", "-l", default=20, help="Number of records to fetch")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
def fetch_trades(limit: int, output: str):
    """
    Fetch recent congressional trades from QuiverQuant.

    Example: mcli run quiverquant fetch --limit 10
    """
    api_key = get_api_key()

    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Fetching {limit} trades from QuiverQuant...[/cyan]")

    try:
        response = httpx.get(
            QUIVERQUANT_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            },
            timeout=30.0,
            params={"pagesize": limit}
        )

        if response.status_code != 200:
            console.print(f"[red]Error: HTTP {response.status_code}[/red]")
            raise SystemExit(1)

        data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            console.print("[yellow]No trades found[/yellow]")
            return

        if output == "json":
            import json
            console.print(json.dumps(data[:limit], indent=2))
        else:
            table = Table(title=f"QuiverQuant Congressional Trades ({len(data)} records)")
            table.add_column("Date", style="cyan", width=12)
            table.add_column("Representative", style="green", width=20)
            table.add_column("Party", width=5)
            table.add_column("Ticker", style="yellow", width=8)
            table.add_column("Type", width=10)
            table.add_column("Amount", width=20)

            for trade in data[:limit]:
                tx_date = trade.get("TransactionDate", "")[:10] if trade.get("TransactionDate") else "-"
                rep = trade.get("Representative", "-")[:18]
                party = trade.get("Party", "-")
                ticker = trade.get("Ticker", "-")
                tx_type = trade.get("Transaction", "-")
                amount = trade.get("Range", trade.get("Amount", "-"))

                table.add_row(tx_date, rep, party, ticker, tx_type, str(amount))

            console.print(table)
            console.print(f"\n[dim]Showing {min(limit, len(data))} of {len(data)} trades[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("stats")
def show_stats():
    """
    Show statistics about QuiverQuant data.

    Example: mcli run quiverquant stats
    """
    api_key = get_api_key()

    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Fetching QuiverQuant stats...[/cyan]")

    try:
        response = httpx.get(
            QUIVERQUANT_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            },
            timeout=60.0,
            params={"pagesize": 1000}  # Get a larger sample for stats
        )

        if response.status_code != 200:
            console.print(f"[red]Error: HTTP {response.status_code}[/red]")
            raise SystemExit(1)

        data = response.json()

        if not isinstance(data, list):
            console.print("[yellow]Unexpected response format[/yellow]")
            return

        # Calculate stats
        total_trades = len(data)
        parties = {}
        tickers = {}
        tx_types = {}
        representatives = set()

        for trade in data:
            party = trade.get("Party", "Unknown")
            parties[party] = parties.get(party, 0) + 1

            ticker = trade.get("Ticker", "Unknown")
            tickers[ticker] = tickers.get(ticker, 0) + 1

            tx_type = trade.get("Transaction", "Unknown")
            tx_types[tx_type] = tx_types.get(tx_type, 0) + 1

            rep = trade.get("Representative", "")
            if rep:
                representatives.add(rep)

        console.print("\n[bold]QuiverQuant Statistics[/bold]")
        console.print("-" * 40)
        console.print(f"Total trades: {total_trades}")
        console.print(f"Unique representatives: {len(representatives)}")

        console.print("\n[bold]By Party:[/bold]")
        for party, count in sorted(parties.items(), key=lambda x: -x[1]):
            console.print(f"  {party}: {count} ({count/total_trades*100:.1f}%)")

        console.print("\n[bold]By Transaction Type:[/bold]")
        for tx, count in sorted(tx_types.items(), key=lambda x: -x[1]):
            console.print(f"  {tx}: {count}")

        console.print("\n[bold]Top 10 Tickers:[/bold]")
        for ticker, count in sorted(tickers.items(), key=lambda x: -x[1])[:10]:
            console.print(f"  {ticker}: {count}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("health")
def health_check():
    """
    Quick health check of QuiverQuant API.

    Example: mcli run quiverquant health
    """
    api_key = get_api_key()

    checks = []

    # Check API key
    if api_key:
        checks.append(("API Key", "configured", True))
    else:
        checks.append(("API Key", "missing", False))
        console.print("[red]API Key: MISSING[/red]")
        console.print("Set with: lsh set QUIVERQUANT_API_KEY <key>")
        raise SystemExit(1)

    # Check API connectivity
    try:
        response = httpx.get(
            QUIVERQUANT_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
            params={"pagesize": 1}
        )
        if response.status_code == 200:
            checks.append(("API Connection", "healthy", True))
        else:
            checks.append(("API Connection", f"HTTP {response.status_code}", False))
    except Exception as e:
        checks.append(("API Connection", str(e)[:30], False))

    # Display results
    console.print("\n[bold]QuiverQuant Health Check[/bold]")
    console.print("-" * 40)

    all_healthy = True
    for name, status, healthy in checks:
        if healthy:
            console.print(f"[green]OK[/green] {name}: {status}")
        else:
            console.print(f"[red]FAIL[/red] {name}: {status}")
            all_healthy = False

    if all_healthy:
        console.print("\n[green]All checks passed[/green]")
    else:
        console.print("\n[red]Some checks failed[/red]")
        raise SystemExit(1)
