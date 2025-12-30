#!/usr/bin/env python3
# @description: Supabase database management for politician-trading-tracker
# @version: 1.0.0
# @group: workflows

"""
Supabase database commands for politician-trading-tracker.

Usage:
    mcli run supabase tables           # List all tables with row counts
    mcli run supabase schema <table>   # Show table schema
    mcli run supabase query <table>    # Query table data
    mcli run supabase stats            # Show database statistics
    mcli run supabase deploy <func>    # Deploy edge function
    mcli run supabase functions        # List edge functions
"""
import os
import subprocess
import click
from pathlib import Path
from dotenv import load_dotenv
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console
from rich.table import Table

logger = get_logger()

# Load environment variables from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin access
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "uljsqvwkomdrlnofmlad")


def get_client():
    """Get Supabase client."""
    try:
        from supabase import create_client
        if not SUPABASE_URL or not SUPABASE_KEY:
            console.print("[red]✗ Supabase credentials not found in .env[/red]")
            return None
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except ImportError:
        console.print("[red]✗ supabase package not installed. Run: pip install supabase[/red]")
        return None


# Known tables in the project
KNOWN_TABLES = [
    "jurisdictions",
    "politicians",
    "trading_disclosures",
    "chart_data",
    "dashboard_stats",
    "filings",
    "profiles",
    "subscriptions",
    "user_notifications",
    "user_alerts",
    "jobs",
]


@click.group(name="supabase")
def supabase():
    """
    🗄️ Supabase database management for politician-trading-tracker.

    Query tables, view schemas, and monitor database statistics.
    """
    pass


@supabase.command(name="tables")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all tables including system tables")
def tables(show_all: bool):
    """List all tables with row counts."""
    client = get_client()
    if not client:
        return

    console.print("[cyan]📊 Database Tables[/cyan]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Table", style="white")
    table.add_column("Rows", justify="right", style="green")
    table.add_column("Status", style="dim")

    tables_to_check = KNOWN_TABLES

    for table_name in tables_to_check:
        try:
            # Get count
            result = client.table(table_name).select("*", count="exact").limit(0).execute()
            count = result.count if result.count is not None else 0
            status = "✓"
            table.add_row(table_name, f"{count:,}", status)
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg.lower() or "404" in error_msg:
                table.add_row(table_name, "-", "[dim]not found[/dim]")
            else:
                table.add_row(table_name, "-", f"[red]error[/red]")

    console.print(table)
    console.print(f"\n[dim]Supabase URL: {SUPABASE_URL}[/dim]")


@supabase.command(name="schema")
@click.argument("table_name")
def schema(table_name: str):
    """Show table schema and sample data."""
    client = get_client()
    if not client:
        return

    console.print(f"[cyan]📋 Schema for '{table_name}'[/cyan]\n")

    try:
        # Get sample row to infer schema
        result = client.table(table_name).select("*").limit(1).execute()

        if result.data and len(result.data) > 0:
            sample = result.data[0]

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Column", style="white")
            table.add_column("Type", style="yellow")
            table.add_column("Sample Value", style="dim", max_width=50)

            for key, value in sample.items():
                value_type = type(value).__name__
                sample_val = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                table.add_row(key, value_type, sample_val)

            console.print(table)
        else:
            console.print(f"[yellow]Table '{table_name}' exists but is empty[/yellow]")

        # Get total count
        count_result = client.table(table_name).select("*", count="exact").limit(0).execute()
        console.print(f"\n[dim]Total rows: {count_result.count:,}[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@supabase.command(name="query")
@click.argument("table_name")
@click.option("--limit", "-l", default=10, help="Number of rows to return")
@click.option("--offset", "-o", default=0, help="Offset for pagination")
@click.option("--select", "-s", default="*", help="Columns to select")
@click.option("--order", default=None, help="Column to order by (prefix with - for desc)")
@click.option("--where", "-w", default=None, help="Filter: column=value")
def query(table_name: str, limit: int, offset: int, select: str, order: str, where: str):
    """Query table data.

    Examples:
        mcli run supabase query politicians -l 5
        mcli run supabase query trading_disclosures --order=-disclosure_date -l 10
        mcli run supabase query politicians -w party=D
    """
    client = get_client()
    if not client:
        return

    console.print(f"[cyan]🔍 Query: {table_name}[/cyan]\n")

    try:
        q = client.table(table_name).select(select)

        # Apply filter
        if where:
            col, val = where.split("=", 1)
            q = q.eq(col.strip(), val.strip())

        # Apply ordering
        if order:
            if order.startswith("-"):
                q = q.order(order[1:], desc=True)
            else:
                q = q.order(order)

        # Apply pagination
        q = q.range(offset, offset + limit - 1)

        result = q.execute()

        if not result.data:
            console.print("[yellow]No results found[/yellow]")
            return

        # Build display table
        table = Table(show_header=True, header_style="bold cyan", show_lines=True)

        # Get columns from first row
        columns = list(result.data[0].keys())

        # Limit columns for readability
        display_cols = columns[:8]  # Max 8 columns
        for col in display_cols:
            table.add_column(col, max_width=30, overflow="ellipsis")

        if len(columns) > 8:
            table.add_column("...", style="dim")

        # Add rows
        for row in result.data:
            values = []
            for col in display_cols:
                val = row.get(col, "")
                val_str = str(val) if val is not None else ""
                values.append(val_str[:30])
            if len(columns) > 8:
                values.append(f"+{len(columns) - 8} cols")
            table.add_row(*values)

        console.print(table)
        console.print(f"\n[dim]Showing {len(result.data)} rows (offset: {offset}, limit: {limit})[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@supabase.command(name="stats")
def stats():
    """Show database statistics."""
    client = get_client()
    if not client:
        return

    console.print("[cyan]📈 Database Statistics[/cyan]\n")

    # Collect stats
    stats_data = {}
    total_rows = 0

    for table_name in KNOWN_TABLES:
        try:
            result = client.table(table_name).select("*", count="exact").limit(0).execute()
            count = result.count if result.count is not None else 0
            stats_data[table_name] = count
            total_rows += count
        except:
            stats_data[table_name] = None

    # Display stats
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Table", style="white")
    table.add_column("Rows", justify="right", style="green")
    table.add_column("% of Total", justify="right", style="yellow")

    for table_name, count in sorted(stats_data.items(), key=lambda x: x[1] or 0, reverse=True):
        if count is not None:
            pct = (count / total_rows * 100) if total_rows > 0 else 0
            table.add_row(table_name, f"{count:,}", f"{pct:.1f}%")
        else:
            table.add_row(table_name, "-", "-")

    console.print(table)
    console.print(f"\n[bold]Total rows: {total_rows:,}[/bold]")

    # Dashboard stats if available
    try:
        result = client.table("dashboard_stats").select("*").limit(1).execute()
        if result.data:
            ds = result.data[0]
            console.print("\n[cyan]Dashboard Stats:[/cyan]")
            console.print(f"  Total Trades: {ds.get('total_trades', 0):,}")
            console.print(f"  Total Volume: ${ds.get('total_volume', 0):,.0f}")
            console.print(f"  Active Politicians: {ds.get('active_politicians', 0):,}")
            console.print(f"  Jurisdictions: {ds.get('jurisdictions_tracked', 0)}")
    except:
        pass

    console.print(f"\n[dim]Supabase URL: {SUPABASE_URL}[/dim]")


@supabase.command(name="upsert")
@click.argument("table_name")
@click.argument("data", required=False)
@click.option("--id", "record_id", help="Record ID for update (if omitted, creates new record)")
@click.option("--file", "-f", "json_file", type=click.Path(exists=True), help="Read JSON data from file")
@click.option("--set", "-s", "set_values", multiple=True, help="Set field: column=value (can be repeated)")
@click.option("--dry-run", is_flag=True, help="Show what would be upserted without executing")
def upsert(table_name: str, data: str, record_id: str, json_file: str, set_values: tuple, dry_run: bool):
    """Upsert (insert or update) a record in a table.

    Examples:
        mcli run supabase upsert politicians --id abc123 -s party=R -s state=PA
        mcli run supabase upsert trading_disclosures --id xyz -s transaction_type=purchase
        mcli run supabase upsert politicians '{"full_name": "John Doe", "party": "D"}'
        mcli run supabase upsert politicians -f data.json
    """
    import json as json_lib

    client = get_client()
    if not client:
        return

    # Build the record data
    record = {}

    # From JSON argument
    if data:
        try:
            record = json_lib.loads(data)
        except json_lib.JSONDecodeError as e:
            console.print(f"[red]✗ Invalid JSON: {e}[/red]")
            return

    # From JSON file
    if json_file:
        try:
            with open(json_file) as f:
                file_data = json_lib.load(f)
                record.update(file_data)
        except Exception as e:
            console.print(f"[red]✗ Error reading file: {e}[/red]")
            return

    # From --set options
    for kv in set_values:
        if "=" not in kv:
            console.print(f"[red]✗ Invalid format '{kv}'. Use: column=value[/red]")
            return
        col, val = kv.split("=", 1)

        # Try to parse value as JSON (for numbers, booleans, null)
        try:
            parsed = json_lib.loads(val)
            record[col.strip()] = parsed
        except json_lib.JSONDecodeError:
            record[col.strip()] = val.strip()

    if not record:
        console.print("[red]✗ No data provided. Use JSON argument, --file, or --set options[/red]")
        return

    # Show what will be upserted
    operation = "Update" if record_id else "Insert"
    console.print(f"[cyan]📝 {operation} into '{table_name}'[/cyan]")
    if record_id:
        console.print(f"[dim]ID: {record_id}[/dim]")
    console.print("[dim]Data:[/dim]")
    for k, v in record.items():
        console.print(f"  {k}: {v}")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/yellow]")
        return

    try:
        if record_id:
            # Update existing record
            result = client.table(table_name).update(record).eq("id", record_id).execute()
            if result.data:
                console.print(f"\n[green]✓ Updated {len(result.data)} record(s)[/green]")
            else:
                console.print(f"\n[yellow]⚠ No records matched ID: {record_id}[/yellow]")
        else:
            # Insert new record
            result = client.table(table_name).insert(record).execute()
            if result.data:
                new_id = result.data[0].get("id", "unknown")
                console.print(f"\n[green]✓ Inserted record with ID: {new_id}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@supabase.command(name="delete")
@click.argument("table_name")
@click.argument("record_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def delete(table_name: str, record_id: str, yes: bool):
    """Delete a record from a table.

    Example:
        mcli run supabase delete trading_disclosures abc-123-xyz
    """
    client = get_client()
    if not client:
        return

    # First fetch the record to show what will be deleted
    try:
        result = client.table(table_name).select("*").eq("id", record_id).execute()
        if not result.data:
            console.print(f"[yellow]⚠ No record found with ID: {record_id}[/yellow]")
            return

        record = result.data[0]
        console.print(f"[cyan]🗑️  Delete from '{table_name}'[/cyan]")
        console.print(f"[dim]ID: {record_id}[/dim]")
        console.print("[dim]Record:[/dim]")
        for k, v in list(record.items())[:10]:  # Show first 10 fields
            val_str = str(v)[:50] if v else ""
            console.print(f"  {k}: {val_str}")
        if len(record) > 10:
            console.print(f"  ... and {len(record) - 10} more fields")

    except Exception as e:
        console.print(f"[red]✗ Error fetching record: {e}[/red]")
        return

    if not yes:
        if not click.confirm("\nDelete this record?"):
            console.print("[dim]Cancelled[/dim]")
            return

    try:
        result = client.table(table_name).delete().eq("id", record_id).execute()
        console.print(f"\n[green]✓ Deleted record[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error deleting: {e}[/red]")


@supabase.command(name="recent")
@click.option("--limit", "-l", default=10, help="Number of trades to show")
def recent(limit: int):
    """Show recent trading disclosures."""
    client = get_client()
    if not client:
        return

    console.print(f"[cyan]📋 Recent Trading Disclosures (last {limit})[/cyan]\n")

    try:
        result = client.table("trading_disclosures").select(
            "disclosure_date, transaction_type, asset_ticker, asset_name, amount_range_min, amount_range_max, politician:politicians(full_name, party)"
        ).order("disclosure_date", desc=True).limit(limit).execute()

        if not result.data:
            console.print("[yellow]No disclosures found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Date", style="white")
        table.add_column("Politician", style="cyan")
        table.add_column("Party", style="yellow")
        table.add_column("Type", style="green")
        table.add_column("Ticker", style="magenta")
        table.add_column("Amount", justify="right")

        for row in result.data:
            pol = row.get("politician") or {}
            pol_name = pol.get("full_name", "Unknown")[:20]
            party = pol.get("party", "?")

            min_amt = row.get("amount_range_min") or 0
            max_amt = row.get("amount_range_max") or 0
            amount = f"${min_amt:,.0f}-${max_amt:,.0f}" if max_amt else f"${min_amt:,.0f}+"

            tx_type = row.get("transaction_type", "")
            type_style = "[green]" if tx_type == "purchase" else "[red]" if tx_type == "sale" else ""

            table.add_row(
                row.get("disclosure_date", "")[:10],
                pol_name,
                party,
                f"{type_style}{tx_type}",
                row.get("asset_ticker") or "-",
                amount,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


# =============================================================================
# Edge Functions Commands
# =============================================================================

@supabase.command(name="deploy")
@click.argument("function_name", required=False)
@click.option("--all", "-a", "deploy_all", is_flag=True, help="Deploy all functions")
@click.option("--project", "-p", default=None, help="Override project reference")
def deploy(function_name: str | None, deploy_all: bool, project: str | None):
    """Deploy edge function(s) to Supabase.

    Examples:
        mcli run supabase deploy trading-signals    # Deploy specific function
        mcli run supabase deploy --all              # Deploy all functions
        mcli run supabase deploy trading-signals -p myproject  # Custom project
    """
    functions_dir = PROJECT_ROOT / "supabase" / "functions"
    project_ref = project or SUPABASE_PROJECT_REF

    if not functions_dir.exists():
        console.print(f"[red]✗ Functions directory not found: {functions_dir}[/red]")
        return

    # Determine which functions to deploy
    if deploy_all:
        functions = [d.name for d in functions_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    elif function_name:
        functions = [function_name]
    else:
        console.print("[yellow]⚠ No function specified. Use function name or --all[/yellow]")
        console.print("\nAvailable functions:")
        for d in functions_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                console.print(f"  • {d.name}")
        return

    console.print(f"[cyan]🚀 Deploying to project: {project_ref}[/cyan]\n")

    for func in functions:
        func_path = functions_dir / func
        if not func_path.exists():
            console.print(f"[yellow]⚠ Function not found: {func}[/yellow]")
            continue

        console.print(f"[dim]Deploying {func}...[/dim]")

        try:
            result = subprocess.run(
                ["npx", "supabase", "functions", "deploy", func, "--project-ref", project_ref],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
            )

            if result.returncode == 0:
                console.print(f"[green]✓ Deployed: {func}[/green]")
            else:
                console.print(f"[red]✗ Failed: {func}[/red]")
                if result.stderr:
                    # Extract meaningful error message
                    error_lines = [l for l in result.stderr.split("\n") if l.strip() and not l.startswith("WARNING")]
                    for line in error_lines[:3]:
                        console.print(f"[dim]  {line}[/dim]")

        except FileNotFoundError:
            console.print("[red]✗ npx/supabase CLI not found. Install with: npm install -g supabase[/red]")
            return
        except Exception as e:
            console.print(f"[red]✗ Error deploying {func}: {e}[/red]")

    console.print(f"\n[dim]Dashboard: https://supabase.com/dashboard/project/{project_ref}/functions[/dim]")


@supabase.command(name="functions")
@click.option("--remote", "-r", is_flag=True, help="List deployed functions (requires auth)")
def functions(remote: bool):
    """List edge functions.

    Examples:
        mcli run supabase functions          # List local functions
        mcli run supabase functions --remote # List deployed functions
    """
    functions_dir = PROJECT_ROOT / "supabase" / "functions"

    if not functions_dir.exists():
        console.print(f"[red]✗ Functions directory not found: {functions_dir}[/red]")
        return

    if remote:
        console.print("[cyan]📡 Deployed Edge Functions[/cyan]\n")
        try:
            result = subprocess.run(
                ["npx", "supabase", "functions", "list", "--project-ref", SUPABASE_PROJECT_REF],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
            )
            if result.returncode == 0:
                console.print(result.stdout)
            else:
                console.print(f"[red]✗ Failed to list functions[/red]")
                if result.stderr:
                    console.print(f"[dim]{result.stderr}[/dim]")
        except FileNotFoundError:
            console.print("[red]✗ supabase CLI not found[/red]")
        return

    console.print("[cyan]📁 Local Edge Functions[/cyan]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Function", style="white")
    table.add_column("Files", style="dim")
    table.add_column("Size", justify="right", style="yellow")

    for func_dir in sorted(functions_dir.iterdir()):
        if not func_dir.is_dir() or func_dir.name.startswith("."):
            continue

        # Count files and calculate size
        files = list(func_dir.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        total_size = sum(f.stat().st_size for f in files if f.is_file())

        # Format size
        if total_size > 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        elif total_size > 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size} B"

        table.add_row(func_dir.name, str(file_count), size_str)

    console.print(table)
    console.print(f"\n[dim]Functions directory: {functions_dir}[/dim]")
    console.print(f"[dim]Project: {SUPABASE_PROJECT_REF}[/dim]")
