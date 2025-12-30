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
def trigger(year: int, limit: int | None, wait: bool):
    """
    Trigger ETL job for a specific year.

    Example: mcli run etl trigger 2024
    """
    click.echo(f"Triggering ETL for year {year}...")

    payload = {"source": "house", "year": year}
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
def ingest_range(start_year: int, end_year: int, limit: int | None, sequential: bool):
    """
    Trigger ETL for a range of years.

    Example: mcli run etl ingest-range 2016 2024
    """
    if start_year > end_year:
        click.echo("Error: start_year must be <= end_year", err=True)
        raise SystemExit(1)

    years = list(range(start_year, end_year + 1))
    click.echo(f"Triggering ETL for years: {years}")

    job_ids = {}

    for year in years:
        click.echo(f"\n{'='*50}")
        click.echo(f"Starting ETL for {year}...")

        payload = {"source": "house", "year": year}
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
# ML Training Commands
# =============================================================================

@etl.command(name="ml-train")
@click.option("--lookback", "-l", default=365, help="Days of training data (default: 365)")
@click.option("--model", "-m", default="xgboost", type=click.Choice(["xgboost", "lightgbm"]), help="Model type")
@click.option("--wait", "-w", is_flag=True, help="Wait for training to complete")
def ml_train(lookback: int, model: str, wait: bool):
    """
    Trigger ML model training.

    Trains a new XGBoost/LightGBM model on historical disclosure data
    to predict trading signals.

    Examples:
        mcli run etl ml-train                    # Train with defaults
        mcli run etl ml-train --lookback 180    # Use 6 months of data
        mcli run etl ml-train --model lightgbm  # Use LightGBM
        mcli run etl ml-train --wait            # Wait for completion
    """
    click.echo(f"🧠 Triggering ML model training...")
    click.echo(f"  Model: {model}")
    click.echo(f"  Lookback: {lookback} days")

    payload = {
        "lookback_days": lookback,
        "model_type": model
    }

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/ml/train",
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data.get("job_id", "unknown")
        click.echo(f"\n✓ Training job started: {job_id}")

        if wait:
            click.echo("\nWaiting for training to complete...")
            _wait_for_ml_training(job_id)
        else:
            click.echo(f"\nTo check status: mcli run etl ml-status {job_id}")

    except httpx.HTTPStatusError as e:
        click.echo(f"Error: {e.response.status_code} - {e.response.text}", err=True)
        raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="ml-status")
@click.argument("job_id", required=False)
@click.option("--watch", "-w", is_flag=True, help="Watch training progress")
def ml_status(job_id: str | None, watch: bool):
    """
    Check ML training job status or list models.

    Without JOB_ID: Lists all trained models
    With JOB_ID: Shows training job status

    Examples:
        mcli run etl ml-status              # List models
        mcli run etl ml-status <job_id>     # Check job status
        mcli run etl ml-status <job_id> -w  # Watch progress
    """
    if job_id:
        if watch:
            _wait_for_ml_training(job_id)
        else:
            _show_ml_training_status(job_id)
    else:
        # List models
        _list_ml_models()


def _show_ml_training_status(job_id: str) -> dict:
    """Show ML training job status."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/ml/train/{job_id}",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        progress = data.get("progress", 0)
        total = data.get("total", 0)
        message = data.get("message", "")

        if total:
            pct = (progress / total * 100) if total else 0
            click.echo(f"Status: {status} | Progress: {progress}/{total} ({pct:.1f}%)")
        else:
            click.echo(f"Status: {status}")

        if message:
            click.echo(f"  {message}")

        return data

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            click.echo(f"Training job not found: {job_id}")
        else:
            click.echo(f"Error: {e}", err=True)
        return {"status": "error"}
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        return {"status": "error"}


def _wait_for_ml_training(job_id: str):
    """Wait for ML training to complete."""
    while True:
        data = _show_ml_training_status(job_id)
        status = data.get("status", "unknown")

        if status in ("completed", "failed", "error"):
            if status == "completed":
                click.echo("\n✓ Training completed successfully!")
                if "metrics" in data:
                    metrics = data["metrics"]
                    click.echo(f"  Accuracy: {metrics.get('accuracy', 0):.2%}")
                    click.echo(f"  F1 Score: {metrics.get('f1_weighted', 0):.2%}")
            else:
                click.echo(f"\n✗ Training ended with status: {status}")
            break

        time.sleep(10)


def _list_ml_models():
    """List all trained ML models."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/ml/models",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        models = data.get("models", [])

        if not models:
            click.echo("No trained models found.")
            click.echo("\nTo train a model: mcli run etl ml-train")
            return

        click.echo(f"Trained Models ({len(models)}):\n")

        for model in models:
            status = model.get("status", "unknown")
            status_icon = "✓" if status == "active" else "○"
            name = model.get("model_name", "unknown")
            version = model.get("model_version", "?")
            model_type = model.get("model_type", "?")
            metrics = model.get("metrics", {})
            accuracy = metrics.get("accuracy", 0)

            click.echo(f"  {status_icon} {name} v{version} ({model_type})")
            click.echo(f"    Status: {status} | Accuracy: {accuracy:.1%}")

            if model.get("training_completed_at"):
                click.echo(f"    Trained: {model['training_completed_at'][:10]}")

            click.echo()

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


@etl.command(name="ml-active")
def ml_active():
    """
    Show the currently active ML model.

    Displays model metrics and feature importance.
    """
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/ml/models/active",
            timeout=10.0
        )

        if response.status_code == 404:
            click.echo("No active ML model found.")
            click.echo("\nTo train a model: mcli run etl ml-train")
            return

        response.raise_for_status()
        data = response.json()

        click.echo("🧠 Active ML Model\n")
        click.echo(f"  Name: {data.get('model_name', 'unknown')}")
        click.echo(f"  Version: {data.get('model_version', '?')}")
        click.echo(f"  Type: {data.get('model_type', '?')}")

        metrics = data.get("metrics", {})
        if metrics:
            click.echo(f"\n  Metrics:")
            click.echo(f"    Accuracy: {metrics.get('accuracy', 0):.2%}")
            click.echo(f"    F1 Score: {metrics.get('f1_weighted', 0):.2%}")
            click.echo(f"    Training samples: {metrics.get('training_samples', 0):,}")

        features = data.get("feature_importance", {})
        if features:
            click.echo(f"\n  Top Features:")
            sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)[:5]
            for name, importance in sorted_features:
                bar = "█" * int(importance * 20)
                click.echo(f"    {name}: {bar} {importance:.3f}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


@etl.command(name="ml-health")
def ml_health():
    """Check ML service health."""
    try:
        response = httpx.get(f"{ETL_SERVICE_URL}/ml/health", timeout=10.0)
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        if status == "healthy":
            click.echo(f"✓ ML service is healthy")
        else:
            click.echo(f"⚠ ML service status: {status}")

        if "model_loaded" in data:
            click.echo(f"  Model loaded: {data['model_loaded']}")

    except httpx.HTTPError as e:
        click.echo(f"✗ ML service unavailable: {e}", err=True)
        raise SystemExit(1)


@etl.command(name="ml-train-watch")
@click.option("--lookback", "-l", default=365, help="Days of training data (default: 365)")
@click.option("--model", "-m", default="xgboost", type=click.Choice(["xgboost", "lightgbm"]), help="Model type")
@click.option("--verbose", "-v", is_flag=True, help="Show all logs (not just ML-related)")
def ml_train_watch(lookback: int, model: str, verbose: bool):
    """
    Train ML model and stream logs in real-time.

    This command triggers training and streams the Fly.io logs so you can
    see feature extraction, model training, and metrics as they happen.

    Examples:
        mcli run etl ml-train-watch                    # Train with defaults
        mcli run etl ml-train-watch --lookback 180    # Use 6 months of data
        mcli run etl ml-train-watch --model lightgbm  # Use LightGBM
        mcli run etl ml-train-watch -v                # Show all logs
    """
    import select
    import signal
    import threading
    from datetime import datetime

    click.echo(f"🧠 ML Training with Live Logs")
    click.echo(f"{'='*50}")
    click.echo(f"  Model: {model}")
    click.echo(f"  Lookback: {lookback} days")
    click.echo(f"  Verbose: {verbose}")
    click.echo(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"{'='*50}\n")

    # ML-related keywords to filter logs
    ML_KEYWORDS = [
        "ml", "train", "model", "feature", "xgboost", "lightgbm",
        "accuracy", "precision", "recall", "f1", "auc", "roc",
        "epoch", "iteration", "batch", "loading", "saving",
        "predict", "inference", "sklearn", "numpy", "pandas",
        "error", "warning", "exception", "failed", "success",
        "supabase", "fetching", "disclosure", "ticker", "signal"
    ]

    # State
    training_complete = threading.Event()
    job_id = None
    log_process = None

    def cleanup(signum=None, frame=None):
        """Clean up log streaming process."""
        nonlocal log_process
        if log_process:
            log_process.terminate()
            try:
                log_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                log_process.kill()
        if signum:
            raise SystemExit(0)

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start training job
    payload = {
        "lookback_days": lookback,
        "model_type": model
    }

    try:
        click.echo("📤 Starting training job...")
        response = httpx.post(
            f"{ETL_SERVICE_URL}/ml/train",
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()

        job_id = data.get("job_id", "unknown")
        click.echo(f"✓ Training job started: {job_id}\n")

    except httpx.HTTPStatusError as e:
        click.echo(f"Error: {e.response.status_code} - {e.response.text}", err=True)
        raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Start streaming logs
    filter_msg = "all logs" if verbose else "ML-related logs (use -v for all)"
    click.echo(f"📺 Streaming {filter_msg} from {FLY_APP}...")
    click.echo(f"{'─'*50}")

    try:
        log_process = subprocess.Popen(
            ["flyctl", "logs", "--app", FLY_APP],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Thread to poll training status
        def poll_status():
            """Background thread to check training completion."""
            while not training_complete.is_set():
                try:
                    resp = httpx.get(
                        f"{ETL_SERVICE_URL}/ml/train/{job_id}",
                        timeout=10.0
                    )
                    if resp.status_code == 200:
                        status_data = resp.json()
                        status = status_data.get("status", "unknown")
                        if status in ("completed", "failed", "error"):
                            training_complete.set()
                            return status_data
                except Exception:
                    pass
                time.sleep(5)
            return None

        # Start status polling in background
        status_thread = threading.Thread(target=poll_status, daemon=True)
        status_thread.start()

        # Stream logs with non-blocking read using select
        import os
        import fcntl

        # Set stdout to non-blocking mode
        fd = log_process.stdout.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        log_buffer = ""

        while not training_complete.is_set():
            # Use select with timeout to check for available data
            ready, _, _ = select.select([log_process.stdout], [], [], 0.5)

            if ready:
                try:
                    chunk = log_process.stdout.read(4096)
                    if chunk:
                        log_buffer += chunk
                        # Process complete lines
                        while "\n" in log_buffer:
                            line, log_buffer = log_buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue

                            # Filter logs based on verbose flag
                            if verbose:
                                click.echo(line)
                            else:
                                line_lower = line.lower()
                                if any(kw in line_lower for kw in ML_KEYWORDS):
                                    click.echo(line)
                except (IOError, OSError):
                    pass

            # Check if process ended
            if log_process.poll() is not None:
                break

        # Wait for status thread to finish
        status_thread.join(timeout=5)

        click.echo(f"\n{'─'*50}")

        # Fetch final status
        try:
            response = httpx.get(
                f"{ETL_SERVICE_URL}/ml/train/{job_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                final_data = response.json()
                final_status = final_data.get("status", "unknown")

                if final_status == "completed":
                    click.echo("\n✅ Training completed successfully!")
                    metrics = final_data.get("metrics", {})
                    if metrics:
                        click.echo(f"\n📊 Model Metrics:")
                        click.echo(f"  Accuracy: {metrics.get('accuracy', 0):.2%}")
                        click.echo(f"  F1 Score: {metrics.get('f1_weighted', 0):.2%}")
                        click.echo(f"  Precision: {metrics.get('precision_weighted', 0):.2%}")
                        click.echo(f"  Recall: {metrics.get('recall_weighted', 0):.2%}")
                        if metrics.get('training_samples'):
                            click.echo(f"  Training samples: {metrics['training_samples']:,}")

                    features = final_data.get("feature_importance", {})
                    if features:
                        click.echo(f"\n🎯 Top Features:")
                        sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)[:5]
                        for name, importance in sorted_features:
                            bar = "█" * int(importance * 20)
                            click.echo(f"  {name}: {bar} {importance:.3f}")
                else:
                    click.echo(f"\n❌ Training ended with status: {final_status}")
                    if final_data.get("message"):
                        click.echo(f"  Message: {final_data['message']}")
        except Exception:
            pass

    except FileNotFoundError:
        click.echo("Error: flyctl not found. Install with: brew install flyctl", err=True)
        raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\n\n⏹️ Stopped watching logs")
    finally:
        cleanup()

    click.echo(f"\nTo check model: mcli run etl ml-active")
