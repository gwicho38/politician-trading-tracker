#!/usr/bin/env python3
# @description: Jobs command
# @version: 1.0.0
# @group: workflows

"""
Jobs command group for mcli.

Provides a unified view of scheduled jobs across:
- Phoenix server (Quantum scheduler)
- Supabase scheduled_jobs table
- ETL service health
"""
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click
import httpx

from mcli.lib.logger.logger import get_logger

logger = get_logger()

# Service URLs
PHOENIX_SERVER_URL = os.environ.get(
    "PHOENIX_SERVER_URL",
    "https://politician-trading-server.fly.dev"
)
ETL_SERVICE_URL = os.environ.get(
    "ETL_SERVICE_URL",
    "https://politician-trading-etl.fly.dev"
)
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://uljsqvwkomdrlnofmlad.supabase.co"
)


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


def format_time_ago(dt_str: str | None) -> str:
    """Format datetime string as 'X ago' or 'never'."""
    if not dt_str:
        return "never"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt

        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds >= 60:
            mins = delta.seconds // 60
            return f"{mins}m ago"
        else:
            return "just now"
    except (ValueError, TypeError):
        return dt_str[:16] if dt_str else "?"


@click.group(name="jobs")
def app():
    """
    View and manage scheduled jobs across all services.

    Shows jobs from:
    - Phoenix server (Quantum scheduler)
    - ETL service
    - Supabase scheduled_jobs table
    """
    pass


@app.command("status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def status(verbose: bool):
    """
    Show status of all scheduled jobs.

    Queries Phoenix server and Supabase for comprehensive job status.

    Examples:
        mcli run jobs status
        mcli run jobs status -v
    """
    click.echo("=" * 80)
    click.echo("SCHEDULED JOBS STATUS")
    click.echo("=" * 80)

    # Fetch Phoenix jobs
    click.echo("\n[Phoenix Server Jobs]")
    phoenix_jobs = _fetch_phoenix_jobs()
    if phoenix_jobs:
        _display_phoenix_jobs(phoenix_jobs, verbose)
    else:
        click.echo("  Unable to fetch Phoenix jobs")

    # Fetch Supabase scheduled_jobs
    click.echo("\n[Supabase Scheduled Jobs]")
    supabase_jobs = _fetch_supabase_jobs()
    if supabase_jobs:
        _display_supabase_jobs(supabase_jobs, verbose)
    else:
        click.echo("  Unable to fetch Supabase jobs")

    # Service health
    click.echo("\n[Service Health]")
    _check_services_health()


def _fetch_phoenix_jobs() -> list[dict] | None:
    """Fetch jobs from Phoenix server."""
    try:
        response = httpx.get(
            f"{PHOENIX_SERVER_URL}/api/jobs",
            timeout=10.0
        )
        if response.status_code == 200:
            return response.json().get("jobs", [])
    except Exception as e:
        logger.warning(f"Failed to fetch Phoenix jobs: {e}")
    return None


def _fetch_supabase_jobs() -> list[dict] | None:
    """Fetch scheduled_jobs from Supabase."""
    service_key = get_supabase_key()
    if not service_key:
        return None

    try:
        response = httpx.get(
            f"{SUPABASE_URL}/rest/v1/scheduled_jobs?select=*&order=job_name",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
            },
            timeout=10.0
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Supabase jobs: {e}")
    return None


def _display_phoenix_jobs(jobs: list[dict], verbose: bool):
    """Display Phoenix server jobs."""
    if not jobs:
        click.echo("  No jobs registered")
        return

    # Sort by last_successful_run (most recent first)
    jobs = sorted(
        jobs,
        key=lambda j: j.get("last_successful_run") or "",
        reverse=True
    )

    for job in jobs:
        enabled = job.get("enabled", False)
        status_icon = "✓" if enabled else "○"
        job_name = job.get("job_name", job.get("job_id", "?"))
        schedule = job.get("schedule", job.get("schedule_value", "?"))
        last_run = format_time_ago(job.get("last_successful_run"))
        failures = job.get("consecutive_failures", 0)

        # Color coding
        if failures > 0:
            status_str = f"[{failures} failures]"
        else:
            status_str = ""

        click.echo(f"  {status_icon} {job_name:40} {schedule:15} Last: {last_run:12} {status_str}")

        if verbose:
            job_id = job.get("job_id", "?")
            click.echo(f"      ID: {job_id}")
            if job.get("metadata"):
                click.echo(f"      Metadata: {job['metadata']}")


def _display_supabase_jobs(jobs: list[dict], verbose: bool):
    """Display Supabase scheduled jobs."""
    if not jobs:
        click.echo("  No jobs found")
        return

    for job in jobs:
        enabled = job.get("enabled", False)
        status_icon = "✓" if enabled else "○"
        job_name = job.get("job_name", "?")
        schedule = job.get("schedule_value", "?")
        last_run = format_time_ago(job.get("last_successful_run"))
        failures = job.get("consecutive_failures", 0)

        status_str = f"[{failures} failures]" if failures > 0 else ""

        click.echo(f"  {status_icon} {job_name:40} {schedule:15} Last: {last_run:12} {status_str}")

        if verbose:
            job_id = job.get("job_id", "?")
            click.echo(f"      ID: {job_id}, Function: {job.get('job_function', '?')}")


def _check_services_health():
    """Check health of all services."""
    services = [
        ("Phoenix Server", f"{PHOENIX_SERVER_URL}/health"),
        ("ETL Service", f"{ETL_SERVICE_URL}/health"),
    ]

    for name, url in services:
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                click.echo(f"  ✓ {name}: healthy")
            else:
                click.echo(f"  ✗ {name}: HTTP {response.status_code}")
        except Exception as e:
            click.echo(f"  ✗ {name}: {str(e)[:50]}")


@app.command("run")
@click.argument("job_id")
def run_job(job_id: str):
    """
    Manually trigger a job to run.

    Example: mcli run jobs run sync-data
    """
    click.echo(f"Triggering job: {job_id}")

    try:
        response = httpx.post(
            f"{PHOENIX_SERVER_URL}/api/jobs/{job_id}/run",
            timeout=120.0
        )

        if response.status_code == 200:
            data = response.json()
            click.echo(f"✓ {data.get('message', 'Job completed')}")
            if data.get("result"):
                click.echo(f"  Result: {data['result']}")
        elif response.status_code == 404:
            click.echo(f"✗ Job '{job_id}' not found")
        else:
            click.echo(f"✗ Failed: {response.text}")
    except httpx.TimeoutException:
        click.echo("✗ Request timed out (job may still be running)")
    except Exception as e:
        click.echo(f"✗ Error: {e}")


@app.command("list")
@click.option("--phoenix", "-p", is_flag=True, help="Show only Phoenix jobs")
@click.option("--supabase", "-s", is_flag=True, help="Show only Supabase jobs")
def list_jobs(phoenix: bool, supabase: bool):
    """
    List all registered jobs.

    Examples:
        mcli run jobs list
        mcli run jobs list --phoenix
        mcli run jobs list --supabase
    """
    show_all = not phoenix and not supabase

    if show_all or phoenix:
        click.echo("\n[Phoenix Server Jobs]")
        jobs = _fetch_phoenix_jobs()
        if jobs:
            for job in jobs:
                job_id = job.get("job_id", "?")
                job_name = job.get("job_name", "?")
                enabled = "✓" if job.get("enabled") else "○"
                click.echo(f"  {enabled} {job_id:30} {job_name}")
        else:
            click.echo("  Unable to fetch or no jobs")

    if show_all or supabase:
        click.echo("\n[Supabase Scheduled Jobs]")
        jobs = _fetch_supabase_jobs()
        if jobs:
            for job in jobs:
                job_id = job.get("job_id", "?")
                job_name = job.get("job_name", "?")
                enabled = "✓" if job.get("enabled") else "○"
                click.echo(f"  {enabled} {job_id:30} {job_name}")
        else:
            click.echo("  Unable to fetch or no jobs")


@app.command("sync-status")
def sync_status():
    """
    Show when data was last synced.

    Example: mcli run jobs sync-status
    """
    try:
        response = httpx.get(
            f"{PHOENIX_SERVER_URL}/api/jobs/sync-status",
            timeout=10.0
        )

        if response.status_code == 200:
            data = response.json()
            last_sync = data.get("last_sync")

            click.echo(f"Last data sync: {format_time_ago(last_sync)}")

            if data.get("jobs"):
                click.echo("\nData collection jobs:")
                for job in data["jobs"]:
                    job_name = job.get("job_name", job.get("job_id", "?"))
                    last_run = format_time_ago(job.get("last_successful_run"))
                    click.echo(f"  {job_name:40} {last_run}")
        else:
            click.echo(f"Failed to get sync status: HTTP {response.status_code}")
    except Exception as e:
        click.echo(f"Error: {e}")


@app.command("run-all")
@click.confirmation_option(prompt="Are you sure you want to trigger all jobs?")
def run_all():
    """
    Trigger all enabled jobs to run (requires confirmation).

    Example: mcli run jobs run-all
    """
    click.echo("Triggering all jobs...")

    try:
        response = httpx.post(
            f"{PHOENIX_SERVER_URL}/api/jobs/run-all",
            timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()
            click.echo(f"✓ {data.get('message', 'Jobs triggered')}")

            if data.get("jobs"):
                for job in data["jobs"]:
                    click.echo(f"  - {job.get('job_name', job.get('job_id', '?'))}")
        else:
            click.echo(f"Failed: HTTP {response.status_code}")
    except Exception as e:
        click.echo(f"Error: {e}")


@app.command("health")
def health():
    """
    Check health of all services.

    Example: mcli run jobs health
    """
    services = [
        ("Phoenix Server", PHOENIX_SERVER_URL, "/health"),
        ("ETL Service", ETL_SERVICE_URL, "/health"),
        ("Supabase", SUPABASE_URL, "/rest/v1/"),
    ]

    click.echo("Service Health Check")
    click.echo("-" * 40)

    all_healthy = True
    for name, base_url, path in services:
        try:
            response = httpx.get(f"{base_url}{path}", timeout=5.0)
            if response.status_code == 200:
                click.echo(f"✓ {name:20} healthy")
            else:
                click.echo(f"✗ {name:20} HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            click.echo(f"✗ {name:20} {str(e)[:30]}")
            all_healthy = False

    if all_healthy:
        click.echo("\nAll services healthy!")
    else:
        click.echo("\nSome services have issues.")
        raise SystemExit(1)


@app.command("portfolio-snapshot")
def portfolio_snapshot():
    """
    Take a manual portfolio snapshot.

    Records the current portfolio value to the snapshots table
    for the performance chart. Normally runs daily at 5:30 PM EST.

    Example: mcli run jobs portfolio-snapshot
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo("Taking portfolio snapshot...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/reference-portfolio",
            json={"action": "take-snapshot"},
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                snapshot = data.get("snapshot", {})
                click.echo(f"\n✓ Snapshot saved!")
                click.echo(f"  Date: {snapshot.get('date', '?')}")
                click.echo(f"  Value: ${snapshot.get('portfolio_value', 0):,.2f}")
                click.echo(f"  Day Return: {snapshot.get('day_return_pct', 0):.2f}%")
                click.echo(f"  Cumulative Return: {snapshot.get('cumulative_return_pct', 0):.2f}%")
            else:
                click.echo(f"Error: {data.get('error', 'Unknown error')}", err=True)
                raise SystemExit(1)
        else:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            click.echo(response.text[:200], err=True)
            raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("alpaca-status")
def alpaca_status():
    """
    Show Alpaca account status and credential usage.

    Displays which Alpaca accounts are configured for:
    - Reference Portfolio (env vars)
    - User accounts (user_api_keys table)

    Example: mcli run jobs alpaca-status
    """
    import subprocess

    service_key = get_supabase_key()

    click.echo("Alpaca Account Status")
    click.echo("=" * 60)

    # Get env var credentials
    try:
        alpaca_key = subprocess.run(
            ["lsh", "get", "ALPACA_API_KEY"],
            capture_output=True, text=True
        ).stdout.strip()
        alpaca_secret = subprocess.run(
            ["lsh", "get", "ALPACA_SECRET_KEY"],
            capture_output=True, text=True
        ).stdout.strip()

        if alpaca_key and alpaca_secret:
            # Get account info from Alpaca
            response = httpx.get(
                "https://paper-api.alpaca.markets/v2/account",
                headers={
                    "APCA-API-KEY-ID": alpaca_key,
                    "APCA-API-SECRET-KEY": alpaca_secret
                },
                timeout=10.0
            )

            if response.status_code == 200:
                acct = response.json()
                click.echo(f"\n[Reference Portfolio - ENV VARS]")
                click.echo(f"  API Key: {alpaca_key[:8]}...{alpaca_key[-4:]}")
                click.echo(f"  Account: {acct.get('account_number', '?')}")
                click.echo(f"  Equity:  ${float(acct.get('equity', 0)):,.2f}")
                click.echo(f"  Cash:    ${float(acct.get('cash', 0)):,.2f}")
                click.echo(f"  Status:  {acct.get('status', '?')}")
            else:
                click.echo(f"\n[Reference Portfolio - ENV VARS]")
                click.echo(f"  API Key: {alpaca_key[:8]}... (invalid)")
        else:
            click.echo("\n[Reference Portfolio - ENV VARS]")
            click.echo("  Not configured")
    except Exception as e:
        click.echo(f"\n[Reference Portfolio - ENV VARS]")
        click.echo(f"  Error: {e}")

    # Get user credentials from database
    if service_key:
        try:
            response = httpx.get(
                f"{SUPABASE_URL}/rest/v1/user_api_keys?select=user_email,paper_api_key",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                users = response.json()
                click.echo(f"\n[User Accounts - Database]")

                if not users:
                    click.echo("  No user accounts configured")
                else:
                    for user in users:
                        email = user.get("user_email", "?")
                        key = user.get("paper_api_key")
                        if key:
                            # Check if same as env var
                            same_as_ref = " (SAME AS REFERENCE!)" if key == alpaca_key else ""
                            click.echo(f"  {email}: {key[:8]}...{key[-4:]}{same_as_ref}")
                        else:
                            click.echo(f"  {email}: Not connected")
        except Exception as e:
            click.echo(f"\n[User Accounts - Database]")
            click.echo(f"  Error: {e}")

    click.echo("\n" + "=" * 60)
    click.echo("To separate accounts:")
    click.echo("  1. Create new Alpaca paper account at https://app.alpaca.markets")
    click.echo("  2. Run: mcli run jobs alpaca-set-reference <api_key> <secret_key>")
    click.echo("  3. Run: mcli run jobs alpaca-reset-portfolio")


@app.command("alpaca-set-reference")
@click.argument("api_key")
@click.argument("secret_key")
def alpaca_set_reference(api_key: str, secret_key: str):
    """
    Set new Alpaca credentials for the Reference Portfolio.

    Creates/updates the ALPACA_API_KEY and ALPACA_SECRET_KEY in lsh.

    Example: mcli run jobs alpaca-set-reference PKABC123 secretkey456
    """
    import subprocess

    click.echo("Validating new credentials...")

    # Test the new credentials
    response = httpx.get(
        "https://paper-api.alpaca.markets/v2/account",
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        },
        timeout=10.0
    )

    if response.status_code != 200:
        click.echo(f"Error: Invalid credentials (HTTP {response.status_code})", err=True)
        raise SystemExit(1)

    acct = response.json()
    click.echo(f"✓ Valid credentials for account {acct.get('account_number')}")
    click.echo(f"  Equity: ${float(acct.get('equity', 0)):,.2f}")

    # Store in lsh
    click.echo("\nStoring credentials in lsh...")
    subprocess.run(["lsh", "set", "ALPACA_API_KEY", api_key], check=True)
    subprocess.run(["lsh", "set", "ALPACA_SECRET_KEY", secret_key], check=True)

    click.echo("✓ Credentials stored")
    click.echo("\nNext steps:")
    click.echo("  1. Redeploy edge functions: supabase functions deploy reference-portfolio")
    click.echo("  2. Reset portfolio state: mcli run jobs alpaca-reset-portfolio")


@app.command("alpaca-reset-portfolio")
@click.option("--initial-capital", "-c", type=float, default=100000.0, help="Initial capital amount")
@click.confirmation_option(prompt="This will reset all portfolio data. Continue?")
def alpaca_reset_portfolio(initial_capital: float):
    """
    Reset the reference portfolio to initial state.

    Clears all positions, snapshots, and resets state to initial capital.
    Use after switching to a new Alpaca account.

    Example: mcli run jobs alpaca-reset-portfolio -c 100000
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json"
    }

    click.echo(f"Resetting portfolio to ${initial_capital:,.2f}...")

    # Clear positions
    response = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/reference_portfolio_positions?is_open=eq.true",
        headers=headers,
        timeout=30.0
    )
    click.echo(f"  Cleared open positions: HTTP {response.status_code}")

    # Clear snapshots
    response = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/reference_portfolio_snapshots?snapshot_date=gte.2020-01-01",
        headers=headers,
        timeout=30.0
    )
    click.echo(f"  Cleared snapshots: HTTP {response.status_code}")

    # Reset state
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    response = httpx.patch(
        f"{SUPABASE_URL}/rest/v1/reference_portfolio_state?id=eq.13a769e8-b323-408b-a3e0-548b5256d215",
        headers=headers,
        json={
            "cash": initial_capital,
            "portfolio_value": initial_capital,
            "positions_value": 0,
            "buying_power": initial_capital,
            "total_return": 0,
            "total_return_pct": 0,
            "day_return": 0,
            "day_return_pct": 0,
            "max_drawdown": 0,
            "current_drawdown": 0,
            "total_trades": 0,
            "trades_today": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "open_positions": 0,
            "peak_portfolio_value": initial_capital
        },
        timeout=30.0
    )
    click.echo(f"  Reset state: HTTP {response.status_code}")

    # Create initial snapshot
    response = httpx.post(
        f"{SUPABASE_URL}/rest/v1/reference_portfolio_snapshots",
        headers=headers,
        json={
            "snapshot_date": today,
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
            "portfolio_value": initial_capital,
            "cash": initial_capital,
            "positions_value": 0,
            "day_return": 0,
            "day_return_pct": 0,
            "cumulative_return": 0,
            "cumulative_return_pct": 0,
            "open_positions": 0,
            "total_trades": 0
        },
        timeout=30.0
    )
    click.echo(f"  Created initial snapshot: HTTP {response.status_code}")

    click.echo(f"\n✓ Portfolio reset to ${initial_capital:,.2f}")
    click.echo("\nThe reference portfolio is now ready to trade with new credentials.")
