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
            last_sync_ago = format_time_ago(last_sync)

            # Calculate days since last sync
            days_since_sync = None
            if last_sync:
                try:
                    sync_dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
                    days_since_sync = (datetime.now(timezone.utc) - sync_dt).days
                except (ValueError, TypeError):
                    pass

            # Header with status indicator
            if days_since_sync and days_since_sync > 7:
                click.echo(f"⚠️  Last data sync: {last_sync_ago}")
                click.echo(click.style(f"   Warning: No successful sync in {days_since_sync} days!", fg="yellow"))
            else:
                click.echo(f"Last data sync: {last_sync_ago}")

            if data.get("jobs"):
                click.echo("\nData collection jobs:")
                never_run = 0
                for job in data["jobs"]:
                    job_name = job.get("job_name", job.get("job_id", "?"))
                    last_run = format_time_ago(job.get("last_successful_run"))
                    if last_run == "never":
                        never_run += 1
                    click.echo(f"  {job_name:40} {last_run}")

                # Show warning if many jobs never ran
                if never_run > len(data["jobs"]) // 2:
                    click.echo(click.style(f"\n⚠️  {never_run}/{len(data['jobs'])} jobs have never run successfully", fg="yellow"))

            # Show suggestions if sync is stale
            if days_since_sync and days_since_sync > 7:
                click.echo("\nTroubleshooting:")
                click.echo("  1. Check Phoenix server logs: mcli run server logs --lines 50")
                click.echo("  2. Try running a job manually: mcli run jobs run sync-data")
                click.echo("  3. Check Supabase pg_cron jobs are enabled")
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
    click.echo("Service Health Check")
    click.echo("-" * 40)

    all_healthy = True

    # Check Phoenix and ETL services (public health endpoints)
    public_services = [
        ("Phoenix Server", PHOENIX_SERVER_URL, "/health"),
        ("ETL Service", ETL_SERVICE_URL, "/health"),
    ]

    for name, base_url, path in public_services:
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

    # Check Supabase (requires authentication)
    service_key = get_supabase_key()
    if service_key:
        try:
            response = httpx.get(
                f"{SUPABASE_URL}/rest/v1/dashboard_stats?select=id&limit=1",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}"
                },
                timeout=5.0
            )
            if response.status_code == 200:
                click.echo(f"✓ {'Supabase':20} healthy")
            else:
                click.echo(f"✗ {'Supabase':20} HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            click.echo(f"✗ {'Supabase':20} {str(e)[:30]}")
            all_healthy = False
    else:
        click.echo(f"✗ {'Supabase':20} No service key")
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


@app.command("regenerate-signals")
@click.option("--min-confidence", "-c", type=float, default=0.65, help="Minimum confidence threshold (default: 0.65)")
@click.option("--limit", "-l", type=int, default=100, help="Max signals to generate (default: 100)")
@click.option("--lookback-days", "-d", type=int, default=90, help="Lookback period in days (default: 90)")
def regenerate_signals(min_confidence: float, limit: int, lookback_days: int):
    """
    Regenerate trading signals with ML predictions.

    Creates fresh signals by analyzing recent congressional trading activity
    and blending heuristic scores with ML model predictions.

    Examples:
        mcli run jobs regenerate-signals
        mcli run jobs regenerate-signals -c 0.70 -l 50
        mcli run jobs regenerate-signals --lookback-days 180
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo(f"Regenerating signals (confidence >= {min_confidence}, limit {limit}, {lookback_days}d lookback)...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/trading-signals/regenerate-signals",
            json={
                "minConfidence": min_confidence,
                "limit": limit,
                "lookbackDays": lookback_days,
            },
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data.get("stats", {})
                click.echo(f"\n✓ {data.get('message', 'Signals regenerated')}")
                click.echo(f"\nStats:")
                click.echo(f"  Disclosures analyzed: {stats.get('totalDisclosures', 0)}")
                click.echo(f"  Unique tickers: {stats.get('uniqueTickers', 0)}")
                click.echo(f"  Signals generated: {stats.get('signalsGenerated', 0)}")
                click.echo(f"  ML predictions: {stats.get('mlPredictionCount', 0)}")
                click.echo(f"  ML enhanced: {stats.get('mlEnhancedCount', 0)}")
                click.echo(f"  Model: {stats.get('modelVersion', 'Unknown')}")

                # Show signal type breakdown from signals list
                signals = data.get("signals", [])
                if signals:
                    types = {}
                    for s in signals:
                        t = s.get("signal_type", "unknown")
                        types[t] = types.get(t, 0) + 1
                    click.echo("\nSignal Breakdown:")
                    for t, count in sorted(types.items(), key=lambda x: -x[1]):
                        click.echo(f"  {t}: {count}")

                    # Show confidence distribution
                    confidences = [s.get("confidence_score", 0) for s in signals]
                    if confidences:
                        click.echo(f"\nConfidence: avg={sum(confidences)/len(confidences):.3f}, "
                                   f"min={min(confidences):.3f}, max={max(confidences):.3f}")
            else:
                click.echo(f"Error: {data.get('error', 'Unknown error')}", err=True)
                raise SystemExit(1)
        else:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            click.echo(response.text[:300], err=True)
            raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("execute-signals")
def execute_signals():
    """
    Execute pending signals for the reference portfolio.

    Processes queued trading signals and executes trades via Alpaca.
    Only executes during market hours. The reference portfolio trades
    based on high-confidence ML-enhanced signals.

    Example: mcli run jobs execute-signals
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo("Executing reference portfolio signals...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/reference-portfolio",
            json={"action": "execute-signals"},
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                executed = data.get("executed", 0)
                skipped = data.get("skipped", 0)
                failed = data.get("failed", 0)
                message = data.get("message", "")

                if message:
                    click.echo(f"\n{message}")
                else:
                    click.echo(f"\n✓ Signal execution complete!")
                    click.echo(f"  Executed: {executed}")
                    click.echo(f"  Skipped: {skipped}")
                    click.echo(f"  Failed: {failed}")

                if data.get("results"):
                    click.echo("\nTrades executed:")
                    for result in data["results"][:10]:
                        click.echo(f"  {result.get('ticker')}: {result.get('shares')} shares @ ${result.get('price', 0):.2f}")
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


@app.command("train-model")
@click.option("--lookback-days", "-d", type=int, default=365, help="Training data lookback (default: 365)")
@click.option("--use-outcomes/--no-outcomes", default=True, help="Include outcome data in training (default: yes)")
@click.option("--outcome-weight", "-w", type=float, default=2.0, help="Weight multiplier for outcome samples (default: 2.0)")
@click.option("--wait/--no-wait", default=True, help="Wait for training to complete (default: yes)")
def train_model(lookback_days: int, use_outcomes: bool, outcome_weight: float, wait: bool):
    """
    Train a new ML model via the ETL service.

    Trains an XGBoost model on congressional trading data, optionally
    incorporating trade outcome data for feedback-aware learning.

    Examples:
        mcli run jobs train-model
        mcli run jobs train-model --lookback-days 180
        mcli run jobs train-model --no-outcomes
        mcli run jobs train-model --no-wait
    """
    import time as _time

    load_env()
    etl_api_key = os.environ.get("ETL_ADMIN_API_KEY") or os.environ.get("ETL_API_KEY", "")

    if not etl_api_key:
        click.echo("Error: No ETL API key found (set ETL_ADMIN_API_KEY or ETL_API_KEY)", err=True)
        raise SystemExit(1)

    click.echo(f"Training model (lookback={lookback_days}d, outcomes={use_outcomes}, weight={outcome_weight})...")

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/ml/train",
            json={
                "lookback_days": lookback_days,
                "use_outcomes": use_outcomes,
                "outcome_weight": outcome_weight,
                "triggered_by": "mcli",
            },
            headers={
                "Content-Type": "application/json",
                "X-API-Key": etl_api_key,
            },
            timeout=30.0
        )

        if response.status_code != 200:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            click.echo(response.text[:300], err=True)
            raise SystemExit(1)

        data = response.json()
        job_id = data.get("job_id")
        click.echo(f"Training job started: {job_id}")

        if not wait:
            click.echo(f"\nCheck status: mcli run etl ml status {job_id}")
            return

        # Poll for completion
        click.echo("Waiting for completion...")
        start = _time.time()
        max_wait = 300  # 5 minutes

        while _time.time() - start < max_wait:
            _time.sleep(10)
            try:
                status_resp = httpx.get(
                    f"{ETL_SERVICE_URL}/ml/train/{job_id}",
                    headers={"X-API-Key": etl_api_key},
                    timeout=10.0
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    job_status = status_data.get("status", "unknown")
                    elapsed = int(_time.time() - start)
                    click.echo(f"  [{elapsed}s] Status: {job_status}")

                    if job_status == "completed":
                        metrics = status_data.get("metrics", {})
                        model_id = status_data.get("model_id", "?")
                        click.echo(f"\n✓ Training complete!")
                        click.echo(f"  Model ID: {model_id}")
                        click.echo(f"  Accuracy: {metrics.get('accuracy', 0):.1%}")
                        click.echo(f"  F1 Score: {metrics.get('f1_weighted', 0):.3f}")
                        click.echo(f"  Samples: {metrics.get('training_samples', '?')}")
                        return

                    if job_status == "failed":
                        error = status_data.get("error", "Unknown error")
                        click.echo(f"\n✗ Training failed: {error}", err=True)
                        raise SystemExit(1)
            except httpx.HTTPError:
                pass

        click.echo(f"\n⚠ Timeout after {max_wait}s. Check: mcli run etl ml status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("record-outcomes")
def record_outcomes():
    """
    Record trading outcomes for closed positions.

    Links closed positions to their original signals and calculates:
    - Win/loss/breakeven classification
    - Return percentage and dollars
    - Holding period
    - Feature snapshot for correlation analysis

    Example: mcli run jobs record-outcomes
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo("Recording signal outcomes...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "record-outcomes"},
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                recorded = data.get("recorded", 0)
                summary = data.get("summary", {})
                click.echo(f"\n✓ Outcomes recorded: {recorded}")
                if summary:
                    click.echo(f"  Wins: {summary.get('wins', 0)}")
                    click.echo(f"  Losses: {summary.get('losses', 0)}")
                    click.echo(f"  Win Rate: {summary.get('winRate', 0)}%")
                    click.echo(f"  Avg Return: {summary.get('avgReturnPct', 0):.2f}%")
            else:
                click.echo(f"Error: {data.get('error', 'Unknown')}", err=True)
                raise SystemExit(1)
        else:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("analyze-features")
def analyze_features():
    """
    Analyze feature importance from trade outcomes.

    Calculates correlation between signal features and actual returns:
    - bipartisan → correlation with returns
    - politician_count → lift when high vs low
    - buy_sell_ratio → win rate comparison

    Results are stored for model weight adjustment recommendations.

    Example: mcli run jobs analyze-features
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo("Analyzing feature importance...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "analyze-features", "windowDays": 90},
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                features = data.get("features", [])
                sample_size = data.get("sampleSize", 0)
                click.echo(f"\n✓ Feature Analysis Complete (sample size: {sample_size})")
                click.echo("\nFeature Importance:")
                click.echo("-" * 70)
                click.echo(f"{'Feature':<20} {'Correlation':<12} {'Lift %':<10} {'Useful':<8} {'Rec. Weight':<12}")
                click.echo("-" * 70)
                for f in features:
                    useful = "Yes" if f.get('feature_useful') else "No"
                    click.echo(
                        f"{f.get('feature_name', '?'):<20} "
                        f"{f.get('correlation_with_return', 0):>10.4f}  "
                        f"{f.get('lift_pct', 0):>8.2f}%  "
                        f"{useful:<8} "
                        f"{f.get('recommended_weight', 0):>10.4f}"
                    )
            else:
                msg = data.get("message", data.get("error", "Unknown"))
                click.echo(f"Note: {msg}")
        else:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("evaluate-model")
def evaluate_model():
    """
    Evaluate ML model performance from actual trade outcomes.

    Calculates performance metrics:
    - Win rate, average return, Sharpe ratio
    - Confidence calibration (high vs low confidence win rates)
    - Max drawdown

    Example: mcli run jobs evaluate-model
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo("Evaluating model performance...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "evaluate-model", "windowDays": 30},
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                perf = data.get("performance", {})
                breakdown = data.get("breakdown", {})
                click.echo(f"\n✓ Model Evaluation Complete")
                click.echo(f"\nModel: {perf.get('model_version', 'Unknown')}")
                click.echo(f"Evaluation Period: {perf.get('evaluation_window_days', 30)} days")
                click.echo("\nPerformance Metrics:")
                click.echo(f"  Win Rate: {perf.get('win_rate', 0) * 100:.1f}%")
                click.echo(f"  Avg Return: {perf.get('avg_return_pct', 0):.2f}%")
                click.echo(f"  Total Return: {perf.get('total_return_pct', 0):.2f}%")
                click.echo(f"  Sharpe Ratio: {perf.get('sharpe_ratio', 0):.2f}")
                click.echo(f"  Max Drawdown: {perf.get('max_drawdown_pct', 0):.2f}%")
                click.echo("\nConfidence Calibration:")
                click.echo(f"  High Confidence (>80%) Win Rate: {perf.get('high_confidence_win_rate', 0) * 100:.1f}%")
                click.echo(f"  Low Confidence (<70%) Win Rate: {perf.get('low_confidence_win_rate', 0) * 100:.1f}%")
                click.echo("\nBreakdown:")
                click.echo(f"  Wins: {breakdown.get('wins', 0)}")
                click.echo(f"  Losses: {breakdown.get('losses', 0)}")
                click.echo(f"  ML Enhanced: {breakdown.get('mlEnhancedCount', 0)}")
            else:
                msg = data.get("message", data.get("error", "Unknown"))
                click.echo(f"Note: {msg}")
        else:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("feedback-summary")
def feedback_summary():
    """
    Get summary of the ML feedback loop.

    Shows overall statistics:
    - Total outcomes recorded
    - Win/loss breakdown
    - Latest feature importance
    - Latest model performance

    Example: mcli run jobs feedback-summary
    """
    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    click.echo("Getting feedback loop summary...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "get-summary"},
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                summary = data.get("summary", {})
                features = data.get("latestFeatureImportance", [])
                perf = data.get("latestModelPerformance")

                click.echo("\n" + "=" * 60)
                click.echo("ML FEEDBACK LOOP SUMMARY")
                click.echo("=" * 60)

                click.echo("\nOutcome Tracking:")
                click.echo(f"  Total Outcomes: {summary.get('totalOutcomes', 0)}")
                click.echo(f"  Closed Trades: {summary.get('closedTrades', 0)}")
                click.echo(f"  Wins: {summary.get('wins', 0)}")
                click.echo(f"  Losses: {summary.get('losses', 0)}")
                click.echo(f"  Win Rate: {summary.get('winRate', 0)}%")
                click.echo(f"  Open Positions: {summary.get('openPositions', 0)}")

                if features:
                    click.echo("\nTop Predictive Features:")
                    for f in features[:3]:
                        useful = "✓" if f.get('feature_useful') else "✗"
                        click.echo(f"  {useful} {f.get('feature_name')}: correlation={f.get('correlation_with_return', 0):.3f}")

                if perf:
                    click.echo(f"\nLatest Model Performance ({perf.get('evaluation_date', '?')}):")
                    click.echo(f"  Win Rate: {perf.get('win_rate', 0) * 100:.1f}%")
                    click.echo(f"  Sharpe Ratio: {perf.get('sharpe_ratio', 0):.2f}")
            else:
                click.echo(f"Error: {data.get('error', 'Unknown')}", err=True)
        else:
            click.echo(f"Failed: HTTP {response.status_code}", err=True)
            raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@app.command("test-feedback-loop")
@click.option("--seed", is_flag=True, help="Seed test data if no outcomes exist")
@click.option("--seed-count", default=10, help="Number of test records to seed (default: 10)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output for each step")
def test_feedback_loop(seed: bool, seed_count: int, verbose: bool):
    """
    Test the entire ML feedback loop end-to-end.

    Runs all feedback loop stages in sequence:
    1. Check prerequisites (signals, positions)
    2. Record outcomes from closed positions
    3. Analyze feature importance
    4. Evaluate model performance
    5. Display comprehensive summary

    Use --seed to create test data if no closed positions exist.

    Example: mcli run jobs test-feedback-loop
    Example: mcli run jobs test-feedback-loop --seed --verbose
    """
    import time

    service_key = get_supabase_key()
    if not service_key:
        click.echo("Error: Could not get Supabase service key", err=True)
        raise SystemExit(1)

    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json"
    }

    click.echo("\n" + "=" * 70)
    click.echo("  ML FEEDBACK LOOP - END-TO-END TEST")
    click.echo("=" * 70)

    results = {
        "prerequisites": None,
        "outcomes_recorded": None,
        "features_analyzed": None,
        "model_evaluated": None
    }

    # =========================================================================
    # STEP 1: Check Prerequisites
    # =========================================================================
    click.echo("\n[1/5] Checking prerequisites...")

    try:
        # Check for signals
        signals_resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/trading_signals?select=count&limit=1",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Prefer": "count=exact"
            },
            timeout=30.0
        )
        signal_count = int(signals_resp.headers.get("content-range", "0-0/0").split("/")[-1])

        # Check for positions
        positions_resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/reference_portfolio_positions?select=id,is_open&limit=100",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key
            },
            timeout=30.0
        )
        positions = positions_resp.json() if positions_resp.status_code == 200 else []
        open_positions = len([p for p in positions if p.get("is_open")])
        closed_positions = len([p for p in positions if not p.get("is_open")])

        # Check for existing outcomes
        outcomes_resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/signal_outcomes?select=count&limit=1",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Prefer": "count=exact"
            },
            timeout=30.0
        )
        outcome_count = int(outcomes_resp.headers.get("content-range", "0-0/0").split("/")[-1])

        click.echo(f"      Signals in database: {signal_count}")
        click.echo(f"      Open positions: {open_positions}")
        click.echo(f"      Closed positions: {closed_positions}")
        click.echo(f"      Existing outcomes: {outcome_count}")

        results["prerequisites"] = {
            "signals": signal_count,
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "existing_outcomes": outcome_count
        }

        if closed_positions == 0 and not seed:
            click.echo("\n      ⚠ No closed positions to analyze.")
            click.echo("        Use --seed to create test data, or wait for positions to close.")

        click.echo("      ✓ Prerequisites checked")

    except Exception as e:
        click.echo(f"      ✗ Failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()

    # =========================================================================
    # STEP 2: Seed Test Data (if requested and needed)
    # =========================================================================
    # Seed if requested and we have fewer than 10 outcomes (minimum for analysis)
    if seed and results["prerequisites"] and results["prerequisites"]["existing_outcomes"] < 10:
        click.echo(f"\n[2/5] Seeding test data ({seed_count} records)...")
        import random

        # Test scenarios with varied feature values and outcomes
        test_scenarios = [
            # High politician count, bipartisan - should correlate with success
            {"pol_count": 8, "buy_sell": 3.0, "bipartisan": True, "activity": 15, "volume": 80000, "return_pct": 5.5},
            {"pol_count": 10, "buy_sell": 2.8, "bipartisan": True, "activity": 20, "volume": 100000, "return_pct": 7.2},
            {"pol_count": 6, "buy_sell": 2.5, "bipartisan": True, "activity": 12, "volume": 60000, "return_pct": 3.1},
            # High politician count, not bipartisan - mixed results
            {"pol_count": 7, "buy_sell": 2.0, "bipartisan": False, "activity": 10, "volume": 50000, "return_pct": 2.0},
            {"pol_count": 9, "buy_sell": 1.5, "bipartisan": False, "activity": 8, "volume": 45000, "return_pct": -1.5},
            # Low politician count - generally worse
            {"pol_count": 2, "buy_sell": 1.2, "bipartisan": False, "activity": 3, "volume": 10000, "return_pct": -2.5},
            {"pol_count": 1, "buy_sell": 1.0, "bipartisan": False, "activity": 1, "volume": 5000, "return_pct": -4.0},
            {"pol_count": 3, "buy_sell": 1.8, "bipartisan": True, "activity": 5, "volume": 20000, "return_pct": 1.0},
            # Edge cases
            {"pol_count": 5, "buy_sell": 2.2, "bipartisan": True, "activity": 8, "volume": 40000, "return_pct": 4.5},
            {"pol_count": 4, "buy_sell": 1.3, "bipartisan": False, "activity": 4, "volume": 15000, "return_pct": -0.8},
        ]

        seeded_count = 0
        try:
            for i in range(min(seed_count, len(test_scenarios))):
                scenario = test_scenarios[i]
                ticker = f"TEST{i+1}"

                # Create test signal with features
                test_signal = {
                    "ticker": ticker,
                    "signal_type": "buy",
                    "confidence_score": 0.5 + (scenario["pol_count"] / 20),  # Higher pol count = higher confidence
                    "features": {
                        "politician_count": scenario["pol_count"],
                        "buy_sell_ratio": scenario["buy_sell"],
                        "bipartisan": scenario["bipartisan"],
                        "recent_activity_30d": scenario["activity"],
                        "net_volume": scenario["volume"]
                    },
                    "model_version": "test-v1",
                    "ml_enhanced": True,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }

                signal_resp = httpx.post(
                    f"{SUPABASE_URL}/rest/v1/trading_signals",
                    json=test_signal,
                    headers={
                        "Authorization": f"Bearer {service_key}",
                        "apikey": service_key,
                        "Content-Type": "application/json",
                        "Prefer": "return=representation"
                    },
                    timeout=30.0
                )

                if signal_resp.status_code in (200, 201):
                    signal_data = signal_resp.json()
                    signal_id = signal_data[0]["id"] if isinstance(signal_data, list) else signal_data.get("id")

                    # Calculate prices from return percentage
                    entry_price = 100.00
                    exit_price = entry_price * (1 + scenario["return_pct"] / 100)
                    exit_reason = "take_profit" if scenario["return_pct"] > 0 else "stop_loss"

                    # Create test closed position
                    test_position = {
                        "ticker": ticker,
                        "entry_signal_id": signal_id,
                        "entry_price": entry_price,
                        "exit_price": round(exit_price, 2),
                        "quantity": 10,
                        "entry_date": (datetime.now(timezone.utc).replace(day=1)).isoformat(),
                        "exit_date": datetime.now(timezone.utc).isoformat(),
                        "is_open": False,
                        "exit_reason": exit_reason,
                        "entry_confidence": test_signal["confidence_score"]
                    }

                    pos_resp = httpx.post(
                        f"{SUPABASE_URL}/rest/v1/reference_portfolio_positions",
                        json=test_position,
                        headers={
                            "Authorization": f"Bearer {service_key}",
                            "apikey": service_key,
                            "Content-Type": "application/json",
                            "Prefer": "return=representation"
                        },
                        timeout=30.0
                    )

                    if pos_resp.status_code in (200, 201):
                        seeded_count += 1
                        if verbose:
                            result = "win" if scenario["return_pct"] > 0.5 else ("loss" if scenario["return_pct"] < -0.5 else "even")
                            click.echo(f"      [{i+1}] {ticker}: {scenario['return_pct']:+.1f}% ({result}) - pol={scenario['pol_count']}, bipartisan={scenario['bipartisan']}")

            click.echo(f"      Created {seeded_count} test positions")
            results["prerequisites"]["closed_positions"] = seeded_count
            click.echo("      ✓ Test data seeded")

        except Exception as e:
            click.echo(f"      ✗ Seeding failed: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
    else:
        click.echo("\n[2/5] Seeding test data... (skipped)")

    # =========================================================================
    # STEP 3: Record Outcomes
    # =========================================================================
    click.echo("\n[3/5] Recording signal outcomes...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "record-outcomes"},
            headers=headers,
            timeout=60.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                recorded = data.get("recorded", 0)
                summary = data.get("summary", {})
                results["outcomes_recorded"] = {
                    "recorded": recorded,
                    "wins": summary.get("wins", 0),
                    "losses": summary.get("losses", 0),
                    "win_rate": summary.get("winRate", 0)
                }

                if recorded > 0:
                    click.echo(f"      Recorded: {recorded} outcomes")
                    click.echo(f"      Wins: {summary.get('wins', 0)}, Losses: {summary.get('losses', 0)}")
                    click.echo(f"      Win Rate: {summary.get('winRate', 0)}%")
                else:
                    msg = data.get("message", "No new outcomes to record")
                    click.echo(f"      {msg}")

                click.echo("      ✓ Outcome recording complete")
            else:
                click.echo(f"      Note: {data.get('message', data.get('error', 'Unknown'))}")
        else:
            click.echo(f"      ✗ HTTP {response.status_code}: {response.text[:200]}", err=True)

    except Exception as e:
        click.echo(f"      ✗ Failed: {e}", err=True)

    time.sleep(0.5)  # Brief pause between API calls

    # =========================================================================
    # STEP 4: Analyze Features
    # =========================================================================
    click.echo("\n[4/5] Analyzing feature importance...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "analyze-features", "windowDays": 90},
            headers=headers,
            timeout=120.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                features = data.get("features", [])
                sample_size = data.get("sampleSize", 0)

                if features:
                    results["features_analyzed"] = {
                        "count": len(features),
                        "sample_size": sample_size,
                        "features": features
                    }

                    click.echo(f"      Analyzed {len(features)} features (sample: {sample_size})")

                    if verbose:
                        click.echo("\n      Feature Correlations:")
                        click.echo("      " + "-" * 60)
                        for f in features:
                            useful = "✓" if f.get("feature_useful") else "✗"
                            click.echo(
                                f"      {useful} {f.get('feature_name', '?'):<20} "
                                f"corr={f.get('correlation_with_return', 0):>7.4f}  "
                                f"lift={f.get('lift_pct', 0):>6.2f}%"
                            )
                        click.echo("      " + "-" * 60)

                    # Highlight top feature
                    if features:
                        top = max(features, key=lambda x: abs(x.get("correlation_with_return", 0)))
                        click.echo(f"      Top feature: {top.get('feature_name')} (corr: {top.get('correlation_with_return', 0):.4f})")

                    click.echo("      ✓ Feature analysis complete")
                else:
                    msg = data.get("message", "Not enough data for analysis")
                    click.echo(f"      {msg}")
            else:
                click.echo(f"      Note: {data.get('message', data.get('error', 'Unknown'))}")
        else:
            click.echo(f"      ✗ HTTP {response.status_code}", err=True)

    except Exception as e:
        click.echo(f"      ✗ Failed: {e}", err=True)

    time.sleep(0.5)

    # =========================================================================
    # STEP 5: Evaluate Model
    # =========================================================================
    click.echo("\n[5/5] Evaluating model performance...")

    try:
        response = httpx.post(
            f"{SUPABASE_URL}/functions/v1/signal-feedback",
            json={"action": "evaluate-model", "windowDays": 30},
            headers=headers,
            timeout=60.0
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                perf = data.get("performance", {})
                breakdown = data.get("breakdown", {})

                if perf:
                    results["model_evaluated"] = {
                        "win_rate": perf.get("win_rate", 0),
                        "avg_return": perf.get("avg_return_pct", 0),
                        "sharpe_ratio": perf.get("sharpe_ratio", 0),
                        "max_drawdown": perf.get("max_drawdown_pct", 0)
                    }

                    click.echo(f"      Win Rate: {perf.get('win_rate', 0) * 100:.1f}%")
                    click.echo(f"      Avg Return: {perf.get('avg_return_pct', 0):.2f}%")
                    click.echo(f"      Sharpe Ratio: {perf.get('sharpe_ratio', 0):.2f}")

                    if verbose:
                        click.echo(f"      Max Drawdown: {perf.get('max_drawdown_pct', 0):.2f}%")
                        click.echo(f"      High Conf Win Rate: {perf.get('high_confidence_win_rate', 0) * 100:.1f}%")
                        click.echo(f"      Low Conf Win Rate: {perf.get('low_confidence_win_rate', 0) * 100:.1f}%")

                    click.echo("      ✓ Model evaluation complete")
                else:
                    msg = data.get("message", "Not enough data for evaluation")
                    click.echo(f"      {msg}")
            else:
                click.echo(f"      Note: {data.get('message', data.get('error', 'Unknown'))}")
        else:
            click.echo(f"      ✗ HTTP {response.status_code}", err=True)

    except Exception as e:
        click.echo(f"      ✗ Failed: {e}", err=True)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    click.echo("\n" + "=" * 70)
    click.echo("  TEST SUMMARY")
    click.echo("=" * 70)

    steps_passed = 0
    total_steps = 4

    # Prerequisites
    if results["prerequisites"]:
        click.echo("  ✓ Prerequisites: OK")
        steps_passed += 1
    else:
        click.echo("  ✗ Prerequisites: FAILED")

    # Outcomes
    if results["outcomes_recorded"] is not None:
        recorded = results["outcomes_recorded"].get("recorded", 0)
        click.echo(f"  ✓ Outcomes: {recorded} recorded")
        steps_passed += 1
    else:
        click.echo("  - Outcomes: No new outcomes")
        steps_passed += 1  # Not a failure, just no data

    # Features
    if results["features_analyzed"]:
        count = results["features_analyzed"].get("count", 0)
        click.echo(f"  ✓ Features: {count} analyzed")
        steps_passed += 1
    else:
        click.echo("  - Features: Insufficient data")

    # Model
    if results["model_evaluated"]:
        wr = results["model_evaluated"].get("win_rate", 0) * 100
        click.echo(f"  ✓ Model: {wr:.1f}% win rate")
        steps_passed += 1
    else:
        click.echo("  - Model: Insufficient data")

    click.echo("=" * 70)
    status = "PASS" if steps_passed >= 2 else "NEEDS DATA"
    click.echo(f"  Result: {status} ({steps_passed}/{total_steps} steps with data)")
    click.echo("=" * 70)

    # Recommendations
    if results["prerequisites"]:
        prereqs = results["prerequisites"]
        if prereqs["closed_positions"] == 0:
            click.echo("\n  💡 Tip: Wait for positions to close, or use --seed for test data")
        elif prereqs["existing_outcomes"] < 10:
            click.echo("\n  💡 Tip: Need ~10+ outcomes for meaningful feature analysis")

    if results["features_analyzed"]:
        features = results["features_analyzed"].get("features", [])
        useful = [f for f in features if f.get("feature_useful")]
        if len(useful) < len(features) // 2:
            click.echo("\n  💡 Insight: Less than half of features show predictive value")
            click.echo("             Consider adjusting model weights in next retraining")

    click.echo("")


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
