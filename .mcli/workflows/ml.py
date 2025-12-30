"""ML model training, testing, and management commands."""

import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import httpx

# Configuration
ETL_SERVICE_URL = os.environ.get(
    "ETL_SERVICE_URL",
    "https://politician-trading-etl.fly.dev"
)
FLY_APP = "politician-trading-etl"


@click.group(name="ml")
def ml():
    """ML model training, testing, and management."""
    pass


# =============================================================================
# Training Commands
# =============================================================================

@ml.command(name="train")
@click.option("--lookback", "-l", default=365, help="Days of training data (default: 365)")
@click.option("--model", "-m", default="xgboost", type=click.Choice(["xgboost", "lightgbm"]), help="Model type")
@click.option("--wait", "-w", is_flag=True, help="Wait for training to complete")
def train(lookback: int, model: str, wait: bool):
    """
    Train a new ML model.

    Examples:
        mcli run ml train                    # Train with defaults
        mcli run ml train --lookback 180     # Use 6 months of data
        mcli run ml train --model lightgbm   # Use LightGBM
        mcli run ml train --wait             # Wait for completion
    """
    click.echo(f"🧠 Training new ML model...")
    click.echo(f"  Model type: {model}")
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
            _wait_for_training(job_id)
        else:
            click.echo(f"\nTo check status: mcli run ml status {job_id}")
            click.echo(f"To watch logs: mcli run ml train-watch --job {job_id}")

    except httpx.HTTPStatusError as e:
        click.echo(f"Error: {e.response.status_code} - {e.response.text}", err=True)
        raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@ml.command(name="train-watch")
@click.option("--lookback", "-l", default=365, help="Days of training data (default: 365)")
@click.option("--model", "-m", default="xgboost", type=click.Choice(["xgboost", "lightgbm"]), help="Model type")
@click.option("--job", "-j", default=None, help="Watch existing job instead of starting new one")
@click.option("--verbose", "-v", is_flag=True, help="Show all logs (not just ML-related)")
def train_watch(lookback: int, model: str, job: Optional[str], verbose: bool):
    """
    Train model and stream logs in real-time.

    Examples:
        mcli run ml train-watch                    # Train with defaults
        mcli run ml train-watch --lookback 180    # Use 6 months of data
        mcli run ml train-watch --job abc123      # Watch existing job
        mcli run ml train-watch -v                # Show all logs
    """
    import select
    import signal
    import threading
    import fcntl

    job_id = job

    # ML-related keywords to filter logs
    ML_KEYWORDS = [
        "ml", "train", "model", "feature", "xgboost", "lightgbm",
        "accuracy", "precision", "recall", "f1", "auc", "roc",
        "epoch", "iteration", "batch", "loading", "saving",
        "predict", "inference", "sklearn", "numpy", "pandas",
        "error", "warning", "exception", "failed", "success",
        "supabase", "fetching", "disclosure", "ticker", "signal"
    ]

    click.echo(f"🧠 ML Training with Live Logs")
    click.echo(f"{'='*50}")

    if not job_id:
        click.echo(f"  Model: {model}")
        click.echo(f"  Lookback: {lookback} days")

    click.echo(f"  Verbose: {verbose}")
    click.echo(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"{'='*50}\n")

    # State
    training_complete = threading.Event()
    log_process = None

    def cleanup(signum=None, frame=None):
        nonlocal log_process
        if log_process:
            log_process.terminate()
            try:
                log_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                log_process.kill()
        if signum:
            raise SystemExit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start training job if not watching existing
    if not job_id:
        payload = {"lookback_days": lookback, "model_type": model}

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

        def poll_status():
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

        status_thread = threading.Thread(target=poll_status, daemon=True)
        status_thread.start()

        # Non-blocking read
        fd = log_process.stdout.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        log_buffer = ""

        while not training_complete.is_set():
            ready, _, _ = select.select([log_process.stdout], [], [], 0.5)

            if ready:
                try:
                    chunk = log_process.stdout.read(4096)
                    if chunk:
                        log_buffer += chunk
                        while "\n" in log_buffer:
                            line, log_buffer = log_buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue

                            if verbose:
                                click.echo(line)
                            else:
                                line_lower = line.lower()
                                if any(kw in line_lower for kw in ML_KEYWORDS):
                                    click.echo(line)
                except (IOError, OSError):
                    pass

            if log_process.poll() is not None:
                break

        status_thread.join(timeout=5)
        click.echo(f"\n{'─'*50}")

        # Fetch final status
        _show_training_result(job_id)

    except FileNotFoundError:
        click.echo("Error: flyctl not found. Install with: brew install flyctl", err=True)
        raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\n\n⏹️ Stopped watching logs")
    finally:
        cleanup()


# =============================================================================
# Model Status & Info Commands
# =============================================================================

@ml.command(name="status")
@click.argument("job_id", required=False)
@click.option("--watch", "-w", is_flag=True, help="Watch training progress")
def status(job_id: Optional[str], watch: bool):
    """
    Check training job status or list all models.

    Examples:
        mcli run ml status              # List all models
        mcli run ml status <job_id>     # Check job status
        mcli run ml status <job_id> -w  # Watch progress
    """
    if job_id:
        if watch:
            _wait_for_training(job_id)
        else:
            _show_training_status(job_id)
    else:
        _list_models()


@ml.command(name="active")
def active():
    """
    Show the currently active model with details.

    Displays model metrics, feature importance, and training info.
    """
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/ml/models/active",
            timeout=10.0
        )

        if response.status_code == 404:
            click.echo("❌ No active ML model found.")
            click.echo("\nTo train a model: mcli run ml train")
            return

        response.raise_for_status()
        data = response.json()

        click.echo("🧠 Active ML Model\n")
        click.echo(f"  ID: {data.get('id', '?')[:8]}...")
        click.echo(f"  Name: {data.get('model_name', 'unknown')}")
        click.echo(f"  Version: {data.get('model_version', '?')}")
        click.echo(f"  Type: {data.get('model_type', '?')}")

        if data.get('training_completed_at'):
            click.echo(f"  Trained: {data['training_completed_at'][:19]}")

        metrics = data.get("metrics", {})
        if metrics:
            click.echo(f"\n📊 Metrics:")
            click.echo(f"  Accuracy: {metrics.get('accuracy', 0):.2%}")
            click.echo(f"  F1 Score: {metrics.get('f1_weighted', 0):.2%}")
            click.echo(f"  Precision: {metrics.get('precision_weighted', 0):.2%}")
            click.echo(f"  Recall: {metrics.get('recall_weighted', 0):.2%}")
            if metrics.get('training_samples'):
                click.echo(f"  Training samples: {metrics['training_samples']:,}")
            if metrics.get('validation_samples'):
                click.echo(f"  Validation samples: {metrics['validation_samples']:,}")

        features = data.get("feature_importance", {})
        if features:
            click.echo(f"\n🎯 Top Features:")
            sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)[:8]
            max_len = max(len(name) for name, _ in sorted_features)
            for name, importance in sorted_features:
                bar = "█" * int(importance * 30)
                click.echo(f"  {name:<{max_len}} {bar} {importance:.3f}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


@ml.command(name="list")
@click.option("--limit", "-n", default=10, help="Number of models to show")
def list_models(limit: int):
    """List all trained models."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/ml/models",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        models = data.get("models", [])[:limit]

        if not models:
            click.echo("No trained models found.")
            click.echo("\nTo train a model: mcli run ml train")
            return

        click.echo(f"📋 Trained Models ({len(models)} shown)\n")

        for model in models:
            status = model.get("status", "unknown")
            status_icon = {"active": "✓", "archived": "○", "failed": "✗", "training": "⋯"}.get(status, "?")
            name = model.get("model_name", "unknown")
            version = model.get("model_version", "?")
            model_type = model.get("model_type", "?")
            metrics = model.get("metrics", {})
            accuracy = metrics.get("accuracy", 0)

            click.echo(f"  {status_icon} {name}")
            click.echo(f"    Version: {version} | Type: {model_type}")
            click.echo(f"    Status: {status} | Accuracy: {accuracy:.1%}")

            if model.get("training_completed_at"):
                click.echo(f"    Trained: {model['training_completed_at'][:10]}")

            click.echo()

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


@ml.command(name="health")
def health():
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

        click.echo(f"  Model loaded: {data.get('model_loaded', False)}")
        if data.get('model_version'):
            click.echo(f"  Model version: {data['model_version']}")
        click.echo(f"  Feature count: {data.get('feature_count', '?')}")

    except httpx.HTTPError as e:
        click.echo(f"✗ ML service unavailable: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# Model Testing & Prediction Commands
# =============================================================================

@ml.command(name="predict")
@click.argument("ticker")
@click.option("--politician-count", "-p", default=3, help="Number of politicians trading")
@click.option("--buy-sell-ratio", "-r", default=2.0, help="Buy/sell ratio")
@click.option("--recent-activity", "-a", default=5, help="Recent activity count (30d)")
@click.option("--bipartisan", "-b", is_flag=True, help="Bipartisan trading")
@click.option("--volume", "-v", default=100000, help="Net volume")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def predict(ticker: str, politician_count: int, buy_sell_ratio: float,
            recent_activity: int, bipartisan: bool, volume: int, as_json: bool):
    """
    Get ML prediction for a ticker with custom features.

    Examples:
        mcli run ml predict AAPL
        mcli run ml predict NVDA -p 5 -r 3.0 -b
        mcli run ml predict MSFT --json
    """
    features = {
        "ticker": ticker.upper(),
        "politician_count": politician_count,
        "buy_sell_ratio": buy_sell_ratio,
        "recent_activity_30d": recent_activity,
        "bipartisan": bipartisan,
        "net_volume": volume,
        "volume_magnitude": len(str(abs(volume))),
        "party_alignment": 0.5,
        "committee_relevance": 0.5,
        "disclosure_delay": 30,
        "sentiment_score": 0.0,
        "market_momentum": 0.0,
        "sector_performance": 0.0,
    }

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/ml/predict",
            json={"features": features, "use_cache": False},
            timeout=30.0
        )

        if response.status_code == 503:
            click.echo("❌ No trained model available.")
            click.echo("\nTo train a model: mcli run ml train")
            return

        response.raise_for_status()
        data = response.json()

        if as_json:
            click.echo(json.dumps(data, indent=2))
        else:
            signal_type = data.get("signal_type", "unknown")
            confidence = data.get("confidence", 0)
            prediction = data.get("prediction", 0)

            # Signal type styling
            signal_colors = {
                "strong_buy": ("🟢", "STRONG BUY"),
                "buy": ("🟢", "BUY"),
                "hold": ("🟡", "HOLD"),
                "sell": ("🔴", "SELL"),
                "strong_sell": ("🔴", "STRONG SELL"),
            }
            icon, label = signal_colors.get(signal_type, ("⚪", signal_type.upper()))

            click.echo(f"\n🧠 ML Prediction for {ticker.upper()}\n")
            click.echo(f"  Signal: {icon} {label}")
            click.echo(f"  Confidence: {confidence:.1%}")
            click.echo(f"  Raw prediction: {prediction}")
            click.echo(f"  Cached: {data.get('cached', False)}")

            click.echo(f"\n  Features used:")
            click.echo(f"    Politicians: {politician_count}")
            click.echo(f"    Buy/Sell ratio: {buy_sell_ratio:.1f}")
            click.echo(f"    Recent activity: {recent_activity}")
            click.echo(f"    Bipartisan: {bipartisan}")
            click.echo(f"    Volume: ${volume:,}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@ml.command(name="test")
@click.option("--tickers", "-t", default="AAPL,MSFT,NVDA,GOOGL,AMZN", help="Comma-separated tickers")
@click.option("--scenarios", "-s", is_flag=True, help="Run multiple test scenarios")
def test(tickers: str, scenarios: bool):
    """
    Test model predictions on sample tickers.

    Examples:
        mcli run ml test                           # Test default tickers
        mcli run ml test -t "AAPL,TSLA,META"       # Custom tickers
        mcli run ml test --scenarios              # Run multiple scenarios
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    click.echo("🧪 ML Model Test\n")

    if scenarios:
        # Test different scenarios
        test_cases = [
            {"name": "Strong Buy Signal", "politician_count": 8, "buy_sell_ratio": 4.0, "bipartisan": True, "recent_activity_30d": 10},
            {"name": "Buy Signal", "politician_count": 4, "buy_sell_ratio": 2.5, "bipartisan": False, "recent_activity_30d": 5},
            {"name": "Neutral/Hold", "politician_count": 2, "buy_sell_ratio": 1.0, "bipartisan": False, "recent_activity_30d": 2},
            {"name": "Sell Signal", "politician_count": 3, "buy_sell_ratio": 0.4, "bipartisan": False, "recent_activity_30d": 4},
            {"name": "Strong Sell Signal", "politician_count": 6, "buy_sell_ratio": 0.2, "bipartisan": True, "recent_activity_30d": 8},
        ]

        click.echo(f"Running {len(test_cases)} scenarios on {ticker_list[0]}...\n")

        for case in test_cases:
            features = {
                "ticker": ticker_list[0],
                "politician_count": case["politician_count"],
                "buy_sell_ratio": case["buy_sell_ratio"],
                "recent_activity_30d": case["recent_activity_30d"],
                "bipartisan": case["bipartisan"],
                "net_volume": 100000,
                "volume_magnitude": 6,
                "party_alignment": 0.5,
                "committee_relevance": 0.5,
                "disclosure_delay": 30,
                "sentiment_score": 0.0,
                "market_momentum": 0.0,
                "sector_performance": 0.0,
            }

            try:
                response = httpx.post(
                    f"{ETL_SERVICE_URL}/ml/predict",
                    json={"features": features, "use_cache": False},
                    timeout=30.0
                )

                if response.status_code == 503:
                    click.echo("❌ No trained model available. Train first: mcli run ml train")
                    return

                response.raise_for_status()
                data = response.json()

                signal = data.get("signal_type", "?")
                confidence = data.get("confidence", 0)

                icon = {"strong_buy": "🟢🟢", "buy": "🟢", "hold": "🟡", "sell": "🔴", "strong_sell": "🔴🔴"}.get(signal, "⚪")

                click.echo(f"  {case['name']:<20} → {icon} {signal:<12} ({confidence:.0%})")

            except httpx.HTTPError as e:
                click.echo(f"  {case['name']:<20} → ❌ Error: {e}")

    else:
        # Test each ticker with default features
        click.echo(f"Testing {len(ticker_list)} tickers with default features...\n")
        click.echo(f"  {'Ticker':<8} {'Signal':<15} {'Confidence':<12} {'Prediction'}")
        click.echo(f"  {'-'*8} {'-'*15} {'-'*12} {'-'*10}")

        for ticker in ticker_list:
            features = {
                "ticker": ticker,
                "politician_count": 3,
                "buy_sell_ratio": 1.5,
                "recent_activity_30d": 4,
                "bipartisan": False,
                "net_volume": 50000,
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
                    f"{ETL_SERVICE_URL}/ml/predict",
                    json={"features": features, "use_cache": False},
                    timeout=30.0
                )

                if response.status_code == 503:
                    click.echo("❌ No trained model available. Train first: mcli run ml train")
                    return

                response.raise_for_status()
                data = response.json()

                signal = data.get("signal_type", "?")
                confidence = data.get("confidence", 0)
                prediction = data.get("prediction", "?")

                click.echo(f"  {ticker:<8} {signal:<15} {confidence:<12.1%} {prediction}")

            except httpx.HTTPError as e:
                click.echo(f"  {ticker:<8} {'error':<15} {'-':<12} {str(e)[:20]}")


@ml.command(name="compare")
@click.argument("ticker")
def compare(ticker: str):
    """
    Compare ML prediction vs heuristic signal for a ticker.

    Fetches real disclosure data and compares both approaches.
    """
    click.echo(f"🔍 Comparing ML vs Heuristic for {ticker.upper()}\n")
    click.echo("(This feature requires fetching real disclosure data)")
    click.echo("Coming soon...")


# =============================================================================
# Model Management Commands
# =============================================================================

@ml.command(name="activate")
@click.argument("model_id")
def activate(model_id: str):
    """
    Activate a specific model for predictions.

    Example: mcli run ml activate abc123
    """
    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/ml/models/{model_id}/activate",
            timeout=30.0
        )

        if response.status_code == 404:
            click.echo(f"❌ Model not found: {model_id}")
            return

        response.raise_for_status()
        data = response.json()

        click.echo(f"✓ Model {model_id[:8]}... activated")
        click.echo(f"  Status: {data.get('status', 'active')}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@ml.command(name="features")
@click.argument("model_id", required=False)
def features(model_id: Optional[str]):
    """
    Show feature importance for a model.

    Examples:
        mcli run ml features           # Active model
        mcli run ml features abc123    # Specific model
    """
    endpoint = f"{ETL_SERVICE_URL}/ml/models/active" if not model_id else f"{ETL_SERVICE_URL}/ml/models/{model_id}"

    try:
        response = httpx.get(endpoint, timeout=10.0)

        if response.status_code == 404:
            click.echo("❌ Model not found")
            return

        response.raise_for_status()
        data = response.json()

        features = data.get("feature_importance", {})
        if not features:
            click.echo("No feature importance data available.")
            return

        click.echo(f"🎯 Feature Importance\n")
        click.echo(f"  Model: {data.get('model_name', 'unknown')}")
        click.echo(f"  Version: {data.get('model_version', '?')}\n")

        sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)
        max_len = max(len(name) for name, _ in sorted_features)

        for name, importance in sorted_features:
            bar = "█" * int(importance * 40)
            click.echo(f"  {name:<{max_len}} {bar} {importance:.4f}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)


# =============================================================================
# Helper Functions
# =============================================================================

def _show_training_status(job_id: str) -> dict:
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
        message = data.get("current_step", "")

        status_icon = {"completed": "✓", "failed": "✗", "running": "⋯", "pending": "○"}.get(status, "?")

        click.echo(f"  Status: {status_icon} {status}")
        click.echo(f"  Progress: {progress}%")
        if message:
            click.echo(f"  Step: {message}")

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


def _wait_for_training(job_id: str):
    """Wait for ML training to complete."""
    while True:
        data = _show_training_status(job_id)
        status = data.get("status", "unknown")

        if status in ("completed", "failed", "error"):
            _show_training_result(job_id)
            break

        time.sleep(10)


def _show_training_result(job_id: str):
    """Show final training result."""
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/ml/train/{job_id}",
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")

            if status == "completed":
                click.echo("\n✅ Training completed successfully!")
                metrics = data.get("result_summary", {})
                if metrics:
                    click.echo(f"\n📊 Model Metrics:")
                    click.echo(f"  Accuracy: {metrics.get('accuracy', 0):.2%}")
                    click.echo(f"  F1 Score: {metrics.get('f1_weighted', 0):.2%}")
                    if metrics.get('training_samples'):
                        click.echo(f"  Training samples: {metrics['training_samples']:,}")
            else:
                click.echo(f"\n❌ Training ended with status: {status}")
                if data.get("error_message"):
                    click.echo(f"  Error: {data['error_message']}")
    except Exception:
        pass


def _list_models():
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
            click.echo("\nTo train a model: mcli run ml train")
            return

        click.echo(f"Trained Models ({len(models)}):\n")

        for model in models:
            status = model.get("status", "unknown")
            status_icon = {"active": "✓", "archived": "○", "failed": "✗"}.get(status, "?")
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
