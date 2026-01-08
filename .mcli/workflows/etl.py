"""ETL commands for politician trading data ingestion and ML training."""

import os
import time
import subprocess
import click
import httpx
from pathlib import Path

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

            click.echo(f"\n{status_icon} [{report_status.upper():8}] {created}")
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
