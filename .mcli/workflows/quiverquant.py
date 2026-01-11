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


def normalize_name_for_match(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    if not name:
        return ""
    # Handle "Last, First" format
    if ", " in name:
        parts = name.split(", ", 1)
        name = f"{parts[1]} {parts[0]}"
    # Remove common prefixes/suffixes
    for term in ["Hon. ", "Rep. ", "Sen. ", " Jr.", " Jr", " Sr.", " Sr", " III", " II", " IV"]:
        name = name.replace(term, "")
    return name.lower().strip()


@app.command("sample-test")
@click.option("--count", "-n", default=5, help="Number of politicians to sample")
@click.option("--trades", "-t", default=30, help="Number of trades to check per politician")
def sample_test(count: int, trades: int):
    """
    Sample random politicians and verify their trades exist in our database.

    For each sampled politician from QuiverQuant:
    1. Find matching politician in our database
    2. Get their recent trades from QuiverQuant
    3. Check if those trades exist in our database

    Example: mcli run quiverquant sample-test --count 5 --trades 30
    """
    import random

    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Sampling {count} politicians, checking up to {trades} trades each...[/cyan]\n")

    # Fetch all QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key, limit=2000)
    if not qq_data:
        console.print("[red]Failed to fetch QuiverQuant data[/red]")
        raise SystemExit(1)

    # Group trades by politician
    qq_by_politician = {}
    for trade in qq_data:
        rep = trade.get("Representative", "")
        bioguide = trade.get("BioGuideID", "")
        if rep:
            key = (rep, bioguide)
            if key not in qq_by_politician:
                qq_by_politician[key] = []
            qq_by_politician[key].append(trade)

    # Get politicians with enough trades to sample
    active_politicians = [(k, v) for k, v in qq_by_politician.items() if len(v) >= 5]
    if len(active_politicians) < count:
        console.print(f"[yellow]Only {len(active_politicians)} politicians with 5+ trades available[/yellow]")
        count = len(active_politicians)

    # Random sample
    sampled = random.sample(active_politicians, count)

    # Fetch our politicians for matching
    app_politicians = fetch_supabase_data(
        config, "politicians",
        "id,full_name,first_name,last_name,bioguide_id",
        limit=2000
    )

    # Build lookup maps (handle duplicates by collecting all IDs)
    app_by_bioguide = {}  # bioguide_id -> list of politician dicts
    for p in app_politicians:
        bg = p.get("bioguide_id")
        if bg:
            if bg not in app_by_bioguide:
                app_by_bioguide[bg] = []
            app_by_bioguide[bg].append(p)

    app_by_name = {}  # normalized name -> list of politician dicts
    for p in app_politicians:
        name = p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        norm = normalize_name_for_match(name)
        if norm:
            if norm not in app_by_name:
                app_by_name[norm] = []
            app_by_name[norm].append(p)

    # Results
    total_qq_trades = 0
    total_matched = 0
    total_missing = 0
    results = []

    for (rep_name, bioguide_id), qq_trades in sampled:
        # Find matching politician(s) in our database (may have duplicates)
        app_pols = []
        match_method = None

        # Try BioGuide ID first
        if bioguide_id and bioguide_id in app_by_bioguide:
            app_pols = app_by_bioguide[bioguide_id]
            match_method = "bioguide_id"
        else:
            # Try name matching
            norm_name = normalize_name_for_match(rep_name)
            if norm_name in app_by_name:
                app_pols = app_by_name[norm_name]
                match_method = "name"

        if not app_pols:
            console.print(f"[yellow]Could not find politician: {rep_name} ({bioguide_id})[/yellow]")
            results.append({
                "politician": rep_name,
                "bioguide": bioguide_id,
                "qq_trades": len(qq_trades[:trades]),
                "matched": 0,
                "missing": len(qq_trades[:trades]),
                "match_rate": 0,
                "status": "NOT_FOUND"
            })
            total_qq_trades += len(qq_trades[:trades])
            total_missing += len(qq_trades[:trades])
            continue

        # Fetch trades for all matching politician IDs (handles duplicates)
        app_pol_trades = []
        for app_pol in app_pols:
            app_pol_id = app_pol.get("id")
            pol_trades = fetch_supabase_data(
                config, "trading_disclosures",
                "id,politician_id,asset_ticker,transaction_date,transaction_type,asset_name",
                limit=500,
                filters={"status": "eq.active", "politician_id": f"eq.{app_pol_id}"},
                order="transaction_date.desc"
            )
            app_pol_trades.extend(pol_trades)

        # Compare trades
        matched = 0
        missing = 0
        missing_trades = []

        for qq_trade in qq_trades[:trades]:
            qq_ticker = qq_trade.get("Ticker", "")
            qq_date = qq_trade.get("TransactionDate", "")[:10]
            qq_type = qq_trade.get("Transaction", "").lower()

            # Look for matching trade in our database
            found = False
            for app_trade in app_pol_trades:
                app_ticker = app_trade.get("asset_ticker") or ""
                app_date = (app_trade.get("transaction_date") or "")[:10]
                app_type = (app_trade.get("transaction_type") or "").lower()

                # Match by ticker and date (type can vary slightly)
                if app_ticker == qq_ticker and app_date == qq_date:
                    found = True
                    break
                # Also check if ticker is in asset_name
                if qq_ticker and qq_ticker in (app_trade.get("asset_name") or "") and app_date == qq_date:
                    found = True
                    break

            if found:
                matched += 1
            else:
                missing += 1
                if len(missing_trades) < 3:
                    missing_trades.append(f"{qq_date} {qq_ticker} ({qq_type})")

        total_qq_trades += len(qq_trades[:trades])
        total_matched += matched
        total_missing += missing

        match_rate = (matched / len(qq_trades[:trades]) * 100) if qq_trades else 0
        status = "[green]GOOD[/green]" if match_rate >= 80 else "[yellow]PARTIAL[/yellow]" if match_rate >= 50 else "[red]LOW[/red]"

        results.append({
            "politician": rep_name,
            "bioguide": bioguide_id,
            "qq_trades": len(qq_trades[:trades]),
            "matched": matched,
            "missing": missing,
            "match_rate": match_rate,
            "status": status,
            "missing_examples": missing_trades
        })

    # Display results
    console.print("[bold]Sample Test Results[/bold]")
    console.print("=" * 80)

    table = Table()
    table.add_column("Politician", style="cyan", width=25)
    table.add_column("BioGuide", width=10)
    table.add_column("QQ Trades", justify="right", width=10)
    table.add_column("Matched", justify="right", width=8)
    table.add_column("Missing", justify="right", width=8)
    table.add_column("Rate", justify="right", width=8)
    table.add_column("Status", width=10)

    for r in results:
        table.add_row(
            r["politician"][:24],
            r["bioguide"] or "-",
            str(r["qq_trades"]),
            str(r["matched"]),
            str(r["missing"]),
            f"{r['match_rate']:.0f}%",
            r["status"]
        )

    console.print(table)

    # Show missing trade examples
    console.print("\n[bold]Missing Trade Examples:[/bold]")
    for r in results:
        if r.get("missing_examples"):
            console.print(f"  [cyan]{r['politician']}[/cyan]:")
            for ex in r["missing_examples"]:
                console.print(f"    - {ex}")

    # Summary
    console.print("\n[bold]Summary[/bold]")
    console.print("-" * 40)
    console.print(f"Politicians sampled: {count}")
    console.print(f"Total QuiverQuant trades checked: {total_qq_trades}")
    console.print(f"Matched in our DB: [green]{total_matched}[/green]")
    console.print(f"Missing from our DB: [yellow]{total_missing}[/yellow]")
    overall_rate = (total_matched / total_qq_trades * 100) if total_qq_trades else 0
    console.print(f"Overall match rate: [{'green' if overall_rate >= 80 else 'yellow' if overall_rate >= 50 else 'red'}]{overall_rate:.1f}%[/]")

    if overall_rate < 50:
        console.print("\n[red]Warning: Low match rate. ETL may be missing data.[/red]")
        raise SystemExit(1)
    elif overall_rate < 80:
        console.print("\n[yellow]Note: Some trades missing. Consider investigating.[/yellow]")


@app.command("freshness-check")
def freshness_check():
    """
    Compare data freshness between QuiverQuant and our database.

    Shows:
    - Most recent trade dates in each source
    - Data lag (how far behind we are)
    - Recent disclosure dates comparison

    Example: mcli run quiverquant freshness-check
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Checking data freshness...[/cyan]\n")

    # Fetch QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key, limit=500)

    # Get most recent dates from QuiverQuant
    qq_tx_dates = [t.get("TransactionDate", "")[:10] for t in qq_data if t.get("TransactionDate")]
    qq_disc_dates = [t.get("ReportDate", t.get("DisclosureDate", ""))[:10] for t in qq_data if t.get("ReportDate") or t.get("DisclosureDate")]

    qq_latest_tx = max(qq_tx_dates) if qq_tx_dates else "N/A"
    qq_latest_disc = max(qq_disc_dates) if qq_disc_dates else "N/A"

    # Fetch our most recent dates
    app_trades = fetch_supabase_data(
        config, "trading_disclosures",
        "transaction_date,disclosure_date",
        limit=500,
        filters={"status": "eq.active"},
        order="disclosure_date.desc"
    )

    app_tx_dates = [(t.get("transaction_date") or "")[:10] for t in app_trades if t.get("transaction_date")]
    app_disc_dates = [(t.get("disclosure_date") or "")[:10] for t in app_trades if t.get("disclosure_date")]

    app_latest_tx = max(app_tx_dates) if app_tx_dates else "N/A"
    app_latest_disc = max(app_disc_dates) if app_disc_dates else "N/A"

    # Display comparison
    table = Table(title="Data Freshness Comparison")
    table.add_column("Metric", style="bold")
    table.add_column("QuiverQuant", style="cyan")
    table.add_column("Our Database", style="green")
    table.add_column("Status", style="yellow")

    # Transaction date comparison
    tx_status = "OK" if app_latest_tx >= qq_latest_tx else f"Behind by {qq_latest_tx}"
    table.add_row("Latest Transaction Date", qq_latest_tx, app_latest_tx, tx_status)

    # Disclosure date comparison
    disc_status = "OK" if app_latest_disc >= qq_latest_disc else f"Behind by {qq_latest_disc}"
    table.add_row("Latest Disclosure Date", qq_latest_disc, app_latest_disc, disc_status)

    # Record counts
    table.add_row("Records Checked", str(len(qq_data)), str(len(app_trades)), "-")

    console.print(table)

    # Calculate lag in days
    from datetime import datetime
    try:
        if qq_latest_disc != "N/A" and app_latest_disc != "N/A":
            qq_date = datetime.strptime(qq_latest_disc, "%Y-%m-%d")
            app_date = datetime.strptime(app_latest_disc, "%Y-%m-%d")
            lag_days = (qq_date - app_date).days
            if lag_days > 0:
                console.print(f"\n[yellow]Data lag: {lag_days} days behind QuiverQuant[/yellow]")
            elif lag_days < 0:
                console.print(f"\n[green]Our data is {-lag_days} days ahead of QuiverQuant sample[/green]")
            else:
                console.print(f"\n[green]Data is current[/green]")
    except Exception:
        pass

    # Show recent disclosures from each source
    console.print("\n[bold]Recent Disclosures (QuiverQuant):[/bold]")
    recent_qq = sorted(set(qq_disc_dates), reverse=True)[:5]
    for d in recent_qq:
        count = qq_disc_dates.count(d)
        console.print(f"  {d}: {count} trades")

    console.print("\n[bold]Recent Disclosures (Our DB):[/bold]")
    recent_app = sorted(set(app_disc_dates), reverse=True)[:5]
    for d in recent_app:
        count = app_disc_dates.count(d)
        console.print(f"  {d}: {count} trades")


@app.command("bioguide-audit")
def bioguide_audit():
    """
    Audit BioGuide ID consistency between QuiverQuant and our database.

    Checks:
    - Politicians with mismatched BioGuide IDs
    - Politicians missing BioGuide IDs
    - BioGuide IDs in QuiverQuant not in our DB

    Example: mcli run quiverquant bioguide-audit
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Auditing BioGuide IDs...[/cyan]\n")

    # Fetch QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key, limit=2000)

    # Build QuiverQuant bioguide -> name mapping
    qq_bioguides = {}
    for trade in qq_data:
        bg = trade.get("BioGuideID", "")
        name = trade.get("Representative", "")
        if bg and name:
            qq_bioguides[bg] = name

    # Fetch our politicians
    app_politicians = fetch_supabase_data(
        config, "politicians",
        "id,full_name,bioguide_id",
        limit=2000
    )

    app_bioguides = {p.get("bioguide_id"): p for p in app_politicians if p.get("bioguide_id")}
    app_missing_bg = [p for p in app_politicians if not p.get("bioguide_id")]

    console.print(f"[bold]BioGuide ID Summary[/bold]")
    console.print("-" * 50)
    console.print(f"QuiverQuant unique BioGuide IDs: [cyan]{len(qq_bioguides)}[/cyan]")
    console.print(f"Our DB with BioGuide IDs: [green]{len(app_bioguides)}[/green]")
    console.print(f"Our DB missing BioGuide IDs: [yellow]{len(app_missing_bg)}[/yellow]")

    # Find matches and mismatches
    matched = 0
    qq_only = []
    name_mismatches = []

    for bg, qq_name in qq_bioguides.items():
        if bg in app_bioguides:
            matched += 1
            app_name = app_bioguides[bg].get("full_name", "")
            # Check for significant name differences
            qq_norm = normalize_name_for_match(qq_name)
            app_norm = normalize_name_for_match(app_name)
            if qq_norm != app_norm and qq_norm not in app_norm and app_norm not in qq_norm:
                name_mismatches.append({
                    "bioguide": bg,
                    "qq_name": qq_name,
                    "app_name": app_name
                })
        else:
            qq_only.append({"bioguide": bg, "name": qq_name})

    console.print(f"\n[bold]Match Results:[/bold]")
    console.print(f"  BioGuide IDs in both: [green]{matched}[/green]")
    console.print(f"  QuiverQuant only: [yellow]{len(qq_only)}[/yellow]")
    console.print(f"  Name mismatches: [{'red' if name_mismatches else 'green'}]{len(name_mismatches)}[/]")

    if qq_only:
        console.print(f"\n[bold]BioGuide IDs in QuiverQuant but not in our DB (sample):[/bold]")
        for item in qq_only[:10]:
            console.print(f"  {item['bioguide']}: {item['name']}")

    if name_mismatches:
        console.print(f"\n[bold]Name Mismatches (same BioGuide, different names):[/bold]")
        for item in name_mismatches[:10]:
            console.print(f"  {item['bioguide']}:")
            console.print(f"    QQ: {item['qq_name']}")
            console.print(f"    DB: {item['app_name']}")

    if app_missing_bg:
        console.print(f"\n[bold]Politicians in our DB missing BioGuide ID (sample):[/bold]")
        for p in app_missing_bg[:10]:
            console.print(f"  {p['full_name']}")


@app.command("coverage-report")
def coverage_report():
    """
    Generate a comprehensive data coverage report.

    Shows overall health metrics:
    - Politician coverage %
    - Trade match rate %
    - Date range coverage
    - Data quality indicators

    Example: mcli run quiverquant coverage-report
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Generating coverage report...[/cyan]\n")

    # Fetch data from both sources
    qq_data = fetch_quiverquant_data(api_key, limit=2000)
    app_politicians = fetch_supabase_data(config, "politicians", "id,full_name,bioguide_id,party", limit=2000)
    app_trades = fetch_supabase_data(
        config, "trading_disclosures",
        "id,asset_ticker,transaction_date,amount_range_min",
        limit=5000,
        filters={"status": "eq.active"}
    )

    # Calculate metrics
    qq_politicians = set()
    qq_tickers = set()
    qq_dates = set()
    for t in qq_data:
        if t.get("Representative"):
            qq_politicians.add(t["Representative"])
        if t.get("Ticker"):
            qq_tickers.add(t["Ticker"])
        if t.get("TransactionDate"):
            qq_dates.add(t["TransactionDate"][:10])

    app_politician_names = set(p.get("full_name", "") for p in app_politicians)
    app_tickers = set(t.get("asset_ticker", "") for t in app_trades if t.get("asset_ticker"))
    app_dates = set((t.get("transaction_date") or "")[:10] for t in app_trades if t.get("transaction_date"))

    # Calculate coverage
    politician_overlap = len(qq_politicians & app_politician_names)
    ticker_overlap = len(qq_tickers & app_tickers)

    # Data quality metrics
    trades_with_amounts = sum(1 for t in app_trades if t.get("amount_range_min"))
    trades_with_tickers = sum(1 for t in app_trades if t.get("asset_ticker"))

    # Display report
    console.print("[bold]=" * 60)
    console.print("[bold]       DATA COVERAGE REPORT[/bold]")
    console.print("[bold]=" * 60)

    console.print("\n[bold]1. POLITICIAN COVERAGE[/bold]")
    console.print("-" * 40)
    console.print(f"  QuiverQuant politicians: {len(qq_politicians)}")
    console.print(f"  Our DB politicians: {len(app_politicians)}")
    console.print(f"  Overlap (name match): {politician_overlap}")
    pct = (politician_overlap / len(qq_politicians) * 100) if qq_politicians else 0
    color = "green" if pct >= 80 else "yellow" if pct >= 60 else "red"
    console.print(f"  Coverage: [{color}]{pct:.1f}%[/]")

    console.print("\n[bold]2. TICKER COVERAGE[/bold]")
    console.print("-" * 40)
    console.print(f"  QuiverQuant tickers: {len(qq_tickers)}")
    console.print(f"  Our DB tickers: {len(app_tickers)}")
    console.print(f"  Overlap: {ticker_overlap}")
    pct = (ticker_overlap / len(qq_tickers) * 100) if qq_tickers else 0
    color = "green" if pct >= 80 else "yellow" if pct >= 60 else "red"
    console.print(f"  Coverage: [{color}]{pct:.1f}%[/]")

    console.print("\n[bold]3. DATE RANGE[/bold]")
    console.print("-" * 40)
    console.print(f"  QuiverQuant: {min(qq_dates) if qq_dates else 'N/A'} to {max(qq_dates) if qq_dates else 'N/A'}")
    console.print(f"  Our DB: {min(app_dates) if app_dates else 'N/A'} to {max(app_dates) if app_dates else 'N/A'}")

    console.print("\n[bold]4. DATA QUALITY[/bold]")
    console.print("-" * 40)
    console.print(f"  Total trades in DB: {len(app_trades)}")
    pct_amounts = (trades_with_amounts / len(app_trades) * 100) if app_trades else 0
    pct_tickers = (trades_with_tickers / len(app_trades) * 100) if app_trades else 0
    color_amt = "green" if pct_amounts >= 90 else "yellow" if pct_amounts >= 70 else "red"
    color_tick = "green" if pct_tickers >= 90 else "yellow" if pct_tickers >= 70 else "red"
    console.print(f"  With amounts: [{color_amt}]{trades_with_amounts} ({pct_amounts:.1f}%)[/]")
    console.print(f"  With tickers: [{color_tick}]{trades_with_tickers} ({pct_tickers:.1f}%)[/]")

    # Overall score
    overall_score = (pct + pct_amounts + pct_tickers) / 3
    color = "green" if overall_score >= 80 else "yellow" if overall_score >= 60 else "red"
    console.print(f"\n[bold]OVERALL HEALTH SCORE: [{color}]{overall_score:.0f}/100[/][/bold]")

    if overall_score < 60:
        console.print("\n[red]Action needed: Run ETL and enrichment jobs[/red]")
    elif overall_score < 80:
        console.print("\n[yellow]Good, but room for improvement[/yellow]")
    else:
        console.print("\n[green]Data quality is healthy[/green]")


@app.command("missing-trades")
@click.option("--days", "-d", default=30, help="Number of days to check")
@click.option("--limit", "-l", default=20, help="Maximum trades to show")
def missing_trades(days: int, limit: int):
    """
    List specific trades in QuiverQuant that are missing from our database.

    Shows actionable list of missing trades with details.

    Example: mcli run quiverquant missing-trades --days 14
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Finding trades from last {days} days missing from our DB...[/cyan]\n")

    # Fetch QuiverQuant data
    qq_data = fetch_quiverquant_data(api_key, limit=2000)

    # Filter to recent trades
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    qq_recent = [t for t in qq_data if (t.get("TransactionDate") or "")[:10] >= cutoff]

    # Fetch our trades
    app_trades = fetch_supabase_data(
        config, "trading_disclosures",
        "asset_ticker,transaction_date,politician_id",
        limit=10000,
        filters={"status": "eq.active"}
    )

    # Build lookup set for our trades (ticker + date)
    app_trade_keys = set()
    for t in app_trades:
        ticker = t.get("asset_ticker", "")
        date = (t.get("transaction_date") or "")[:10]
        if ticker and date:
            app_trade_keys.add(f"{ticker}:{date}")

    # Find missing trades
    missing = []
    for t in qq_recent:
        ticker = t.get("Ticker", "")
        date = (t.get("TransactionDate") or "")[:10]
        key = f"{ticker}:{date}"

        if ticker and date and key not in app_trade_keys:
            missing.append({
                "ticker": ticker,
                "date": date,
                "politician": t.get("Representative", "Unknown"),
                "type": t.get("Transaction", ""),
                "amount": t.get("Range", ""),
                "bioguide": t.get("BioGuideID", "")
            })

    console.print(f"[bold]Missing Trades Report (last {days} days)[/bold]")
    console.print("=" * 70)
    console.print(f"QuiverQuant trades in period: {len(qq_recent)}")
    console.print(f"Missing from our DB: [{'red' if len(missing) > 20 else 'yellow' if missing else 'green'}]{len(missing)}[/]")

    if missing:
        # Group by politician
        by_politician = {}
        for m in missing:
            pol = m["politician"]
            if pol not in by_politician:
                by_politician[pol] = []
            by_politician[pol].append(m)

        console.print(f"\n[bold]Missing Trades by Politician:[/bold]")
        shown = 0
        for pol, trades in sorted(by_politician.items(), key=lambda x: -len(x[1])):
            if shown >= limit:
                console.print(f"\n... and {len(missing) - shown} more")
                break

            console.print(f"\n[cyan]{pol}[/cyan] ({len(trades)} missing):")
            for t in trades[:5]:
                console.print(f"  {t['date']} {t['ticker']:6} {t['type']:20} {t['amount']}")
                shown += 1
                if shown >= limit:
                    break

        # Summary by ticker
        ticker_counts = {}
        for m in missing:
            ticker_counts[m["ticker"]] = ticker_counts.get(m["ticker"], 0) + 1

        console.print(f"\n[bold]Most Missed Tickers:[/bold]")
        for ticker, count in sorted(ticker_counts.items(), key=lambda x: -x[1])[:10]:
            console.print(f"  {ticker}: {count} missing")
    else:
        console.print("\n[green]No missing trades found![/green]")
