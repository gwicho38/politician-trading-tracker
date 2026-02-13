"""ETL commands for politician trading data ingestion and ML training."""

import os
import time
import subprocess
import click
import httpx
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table

console = Console()

# ETL service configuration
ETL_DIR = Path(__file__).parent.parent.parent / "python-etl-service"
ETL_SERVICE_URL = os.environ.get(
    "ETL_SERVICE_URL",
    "https://politician-trading-etl.fly.dev"
)
FLY_APP = "politician-trading-etl"


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


@click.group(name="etl")
def etl():
    """ETL commands for data ingestion."""
    pass


@etl.command(name="trigger")
@click.argument("year", type=int)
@click.option("--limit", "-l", type=int, default=None, help="Limit PDFs to process (for testing)")
@click.option("--wait", "-w", is_flag=True, help="Wait for job to complete")
@click.option("--update", "-u", is_flag=True, help="Update mode: re-parse and update existing records")
def trigger(year: int, limit: int | None, wait: bool, update: bool):
    """
    Trigger ETL job for a specific year.

    Examples:
        mcli run etl trigger 2024              # Normal mode (skip duplicates)
        mcli run etl trigger 2024 --update     # Update mode (re-parse all)
        mcli run etl trigger 2024 -l 10 -u     # Update first 10 PDFs
    """
    mode_str = " (UPDATE MODE)" if update else ""
    click.echo(f"Triggering ETL for year {year}{mode_str}...")

    payload = {"source": "house", "year": year, "update_mode": update}
    if limit:
        payload["limit"] = limit

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/etl/trigger",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data["job_id"]
        click.echo(f"Job started: {job_id}")
        click.echo(f"Message: {data['message']}")

        if wait:
            click.echo("\nWaiting for completion...")
            _wait_for_job(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="status")
@click.argument("job_id")
@click.option("--watch", "-w", is_flag=True, help="Watch job progress until completion")
def status(job_id: str, watch: bool):
    """
    Check status of an ETL job.

    Example: mcli run etl status <job_id>
    """
    if watch:
        _wait_for_job(job_id)
    else:
        _show_status(job_id)


def _show_status(job_id: str) -> dict:
    """Show status of a job and return the status data."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/etl/status/{job_id}",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        status = data["status"]
        progress = data.get("progress", 0)
        total = data.get("total", 0)
        message = data.get("message", "")

        if total:
            pct = (progress / total * 100) if total else 0
            click.echo(f"Status: {status} | Progress: {progress}/{total} ({pct:.1f}%) | {message}")
        else:
            click.echo(f"Status: {status} | {message}")

        return data

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        return {"status": "error"}


def _wait_for_job(job_id: str):
    """Wait for job to complete, showing progress."""
    while True:
        data = _show_status(job_id)
        status = data.get("status", "unknown")

        if status in ("completed", "failed", "error"):
            if status == "completed":
                click.echo("\nJob completed successfully!")
            else:
                click.echo(f"\nJob ended with status: {status}")
            break

        time.sleep(5)


@etl.command(name="ingest-range")
@click.argument("start_year", type=int)
@click.argument("end_year", type=int)
@click.option("--limit", "-l", type=int, default=None, help="Limit PDFs per year (for testing)")
@click.option("--sequential", "-s", is_flag=True, help="Wait for each year to complete before starting next")
@click.option("--update", "-u", is_flag=True, help="Update mode: re-parse and update existing records")
def ingest_range(start_year: int, end_year: int, limit: int | None, sequential: bool, update: bool):
    """
    Trigger ETL for a range of years.

    Examples:
        mcli run etl ingest-range 2016 2024           # Normal mode
        mcli run etl ingest-range 2016 2024 --update  # Update all years
    """
    if start_year > end_year:
        click.echo("Error: start_year must be <= end_year", err=True)
        raise SystemExit(1)

    years = list(range(start_year, end_year + 1))
    mode_str = " (UPDATE MODE)" if update else ""
    click.echo(f"Triggering ETL for years: {years}{mode_str}")

    job_ids = {}

    for year in years:
        click.echo(f"\n{'='*50}")
        click.echo(f"Starting ETL for {year}{mode_str}...")

        payload = {"source": "house", "year": year, "update_mode": update}
        if limit:
            payload["limit"] = limit

        try:
            response = httpx.post(
                f"{ETL_SERVICE_URL}/etl/trigger",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            job_id = data["job_id"]
            job_ids[year] = job_id
            click.echo(f"Job ID: {job_id}")

            if sequential:
                click.echo("Waiting for completion...")
                _wait_for_job(job_id)

        except httpx.HTTPError as e:
            click.echo(f"Error starting {year}: {e}", err=True)

    click.echo(f"\n{'='*50}")
    click.echo("Summary of jobs:")
    for year, job_id in job_ids.items():
        click.echo(f"  {year}: {job_id}")

    if not sequential:
        click.echo("\nTo check status: mcli run etl status <job_id>")


@etl.command(name="update")
@click.argument("year", type=int)
@click.option("--limit", "-l", type=int, default=None, help="Limit PDFs to process (for testing)")
@click.option("--wait", "-w", is_flag=True, help="Wait for job to complete")
def update(year: int, limit: int | None, wait: bool):
    """
    Re-parse and update existing records for a year.

    This is a shortcut for 'trigger --update'. It re-downloads PDFs,
    re-parses them with the latest parsing logic, and updates existing
    database records.

    Examples:
        mcli run etl update 2025              # Update all 2025 records
        mcli run etl update 2025 -l 10 -w     # Update first 10, wait for completion
    """
    click.echo(f"🔄 Updating ETL records for year {year}...")

    payload = {"source": "house", "year": year, "update_mode": True}
    if limit:
        payload["limit"] = limit

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/etl/trigger",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data["job_id"]
        click.echo(f"Job started: {job_id}")
        click.echo(f"Message: {data['message']}")

        if wait:
            click.echo("\nWaiting for completion...")
            _wait_for_job(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="check-years")
@click.option("--start", "-s", type=int, default=2008, help="Start year to check")
@click.option("--end", "-e", type=int, default=2025, help="End year to check")
def check_years(start: int, end: int):
    """
    Check which years have PTR (Periodic Transaction Report) data available.

    The STOCK Act (2012) required more frequent disclosure. PTR filings
    started appearing around 2013-2014.

    Example: mcli run etl check-years
    """
    import io
    import zipfile

    click.echo(f"Checking PTR filing availability for years {start}-{end}...")
    click.echo("-" * 50)

    for year in range(start, end + 1):
        zip_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.ZIP"

        try:
            response = httpx.get(zip_url, timeout=30.0)

            if response.status_code == 404:
                click.echo(f"{year}: No data available (404)")
                continue

            response.raise_for_status()

            # Extract and check index file
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                txt_filename = f"{year}FD.txt"
                if txt_filename not in z.namelist():
                    click.echo(f"{year}: No index file found")
                    continue

                with z.open(txt_filename) as f:
                    content = f.read().decode("utf-8", errors="ignore")

                # Count PTR filings (filing_type = P)
                lines = content.strip().split("\n")
                ptr_count = sum(1 for line in lines if "\tP\t" in line)
                total_count = len(lines) - 1  # Exclude header

                if ptr_count > 0:
                    click.echo(f"{year}: {ptr_count} PTR filings (of {total_count} total)")
                else:
                    click.echo(f"{year}: 0 PTR filings ({total_count} annual disclosures only)")

        except Exception as e:
            click.echo(f"{year}: Error - {e}")


@etl.command(name="health")
def health():
    """Check ETL service health."""
    try:
        response = httpx.get(f"{ETL_SERVICE_URL}/health", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        click.echo(f"ETL Service: {data.get('status', 'unknown')}")
        click.echo(f"URL: {ETL_SERVICE_URL}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="ingest")
@click.argument("url")
@click.option("--name", "-n", default=None, help="Politician name (optional)")
@click.option("--dry-run", "-d", is_flag=True, help="Parse only, don't upload to database")
@click.option("--verbose", "-v", is_flag=True, help="Show full transaction details")
def ingest(url: str, name: str | None, dry_run: bool, verbose: bool):
    """
    Ingest a single disclosure PDF by URL.

    Useful for testing ETL parsing on specific filings.

    Examples:
        mcli run etl ingest https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033576.pdf
        mcli run etl ingest URL --dry-run  # Parse without uploading
        mcli run etl ingest URL --name "Nancy Pelosi"  # Override politician name
    """
    click.echo(f"Ingesting PDF: {url}")

    payload = {"url": url, "dry_run": dry_run}
    if name:
        payload["politician_name"] = name

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/etl/ingest-url",
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()

        # Show summary
        click.echo(f"\n{'='*60}")
        click.echo(f"Document ID: {data['doc_id']}")
        click.echo(f"Year: {data['year']}")
        click.echo(f"Politician: {data.get('politician_name', 'Unknown')}")
        if data.get('politician_id'):
            click.echo(f"Politician ID: {data['politician_id']}")
        click.echo(f"{'='*60}")
        click.echo(f"Transactions found: {data['transactions_found']}")

        if dry_run:
            click.echo(f"Dry run: transactions NOT uploaded")
        else:
            click.echo(f"Transactions uploaded: {data['transactions_uploaded']}")

        # Show transactions
        if data['transactions']:
            click.echo(f"\n{'─'*60}")
            click.echo("Transactions:")
            for i, txn in enumerate(data['transactions'], 1):
                ticker = txn.get('asset_ticker') or '-'
                asset = txn.get('asset_name', 'Unknown')[:40]
                tx_type = txn.get('transaction_type') or 'unknown'
                value_low = txn.get('value_low')
                value_high = txn.get('value_high')

                if value_low and value_high:
                    value_str = f"${value_low:,.0f} - ${value_high:,.0f}"
                else:
                    value_str = "-"

                click.echo(f"  {i:2}. [{ticker:5}] {asset:40} {tx_type:8} {value_str}")

                if verbose:
                    tx_date = txn.get('transaction_date', '-')
                    notif_date = txn.get('notification_date', '-')
                    click.echo(f"      Transaction: {tx_date}, Notification: {notif_date}")
        else:
            click.echo("\nNo transactions found in PDF.")

    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get('detail', str(e))
        except Exception:
            detail = str(e)
        click.echo(f"Error: {detail}", err=True)
        raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="enrich-parties")
@click.option("--limit", "-l", type=int, default=None, help="Limit politicians to process")
@click.option("--wait", "-w", is_flag=True, help="Wait for job to complete")
def enrich_parties(limit: int | None, wait: bool):
    """
    Trigger party enrichment job using Ollama LLM.

    This updates politicians with missing party data by querying
    the Ollama service to determine their political affiliation.

    Example: mcli run etl enrich-parties --limit 50 --wait
    """
    click.echo("Triggering party enrichment job...")

    payload = {}
    if limit:
        payload["limit"] = limit

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/enrichment/trigger",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data["job_id"]
        click.echo(f"Job started: {job_id}")
        click.echo(f"Message: {data['message']}")

        if wait:
            click.echo("\nWaiting for completion...")
            _wait_for_enrichment_job(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl enrich-status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="enrich-status")
@click.argument("job_id")
@click.option("--watch", "-w", is_flag=True, help="Watch job progress until completion")
def enrich_status(job_id: str, watch: bool):
    """
    Check status of a party enrichment job.

    Example: mcli run etl enrich-status <job_id>
    """
    if watch:
        _wait_for_enrichment_job(job_id)
    else:
        _show_enrichment_status(job_id)


def _show_enrichment_status(job_id: str) -> dict:
    """Show status of an enrichment job and return the status data."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/enrichment/status/{job_id}",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        status = data["status"]
        progress = data.get("progress", 0)
        total = data.get("total", 0)
        updated = data.get("updated", 0)
        skipped = data.get("skipped", 0)
        errors = data.get("errors", 0)
        message = data.get("message", "")

        if total:
            pct = (progress / total * 100) if total else 0
            click.echo(f"Status: {status} | Progress: {progress}/{total} ({pct:.1f}%)")
            click.echo(f"  Updated: {updated} | Skipped: {skipped} | Errors: {errors}")
            click.echo(f"  {message}")
        else:
            click.echo(f"Status: {status} | {message}")

        return data

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        return {"status": "error"}


def _wait_for_enrichment_job(job_id: str):
    """Wait for enrichment job to complete, showing progress."""
    while True:
        data = _show_enrichment_status(job_id)
        status = data.get("status", "unknown")

        if status in ("completed", "failed", "error"):
            if status == "completed":
                click.echo("\nJob completed successfully!")
                click.echo(f"  Updated: {data.get('updated', 0)} politicians")
                click.echo(f"  Skipped: {data.get('skipped', 0)} (could not determine)")
                click.echo(f"  Errors: {data.get('errors', 0)}")
            else:
                click.echo(f"\nJob ended with status: {status}")
            break

        time.sleep(5)


@etl.command(name="enrich-preview")
def enrich_preview():
    """
    Preview politicians that need party enrichment.

    Shows count and sample of politicians with missing party data.
    """
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/enrichment/preview",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total_missing_party", 0)
        sample = data.get("sample", [])

        click.echo(f"Politicians with missing party: {total}")
        click.echo("\nSample:")
        for p in sample:
            state = p.get("state") or "?"
            chamber = p.get("chamber") or "?"
            click.echo(f"  {p['full_name']} ({state}, {chamber})")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# Name Enrichment Commands (Ollama-based - PREFERRED)
# =============================================================================

@etl.command(name="enrich-names")
@click.option("--limit", "-l", type=int, default=None, help="Limit politicians to process")
@click.option("--wait", "-w", is_flag=True, help="Wait for job to complete")
def enrich_names(limit: int | None, wait: bool):
    """
    Trigger name enrichment job using Ollama LLM.

    This is the PREFERRED method for replacing placeholder names like
    "House Member (Placeholder)" with proper politician names extracted
    from raw disclosure data.

    Priority order:
    1. Ollama (this) - Extract names from raw_data
    2. Congress.gov API - Use BioGuide ID for official name
    3. Placeholder - Only if nothing else works

    Example: mcli run etl enrich-names --limit 10 --wait
    """
    click.echo("Triggering name enrichment job (Ollama)...")
    click.echo("This will replace placeholder names with proper politician names.\n")

    payload = {}
    if limit:
        payload["limit"] = limit

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/enrichment/name/trigger",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data["job_id"]
        click.echo(f"Job started: {job_id}")
        click.echo(f"Message: {data['message']}")

        if wait:
            click.echo("\nWaiting for completion...")
            _wait_for_name_enrichment_job(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl enrich-names-status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="enrich-names-status")
@click.argument("job_id")
@click.option("--watch", "-w", is_flag=True, help="Watch job progress until completion")
def enrich_names_status(job_id: str, watch: bool):
    """
    Check status of a name enrichment job.

    Example: mcli run etl enrich-names-status <job_id>
    """
    if watch:
        _wait_for_name_enrichment_job(job_id)
    else:
        _show_name_enrichment_status(job_id)


def _show_name_enrichment_status(job_id: str) -> dict:
    """Show status of a name enrichment job and return the status data."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/enrichment/name/status/{job_id}",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        status = data["status"]
        progress = data.get("progress", 0)
        total = data.get("total", 0)
        updated = data.get("updated", 0)
        skipped = data.get("skipped", 0)
        errors = data.get("errors", 0)
        message = data.get("message", "")

        if total:
            pct = (progress / total * 100) if total else 0
            click.echo(f"Status: {status} | Progress: {progress}/{total} ({pct:.1f}%)")
            click.echo(f"  Updated: {updated} | Skipped: {skipped} | Errors: {errors}")
            click.echo(f"  {message}")
        else:
            click.echo(f"Status: {status} | {message}")

        return data

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        return {"status": "error"}


def _wait_for_name_enrichment_job(job_id: str):
    """Wait for name enrichment job to complete, showing progress."""
    while True:
        data = _show_name_enrichment_status(job_id)
        status = data.get("status", "unknown")

        if status in ("completed", "failed", "error"):
            if status == "completed":
                click.echo("\nJob completed successfully!")
                click.echo(f"  Updated: {data.get('updated', 0)} politician names")
                click.echo(f"  Skipped: {data.get('skipped', 0)} (no raw_data or extraction failed)")
                click.echo(f"  Errors: {data.get('errors', 0)}")
            else:
                click.echo(f"\nJob ended with status: {status}")
            break

        time.sleep(5)


@etl.command(name="enrich-names-preview")
def enrich_names_preview():
    """
    Preview politicians with placeholder names that need enrichment.

    Shows politicians with names like "House Member (Placeholder)" that
    would be updated by the name enrichment job.
    """
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/enrichment/name/preview",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total_placeholder_names", 0)
        sample = data.get("sample", [])

        click.echo(f"Politicians with placeholder names: {total}")
        click.echo("\nSample:")
        for p in sample:
            party = p.get("party") or "?"
            state = p.get("state") or "?"
            click.echo(f"  {p['full_name']} ({party}, {state})")

        click.echo(f"\n{data.get('note', '')}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# Deployment Commands
# =============================================================================

@etl.command(name="deploy")
@click.option("--build-only", is_flag=True, help="Only build, don't deploy")
def deploy(build_only: bool):
    """
    Deploy Python ETL service to Fly.io.

    Example: mcli run etl deploy
    """
    click.echo(f"🐍 Deploying Python ETL service...")
    click.echo(f"Directory: {ETL_DIR}")

    if not ETL_DIR.exists():
        click.echo(f"Error: ETL directory not found: {ETL_DIR}", err=True)
        raise SystemExit(1)

    try:
        cmd = ["flyctl", "deploy", "--now"]
        if build_only:
            cmd = ["flyctl", "deploy", "--build-only"]

        result = subprocess.run(cmd, cwd=ETL_DIR)

        if result.returncode == 0:
            click.echo(f"\n✓ Deployment successful!")
            click.echo(f"URL: {ETL_SERVICE_URL}")
        else:
            click.echo(f"\n✗ Deployment failed (exit code {result.returncode})", err=True)
            raise SystemExit(1)

    except FileNotFoundError:
        click.echo("Error: flyctl not found. Install with: brew install flyctl", err=True)
        raise SystemExit(1)


@etl.command(name="logs")
@click.option("-n", "--lines", default=50, help="Number of lines to show")
@click.option("-f", "--follow", is_flag=True, help="Follow logs in real-time")
def logs(lines: int, follow: bool):
    """
    View ETL service logs from Fly.io.

    Examples:
        mcli run etl logs           # Last 50 lines
        mcli run etl logs -f        # Follow logs
        mcli run etl logs -n 100    # Last 100 lines
    """
    cmd = ["flyctl", "logs", "--app", FLY_APP]

    if follow:
        click.echo(f"Following ETL logs... (Ctrl+C to stop)")
    else:
        cmd.append("--no-tail")
        click.echo(f"Fetching last {lines} lines...")

    try:
        if follow:
            subprocess.run(cmd)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                log_lines = result.stdout.strip().split("\n")
                for line in log_lines[-lines:]:
                    click.echo(line)
            else:
                click.echo(f"Error: {result.stderr}", err=True)
    except FileNotFoundError:
        click.echo("Error: flyctl not found", err=True)
    except KeyboardInterrupt:
        click.echo("\nStopped following logs")


@etl.command(name="restart")
def restart():
    """Restart ETL service instances on Fly.io."""
    click.echo(f"🔄 Restarting {FLY_APP}...")

    try:
        result = subprocess.run(["flyctl", "apps", "restart", FLY_APP])
        if result.returncode == 0:
            click.echo("✓ Restart initiated")
        else:
            click.echo("✗ Restart failed", err=True)
    except FileNotFoundError:
        click.echo("Error: flyctl not found", err=True)


@etl.command(name="open")
def open_dashboard():
    """Open Fly.io dashboard for ETL service."""
    import webbrowser
    url = f"https://fly.io/apps/{FLY_APP}"
    click.echo(f"Opening {url}...")
    webbrowser.open(url)

# =============================================================================
# ML commands have been moved to ml.py
# Use: mcli run ml <command>
# =============================================================================


# =============================================================================
# Database Cleanup Commands
# =============================================================================

def get_supabase_keys():
    """Get Supabase URL and service role key from environment."""
    load_env()
    url = os.environ.get("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not service_key:
        # Try getting from lsh
        try:
            result = subprocess.run(
                ["lsh", "get", "SUPABASE_SERVICE_ROLE_KEY"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                service_key = result.stdout.strip()
        except FileNotFoundError:
            pass

    if not service_key:
        raise click.ClickException(
            "SUPABASE_SERVICE_ROLE_KEY not found. "
            "Set it in .env or via: lsh set SUPABASE_SERVICE_ROLE_KEY <key>"
        )

    return url, service_key


@etl.command(name="cleanup-bad-dates")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would be deleted without deleting")
def cleanup_bad_dates(dry_run: bool):
    """
    Delete records with invalid future dates (e.g., 2204 instead of 2024).

    These are typos in the original PDF that were faithfully parsed.

    Example:
        mcli run etl cleanup-bad-dates --dry-run  # Preview
        mcli run etl cleanup-bad-dates            # Delete
    """
    url, service_key = get_supabase_keys()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    # Find records with disclosure_date > 2030
    query_url = f"{url}/rest/v1/trading_disclosures?select=id,disclosure_date,asset_name&disclosure_date=gt.2030-01-01"

    try:
        response = httpx.get(query_url, headers=headers, timeout=30.0)
        response.raise_for_status()
        records = response.json()

        if not records:
            click.echo("No records with future dates found.")
            return

        click.echo(f"Found {len(records)} records with future dates:")
        for r in records[:10]:
            click.echo(f"  - {r['disclosure_date'][:10]}: {r['asset_name'][:50]}...")

        if len(records) > 10:
            click.echo(f"  ... and {len(records) - 10} more")

        if dry_run:
            click.echo("\nDry run - no changes made.")
            return

        # Delete
        delete_url = f"{url}/rest/v1/trading_disclosures?disclosure_date=gt.2030-01-01"
        response = httpx.delete(delete_url, headers=headers, timeout=30.0)
        response.raise_for_status()

        click.echo(f"\n✓ Deleted {len(records)} records with future dates.")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="cleanup-raw-pdf-text")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would be deleted without deleting")
@click.option("--pattern", "-p", default="F S: New", help="Pattern to match in asset_name")
def cleanup_raw_pdf_text(dry_run: bool, pattern: str):
    """
    Delete records where asset_name contains raw PDF metadata.

    These are duplicates from older ETL runs that didn't properly parse
    the PDF table columns.

    Common patterns:
        - "F S: New" (filing status metadata)
        - " P DD/DD/DDDD " (purchase + dates)
        - " S DD/DD/DDDD " (sale + dates)

    Examples:
        mcli run etl cleanup-raw-pdf-text --dry-run
        mcli run etl cleanup-raw-pdf-text --pattern "S: New"
    """
    url, service_key = get_supabase_keys()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    # URL-encode the pattern for ilike query
    import urllib.parse
    encoded_pattern = urllib.parse.quote(f"*{pattern}*")

    # Find matching records
    query_url = f"{url}/rest/v1/trading_disclosures?select=id,asset_name&asset_name=ilike.{encoded_pattern}&limit=500"

    try:
        response = httpx.get(query_url, headers=headers, timeout=30.0)
        response.raise_for_status()
        records = response.json()

        if not records:
            click.echo(f"No records matching pattern '{pattern}' found.")
            return

        click.echo(f"Found {len(records)} records containing '{pattern}':")
        for r in records[:5]:
            click.echo(f"  - {r['asset_name'][:70]}...")

        if len(records) > 5:
            click.echo(f"  ... and {len(records) - 5} more")

        if dry_run:
            click.echo("\nDry run - no changes made.")
            return

        # Delete
        delete_url = f"{url}/rest/v1/trading_disclosures?asset_name=ilike.{encoded_pattern}"
        response = httpx.delete(delete_url, headers=headers, timeout=30.0)
        response.raise_for_status()

        click.echo(f"\n✓ Deleted {len(records)} records matching '{pattern}'.")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="suggestions")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all reports (not just pending)")
@click.option("--status", "-s", type=str, default=None, help="Filter by status (pending, fixed, rejected)")
@click.option("--limit", "-l", type=int, default=50, help="Maximum number of reports to show")
def suggestions(show_all: bool, status: str | None, limit: int):
    """
    List open user error reports (auto-suggestions).

    Users can report data quality issues through the UI. This command
    shows pending reports that need admin review.

    Examples:
        mcli run etl suggestions              # Show pending reports
        mcli run etl suggestions --all        # Show all reports
        mcli run etl suggestions -s fixed     # Show fixed reports
    """
    url, service_key = get_supabase_keys()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    # Build query
    query_params = f"select=*&order=created_at.desc&limit={limit}"
    if status:
        query_params += f"&status=eq.{status}"
    elif not show_all:
        query_params += "&status=eq.pending"

    query_url = f"{url}/rest/v1/user_error_reports?{query_params}"

    try:
        response = httpx.get(query_url, headers=headers, timeout=30.0)
        response.raise_for_status()
        reports = response.json()

        if not reports:
            filter_desc = f"with status '{status}'" if status else ("" if show_all else "(pending)")
            click.echo(f"No user error reports found {filter_desc}.")
            return

        # Count by status if showing all
        status_filter = f" ({status})" if status else (" (all)" if show_all else " (pending)")
        click.echo(f"User Error Reports{status_filter}: {len(reports)}")
        click.echo("=" * 80)

        for r in reports:
            snapshot = r.get("disclosure_snapshot", {})
            politician = snapshot.get("politician_name", "Unknown")
            asset = snapshot.get("asset_name", "Unknown")[:50]
            ticker = snapshot.get("asset_ticker") or "-"
            error_type = r.get("error_type", "unknown")
            report_status = r.get("status", "unknown")
            created = r.get("created_at", "")[:10]
            description = r.get("description", "")[:100]

            # Status indicator
            status_icon = {
                "pending": "⏳",
                "fixed": "✓",
                "rejected": "✗",
                "reviewing": "👁"
            }.get(report_status, "?")

            report_id = r.get("id", "unknown")
            click.echo(f"\n{status_icon} [{report_status.upper():8}] {created}")
            click.echo(f"   ID: {report_id}")
            click.echo(f"   Politician: {politician}")
            click.echo(f"   Asset: [{ticker:5}] {asset}")
            click.echo(f"   Type: {error_type}")
            click.echo(f"   Description: {description}")

            if r.get("admin_notes"):
                click.echo(f"   Admin Notes: {r['admin_notes'][:80]}")

            source_url = snapshot.get("source_url", "")
            if source_url:
                click.echo(f"   Source: {source_url}")

        click.echo("\n" + "=" * 80)
        click.echo(f"Total: {len(reports)} report(s)")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="suggestions-review")
def suggestions_review():
    """
    List suggestions that need manual review.

    Shows reports where Ollama suggested corrections but confidence
    was below 80%, requiring human verification.

    Example: mcli run etl suggestions-review
    """
    click.echo("Fetching suggestions needing review...")

    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/error-reports/needs-review",
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        reports = data.get("reports", [])
        if not reports:
            click.echo("No suggestions needing review.")
            return

        click.echo(f"\nSuggestions Needing Review: {len(reports)}")
        click.echo("=" * 80)

        for r in reports:
            report_id = r.get("id", "?")[:8]
            snapshot = r.get("disclosure_snapshot", {})
            politician = snapshot.get("politician_name", "Unknown")
            asset = snapshot.get("asset_name", "Unknown")[:40]
            error_type = r.get("error_type", "unknown")
            description = r.get("description", "")[:80]
            admin_notes = r.get("admin_notes", "")

            click.echo(f"\n[{report_id}] {error_type}")
            click.echo(f"   Politician: {politician}")
            click.echo(f"   Asset: {asset}")
            click.echo(f"   User said: {description}")
            if admin_notes:
                click.echo(f"   Suggested: {admin_notes}")
            click.echo(f"   Full ID: {r.get('id')}")

        click.echo("\n" + "=" * 80)
        click.echo("To apply a suggestion:")
        click.echo("  mcli run etl suggestion-apply <report_id> <field> <new_value>")
        click.echo("  mcli run etl suggestion-reanalyze <report_id> --threshold 0.5")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="suggestion-apply")
@click.argument("report_id")
@click.argument("field")
@click.argument("new_value")
@click.option("--old-value", "-o", default=None, help="Original value (for logging)")
def suggestion_apply(report_id: str, field: str, new_value: str, old_value: str | None):
    """
    Manually apply a correction to a suggestion.

    Forces the correction regardless of confidence score.

    Examples:
        mcli run etl suggestion-apply abc123 politician_party D
        mcli run etl suggestion-apply abc123 amount_range_min 5000001
        mcli run etl suggestion-apply abc123 asset_ticker AAPL -o "?"
    """
    click.echo(f"Applying correction: {field} = {new_value}")

    # Parse new_value as number if it looks like one
    parsed_value: str | int | float = new_value
    try:
        if new_value.isdigit():
            parsed_value = int(new_value)
        elif new_value.replace(".", "", 1).isdigit():
            parsed_value = float(new_value)
    except (ValueError, AttributeError):
        pass

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/error-reports/force-apply",
            json={
                "report_id": report_id,
                "corrections": [
                    {"field": field, "new_value": parsed_value, "old_value": old_value}
                ]
            },
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            click.echo(f"✓ Correction applied successfully")
            click.echo(f"   {data.get('admin_notes', '')}")
        else:
            click.echo(f"✗ Failed to apply correction")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        if hasattr(e, 'response') and e.response is not None:
            click.echo(f"Details: {e.response.text}")
        raise SystemExit(1)


@etl.command(name="suggestion-reanalyze")
@click.argument("report_id")
@click.option("--threshold", "-t", type=float, default=0.5,
              help="Confidence threshold (default 0.5, normal is 0.8)")
@click.option("--dry-run", "-d", is_flag=True, help="Preview without applying")
def suggestion_reanalyze(report_id: str, threshold: float, dry_run: bool):
    """
    Reanalyze a suggestion with a lower confidence threshold.

    Useful for applying corrections that were just under the 80% threshold.

    Examples:
        mcli run etl suggestion-reanalyze abc123 --threshold 0.6
        mcli run etl suggestion-reanalyze abc123 -t 0.5 --dry-run
    """
    mode = "DRY RUN" if dry_run else "APPLYING"
    click.echo(f"Reanalyzing with {threshold*100:.0f}% threshold ({mode})...")

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/error-reports/reanalyze",
            json={
                "report_id": report_id,
                "confidence_threshold": threshold,
                "dry_run": dry_run
            },
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        corrections = data.get("corrections", [])

        click.echo(f"\nResult: {status}")
        click.echo(f"Threshold: {data.get('confidence_threshold', threshold)*100:.0f}%")

        if corrections:
            click.echo("\nCorrections:")
            for c in corrections:
                conf = c.get("confidence", 0) * 100
                field = c.get("field", "?")
                old_val = c.get("old_value", "?")
                new_val = c.get("new_value", "?")
                reasoning = c.get("reasoning", "")[:60]

                status_icon = "✓" if conf >= threshold * 100 else "○"
                click.echo(f"  {status_icon} {field}: {old_val} → {new_val} ({conf:.0f}%)")
                if reasoning:
                    click.echo(f"      Reason: {reasoning}")

        if data.get("admin_notes"):
            click.echo(f"\nNotes: {data['admin_notes']}")

        if dry_run:
            click.echo("\nDRY RUN - no changes made")
            click.echo("Remove --dry-run to apply")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        if hasattr(e, 'response') and e.response is not None:
            click.echo(f"Details: {e.response.text}")
        raise SystemExit(1)


@etl.command(name="suggestion-generate")
@click.argument("report_id")
@click.option("--model", "-m", default="llama3.1:8b", help="Ollama model to use")
def suggestion_generate(report_id: str, model: str):
    """
    Force Ollama to generate suggested corrections for a report.

    Analyzes the report using the specified Ollama model and shows
    what corrections it would suggest, WITHOUT applying them.

    Examples:
        mcli run etl suggestion-generate abc123
        mcli run etl suggestion-generate abc123 --model llama3.2:3b
    """
    click.echo(f"Generating suggestions for report {report_id[:8]}... using {model}")

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/error-reports/generate-suggestion",
            json={"report_id": report_id, "model": model},
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")

        # Show report summary
        summary = data.get("report_summary", {})
        click.echo(f"\n{'='*60}")
        click.echo(f"Report: {report_id[:8]}...")
        click.echo(f"  Type: {summary.get('error_type', 'unknown')}")
        click.echo(f"  Politician: {summary.get('politician', 'Unknown')}")
        click.echo(f"  Asset: {summary.get('asset', 'Unknown')[:50]}")
        click.echo(f"  Description: {summary.get('description', '')[:80]}")
        click.echo(f"  Current Status: {summary.get('current_status', 'unknown')}")

        if status == "no_corrections":
            click.echo(f"\n⚠ Ollama could not determine any corrections for this report.")
            return

        # Show corrections
        corrections = data.get("corrections", [])
        stats = data.get("summary", {})

        click.echo(f"\n{'─'*60}")
        click.echo(f"Suggested Corrections ({stats.get('total_suggestions', 0)} total):")
        click.echo(f"  High confidence (≥{stats.get('confidence_threshold', '80%')}): {stats.get('high_confidence', 0)}")
        click.echo(f"  Low confidence: {stats.get('low_confidence', 0)}")
        click.echo(f"{'─'*60}")

        for c in corrections:
            conf = c.get("confidence", 0) * 100
            field = c.get("field", "?")
            old_val = c.get("old_value", "?")
            new_val = c.get("new_value", "?")
            reasoning = c.get("reasoning", "")[:60]
            auto = "✓ auto" if c.get("would_auto_apply") else "○ manual"

            click.echo(f"\n  [{auto}] {field}: {old_val} → {new_val}")
            click.echo(f"         Confidence: {conf:.0f}%")
            if reasoning:
                click.echo(f"         Reason: {reasoning}")

        click.echo(f"\n{'='*60}")
        click.echo("Next steps:")
        click.echo(f"  To apply with lower threshold:")
        click.echo(f"    mcli run etl suggestion-reanalyze {report_id} -t 0.5")
        click.echo(f"  To manually apply a specific correction:")
        click.echo(f"    mcli run etl suggestion-apply {report_id} <field> <new_value>")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        if hasattr(e, 'response') and e.response is not None:
            click.echo(f"Details: {e.response.text}", err=True)
        raise SystemExit(1)


@etl.command(name="cleanup-all")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would be deleted without deleting")
def cleanup_all(dry_run: bool):
    """
    Run all cleanup tasks: bad dates and raw PDF text patterns.

    This is a convenience command that runs:
        1. cleanup-bad-dates (future dates like 2204)
        2. cleanup-raw-pdf-text with pattern "F S: New"
        3. cleanup-raw-pdf-text with pattern " P __/__/____ "
        4. cleanup-raw-pdf-text with pattern " S __/__/____ "

    Example:
        mcli run etl cleanup-all --dry-run  # Preview all
        mcli run etl cleanup-all            # Delete all
    """
    url, service_key = get_supabase_keys()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    total_deleted = 0

    # Pattern definitions
    patterns = [
        ("future dates (> 2030)", "disclosure_date=gt.2030-01-01"),
        ("'F S: New' in asset_name", "asset_name=ilike.*F%20S:%20New*"),
        ("' P DD/DD/DDDD ' in asset_name", "asset_name=like.*%20P%20__/__/____%20*"),
        ("' S DD/DD/DDDD ' in asset_name", "asset_name=like.*%20S%20__/__/____%20*"),
    ]

    for desc, filter_query in patterns:
        try:
            # Count matching records
            query_url = f"{url}/rest/v1/trading_disclosures?select=id&{filter_query}&limit=1000"
            response = httpx.get(query_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            records = response.json()
            count = len(records)

            if count == 0:
                click.echo(f"  ○ {desc}: 0 records")
                continue

            click.echo(f"  ● {desc}: {count} records")

            if dry_run:
                continue

            # Delete
            delete_url = f"{url}/rest/v1/trading_disclosures?{filter_query}"
            response = httpx.delete(delete_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            total_deleted += count

        except httpx.HTTPError as e:
            click.echo(f"    Error: {e}", err=True)

    if dry_run:
        click.echo("\nDry run - no changes made.")
    else:
        click.echo(f"\n✓ Total deleted: {total_deleted} records")


# =============================================================================
# Politician Deduplication Commands
# =============================================================================

@etl.command(name="dedup-preview")
@click.option("--limit", "-l", type=int, default=20, help="Maximum groups to show")
def dedup_preview(limit: int):
    """
    Preview duplicate politician records.

    Shows groups of politicians with matching normalized names
    that appear to be duplicates.

    Example: mcli run etl dedup-preview
    """
    click.echo("Scanning for duplicate politicians...")

    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/dedup/preview?limit={limit}",
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        groups = data.get("groups", [])
        if not groups:
            click.echo("No duplicate politicians found.")
            return

        click.echo(f"\nFound {data.get('duplicate_groups', 0)} duplicate groups "
                   f"({data.get('total_duplicates', 0)} records to merge)")
        click.echo("=" * 70)

        for group in groups:
            click.echo(f"\n{group['normalized_name']}")
            click.echo(f"  Disclosures to update: {group.get('disclosures_to_update', 0)}")
            for rec in group.get("records", []):
                winner = "★" if rec.get("is_winner") else " "
                party = rec.get("party") or "-"
                state = rec.get("state") or "-"
                click.echo(f"  {winner} [{party:1}] {rec['full_name']:40} state={state}")

        click.echo("\n" + "=" * 70)
        click.echo("★ = record to keep (winner)")
        click.echo("\nTo merge: mcli run etl dedup --dry-run")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# Record Testing Commands
# =============================================================================

@etl.command(name="test-record")
@click.argument("record_id")
@click.option("--type", "-t", "record_type", type=click.Choice(["disclosure", "politician"]),
              default="disclosure", help="Type of record ID")
@click.option("--dry-run", "-d", is_flag=True, help="Parse without uploading")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def test_record(record_id: str, record_type: str, dry_run: bool, verbose: bool):
    """
    Test extraction capabilities on a single record by ID.

    Looks up the record in Supabase and attempts to re-extract data from
    the source URL. Useful for debugging extraction issues.

    Examples:
        mcli run etl test-record abc123-disclosure-id
        mcli run etl test-record abc123-politician-id --type politician
        mcli run etl test-record abc123 --dry-run -v
    """
    load_env()
    url, service_key = get_supabase_keys()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    if record_type == "disclosure":
        # Look up disclosure
        query_url = f"{url}/rest/v1/trading_disclosures?select=*,politicians(full_name,party,state)&id=eq.{record_id}"
        try:
            response = httpx.get(query_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            records = response.json()

            if not records:
                click.echo(f"Disclosure {record_id} not found", err=True)
                raise SystemExit(1)

            disclosure = records[0]
            click.echo(f"\n{'='*60}")
            click.echo(f"Disclosure: {record_id[:8]}...")
            click.echo(f"{'='*60}")

            politician = disclosure.get("politicians") or {}
            click.echo(f"Politician: {politician.get('full_name', 'Unknown')}")
            click.echo(f"Party: {politician.get('party', '?')} | State: {politician.get('state', '?')}")
            click.echo(f"Asset: {disclosure.get('asset_name', 'Unknown')[:60]}")
            click.echo(f"Ticker: {disclosure.get('asset_ticker') or '-'}")
            click.echo(f"Type: {disclosure.get('transaction_type', 'unknown')}")
            click.echo(f"Date: {disclosure.get('transaction_date', '-')}")

            low = disclosure.get("amount_range_min")
            high = disclosure.get("amount_range_max")
            if low and high:
                click.echo(f"Amount: ${low:,.0f} - ${high:,.0f}")
            else:
                click.echo(f"Amount: Not disclosed")

            source_url = disclosure.get("source_url")
            click.echo(f"\nSource: {source_url or 'N/A'}")

            raw_data = disclosure.get("raw_data") or {}
            source_type = raw_data.get("source", "unknown")
            click.echo(f"Source Type: {source_type}")

            if verbose and raw_data:
                click.echo(f"\n{'─'*60}")
                click.echo("Raw Data:")
                import json
                click.echo(json.dumps(raw_data, indent=2)[:1000])

            # If we have a source URL, offer to re-extract
            if source_url:
                click.echo(f"\n{'─'*60}")
                click.echo("To re-extract this disclosure:")
                if source_type == "us_house":
                    click.echo(f"  mcli run etl ingest {source_url} --dry-run")
                elif source_type == "us_senate":
                    click.echo(f"  mcli run etl test-senate-url {source_url} --dry-run")
                else:
                    click.echo(f"  Source type '{source_type}' not supported for re-extraction")

        except httpx.HTTPError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

    else:  # politician
        # Look up politician and their disclosures
        query_url = f"{url}/rest/v1/politicians?select=*&id=eq.{record_id}"
        try:
            response = httpx.get(query_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            records = response.json()

            if not records:
                click.echo(f"Politician {record_id} not found", err=True)
                raise SystemExit(1)

            politician = records[0]
            click.echo(f"\n{'='*60}")
            click.echo(f"Politician: {politician.get('full_name', 'Unknown')}")
            click.echo(f"{'='*60}")
            click.echo(f"ID: {record_id}")
            click.echo(f"Party: {politician.get('party', '?')}")
            click.echo(f"State: {politician.get('state') or politician.get('state_or_country', '?')}")
            click.echo(f"Chamber: {politician.get('chamber', '?')}")
            click.echo(f"Role: {politician.get('role', '?')}")
            click.echo(f"BioGuide ID: {politician.get('bioguide_id') or 'N/A'}")

            # Get disclosure count and sample
            disc_url = f"{url}/rest/v1/trading_disclosures?select=id,asset_name,asset_ticker,transaction_type,source_url,raw_data&politician_id=eq.{record_id}&limit=10"
            disc_response = httpx.get(disc_url, headers=headers, timeout=30.0)
            disc_response.raise_for_status()
            disclosures = disc_response.json()

            click.echo(f"\n{'─'*60}")
            click.echo(f"Recent Disclosures (showing up to 10):")

            # Identify source types
            sources = set()
            for d in disclosures:
                raw = d.get("raw_data") or {}
                sources.add(raw.get("source", "unknown"))

            click.echo(f"Source types: {', '.join(sources)}")
            click.echo()

            for d in disclosures:
                ticker = d.get("asset_ticker") or "-"
                asset = d.get("asset_name", "?")[:40]
                tx_type = d.get("transaction_type", "?")
                click.echo(f"  [{ticker:5}] {asset:40} ({tx_type})")

            if not disclosures:
                click.echo("  No disclosures found")

        except httpx.HTTPError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)


@etl.command(name="list-senators")
@click.option("--refresh", "-r", is_flag=True, help="Refresh list from Senate.gov XML")
def list_senators(refresh: bool):
    """
    List current senators and their disclosure status.

    Fetches the current list of senators from Senate.gov and shows
    which ones have disclosures in our database.

    Examples:
        mcli run etl list-senators
        mcli run etl list-senators --refresh
    """
    click.echo("Fetching senators...")

    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/etl/senators",
            params={"refresh": refresh},
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()

        senators = data.get("senators", [])
        click.echo(f"\nCurrent Senators: {len(senators)}")
        click.echo(f"With disclosures: {data.get('with_disclosures', 0)}")
        click.echo(f"Total disclosures: {data.get('total_disclosures', 0)}")
        click.echo(f"\n{'='*70}")

        # Sort by party then state
        senators.sort(key=lambda s: (s.get("party", ""), s.get("state", "")))

        for s in senators:
            party = s.get("party", "?")
            state = s.get("state", "??")
            name = s.get("full_name", "Unknown")[:40]
            disc_count = s.get("disclosure_count", 0)
            bioguide = s.get("bioguide_id", "")[:10] if s.get("bioguide_id") else ""

            disc_str = f"{disc_count:3} disclosures" if disc_count else "no disclosures"
            click.echo(f"  [{party}] {state:2} {name:40} {disc_str}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="senate-trigger")
@click.option("--lookback", "-l", type=int, default=30, help="Days to look back for disclosures")
@click.option("--limit", type=int, default=None, help="Limit number of disclosures to process")
@click.option("--wait", "-w", is_flag=True, help="Wait for job to complete")
def senate_trigger(lookback: int, limit: int | None, wait: bool):
    """
    Trigger Senate ETL job.

    Scrapes the Senate EFD website for Periodic Transaction Reports and
    uploads transactions to Supabase.

    Note: This uses Playwright browser automation to bypass anti-bot protection.

    Examples:
        mcli run etl senate-trigger                    # Last 30 days
        mcli run etl senate-trigger --lookback 90     # Last 90 days
        mcli run etl senate-trigger --limit 10 -w     # Test with 10 disclosures
    """
    click.echo(f"Triggering Senate ETL (lookback: {lookback} days)...")

    payload = {
        "source": "senate",
        "lookback_days": lookback,
    }
    if limit:
        payload["limit"] = limit

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/etl/trigger",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data["job_id"]
        click.echo(f"Job started: {job_id}")
        click.echo(f"Message: {data['message']}")

        if wait:
            click.echo("\nWaiting for completion...")
            _wait_for_job(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="eu-trigger")
@click.option("--limit", "-l", type=int, default=None, help="Limit number of MEPs to process (for testing)")
@click.option("--wait", "-w", is_flag=True, help="Wait for job to complete")
def eu_trigger(limit: int | None, wait: bool):
    """
    Trigger EU Parliament ETL job.

    Fetches MEP financial interest declarations (DPI PDFs) from the
    EU Parliament website, parses them, and uploads to Supabase.

    Examples:
        mcli run etl eu-trigger                    # Process all MEPs
        mcli run etl eu-trigger --limit 10         # Test with 10 MEPs
        mcli run etl eu-trigger --limit 5 -w       # Test and wait for completion
    """
    limit_msg = f" (limit: {limit} MEPs)" if limit else " (all MEPs)"
    click.echo(f"Triggering EU Parliament ETL{limit_msg}...")

    payload = {"source": "eu_parliament"}
    if limit:
        payload["limit"] = limit

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/etl/trigger",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data["job_id"]
        click.echo(f"Job started: {job_id}")
        click.echo(f"Message: {data['message']}")

        if wait:
            click.echo("\nWaiting for completion...")
            _wait_for_job(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl status {job_id}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="dedup")
@click.option("--dry-run", "-d", is_flag=True, help="Preview without making changes")
@click.option("--limit", "-l", type=int, default=50, help="Maximum groups to process")
def dedup(dry_run: bool, limit: int):
    """
    Merge duplicate politician records.

    Finds politicians with matching normalized names and:
    1. Keeps the record with the most complete data
    2. Updates all trading_disclosures to point to the winner
    3. Deletes duplicate records

    Examples:
        mcli run etl dedup --dry-run     # Preview what would happen
        mcli run etl dedup               # Actually merge duplicates
        mcli run etl dedup -l 10         # Process only 10 groups
    """
    mode = "DRY RUN" if dry_run else "MERGING"
    click.echo(f"Processing duplicate politicians ({mode})...")

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/dedup/process",
            json={"limit": limit, "dry_run": dry_run},
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

        processed = data.get("processed", 0)
        merged = data.get("merged", 0)
        disclosures = data.get("disclosures_updated", 0)
        errors = data.get("errors", 0)

        if processed == 0:
            click.echo("No duplicates found to process.")
            return

        click.echo(f"\n{'='*60}")
        click.echo(f"Processed: {processed} duplicate groups")
        click.echo(f"Merged: {merged} groups")
        click.echo(f"Disclosures updated: {disclosures}")
        if errors:
            click.echo(f"Errors: {errors}")

        # Show details
        results = data.get("results", [])
        if results:
            click.echo(f"\n{'─'*60}")
            for r in results[:10]:
                status_icon = "✓" if r["status"] == "success" else ("○" if r["status"] == "dry_run" else "✗")
                name = r.get("normalized_name", "?")
                losers = r.get("losers_merged", 0)
                updated = r.get("disclosures_updated", r.get("disclosures_to_update", 0))
                click.echo(f"  {status_icon} {name:40} merged {losers} → updated {updated} disclosures")

            if len(results) > 10:
                click.echo(f"  ... and {len(results) - 10} more")

        if dry_run:
            click.echo(f"\n{'='*60}")
            click.echo("DRY RUN - no changes made")
            click.echo("To apply changes: mcli run etl dedup")
        else:
            click.echo(f"\n✓ Deduplication complete!")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# Congress.gov API Commands (Subgroup)
# =============================================================================

CONGRESS_API_URL = "https://api.congress.gov/v3"
CURRENT_CONGRESS = 119  # 119th Congress (2025-2027)


def _get_congress_api_key() -> Optional[str]:
    """Get Congress.gov API key from lsh."""
    try:
        result = subprocess.run(
            ["lsh", "get", "CONGRESS_API_KEY"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _make_congress_request(endpoint: str, params: Dict[str, Any] = None) -> Dict:
    """Make authenticated request to Congress.gov API."""
    api_key = _get_congress_api_key()
    if not api_key:
        raise click.ClickException("CONGRESS_API_KEY not found. Set with: lsh set CONGRESS_API_KEY <key>")

    url = f"{CONGRESS_API_URL}{endpoint}"
    params = params or {}
    params["api_key"] = api_key
    params["format"] = "json"

    response = httpx.get(url, params=params, timeout=30.0)

    if response.status_code != 200:
        raise click.ClickException(f"API error: HTTP {response.status_code} - {response.text[:200]}")

    return response.json()


def _normalize_congress_name(name: str) -> str:
    """Normalize a name for matching."""
    if not name:
        return ""
    # Handle "Last, First" format
    if ", " in name:
        parts = name.split(", ", 1)
        name = f"{parts[1]} {parts[0]}"
    # Remove common suffixes/prefixes
    for suffix in [" Jr.", " Jr", " Sr.", " Sr", " III", " II", " IV"]:
        name = name.replace(suffix, "")
    return name.lower().strip()


def _fetch_all_congress_members() -> List[Dict]:
    """Fetch all current Congress members from Congress.gov API."""
    all_members = []
    offset = 0
    page_size = 250

    while True:
        params = {
            "limit": page_size,
            "offset": offset,
            "currentMember": "true"
        }
        data = _make_congress_request("/member", params)
        members = data.get("members", [])

        if not members:
            break

        for member in members:
            terms = member.get("terms", {}).get("item", [])
            current_term = terms[0] if terms else {}

            all_members.append({
                "bioguide_id": member.get("bioguideId", ""),
                "name": member.get("name", ""),
                "direct_name": member.get("directOrderName", ""),
                "state": member.get("state", ""),
                "district": member.get("district"),
                "party": member.get("partyName", ""),
                "chamber": current_term.get("chamber", ""),
            })

        offset += page_size
        total = data.get("pagination", {}).get("count", 0)
        if offset >= total:
            break

    return all_members


def _get_congress_supabase_config() -> Dict[str, str]:
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


def _fetch_app_politicians(config: Dict[str, str]) -> List[Dict]:
    """Fetch politicians from app database."""
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        return []

    response = httpx.get(
        f"{url}/rest/v1/politicians",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        params={
            "select": "id,full_name,first_name,last_name,bioguide_id,party,state_or_country,chamber",
            "limit": 2000
        },
        timeout=30.0
    )

    if response.status_code == 200:
        return response.json()
    return []


def _update_politician_bioguide(config: Dict[str, str], politician_id: str, bioguide_id: str) -> bool:
    """Update a politician's bioguide_id in the database."""
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        return False

    response = httpx.patch(
        f"{url}/rest/v1/politicians",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        params={"id": f"eq.{politician_id}"},
        json={"bioguide_id": bioguide_id},
        timeout=10.0
    )

    return response.status_code in [200, 204]


@etl.group(name="congress")
def congress():
    """
    Congress.gov API commands.

    Fetch member data, bills, and voting records from Congress.gov.
    """
    pass


@congress.command("test")
def congress_test():
    """
    Test connection to Congress.gov API.

    Example: mcli run etl congress test
    """
    api_key = _get_congress_api_key()

    if not api_key:
        console.print("[red]Error: CONGRESS_API_KEY not found[/red]")
        console.print("Get a free API key at: https://api.congress.gov/sign-up/")
        console.print("Then set it with: lsh set CONGRESS_API_KEY <your_key>")
        raise SystemExit(1)

    console.print("[cyan]Testing Congress.gov API connection...[/cyan]")
    console.print(f"[dim]API Key: {api_key[:8]}...{api_key[-4:]}[/dim]")

    try:
        data = _make_congress_request("/member", {"limit": 1})

        if "members" in data:
            console.print("[green]Success: API connection works[/green]")
            total = data.get("pagination", {}).get("count", "unknown")
            console.print(f"  Total members in database: {total}")
        else:
            console.print("[yellow]Warning: Unexpected response format[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@congress.command("members")
@click.option("--congress-num", "-c", "congress_num", default=CURRENT_CONGRESS, help=f"Congress number (default: {CURRENT_CONGRESS})")
@click.option("--chamber", type=click.Choice(["house", "senate", "all"]), default="all", help="Chamber filter")
@click.option("--state", "-s", help="Filter by state (e.g., CA, TX, NY)")
@click.option("--party", "-p", type=click.Choice(["D", "R", "I", "all"]), default="all", help="Party filter")
@click.option("--limit", "-l", default=50, help="Number of members to show")
@click.option("--output", "-o", type=click.Choice(["table", "json", "csv"]), default="table")
@click.option("--current/--all-time", default=True, help="Only current members")
def congress_members(congress_num: int, chamber: str, state: str, party: str, limit: int, output: str, current: bool):
    """
    List members of Congress.

    Examples:
        mcli run etl congress members
        mcli run etl congress members --chamber senate --state CA
        mcli run etl congress members --party D --limit 100
    """
    console.print(f"[cyan]Fetching members of the {congress_num}th Congress...[/cyan]")

    try:
        all_members = []
        offset = 0
        page_size = 250  # Max allowed by API

        # Fetch all members (paginated)
        while True:
            params = {
                "limit": page_size,
                "offset": offset,
                "currentMember": "true" if current else None
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            data = _make_congress_request("/member", params)
            members = data.get("members", [])

            if not members:
                break

            all_members.extend(members)
            offset += page_size

            # Check if we've fetched enough or reached the end
            total = data.get("pagination", {}).get("count", 0)
            if offset >= total or len(all_members) >= 1000:  # Safety limit
                break

        console.print(f"[dim]Fetched {len(all_members)} total members[/dim]")

        # Filter members
        filtered = []
        for member in all_members:
            # Get current term info
            terms = member.get("terms", {}).get("item", [])
            current_term = terms[0] if terms else {}

            member_chamber = current_term.get("chamber", "").lower()
            member_state = member.get("state", "")
            member_party = member.get("partyName", "")

            # Apply filters
            if chamber != "all" and member_chamber != chamber:
                continue
            if state and member_state.upper() != state.upper():
                continue
            if party != "all":
                party_letter = member_party[0].upper() if member_party else ""
                if party_letter != party:
                    continue

            filtered.append({
                "name": member.get("name", ""),
                "bioguideId": member.get("bioguideId", ""),
                "state": member_state,
                "district": member.get("district"),
                "party": member_party,
                "chamber": member_chamber.title() if member_chamber else "",
                "url": member.get("url", ""),
            })

        # Sort by state, then name
        filtered.sort(key=lambda x: (x["state"], x["name"]))

        # Apply limit
        display_members = filtered[:limit]

        if output == "json":
            import json
            console.print(json.dumps(display_members, indent=2))

        elif output == "csv":
            console.print("name,bioguideId,state,district,party,chamber")
            for m in display_members:
                console.print(f'"{m["name"]}",{m["bioguideId"]},{m["state"]},{m["district"] or ""},"{m["party"]}",{m["chamber"]}')

        else:
            # Table output
            title = f"Members of {congress_num}th Congress"
            if chamber != "all":
                title += f" ({chamber.title()})"
            if state:
                title += f" - {state.upper()}"

            table = Table(title=title)
            table.add_column("Name", style="green", width=25)
            table.add_column("State", width=6)
            table.add_column("Dist", width=5)
            table.add_column("Party", width=12)
            table.add_column("Chamber", width=8)
            table.add_column("BioGuide ID", style="dim", width=12)

            for m in display_members:
                party_style = "blue" if m["party"].startswith("Democrat") else "red" if m["party"].startswith("Republican") else "yellow"
                table.add_row(
                    m["name"][:24],
                    m["state"],
                    str(m["district"]) if m["district"] else "-",
                    f"[{party_style}]{m['party'][:10]}[/{party_style}]",
                    m["chamber"][:7],
                    m["bioguideId"]
                )

            console.print(table)
            console.print(f"\n[dim]Showing {len(display_members)} of {len(filtered)} filtered members[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@congress.command("member")
@click.argument("bioguide_id")
def congress_member(bioguide_id: str):
    """
    Get details for a specific member by BioGuide ID.

    Example: mcli run etl congress member P000197
    """
    console.print(f"[cyan]Fetching member {bioguide_id}...[/cyan]")

    try:
        data = _make_congress_request(f"/member/{bioguide_id}")
        member = data.get("member", {})

        if not member:
            console.print(f"[red]Member not found: {bioguide_id}[/red]")
            raise SystemExit(1)

        console.print(f"\n[bold]{member.get('directOrderName', member.get('name', 'Unknown'))}[/bold]")
        console.print("-" * 50)
        console.print(f"BioGuide ID: {member.get('bioguideId', '-')}")
        console.print(f"Party: {member.get('partyHistory', [{}])[0].get('partyName', '-')}")
        console.print(f"State: {member.get('state', '-')}")
        console.print(f"District: {member.get('district', '-')}")
        console.print(f"Birth Year: {member.get('birthYear', '-')}")

        # Terms
        terms = member.get("terms", [])
        if terms:
            console.print(f"\n[bold]Terms ({len(terms)}):[/bold]")
            for term in terms[:5]:  # Show last 5 terms
                chamber = term.get("chamber", "-")
                start = term.get("startYear", "-")
                end = term.get("endYear", "present")
                cong = term.get("congress", "-")
                console.print(f"  {cong}th Congress: {chamber} ({start}-{end})")

        # Sponsored legislation count
        sponsored = member.get("sponsoredLegislation", {}).get("count", 0)
        cosponsored = member.get("cosponsoredLegislation", {}).get("count", 0)
        console.print(f"\n[bold]Legislation:[/bold]")
        console.print(f"  Sponsored: {sponsored}")
        console.print(f"  Co-sponsored: {cosponsored}")

        # Official URL
        if member.get("officialWebsiteUrl"):
            console.print(f"\nWebsite: {member.get('officialWebsiteUrl')}")

    except click.ClickException:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@congress.command("stats")
@click.option("--congress-num", "-c", "congress_num", default=CURRENT_CONGRESS, help=f"Congress number")
def congress_stats(congress_num: int):
    """
    Show statistics about current Congress members.

    Example: mcli run etl congress stats
    """
    console.print(f"[cyan]Fetching stats for {congress_num}th Congress...[/cyan]")

    try:
        all_members = []
        offset = 0

        # Fetch all current members
        while True:
            params = {"limit": 250, "offset": offset, "currentMember": "true"}
            data = _make_congress_request("/member", params)
            members = data.get("members", [])

            if not members:
                break

            all_members.extend(members)
            offset += 250

            if offset >= data.get("pagination", {}).get("count", 0):
                break

        # Calculate stats
        house = {"D": 0, "R": 0, "I": 0, "Other": 0}
        senate = {"D": 0, "R": 0, "I": 0, "Other": 0}
        states = {}

        for member in all_members:
            terms = member.get("terms", {}).get("item", [])
            if not terms:
                continue

            current_term = terms[0]
            chamber = current_term.get("chamber", "").lower()
            party = member.get("partyName", "")
            state = member.get("state", "Unknown")

            party_key = party[0].upper() if party else "Other"
            if party_key not in ["D", "R", "I"]:
                party_key = "Other"

            if chamber == "house of representatives":
                house[party_key] += 1
            elif chamber == "senate":
                senate[party_key] += 1

            states[state] = states.get(state, 0) + 1

        console.print(f"\n[bold]{congress_num}th Congress Statistics[/bold]")
        console.print("=" * 50)

        # House
        house_total = sum(house.values())
        console.print(f"\n[bold]House of Representatives ({house_total} members):[/bold]")
        console.print(f"  [blue]Democrats: {house['D']}[/blue]")
        console.print(f"  [red]Republicans: {house['R']}[/red]")
        if house["I"]:
            console.print(f"  [yellow]Independents: {house['I']}[/yellow]")

        # Senate
        senate_total = sum(senate.values())
        console.print(f"\n[bold]Senate ({senate_total} members):[/bold]")
        console.print(f"  [blue]Democrats: {senate['D']}[/blue]")
        console.print(f"  [red]Republicans: {senate['R']}[/red]")
        if senate["I"]:
            console.print(f"  [yellow]Independents: {senate['I']}[/yellow]")

        # Top states
        console.print(f"\n[bold]Top 10 States by Representation:[/bold]")
        for state, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
            console.print(f"  {state}: {count}")

        console.print(f"\n[dim]Total members: {len(all_members)}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@congress.command("health")
def congress_health():
    """
    Quick health check of Congress.gov API.

    Example: mcli run etl congress health
    """
    api_key = _get_congress_api_key()

    console.print("\n[bold]Congress.gov API Health Check[/bold]")
    console.print("-" * 40)

    # Check API key
    if api_key:
        console.print(f"[green]OK[/green] API Key: configured")
    else:
        console.print("[red]FAIL[/red] API Key: missing")
        console.print("Get one at: https://api.congress.gov/sign-up/")
        raise SystemExit(1)

    # Check connectivity
    try:
        data = _make_congress_request("/member", {"limit": 1})
        if "members" in data:
            console.print("[green]OK[/green] API Connection: healthy")
        else:
            console.print("[red]FAIL[/red] API Connection: unexpected response")
            raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]FAIL[/red] API Connection: {str(e)[:40]}")
        raise SystemExit(1)

    console.print("\n[green]All checks passed[/green]")


@congress.command("backfill-bioguide")
@click.option("--dry-run", is_flag=True, help="Show matches without updating database")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed matching info")
def congress_backfill_bioguide(dry_run: bool, verbose: bool):
    """
    Backfill bioguide_id for politicians by matching with Congress.gov data.

    Example: mcli run etl congress backfill-bioguide --dry-run
    Example: mcli run etl congress backfill-bioguide
    """
    config = _get_congress_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found in lsh[/red]")
        raise SystemExit(1)

    console.print("[cyan]Fetching Congress members from Congress.gov...[/cyan]")
    congress_members = _fetch_all_congress_members()
    console.print(f"  Found {len(congress_members)} current members")

    console.print("[cyan]Fetching politicians from app database...[/cyan]")
    app_politicians = _fetch_app_politicians(config)
    console.print(f"  Found {len(app_politicians)} politicians")

    # Filter to those without bioguide_id
    missing_bioguide = [p for p in app_politicians if not p.get("bioguide_id")]
    already_have = len(app_politicians) - len(missing_bioguide)
    console.print(f"  Already have bioguide_id: {already_have}")
    console.print(f"  Missing bioguide_id: {len(missing_bioguide)}")

    # Build lookup tables for Congress members
    congress_by_name = {}
    congress_by_direct_name = {}
    for m in congress_members:
        norm_name = _normalize_congress_name(m["name"])
        norm_direct = _normalize_congress_name(m["direct_name"])
        if norm_name:
            congress_by_name[norm_name] = m
        if norm_direct:
            congress_by_direct_name[norm_direct] = m

    # Match politicians
    matches = []
    no_match = []

    for pol in missing_bioguide:
        full_name = pol.get("full_name", "")
        first_name = pol.get("first_name", "")
        last_name = pol.get("last_name", "")

        # Try different name formats
        names_to_try = [
            _normalize_congress_name(full_name),
            _normalize_congress_name(f"{first_name} {last_name}"),
            _normalize_congress_name(f"{last_name}, {first_name}"),
        ]

        match = None
        matched_name = None
        for name in names_to_try:
            if name in congress_by_name:
                match = congress_by_name[name]
                matched_name = name
                break
            if name in congress_by_direct_name:
                match = congress_by_direct_name[name]
                matched_name = name
                break

        if match:
            matches.append({
                "politician": pol,
                "congress_member": match,
                "matched_on": matched_name
            })
        else:
            no_match.append(pol)

    console.print(f"\n[bold]Matching Results[/bold]")
    console.print("-" * 60)
    console.print(f"[green]Matched: {len(matches)}[/green]")
    console.print(f"[yellow]No match: {len(no_match)}[/yellow]")

    if verbose and matches:
        console.print(f"\n[bold]Matches:[/bold]")
        for m in matches[:20]:
            pol = m["politician"]
            cong = m["congress_member"]
            console.print(f"  {pol['full_name']} -> {cong['bioguide_id']} ({cong['name']})")
        if len(matches) > 20:
            console.print(f"  ... and {len(matches) - 20} more")

    if verbose and no_match:
        console.print(f"\n[bold]No Match Found:[/bold]")
        for pol in no_match[:10]:
            console.print(f"  {pol['full_name']} ({pol.get('state_or_country', '?')})")
        if len(no_match) > 10:
            console.print(f"  ... and {len(no_match) - 10} more")

    if dry_run:
        console.print(f"\n[yellow]Dry run - no changes made[/yellow]")
        return

    if not matches:
        console.print("[yellow]No matches to update[/yellow]")
        return

    # Update database
    console.print(f"\n[cyan]Updating {len(matches)} politicians...[/cyan]")
    updated = 0
    failed = 0

    for m in matches:
        pol_id = m["politician"]["id"]
        bioguide_id = m["congress_member"]["bioguide_id"]

        if _update_politician_bioguide(config, pol_id, bioguide_id):
            updated += 1
        else:
            failed += 1
            if verbose:
                console.print(f"  [red]Failed to update {m['politician']['full_name']}[/red]")

    console.print(f"\n[bold]Update Results[/bold]")
    console.print(f"  [green]Updated: {updated}[/green]")
    if failed:
        console.print(f"  [red]Failed: {failed}[/red]")


@congress.command("lookup")
@click.argument("name")
def congress_lookup(name: str):
    """
    Look up a Congress member by name and show their BioGuide ID.

    Example: mcli run etl congress lookup "Nancy Pelosi"
    Example: mcli run etl congress lookup "Pelosi"
    """
    console.print(f"[cyan]Searching for '{name}'...[/cyan]")

    try:
        # Fetch all current members
        all_members = _fetch_all_congress_members()

        # Search by name (case-insensitive partial match)
        search_lower = name.lower()
        matches = []

        for member in all_members:
            if (search_lower in member["name"].lower() or
                search_lower in member.get("direct_name", "").lower()):
                matches.append(member)

        if not matches:
            console.print(f"[yellow]No members found matching '{name}'[/yellow]")
            return

        console.print(f"\n[bold]Found {len(matches)} match(es):[/bold]")
        table = Table()
        table.add_column("Name", style="green", width=30)
        table.add_column("BioGuide ID", style="cyan", width=12)
        table.add_column("State", width=6)
        table.add_column("Party", width=12)
        table.add_column("Chamber", width=10)

        for m in matches[:20]:
            party_style = "blue" if "Democrat" in m["party"] else "red" if "Republican" in m["party"] else "yellow"
            table.add_row(
                m["direct_name"] or m["name"],
                m["bioguide_id"],
                m["state"],
                f"[{party_style}]{m['party'][:10]}[/{party_style}]",
                m["chamber"][:10] if m["chamber"] else "-"
            )

        console.print(table)

        if len(matches) > 20:
            console.print(f"\n[dim]Showing first 20 of {len(matches)} matches[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# =============================================================================
# QuiverQuant API Commands (Subgroup)
# =============================================================================

QUIVERQUANT_API_URL = "https://api.quiverquant.com/beta/live/congresstrading"


def _get_quiver_api_key() -> Optional[str]:
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


def _get_quiver_supabase_config():
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


def _fetch_quiverquant_data(api_key: str, limit: int = 1000, politician: str = None):
    """Fetch data from QuiverQuant API."""
    params = {"pagesize": limit}
    url = QUIVERQUANT_API_URL
    if politician:
        url = f"{QUIVERQUANT_API_URL}/{politician}"

    response = httpx.get(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        },
        timeout=60.0,
        params=params
    )
    if response.status_code == 200:
        return response.json()
    return []


def _fetch_quiver_supabase_data(config: dict, table: str, select: str = "*", limit: int = 1000, filters: dict = None, order: str = None):
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


def _normalize_quiver_name(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    if not name:
        return ""
    if ", " in name:
        parts = name.split(", ", 1)
        name = f"{parts[1]} {parts[0]}"
    for term in ["Hon. ", "Rep. ", "Sen. ", " Jr.", " Jr", " Sr.", " Sr", " III", " II", " IV"]:
        name = name.replace(term, "")
    return name.lower().strip()


@etl.group(name="quiver")
def quiver():
    """
    QuiverQuant congressional trading API commands.

    Test connection and fetch trading data from QuiverQuant.
    """
    pass


@quiver.command("test")
def quiver_test():
    """
    Test connection to QuiverQuant API.

    Example: mcli run etl quiver test
    """
    api_key = _get_quiver_api_key()

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
            params={"pagesize": 1}
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


@quiver.command("fetch")
@click.option("--limit", "-l", default=20, help="Number of records to fetch")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
def quiver_fetch(limit: int, output: str):
    """
    Fetch recent congressional trades from QuiverQuant.

    Example: mcli run etl quiver fetch --limit 10
    """
    api_key = _get_quiver_api_key()

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


@quiver.command("stats")
def quiver_stats():
    """
    Show statistics about QuiverQuant data.

    Example: mcli run etl quiver stats
    """
    api_key = _get_quiver_api_key()

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
            params={"pagesize": 1000}
        )

        if response.status_code != 200:
            console.print(f"[red]Error: HTTP {response.status_code}[/red]")
            raise SystemExit(1)

        data = response.json()

        if not isinstance(data, list):
            console.print("[yellow]Unexpected response format[/yellow]")
            return

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


@quiver.command("health")
def quiver_health():
    """
    Quick health check of QuiverQuant API.

    Example: mcli run etl quiver health
    """
    api_key = _get_quiver_api_key()

    checks = []

    if api_key:
        checks.append(("API Key", "configured", True))
    else:
        checks.append(("API Key", "missing", False))
        console.print("[red]API Key: MISSING[/red]")
        console.print("Set with: lsh set QUIVERQUANT_API_KEY <key>")
        raise SystemExit(1)

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


@quiver.command("validate-politicians")
def quiver_validate_politicians():
    """
    Compare politician data between QuiverQuant and app database.

    Example: mcli run etl quiver validate-politicians
    """
    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Fetching data from both sources...[/cyan]")

    qq_data = _fetch_quiverquant_data(api_key)
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

    app_politicians = _fetch_quiver_supabase_data(
        config, "politicians",
        "full_name,bioguide_id,party,chamber,total_trades"
    )
    app_by_name = {p.get("full_name", ""): p for p in app_politicians}
    app_by_bioguide = {p.get("bioguide_id", ""): p for p in app_politicians if p.get("bioguide_id")}

    console.print(f"\n[bold]Politician Comparison[/bold]")
    console.print("-" * 60)
    console.print(f"QuiverQuant unique politicians: [cyan]{len(qq_politicians)}[/cyan]")
    console.print(f"App database politicians: [cyan]{len(app_politicians)}[/cyan]")

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


@quiver.command("validate-trades")
@click.option("--days", "-d", default=30, help="Number of days to compare")
def quiver_validate_trades(days: int):
    """
    Compare recent trades between QuiverQuant and app database.

    Example: mcli run etl quiver validate-trades --days 30
    """
    from datetime import datetime, timedelta

    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Comparing trades from last {days} days...[/cyan]")

    qq_data = _fetch_quiverquant_data(api_key)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    qq_recent = [t for t in qq_data if t.get("TransactionDate", "") >= cutoff]

    app_trades = _fetch_quiver_supabase_data(
        config, "trading_disclosures",
        "asset_ticker,transaction_date,disclosure_date,transaction_type,politician_id",
        limit=2000,
        filters={"status": "eq.active"},
        order="disclosure_date.desc"
    )
    app_recent = [t for t in app_trades if (t.get("transaction_date") or "")[:10] >= cutoff]

    console.print(f"\n[bold]Trade Comparison (last {days} days)[/bold]")
    console.print("-" * 60)
    console.print(f"QuiverQuant trades: [cyan]{len(qq_recent)}[/cyan]")
    console.print(f"App database trades: [cyan]{len(app_recent)}[/cyan]")


@quiver.command("freshness-check")
def quiver_freshness_check():
    """
    Compare data freshness between QuiverQuant and our database.

    Example: mcli run etl quiver freshness-check
    """
    from datetime import datetime

    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[cyan]Checking data freshness...[/cyan]\n")

    qq_data = _fetch_quiverquant_data(api_key, limit=500)
    qq_tx_dates = [t.get("TransactionDate", "")[:10] for t in qq_data if t.get("TransactionDate")]
    qq_disc_dates = [t.get("ReportDate", t.get("DisclosureDate", ""))[:10] for t in qq_data if t.get("ReportDate") or t.get("DisclosureDate")]

    qq_latest_tx = max(qq_tx_dates) if qq_tx_dates else "N/A"
    qq_latest_disc = max(qq_disc_dates) if qq_disc_dates else "N/A"

    app_trades = _fetch_quiver_supabase_data(
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

    table = Table(title="Data Freshness Comparison")
    table.add_column("Metric", style="bold")
    table.add_column("QuiverQuant", style="cyan")
    table.add_column("Our Database", style="green")
    table.add_column("Status", style="yellow")

    tx_status = "OK" if app_latest_tx >= qq_latest_tx else f"Behind by {qq_latest_tx}"
    table.add_row("Latest Transaction Date", qq_latest_tx, app_latest_tx, tx_status)

    disc_status = "OK" if app_latest_disc >= qq_latest_disc else f"Behind by {qq_latest_disc}"
    table.add_row("Latest Disclosure Date", qq_latest_disc, app_latest_disc, disc_status)
    table.add_row("Records Checked", str(len(qq_data)), str(len(app_trades)), "-")

    console.print(table)


@quiver.command("list-politicians")
@click.option("--limit", "-l", default=100, help="Number of recent trades to scan")
def quiver_list_politicians(limit: int):
    """
    List all politicians in the QuiverQuant dataset.

    Example: mcli run etl quiver list-politicians
    """
    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Fetching politicians from QuiverQuant...[/cyan]\n")

    qq_data = _fetch_quiverquant_data(api_key, limit=limit)

    if not qq_data:
        console.print("[red]Failed to fetch data[/red]")
        raise SystemExit(1)

    politicians = {}
    for trade in qq_data:
        rep = trade.get("Representative", "")
        party = trade.get("Party", "?")
        house = trade.get("House", "?")
        bioguide = trade.get("BioGuideID", "")

        if rep:
            if rep not in politicians:
                politicians[rep] = {
                    "party": party,
                    "house": house,
                    "bioguide": bioguide,
                    "count": 0
                }
            politicians[rep]["count"] += 1

    console.print(f"[bold]Politicians in QuiverQuant (from {len(qq_data)} trades)[/bold]")
    console.print("=" * 70)

    table = Table()
    table.add_column("Name", style="cyan", width=30)
    table.add_column("Party", width=6)
    table.add_column("Chamber", width=15)
    table.add_column("Trades", justify="right", width=8)
    table.add_column("BioGuide", width=12)

    for name, info in sorted(politicians.items(), key=lambda x: -x[1]["count"]):
        table.add_row(
            name[:28],
            info["party"],
            info["house"][:13] if info["house"] else "?",
            str(info["count"]),
            info["bioguide"] or "-"
        )

    console.print(table)
    console.print(f"\n[dim]Total unique politicians: {len(politicians)}[/dim]")


@quiver.command("politician-trades")
@click.argument("name")
@click.option("--limit", "-l", default=50, help="Maximum trades to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table")
@click.option("--local-filter", "-f", is_flag=True, help="Use local filtering instead of API filtering")
def quiver_politician_trades(name: str, limit: int, output: str, local_filter: bool):
    """
    Fetch all trades for a specific politician from QuiverQuant.

    Examples:
        mcli run etl quiver politician-trades "Nancy Pelosi"
        mcli run etl quiver politician-trades "Pelosi" --local-filter
    """
    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Searching for trades by '{name}'...[/cyan]")

    matching_trades = []

    if local_filter:
        console.print("[dim]Using local filtering (partial match)...[/dim]\n")
        qq_data = _fetch_quiverquant_data(api_key, limit=5000)

        if not qq_data:
            console.print("[red]Failed to fetch data from QuiverQuant[/red]")
            raise SystemExit(1)

        name_lower = name.lower()
        for trade in qq_data:
            rep = trade.get("Representative", "")
            if name_lower in rep.lower():
                matching_trades.append(trade)
    else:
        console.print("[dim]Using API politician filter...[/dim]\n")
        matching_trades = _fetch_quiverquant_data(api_key, limit=limit, politician=name)

        if not matching_trades:
            console.print("[dim]No exact match, trying local filter...[/dim]")
            qq_data = _fetch_quiverquant_data(api_key, limit=5000)
            if qq_data:
                name_lower = name.lower()
                for trade in qq_data:
                    rep = trade.get("Representative", "")
                    if name_lower in rep.lower():
                        matching_trades.append(trade)

    if not matching_trades:
        console.print(f"[yellow]No trades found for '{name}'[/yellow]")
        raise SystemExit(1)

    trades_to_show = matching_trades[:limit]

    if output == "json":
        import json
        console.print(json.dumps(trades_to_show, indent=2, default=str))
    else:
        first_trade = trades_to_show[0]
        console.print(f"[bold]Politician: {first_trade.get('Representative', 'Unknown')}[/bold]")
        console.print(f"Party: {first_trade.get('Party', '?')}")
        console.print(f"Chamber: {first_trade.get('House', '?')}")
        console.print(f"BioGuide ID: {first_trade.get('BioGuideID', 'N/A')}")
        console.print(f"\n[bold]Total trades found: {len(matching_trades)}[/bold]")
        console.print(f"Showing: {len(trades_to_show)}\n")

        table = Table(title=f"Trades for {first_trade.get('Representative', name)}")
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Ticker", style="yellow", width=8)
        table.add_column("Asset", width=30)
        table.add_column("Type", width=15)
        table.add_column("Amount", width=20)

        for trade in trades_to_show:
            tx_date = (trade.get("TransactionDate") or "")[:10]
            ticker = trade.get("Ticker", "-")
            asset = (trade.get("Asset") or trade.get("Description") or "-")[:28]
            tx_type = trade.get("Transaction", "-")
            amount = trade.get("Range", trade.get("Amount", "-"))

            table.add_row(tx_date, ticker, asset, tx_type, str(amount))

        console.print(table)


@quiver.command("missing-trades")
@click.option("--days", "-d", default=30, help="Number of days to check")
@click.option("--limit", "-l", default=20, help="Maximum trades to show")
def quiver_missing_trades(days: int, limit: int):
    """
    List specific trades in QuiverQuant that are missing from our database.

    Example: mcli run etl quiver missing-trades --days 14
    """
    from datetime import datetime, timedelta

    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Finding trades from last {days} days missing from our DB...[/cyan]\n")

    qq_data = _fetch_quiverquant_data(api_key, limit=2000)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    qq_recent = [t for t in qq_data if (t.get("TransactionDate") or "")[:10] >= cutoff]

    app_trades = _fetch_quiver_supabase_data(
        config, "trading_disclosures",
        "asset_ticker,transaction_date,politician_id",
        limit=10000,
        filters={"status": "eq.active"}
    )

    app_trade_keys = set()
    for t in app_trades:
        ticker = t.get("asset_ticker", "")
        date = (t.get("transaction_date") or "")[:10]
        if ticker and date:
            app_trade_keys.add(f"{ticker}:{date}")

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
    else:
        console.print("\n[green]No missing trades found![/green]")


# =============================================================================
# QuiverQuant Validation Engine
# =============================================================================

def _parse_quiver_amount_range(range_str: str) -> tuple:
    """Parse QuiverQuant amount range string into min/max values."""
    if not range_str:
        return None, None

    # Handle formats like "$1,001 - $15,000" or "$15,001 - $50,000"
    import re
    matches = re.findall(r'\$?([\d,]+)', range_str)
    if len(matches) >= 2:
        try:
            min_val = float(matches[0].replace(',', ''))
            max_val = float(matches[1].replace(',', ''))
            return min_val, max_val
        except ValueError:
            pass
    elif len(matches) == 1:
        try:
            val = float(matches[0].replace(',', ''))
            return val, val
        except ValueError:
            pass
    return None, None


def _normalize_transaction_type(tx_type: str) -> str:
    """Normalize transaction type for comparison."""
    if not tx_type:
        return ""
    tx_lower = tx_type.lower()
    if "purchase" in tx_lower or "buy" in tx_lower:
        return "purchase"
    elif "sale" in tx_lower or "sell" in tx_lower:
        return "sale"
    elif "exchange" in tx_lower:
        return "exchange"
    return tx_lower


def _create_match_key(bioguide_id: str, name: str, ticker: str, tx_date: str, tx_type: str) -> str:
    """Create a unique key for matching trades."""
    norm_name = _normalize_quiver_name(name) if name else ""
    norm_type = _normalize_transaction_type(tx_type)
    ticker_upper = (ticker or "").upper().strip()
    date_part = (tx_date or "")[:10]

    # Prefer bioguide_id, fall back to name
    id_part = bioguide_id if bioguide_id else norm_name
    return f"{id_part}|{ticker_upper}|{date_part}|{norm_type}"


def _compare_fields(app_trade: dict, quiver_trade: dict, app_politician: dict) -> dict:
    """Compare fields between app and QuiverQuant trade, return mismatches."""
    from difflib import SequenceMatcher

    mismatches = {}

    # Critical fields
    # Politician name (fuzzy match)
    app_name = app_politician.get("full_name", "") if app_politician else ""
    quiver_name = quiver_trade.get("Representative", "")
    norm_app = _normalize_quiver_name(app_name)
    norm_quiver = _normalize_quiver_name(quiver_name)

    if norm_app and norm_quiver:
        similarity = SequenceMatcher(None, norm_app, norm_quiver).ratio()
        if similarity < 0.9:
            mismatches["politician_name"] = {
                "app": app_name,
                "quiver": quiver_name,
                "severity": "critical",
                "match": False,
                "similarity": round(similarity, 2)
            }

    # BioGuide ID
    app_bioguide = app_politician.get("bioguide_id", "") if app_politician else ""
    quiver_bioguide = quiver_trade.get("BioGuideID", "")
    if app_bioguide and quiver_bioguide and app_bioguide != quiver_bioguide:
        mismatches["bioguide_id"] = {
            "app": app_bioguide,
            "quiver": quiver_bioguide,
            "severity": "critical",
            "match": False
        }

    # Ticker
    app_ticker = (app_trade.get("asset_ticker") or "").upper()
    quiver_ticker = (quiver_trade.get("Ticker") or "").upper()
    if app_ticker != quiver_ticker:
        mismatches["ticker"] = {
            "app": app_ticker,
            "quiver": quiver_ticker,
            "severity": "critical",
            "match": False
        }

    # Transaction date
    app_date = (app_trade.get("transaction_date") or "")[:10]
    quiver_date = (quiver_trade.get("TransactionDate") or "")[:10]
    if app_date != quiver_date:
        mismatches["transaction_date"] = {
            "app": app_date,
            "quiver": quiver_date,
            "severity": "critical",
            "match": False
        }

    # Transaction type
    app_type = _normalize_transaction_type(app_trade.get("transaction_type", ""))
    quiver_type = _normalize_transaction_type(quiver_trade.get("Transaction", ""))
    if app_type != quiver_type:
        mismatches["transaction_type"] = {
            "app": app_trade.get("transaction_type", ""),
            "quiver": quiver_trade.get("Transaction", ""),
            "severity": "critical",
            "match": False
        }

    # Warning fields
    # Disclosure date
    app_disc = (app_trade.get("disclosure_date") or "")[:10]
    quiver_disc = (quiver_trade.get("ReportDate") or "")[:10]
    if app_disc and quiver_disc and app_disc != quiver_disc:
        mismatches["disclosure_date"] = {
            "app": app_disc,
            "quiver": quiver_disc,
            "severity": "warning",
            "match": False
        }

    # Amount range
    app_min = float(app_trade.get("amount_range_min") or 0)
    app_max = float(app_trade.get("amount_range_max") or 0)
    quiver_min, quiver_max = _parse_quiver_amount_range(quiver_trade.get("Range", ""))

    if quiver_min is not None and quiver_max is not None:
        if abs(app_min - quiver_min) > 1 or abs(app_max - quiver_max) > 1:
            mismatches["amount_range"] = {
                "app": f"${app_min:,.0f} - ${app_max:,.0f}",
                "quiver": quiver_trade.get("Range", ""),
                "severity": "warning",
                "match": False
            }

    # Party
    app_party = (app_politician.get("party") or "").upper()[:1] if app_politician else ""
    quiver_party = (quiver_trade.get("Party") or "").upper()[:1]
    if app_party and quiver_party and app_party != quiver_party:
        mismatches["party"] = {
            "app": app_party,
            "quiver": quiver_party,
            "severity": "warning",
            "match": False
        }

    return mismatches


def _diagnose_root_cause(mismatches: dict, app_trade: dict, quiver_trade: dict) -> str:
    """Diagnose the root cause of mismatches."""
    if not mismatches:
        return None

    # Check for name normalization issues
    if "politician_name" in mismatches:
        similarity = mismatches["politician_name"].get("similarity", 0)
        if similarity > 0.7:
            return "name_normalization"

    # Check for date issues
    if "transaction_date" in mismatches or "disclosure_date" in mismatches:
        return "date_parse_error"

    # Check for amount parsing
    if "amount_range" in mismatches:
        return "amount_parse_error"

    # Check for transaction type mapping
    if "transaction_type" in mismatches:
        return "transaction_type_mapping"

    # Check for ticker mismatch
    if "ticker" in mismatches:
        return "ticker_mismatch"

    return "unknown"


def _get_severity(mismatches: dict) -> str:
    """Determine overall severity from mismatches."""
    if not mismatches:
        return "info"
    for field_data in mismatches.values():
        if field_data.get("severity") == "critical":
            return "critical"
    return "warning"


def _store_validation_result(config: dict, result: dict) -> bool:
    """Store a validation result in the database."""
    import json

    url = config["SUPABASE_URL"]
    key = config.get("SUPABASE_KEY") or config.get("SUPABASE_SERVICE_ROLE_KEY")

    payload = {
        "trading_disclosure_id": result.get("trading_disclosure_id"),
        "quiver_record": result.get("quiver_record"),
        "match_key": result.get("match_key"),
        "validation_status": result["validation_status"],
        "field_mismatches": result.get("field_mismatches", {}),
        "root_cause": result.get("root_cause"),
        "severity": result.get("severity", "warning")
    }

    try:
        response = httpx.post(
            f"{url}/rest/v1/trade_validation_results",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json=payload,
            timeout=30
        )
        return response.status_code in [200, 201]
    except Exception as e:
        console.print(f"[red]Error storing validation result: {e}[/red]")
        return False


def _update_disclosure_validation_status(config: dict, disclosure_id: str, status: str) -> bool:
    """Update the validation status on a trading disclosure."""
    from datetime import datetime

    url = config["SUPABASE_URL"]
    key = config.get("SUPABASE_KEY") or config.get("SUPABASE_SERVICE_ROLE_KEY")

    try:
        response = httpx.patch(
            f"{url}/rest/v1/trading_disclosures?id=eq.{disclosure_id}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json={
                "quiver_validation_status": status,
                "quiver_validated_at": datetime.now().isoformat()
            },
            timeout=30
        )
        return response.status_code in [200, 204]
    except Exception:
        return False


@quiver.command("audit")
@click.option("--full", is_flag=True, help="Run full historical audit")
@click.option("--from", "from_date", help="Start date (YYYY-MM-DD)")
@click.option("--to", "to_date", help="End date (YYYY-MM-DD)")
@click.option("--limit", "-l", default=5000, help="Max QuiverQuant records to fetch")
@click.option("--dry-run", is_flag=True, help="Don't store results, just report")
def quiver_audit(full: bool, from_date: str, to_date: str, limit: int, dry_run: bool):
    """
    Run a deep validation audit comparing all trades against QuiverQuant.

    Examples:
        mcli run etl quiver audit --full
        mcli run etl quiver audit --from 2025-01-01 --to 2025-06-30
        mcli run etl quiver audit --full --dry-run
    """
    from datetime import datetime, timedelta
    import json

    api_key = _get_quiver_api_key()
    if not api_key:
        console.print("[red]Error: QUIVERQUANT_API_KEY not found[/red]")
        raise SystemExit(1)

    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    console.print("[bold cyan]QuiverQuant Validation Audit[/bold cyan]")
    console.print("=" * 60)

    if dry_run:
        console.print("[yellow]DRY RUN - results will not be stored[/yellow]\n")

    # Fetch QuiverQuant data
    console.print(f"[cyan]Fetching up to {limit} records from QuiverQuant...[/cyan]")
    qq_data = _fetch_quiverquant_data(api_key, limit=limit)

    if not qq_data:
        console.print("[red]Failed to fetch QuiverQuant data[/red]")
        raise SystemExit(1)

    console.print(f"  Fetched [green]{len(qq_data)}[/green] QuiverQuant records")

    # Filter by date if specified
    if from_date:
        qq_data = [t for t in qq_data if (t.get("TransactionDate") or "")[:10] >= from_date]
        console.print(f"  Filtered to [green]{len(qq_data)}[/green] records from {from_date}")
    if to_date:
        qq_data = [t for t in qq_data if (t.get("TransactionDate") or "")[:10] <= to_date]
        console.print(f"  Filtered to [green]{len(qq_data)}[/green] records until {to_date}")

    # Build QuiverQuant lookup by match key
    qq_by_key = {}
    for trade in qq_data:
        key = _create_match_key(
            trade.get("BioGuideID"),
            trade.get("Representative"),
            trade.get("Ticker"),
            trade.get("TransactionDate"),
            trade.get("Transaction")
        )
        qq_by_key[key] = trade

    console.print(f"  Created [green]{len(qq_by_key)}[/green] unique match keys\n")

    # Fetch app data with politicians
    console.print("[cyan]Fetching app database records...[/cyan]")
    app_trades = _fetch_quiver_supabase_data(
        config, "trading_disclosures",
        "id,asset_ticker,transaction_date,disclosure_date,transaction_type,amount_range_min,amount_range_max,politician_id,status",
        limit=50000,
        filters={"status": "eq.active"}
    )

    # Filter app trades by date
    if from_date:
        app_trades = [t for t in app_trades if (t.get("transaction_date") or "")[:10] >= from_date]
    if to_date:
        app_trades = [t for t in app_trades if (t.get("transaction_date") or "")[:10] <= to_date]

    console.print(f"  Found [green]{len(app_trades)}[/green] app trades in range")

    # Fetch politicians for lookup
    politicians = _fetch_quiver_supabase_data(
        config, "politicians",
        "id,full_name,bioguide_id,party,chamber",
        limit=10000
    )
    pol_by_id = {p["id"]: p for p in politicians if p.get("id")}
    console.print(f"  Loaded [green]{len(pol_by_id)}[/green] politicians\n")

    # Compare
    console.print("[cyan]Comparing trades...[/cyan]")

    results = {
        "match": 0,
        "mismatch": 0,
        "app_only": 0,
        "quiver_only": 0
    }
    root_causes = {}
    mismatched_trades = []
    app_keys_found = set()

    for app_trade in app_trades:
        politician = pol_by_id.get(app_trade.get("politician_id"))

        key = _create_match_key(
            politician.get("bioguide_id") if politician else None,
            politician.get("full_name") if politician else None,
            app_trade.get("asset_ticker"),
            app_trade.get("transaction_date"),
            app_trade.get("transaction_type")
        )
        app_keys_found.add(key)

        if key in qq_by_key:
            quiver_trade = qq_by_key[key]
            mismatches = _compare_fields(app_trade, quiver_trade, politician)

            if mismatches:
                results["mismatch"] += 1
                root_cause = _diagnose_root_cause(mismatches, app_trade, quiver_trade)
                severity = _get_severity(mismatches)

                root_causes[root_cause] = root_causes.get(root_cause, 0) + 1

                if len(mismatched_trades) < 50:  # Keep first 50 for display
                    mismatched_trades.append({
                        "app": app_trade,
                        "quiver": quiver_trade,
                        "mismatches": mismatches,
                        "root_cause": root_cause
                    })

                if not dry_run:
                    _store_validation_result(config, {
                        "trading_disclosure_id": app_trade.get("id"),
                        "quiver_record": quiver_trade,
                        "match_key": key,
                        "validation_status": "mismatch",
                        "field_mismatches": mismatches,
                        "root_cause": root_cause,
                        "severity": severity
                    })
                    _update_disclosure_validation_status(config, app_trade.get("id"), "mismatch")
            else:
                results["match"] += 1
                if not dry_run:
                    _update_disclosure_validation_status(config, app_trade.get("id"), "validated")
        else:
            results["app_only"] += 1
            if not dry_run:
                _store_validation_result(config, {
                    "trading_disclosure_id": app_trade.get("id"),
                    "match_key": key,
                    "validation_status": "app_only",
                    "root_cause": "missing_in_source",
                    "severity": "warning"
                })
                _update_disclosure_validation_status(config, app_trade.get("id"), "unmatched")

    # Find quiver-only trades
    for key, quiver_trade in qq_by_key.items():
        if key not in app_keys_found:
            results["quiver_only"] += 1
            root_causes["data_lag"] = root_causes.get("data_lag", 0) + 1

            if not dry_run:
                _store_validation_result(config, {
                    "quiver_record": quiver_trade,
                    "match_key": key,
                    "validation_status": "quiver_only",
                    "root_cause": "data_lag",
                    "severity": "warning"
                })

    # Print results
    total = sum(results.values())
    match_pct = (results["match"] / total * 100) if total > 0 else 0

    console.print("\n" + "=" * 60)
    console.print("[bold]Validation Audit Results[/bold]")
    console.print("=" * 60)

    table = Table()
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    table.add_row("✓ Matched", str(results["match"]), f"[green]{match_pct:.1f}%[/green]")
    table.add_row("⚠ Mismatched", str(results["mismatch"]), f"[yellow]{results['mismatch']/total*100:.1f}%[/yellow]" if total else "0%")
    table.add_row("✗ App Only", str(results["app_only"]), f"[yellow]{results['app_only']/total*100:.1f}%[/yellow]" if total else "0%")
    table.add_row("✗ Quiver Only", str(results["quiver_only"]), f"[yellow]{results['quiver_only']/total*100:.1f}%[/yellow]" if total else "0%")
    table.add_row("─" * 15, "─" * 8, "─" * 10)
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]", "[bold]100%[/bold]")

    console.print(table)

    if root_causes:
        console.print("\n[bold]Root Cause Breakdown:[/bold]")
        for cause, count in sorted(root_causes.items(), key=lambda x: -x[1]):
            console.print(f"  {cause}: [cyan]{count}[/cyan]")

    if mismatched_trades:
        console.print(f"\n[bold]Sample Mismatches (first {len(mismatched_trades)}):[/bold]")
        for i, m in enumerate(mismatched_trades[:5]):
            console.print(f"\n  [{i+1}] {m['quiver'].get('Representative', 'Unknown')} - {m['quiver'].get('Ticker', '?')}")
            console.print(f"      Root cause: [yellow]{m['root_cause']}[/yellow]")
            for field, data in m["mismatches"].items():
                console.print(f"      {field}: app=[cyan]{data['app']}[/cyan] vs quiver=[magenta]{data['quiver']}[/magenta]")

    if not dry_run:
        console.print(f"\n[green]Results stored in trade_validation_results table[/green]")


@quiver.command("report")
@click.option("--critical", is_flag=True, help="Show only critical mismatches")
@click.option("--root-cause", "by_root_cause", is_flag=True, help="Group by root cause")
@click.option("--unresolved", is_flag=True, help="Show only unresolved issues")
@click.option("--export", "export_format", type=click.Choice(["json", "csv"]), help="Export format")
def quiver_report(critical: bool, by_root_cause: bool, unresolved: bool, export_format: str):
    """
    Generate a report of validation results.

    Examples:
        mcli run etl quiver report
        mcli run etl quiver report --critical
        mcli run etl quiver report --root-cause
        mcli run etl quiver report --export csv
    """
    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    # Build query filters
    filters = {}
    if critical:
        filters["severity"] = "eq.critical"
    if unresolved:
        filters["resolved_at"] = "is.null"

    # Fetch validation results
    results = _fetch_quiver_supabase_data(
        config, "trade_validation_results",
        "*",
        limit=10000,
        filters=filters if filters else None,
        order="validated_at.desc"
    )

    if not results:
        console.print("[yellow]No validation results found[/yellow]")
        return

    console.print(f"\n[bold]QuiverQuant Validation Report[/bold]")
    console.print("=" * 60)
    console.print(f"Total results: [cyan]{len(results)}[/cyan]")

    # Aggregate by status
    by_status = {}
    by_cause = {}
    by_severity = {}

    for r in results:
        status = r.get("validation_status", "unknown")
        cause = r.get("root_cause", "unknown")
        severity = r.get("severity", "warning")

        by_status[status] = by_status.get(status, 0) + 1
        if cause:
            by_cause[cause] = by_cause.get(cause, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1

    console.print("\n[bold]By Status:[/bold]")
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        color = "green" if status == "match" else "yellow" if status in ["mismatch", "app_only"] else "red"
        console.print(f"  {status}: [{color}]{count}[/{color}]")

    if by_root_cause and by_cause:
        console.print("\n[bold]By Root Cause:[/bold]")
        for cause, count in sorted(by_cause.items(), key=lambda x: -x[1]):
            console.print(f"  {cause}: [cyan]{count}[/cyan]")

    console.print("\n[bold]By Severity:[/bold]")
    for sev, count in sorted(by_severity.items()):
        color = "red" if sev == "critical" else "yellow" if sev == "warning" else "dim"
        console.print(f"  {sev}: [{color}]{count}[/{color}]")

    # Export if requested
    if export_format:
        import json
        from pathlib import Path

        filename = f"quiver_validation_report.{export_format}"

        if export_format == "json":
            with open(filename, "w") as f:
                json.dump(results, f, indent=2, default=str)
        elif export_format == "csv":
            import csv
            with open(filename, "w", newline="") as f:
                if results:
                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)

        console.print(f"\n[green]Exported to {filename}[/green]")


@quiver.command("resolve")
@click.argument("validation_id")
@click.option("--notes", "-n", required=True, help="Resolution notes")
def quiver_resolve(validation_id: str, notes: str):
    """
    Mark a validation issue as resolved.

    Example: mcli run etl quiver resolve abc123 --notes "Fixed name normalization"
    """
    from datetime import datetime

    config = _get_quiver_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found[/red]")
        raise SystemExit(1)

    url = config["SUPABASE_URL"]
    key = config.get("SUPABASE_KEY") or config.get("SUPABASE_SERVICE_ROLE_KEY")

    try:
        response = httpx.patch(
            f"{url}/rest/v1/trade_validation_results?id=eq.{validation_id}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json={
                "resolved_at": datetime.now().isoformat(),
                "resolution_notes": notes
            },
            timeout=30
        )

        if response.status_code in [200, 204]:
            console.print(f"[green]Marked validation {validation_id} as resolved[/green]")
            console.print(f"Notes: {notes}")
        else:
            console.print(f"[red]Failed to update: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# =============================================================================
# Backfill Commands (Subgroup)
# =============================================================================

def _load_env():
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


def _get_backfill_supabase_client():
    """Create Supabase client for backfill operations."""
    from supabase import create_client
    _load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def _extract_transaction_type(raw_data: dict) -> Optional[str]:
    """Extract transaction type from raw_data."""
    import re
    if not raw_data:
        return None
    raw_row = raw_data.get("raw_row", [])
    if not raw_row:
        return None
    full_text = " ".join(str(cell).replace("\x00", "") for cell in raw_row if cell)
    full_lower = full_text.lower()
    if any(kw in full_lower for kw in ["purchase", "bought", "buy"]):
        return "purchase"
    elif any(kw in full_lower for kw in ["sale", "sold", "sell", "exchange"]):
        return "sale"
    if re.search(r"\bP\s+\d{1,2}/\d{1,2}/\d{4}", full_text):
        return "purchase"
    elif re.search(r"\bS\s+\d{1,2}/\d{1,2}/\d{4}", full_text):
        return "sale"
    return None


def _is_metadata_only(asset_name: str) -> bool:
    """Check if an asset_name is just metadata."""
    import re
    if not asset_name:
        return True
    clean_name = asset_name.replace("\x00", "").strip()
    metadata_patterns = [
        r"^F\s*S\s*:", r"^S\s*O\s*:", r"^Owner\s*:", r"^Filing\s*(ID|Date)\s*:",
        r"^Document\s*ID\s*:", r"^Filer\s*:", r"^Status\s*:", r"^Type\s*:",
    ]
    for pattern in metadata_patterns:
        if re.match(pattern, clean_name, re.IGNORECASE):
            return True
    return False


def _extract_ticker_from_name(asset_name: str) -> Optional[str]:
    """Extract ticker from asset name."""
    import re
    if not asset_name:
        return None
    match = re.search(r"\(([A-Z]{1,5})\)", asset_name)
    if match:
        return match.group(1)
    return None


def _extract_dates_from_raw_row(raw_data: dict):
    """Extract dates from raw_data."""
    import re
    from datetime import datetime as dt
    if not raw_data:
        return None, None
    raw_row = raw_data.get("raw_row", [])
    if not raw_row:
        return None, None
    row_text = " ".join(str(cell).replace("\x00", "") for cell in raw_row if cell)
    date_pattern = r"[PS]\s*(?:\(partial\))?\s*(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})"
    match = re.search(date_pattern, row_text, re.IGNORECASE)
    if match:
        try:
            tx_date = dt.strptime(match.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
            notif_date = dt.strptime(match.group(2), "%m/%d/%Y").strftime("%Y-%m-%d")
            return tx_date, notif_date
        except ValueError:
            pass
    return None, None


@etl.group(name="backfill")
def backfill():
    """Data quality backfill commands."""
    pass


@backfill.command(name="transaction-types")
@click.option("--limit", "-l", type=int, default=None, help="Limit records to process")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--delete-metadata", is_flag=True, help="Delete metadata-only records")
def backfill_transaction_types(limit: Optional[int], dry_run: bool, delete_metadata: bool):
    """
    Backfill transaction_type for records with 'unknown' type.

    Example: mcli run etl backfill transaction-types --dry-run
    """
    click.echo("Connecting to Supabase...")
    supabase = _get_backfill_supabase_client()

    click.echo("Querying records with unknown transaction_type...")
    all_records = []
    offset = 0
    batch_size = 1000

    while True:
        response = (
            supabase.table("trading_disclosures")
            .select("id, transaction_type, raw_data, asset_name")
            .eq("transaction_type", "unknown")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        records = response.data or []
        if not records:
            break
        all_records.extend(records)
        if len(records) < batch_size or (limit and len(all_records) >= limit):
            break
        offset += batch_size

    if limit:
        all_records = all_records[:limit]

    click.echo(f"Found {len(all_records)} records")
    updated = deleted = no_type_found = errors = 0

    for record in all_records:
        record_id = record["id"]
        raw_data = record.get("raw_data") or {}
        asset_name = record.get("asset_name", "")

        if delete_metadata and _is_metadata_only(asset_name):
            if not dry_run:
                try:
                    supabase.table("trading_disclosures").delete().eq("id", record_id).execute()
                except Exception:
                    errors += 1
            deleted += 1
            continue

        tx_type = _extract_transaction_type(raw_data)
        if tx_type:
            if not dry_run:
                try:
                    supabase.table("trading_disclosures").update({"transaction_type": tx_type}).eq("id", record_id).execute()
                except Exception:
                    errors += 1
            updated += 1
        else:
            no_type_found += 1

    click.echo(f"\nResults: Updated={updated}, Deleted={deleted}, No type={no_type_found}, Errors={errors}")


@backfill.command(name="tickers")
@click.option("--limit", "-l", type=int, default=None)
@click.option("--dry-run", is_flag=True)
def backfill_tickers(limit: Optional[int], dry_run: bool):
    """Backfill asset_ticker for records with missing tickers."""
    supabase = _get_backfill_supabase_client()
    response = supabase.table("trading_disclosures").select("id, asset_name").is_("asset_ticker", "null").limit(limit or 1000).execute()
    records = response.data or []
    click.echo(f"Found {len(records)} records with missing tickers")

    updated = 0
    for record in records:
        ticker = _extract_ticker_from_name(record.get("asset_name", ""))
        if ticker and not dry_run:
            try:
                supabase.table("trading_disclosures").update({"asset_ticker": ticker}).eq("id", record["id"]).execute()
                updated += 1
            except Exception:
                pass

    click.echo(f"Updated: {updated}")


@backfill.command(name="stats")
def backfill_stats():
    """Show current data quality statistics."""
    supabase = _get_backfill_supabase_client()

    click.echo("\nTransaction Type Distribution:")
    for tx_type in ["purchase", "sale", "holding", "unknown"]:
        response = supabase.table("trading_disclosures").select("id", count="exact").eq("transaction_type", tx_type).execute()
        click.echo(f"  {tx_type:12}: {response.count or 0:,}")


# =============================================================================
# ML Commands (Subgroup)
# =============================================================================

ML_ETL_SERVICE_URL = os.environ.get("ETL_SERVICE_URL", "https://politician-trading-etl.fly.dev")


@etl.group(name="ml")
def ml():
    """ML model training, testing, and management."""
    pass


@ml.command(name="train")
@click.option("--lookback", "-l", default=365, help="Days of training data")
@click.option("--model", "-m", default="xgboost", type=click.Choice(["xgboost", "lightgbm"]))
@click.option("--wait", "-w", is_flag=True, help="Wait for training to complete")
def ml_train(lookback: int, model: str, wait: bool):
    """
    Train a new ML model.

    Example: mcli run etl ml train --model lightgbm
    """
    click.echo(f"🧠 Training new ML model ({model}, {lookback} days)...")

    try:
        response = httpx.post(
            f"{ML_ETL_SERVICE_URL}/ml/train",
            json={"lookback_days": lookback, "model_type": model},
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        job_id = data.get("job_id", "unknown")
        click.echo(f"✓ Training job started: {job_id}")

        if wait:
            _ml_wait_for_training(job_id)

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@ml.command(name="status")
@click.argument("job_id", required=False)
def ml_status(job_id: Optional[str]):
    """Check training job status or list all models."""
    if job_id:
        _ml_show_training_status(job_id)
    else:
        _ml_list_models()


@ml.command(name="active")
def ml_active():
    """Show the currently active model."""
    try:
        response = httpx.get(f"{ML_ETL_SERVICE_URL}/ml/models/active", timeout=10.0)
        if response.status_code == 404:
            click.echo("❌ No active ML model found.")
            return
        response.raise_for_status()
        data = response.json()
        click.echo("🧠 Active ML Model")
        click.echo(f"  Name: {data.get('model_name', 'unknown')}")
        click.echo(f"  Type: {data.get('model_type', '?')}")
        metrics = data.get("metrics", {})
        if metrics:
            click.echo(f"  Accuracy: {metrics.get('accuracy', 0):.2%}")
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


@ml.command(name="health")
def ml_health():
    """Check ML service health."""
    try:
        response = httpx.get(f"{ML_ETL_SERVICE_URL}/ml/health", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        status = data.get("status", "unknown")
        click.echo(f"{'✓' if status == 'healthy' else '⚠'} ML service: {status}")
    except httpx.HTTPError as e:
        click.echo(f"✗ ML service unavailable: {e}", err=True)


@ml.command(name="predict")
@click.argument("ticker")
@click.option("--politician-count", "-p", default=3)
@click.option("--buy-sell-ratio", "-r", default=2.0)
def ml_predict(ticker: str, politician_count: int, buy_sell_ratio: float):
    """Get ML prediction for a ticker."""
    features = {
        "ticker": ticker.upper(),
        "politician_count": politician_count,
        "buy_sell_ratio": buy_sell_ratio,
        "recent_activity_30d": 4,
        "bipartisan": False,
        "net_volume": 100000,
        "volume_magnitude": 5,
        "party_alignment": 0.5,
        "committee_relevance": 0.5,
        "disclosure_delay": 30,
        "sentiment_score": 0.0,
        "market_momentum": 0.0,
        "sector_performance": 0.0,
    }

    try:
        response = httpx.post(
            f"{ML_ETL_SERVICE_URL}/ml/predict",
            json={"features": features, "use_cache": False},
            timeout=30.0
        )
        if response.status_code == 503:
            click.echo("❌ No trained model available.")
            return
        response.raise_for_status()
        data = response.json()
        signal = data.get("signal_type", "unknown")
        confidence = data.get("confidence", 0)
        click.echo(f"🧠 {ticker.upper()}: {signal} ({confidence:.1%})")
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


@ml.command(name="list")
@click.option("--limit", "-n", default=10)
def ml_list(limit: int):
    """List all trained models."""
    try:
        response = httpx.get(f"{ML_ETL_SERVICE_URL}/ml/models", timeout=10.0)
        response.raise_for_status()
        models = response.json().get("models", [])[:limit]
        if not models:
            click.echo("No models found. Train with: mcli run etl ml train")
            return
        for m in models:
            status_icon = {"active": "✓", "archived": "○", "failed": "✗"}.get(m.get("status", ""), "?")
            click.echo(f"  {status_icon} {m.get('model_name', 'unknown')} ({m.get('model_type', '?')})")
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


def _ml_show_training_status(job_id: str):
    """Show training status."""
    try:
        response = httpx.get(f"{ML_ETL_SERVICE_URL}/ml/train/{job_id}", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        click.echo(f"Status: {data.get('status', 'unknown')} ({data.get('progress', 0)}%)")
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


def _ml_wait_for_training(job_id: str):
    """Wait for training to complete."""
    while True:
        try:
            response = httpx.get(f"{ML_ETL_SERVICE_URL}/ml/train/{job_id}", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                if status in ("completed", "failed", "error"):
                    click.echo(f"Training {status}")
                    break
        except Exception:
            pass
        time.sleep(10)


def _ml_list_models():
    """List trained models."""
    try:
        response = httpx.get(f"{ML_ETL_SERVICE_URL}/ml/models", timeout=10.0)
        response.raise_for_status()
        models = response.json().get("models", [])
        if not models:
            click.echo("No trained models found.")
            return
        for m in models:
            click.echo(f"  {m.get('model_name', 'unknown')} - {m.get('status', '?')}")
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)

# Entry point for mcli
app = etl
