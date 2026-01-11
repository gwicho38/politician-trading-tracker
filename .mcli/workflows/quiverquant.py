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


def get_supabase_config():
    """Get Supabase configuration from lsh."""
    config = {}
    for key in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
        try:
            result = subprocess.run(
                ["lsh", "get", key],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                config[key] = result.stdout.strip()
        except Exception:
            pass
    return config


def fetch_quiverquant_data(api_key: str, limit: int = 1000):
    """Fetch data from QuiverQuant API."""
    response = httpx.get(
        QUIVERQUANT_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        },
        timeout=60.0,
        params={"pagesize": limit}
    )
    if response.status_code == 200:
        return response.json()
    return []


def fetch_supabase_data(config: dict, table: str, select: str = "*", limit: int = 1000, filters: dict = None, order: str = None):
    """Fetch data from Supabase with optional filters."""
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return []

    params = {"select": select, "limit": limit}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order

    response = httpx.get(
        f"{url}/rest/v1/{table}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        params=params,
        timeout=30.0
    )
    if response.status_code == 200:
        return response.json()
    return []


@app.command("validate-politicians")
def validate_politicians():
    """
    Compare politician data between QuiverQuant and app database.

    Example: mcli run quiverquant validate-politicians
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Fetching data from both sources...[/cyan]")

    # Fetch QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key)
    qq_politicians = {}
    for trade in qq_data:
        rep = trade.get("Representative", "")
        if rep:
            if rep not in qq_politicians:
                qq_politicians[rep] = {
                    "name": rep,
                    "bioguide_id": trade.get("BioGuideID"),
                    "party": trade.get("Party"),
                    "chamber": trade.get("House"),
                    "trade_count": 0
                }
            qq_politicians[rep]["trade_count"] += 1

    # Fetch app database politicians
    app_politicians = fetch_supabase_data(
        config, "politicians",
        "full_name,bioguide_id,party,chamber,total_trades"
    )
    app_by_name = {p.get("full_name", ""): p for p in app_politicians}
    app_by_bioguide = {p.get("bioguide_id", ""): p for p in app_politicians if p.get("bioguide_id")}

    console.print(f"\n[bold]Politician Comparison[/bold]")
    console.print("-" * 60)
    console.print(f"QuiverQuant unique politicians: [cyan]{len(qq_politicians)}[/cyan]")
    console.print(f"App database politicians: [cyan]{len(app_politicians)}[/cyan]")

    # Find matches and mismatches
    matched_by_name = 0
    matched_by_bioguide = 0
    qq_only = []

    for name, qq_pol in qq_politicians.items():
        bioguide = qq_pol.get("bioguide_id")
        if name in app_by_name:
            matched_by_name += 1
        elif bioguide and bioguide in app_by_bioguide:
            matched_by_bioguide += 1
        else:
            qq_only.append(qq_pol)

    console.print(f"\n[bold]Match Results:[/bold]")
    console.print(f"  Matched by name: [green]{matched_by_name}[/green]")
    console.print(f"  Matched by BioGuide ID: [green]{matched_by_bioguide}[/green]")
    console.print(f"  QuiverQuant only (not in app): [yellow]{len(qq_only)}[/yellow]")

    if qq_only and len(qq_only) <= 20:
        console.print(f"\n[bold]Politicians in QuiverQuant but not in app:[/bold]")
        for pol in sorted(qq_only, key=lambda x: -x["trade_count"])[:10]:
            console.print(f"  {pol['name']} ({pol['party']}) - {pol['trade_count']} trades")

    # Party distribution comparison
    console.print(f"\n[bold]Party Distribution:[/bold]")
    qq_parties = {}
    for pol in qq_politicians.values():
        party = pol.get("party", "Unknown")
        qq_parties[party] = qq_parties.get(party, 0) + 1

    app_parties = {}
    for pol in app_politicians:
        party = pol.get("party", "Unknown")
        if party:
            # Normalize party names
            if party.startswith("D"):
                party = "D"
            elif party.startswith("R"):
                party = "R"
            else:
                party = "I"
        app_parties[party] = app_parties.get(party, 0) + 1

    table = Table()
    table.add_column("Party", style="bold")
    table.add_column("QuiverQuant", justify="right")
    table.add_column("App DB", justify="right")

    all_parties = set(qq_parties.keys()) | set(app_parties.keys())
    for party in sorted([p for p in all_parties if p is not None]):
        qq_count = qq_parties.get(party, 0)
        app_count = app_parties.get(party, 0)
        table.add_row(party, str(qq_count), str(app_count))

    console.print(table)


@app.command("validate-trades")
@click.option("--days", "-d", default=30, help="Number of days to compare")
def validate_trades(days: int):
    """
    Compare recent trades between QuiverQuant and app database.

    Example: mcli run quiverquant validate-trades --days 30
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Comparing trades from last {days} days...[/cyan]")

    # Fetch QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key)

    # Filter to recent trades by TransactionDate
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    qq_recent = [t for t in qq_data if t.get("TransactionDate", "") >= cutoff]

    # Fetch app database trades (status=active, ordered by disclosure_date)
    app_trades = fetch_supabase_data(
        config, "trading_disclosures",
        "asset_ticker,transaction_date,disclosure_date,transaction_type,politician_id",
        limit=2000,
        filters={"status": "eq.active"},
        order="disclosure_date.desc"
    )
    # Filter by transaction_date (the actual trade date, not disclosure date)
    app_recent = [t for t in app_trades if (t.get("transaction_date") or "")[:10] >= cutoff]

    console.print(f"\n[bold]Trade Comparison (last {days} days)[/bold]")
    console.print("-" * 60)
    console.print(f"QuiverQuant trades: [cyan]{len(qq_recent)}[/cyan]")
    console.print(f"App database trades: [cyan]{len(app_recent)}[/cyan]")

    # Compare by ticker
    qq_tickers = {}
    for t in qq_recent:
        ticker = t.get("Ticker", "")
        if ticker:
            qq_tickers[ticker] = qq_tickers.get(ticker, 0) + 1

    app_tickers = {}
    for t in app_recent:
        ticker = t.get("asset_ticker", "")
        if ticker:
            app_tickers[ticker] = app_tickers.get(ticker, 0) + 1

    console.print(f"\n[bold]Top 10 Tickers Comparison:[/bold]")
    table = Table()
    table.add_column("Ticker", style="yellow")
    table.add_column("QuiverQuant", justify="right")
    table.add_column("App DB", justify="right")
    table.add_column("Diff", justify="right")

    # Get top tickers from both sources
    all_tickers = set(list(qq_tickers.keys())[:20]) | set(list(app_tickers.keys())[:20])
    ticker_data = []
    for ticker in all_tickers:
        qq_count = qq_tickers.get(ticker, 0)
        app_count = app_tickers.get(ticker, 0)
        ticker_data.append((ticker, qq_count, app_count, qq_count - app_count))

    # Sort by QuiverQuant count
    ticker_data.sort(key=lambda x: -x[1])

    for ticker, qq_count, app_count, diff in ticker_data[:10]:
        diff_style = "[green]" if diff == 0 else "[yellow]" if abs(diff) <= 2 else "[red]"
        table.add_row(
            ticker,
            str(qq_count),
            str(app_count),
            f"{diff_style}{diff:+d}[/{diff_style.strip('[]')}]"
        )

    console.print(table)

    # Transaction type comparison
    console.print(f"\n[bold]Transaction Type Comparison:[/bold]")
    qq_types = {"Purchase": 0, "Sale": 0}
    for t in qq_recent:
        tx = t.get("Transaction", "")
        if "Purchase" in tx:
            qq_types["Purchase"] += 1
        elif "Sale" in tx:
            qq_types["Sale"] += 1

    app_types = {"Purchase": 0, "Sale": 0}
    for t in app_recent:
        tx = t.get("transaction_type", "")
        if tx and tx.lower() in ["buy", "purchase"]:
            app_types["Purchase"] += 1
        elif tx and tx.lower() in ["sell", "sale"]:
            app_types["Sale"] += 1

    table2 = Table()
    table2.add_column("Type", style="bold")
    table2.add_column("QuiverQuant", justify="right")
    table2.add_column("App DB", justify="right")

    table2.add_row("Purchases/Buys", str(qq_types["Purchase"]), str(app_types["Purchase"]))
    table2.add_row("Sales/Sells", str(qq_types["Sale"]), str(app_types["Sale"]))

    console.print(table2)


@app.command("validate-tickers")
def validate_tickers():
    """
    Compare top traded tickers between QuiverQuant and app database.

    Example: mcli run quiverquant validate-tickers
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Comparing top tickers...[/cyan]")

    # Fetch QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key)
    qq_tickers = {}
    for t in qq_data:
        ticker = t.get("Ticker", "")
        if ticker:
            qq_tickers[ticker] = qq_tickers.get(ticker, 0) + 1

    # Fetch app database trades
    app_trades = fetch_supabase_data(
        config, "trading_disclosures",
        "asset_ticker",
        limit=5000
    )
    app_tickers = {}
    for t in app_trades:
        ticker = t.get("asset_ticker", "")
        if ticker:
            app_tickers[ticker] = app_tickers.get(ticker, 0) + 1

    console.print(f"\n[bold]Top Tickers Comparison[/bold]")
    console.print("-" * 60)
    console.print(f"QuiverQuant unique tickers: [cyan]{len(qq_tickers)}[/cyan]")
    console.print(f"App database unique tickers: [cyan]{len(app_tickers)}[/cyan]")

    # Get top 20 from each
    qq_top = sorted(qq_tickers.items(), key=lambda x: -x[1])[:20]
    app_top = sorted(app_tickers.items(), key=lambda x: -x[1])[:20]

    console.print(f"\n[bold]Top 20 Tickers Side-by-Side:[/bold]")
    table = Table()
    table.add_column("#", style="dim", width=3)
    table.add_column("QuiverQuant", style="yellow", width=12)
    table.add_column("QQ Count", justify="right", width=8)
    table.add_column("App DB", style="cyan", width=12)
    table.add_column("App Count", justify="right", width=8)
    table.add_column("Match", width=6)

    for i in range(20):
        qq_ticker = qq_top[i][0] if i < len(qq_top) else "-"
        qq_count = qq_top[i][1] if i < len(qq_top) else 0
        app_ticker = app_top[i][0] if i < len(app_top) else "-"
        app_count = app_top[i][1] if i < len(app_top) else 0

        # Check if tickers match at this rank
        match = "[green]Yes[/green]" if qq_ticker == app_ticker else "[red]No[/red]"

        table.add_row(
            str(i + 1),
            qq_ticker,
            str(qq_count),
            app_ticker,
            str(app_count),
            match
        )

    console.print(table)

    # Find common tickers
    common = set(qq_tickers.keys()) & set(app_tickers.keys())
    qq_only = set(qq_tickers.keys()) - set(app_tickers.keys())
    app_only = set(app_tickers.keys()) - set(qq_tickers.keys())

    console.print(f"\n[bold]Ticker Overlap:[/bold]")
    console.print(f"  Common tickers: [green]{len(common)}[/green]")
    console.print(f"  QuiverQuant only: [yellow]{len(qq_only)}[/yellow]")
    console.print(f"  App DB only: [yellow]{len(app_only)}[/yellow]")


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
