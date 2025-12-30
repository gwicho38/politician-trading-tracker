#!/usr/bin/env python3
# @description: Deploy and manage politician-trading-tracker Elixir server
# @version: 2.1.0
# @group: workflows

"""
Server deployment and management commands for politician-trading-tracker.

Usage:
    mcli run server deploy              # Deploy new version to Fly.io
    mcli run server deploy --deps       # Install deps before deploying
    mcli run server status              # Check server health
    mcli run server jobs                # List all jobs
    mcli run server jobs <id>           # Get job details
    mcli run server run <job_id>        # Run a specific job
    mcli run server run-all             # Run all enabled jobs
"""
import click
import subprocess
import requests
from pathlib import Path
from typing import Optional
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console
from rich.table import Table

logger = get_logger()

# Server configuration
SERVER_DIR = Path(__file__).parent.parent.parent / "server"
SERVER_URL = "https://politician-trading-server.fly.dev"
FLY_APP = "politician-trading-server"


@click.group(name="server")
@click.option("--url", default=SERVER_URL, help="Server URL")
@click.option("--local", is_flag=True, help="Use localhost:4000 instead of Fly.io")
@click.pass_context
def server(ctx, url: str, local: bool):
    """
    🖥️ Deploy and manage the politician-trading-tracker Elixir server.

    Interact with the backend server for deployment, job management,
    data ingestion, and status monitoring.
    """
    ctx.ensure_object(dict)
    ctx.obj["url"] = "http://localhost:4000" if local else url


@server.command(name="deploy")
@click.option("--deps", is_flag=True, help="Run mix deps.get before deploying")
@click.option("--build-only", is_flag=True, help="Only build, don't deploy")
def deploy(deps: bool, build_only: bool):
    """Deploy new version to Fly.io.

    Builds the Docker image and deploys to Fly.io.
    Use --deps to install dependencies first (after adding new packages).

    Examples:
        mcli run server deploy           # Standard deploy
        mcli run server deploy --deps    # Install deps first (after mix.exs changes)
    """
    console.print(f"[cyan]🔧 Deploying Phoenix API server...[/cyan]")
    console.print(f"[dim]Directory: {SERVER_DIR}[/dim]")

    if not SERVER_DIR.exists():
        console.print(f"[red]✗ Server directory not found: {SERVER_DIR}[/red]")
        return

    try:
        # Install dependencies if requested
        if deps:
            console.print("\n[yellow]Installing dependencies...[/yellow]")
            result = subprocess.run(
                ["mix", "deps.get"],
                cwd=SERVER_DIR,
                capture_output=False,
            )
            if result.returncode != 0:
                console.print(f"[red]✗ Failed to install dependencies[/red]")
                return

        # Deploy
        console.print("\n[yellow]Deploying to Fly.io...[/yellow]")
        cmd = ["flyctl", "deploy", "--now"]
        if build_only:
            cmd = ["flyctl", "deploy", "--build-only"]

        result = subprocess.run(
            cmd,
            cwd=SERVER_DIR,
            capture_output=False,
        )

        if result.returncode == 0:
            console.print(f"\n[green]✓ Deployment successful![/green]")
            console.print(f"[dim]API: {SERVER_URL}[/dim]")
        else:
            console.print(f"\n[red]✗ Deployment failed (exit code {result.returncode})[/red]")

    except FileNotFoundError as e:
        if "mix" in str(e):
            console.print("[red]✗ mix not found. Install Elixir first.[/red]")
        else:
            console.print("[red]✗ flyctl not found. Install with: brew install flyctl[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="restart")
def restart():
    """Restart the server instances on Fly.io."""
    console.print(f"[cyan]🔄 Restarting {FLY_APP}...[/cyan]\n")

    try:
        result = subprocess.run(
            ["flyctl", "apps", "restart", FLY_APP],
            capture_output=False,
        )
        if result.returncode == 0:
            console.print(f"[green]✓ Restart initiated[/green]")
        else:
            console.print(f"[red]✗ Restart failed[/red]")
    except FileNotFoundError:
        console.print("[red]✗ flyctl not found. Install with: brew install flyctl[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="ssh")
def ssh():
    """SSH into the running server instance."""
    console.print(f"[cyan]🔐 Connecting to {FLY_APP}...[/cyan]\n")

    try:
        subprocess.run(
            ["flyctl", "ssh", "console", "-a", FLY_APP],
            cwd=SERVER_DIR,
        )
    except FileNotFoundError:
        console.print("[red]✗ flyctl not found. Install with: brew install flyctl[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="open")
@click.option("--api", is_flag=True, help="Open API health endpoint instead of dashboard")
def open_site(api: bool):
    """Open Fly.io dashboard in browser."""
    import webbrowser

    if api:
        url = f"{SERVER_URL}/health"
        console.print(f"[cyan]Opening API health endpoint...[/cyan]")
    else:
        url = f"https://fly.io/apps/{FLY_APP}"
        console.print(f"[cyan]Opening Fly.io dashboard...[/cyan]")

    webbrowser.open(url)
    console.print(f"[green]✓ Opened {url}[/green]")


@server.command(name="status")
@click.pass_context
def status(ctx):
    """Check server health and readiness."""
    url = ctx.obj["url"]
    try:
        # Check liveness
        resp = requests.get(f"{url}/health", timeout=5)
        if resp.ok:
            console.print(f"[green]✓ Server is alive[/green] ({url})")
        else:
            console.print(f"[yellow]⚠ Liveness check returned {resp.status_code}[/yellow]")

        # Check readiness (database)
        resp = requests.get(f"{url}/health/ready", timeout=5)
        if resp.ok:
            data = resp.json()
            console.print(f"[green]✓ Database connected[/green]")
            if "database" in data:
                console.print(f"  database: {data['database']}")
        else:
            console.print(f"[red]✗ Database not ready: {resp.status_code}[/red]")

    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Cannot connect to server at {url}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="jobs")
@click.argument("job_id", required=False)
@click.pass_context
def jobs(ctx, job_id: Optional[str]):
    """List jobs or get job details.

    Without JOB_ID: Lists all jobs in a table
    With JOB_ID: Shows details for specific job
    """
    url = ctx.obj["url"]
    try:
        if job_id:
            resp = requests.get(f"{url}/api/jobs/{job_id}", timeout=10)
            if resp.ok:
                console.print_json(data=resp.json())
            elif resp.status_code == 404:
                console.print(f"[red]Job '{job_id}' not found[/red]")
            else:
                console.print(f"[red]Error: {resp.status_code} - {resp.text}[/red]")
        else:
            resp = requests.get(f"{url}/api/jobs", timeout=10)
            if resp.ok:
                data = resp.json()
                jobs_list = data.get("jobs", [])

                table = Table(title=f"Jobs ({len(jobs_list)} registered)")
                table.add_column("Job ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Schedule", style="dim")
                table.add_column("Enabled", justify="center")
                table.add_column("Last Run", style="dim")
                table.add_column("Failures", justify="right")

                for job in jobs_list:
                    enabled = "[green]✓[/green]" if job.get("enabled") else "[red]✗[/red]"
                    last_run = job.get("last_run_at") or "-"
                    if last_run != "-":
                        last_run = last_run[:19].replace("T", " ")
                    failures = job.get("consecutive_failures", 0)
                    fail_style = "[red]" if failures > 0 else ""
                    fail_end = "[/red]" if failures > 0 else ""

                    table.add_row(
                        job.get("job_id", ""),
                        job.get("job_name", ""),
                        job.get("schedule", ""),
                        enabled,
                        last_run,
                        f"{fail_style}{failures}{fail_end}",
                    )

                console.print(table)
            else:
                console.print(f"[red]Error: {resp.status_code} - {resp.text}[/red]")

    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Cannot connect to server at {url}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="run")
@click.argument("job_id")
@click.pass_context
def run_job(ctx, job_id: str):
    """Run a specific job immediately.

    Example: mcli run server run politician-trading-house
    """
    url = ctx.obj["url"]
    try:
        console.print(f"[dim]Triggering job: {job_id}...[/dim]")
        resp = requests.post(f"{url}/api/jobs/{job_id}/run", timeout=60)

        if resp.ok:
            data = resp.json()
            status = data.get("status", "unknown")
            if status == "success":
                console.print(f"[green]✓ Job completed successfully[/green]")
                if "result" in data:
                    console.print(f"  Result: {data['result']}")
                if "message" in data:
                    console.print(f"  {data['message']}")
            else:
                console.print(f"[red]✗ Job failed[/red]")
                if "error" in data:
                    console.print(f"  Error: {data['error']}")
        elif resp.status_code == 404:
            console.print(f"[red]Job '{job_id}' not found[/red]")
        else:
            console.print(f"[red]Error: {resp.status_code} - {resp.text}[/red]")

    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Cannot connect to server at {url}[/red]")
    except requests.exceptions.Timeout:
        console.print(f"[yellow]⚠ Request timed out (job may still be running)[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="run-all")
@click.pass_context
def run_all(ctx):
    """Run all enabled jobs immediately.

    Jobs are triggered asynchronously and this returns immediately.
    """
    url = ctx.obj["url"]
    try:
        console.print("[dim]Triggering all enabled jobs...[/dim]")
        resp = requests.post(f"{url}/api/jobs/run-all", timeout=30)

        if resp.ok:
            data = resp.json()
            message = data.get("message", "Jobs triggered")
            console.print(f"[green]✓ {message}[/green]")

            jobs_list = data.get("jobs", [])
            if jobs_list:
                table = Table(title="Triggered Jobs")
                table.add_column("Job ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Status", style="green")

                for job in jobs_list:
                    table.add_row(
                        job.get("job_id", ""),
                        job.get("job_name", ""),
                        job.get("status", ""),
                    )

                console.print(table)
        else:
            console.print(f"[red]Error: {resp.status_code} - {resp.text}[/red]")

    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Cannot connect to server at {url}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="logs")
@click.option("--etl", "show_etl", is_flag=True, help="Show ETL service logs instead of main server")
@click.option("-n", "--lines", default=50, help="Number of lines to show")
@click.option("-f", "--follow", is_flag=True, help="Follow logs in real-time")
@click.pass_context
def logs(ctx, show_etl: bool, lines: int, follow: bool):
    """Show server logs from Fly.io.

    Examples:
        mcli run server logs           # Last 50 lines from main server
        mcli run server logs -f        # Follow main server logs
        mcli run server logs --etl     # Show ETL service logs
        mcli run server logs -n 100    # Last 100 lines
    """
    import subprocess

    app = "politician-trading-etl" if show_etl else "politician-trading-server"
    app_label = "ETL service" if show_etl else "main server"

    cmd = ["flyctl", "logs", "--app", app]

    if follow:
        console.print(f"[dim]Following logs from {app_label}... (Ctrl+C to stop)[/dim]")
    else:
        cmd.append("--no-tail")
        console.print(f"[dim]Fetching last {lines} lines from {app_label}...[/dim]")

    try:
        if follow:
            # Stream logs in real-time
            subprocess.run(cmd)
        else:
            # Get logs and show last N lines
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                log_lines = result.stdout.strip().split("\n")
                for line in log_lines[-lines:]:
                    # Color-code log levels
                    if "[error]" in line.lower():
                        console.print(f"[red]{line}[/red]")
                    elif "[warning]" in line.lower() or "[warn]" in line.lower():
                        console.print(f"[yellow]{line}[/yellow]")
                    elif "completed" in line.lower() and "success" in line.lower():
                        console.print(f"[green]{line}[/green]")
                    else:
                        console.print(line)
            else:
                console.print(f"[red]Error: {result.stderr}[/red]")
    except FileNotFoundError:
        console.print("[red]✗ flyctl not found. Install it from https://fly.io/docs/hands-on/install-flyctl/[/red]")
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following logs[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="etl")
@click.option("--status", "job_id", help="Check status of an ETL job by ID")
@click.pass_context
def etl(ctx, job_id: Optional[str]):
    """Check Python ETL service status.

    Without --status: Check ETL service health
    With --status <id>: Check specific ETL job status
    """
    etl_url = "https://politician-trading-etl.fly.dev"
    try:
        if job_id:
            resp = requests.get(f"{etl_url}/etl/status/{job_id}", timeout=10)
            if resp.ok:
                console.print_json(data=resp.json())
            else:
                console.print(f"[red]Error: {resp.status_code} - {resp.text}[/red]")
        else:
            resp = requests.get(f"{etl_url}/health", timeout=5)
            if resp.ok:
                console.print(f"[green]✓ ETL service is healthy[/green] ({etl_url})")
                console.print_json(data=resp.json())
            else:
                console.print(f"[red]✗ ETL service returned {resp.status_code}[/red]")

    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗ Cannot connect to ETL service at {etl_url}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@server.command(name="etl-run")
@click.argument("years", nargs=-1, type=int)
@click.option("--limit", "-l", type=int, help="Limit PDFs per year (for testing)")
@click.pass_context
def etl_run(ctx, years, limit: Optional[int]):
    """Trigger ETL job for one or more years.

    Examples:
        mcli run server etl-run 2025           # Process 2025
        mcli run server etl-run 2025 2024 2023 # Process multiple years
        mcli run server etl-run 2025 -l 10     # Test with 10 PDFs
    """
    import time

    etl_url = "https://politician-trading-etl.fly.dev"

    if not years:
        years = [2025]

    for year in years:
        try:
            payload = {"source": "house", "year": year}
            if limit:
                payload["limit"] = limit

            console.print(f"[dim]Triggering ETL for {year}...[/dim]")
            resp = requests.post(f"{etl_url}/etl/trigger", json=payload, timeout=30)

            if resp.ok:
                data = resp.json()
                job_id = data.get("job_id")
                console.print(f"[green]✓ Started job for {year}[/green]: {job_id}")

                # Poll for completion if processing single year
                if len(years) == 1:
                    console.print("[dim]Waiting for completion...[/dim]")
                    while True:
                        time.sleep(5)
                        status_resp = requests.get(f"{etl_url}/etl/status/{job_id}", timeout=10)
                        if status_resp.ok:
                            status_data = status_resp.json()
                            progress = status_data.get("progress", 0)
                            total = status_data.get("total", 0)
                            status = status_data.get("status")
                            console.print(f"  Progress: {progress}/{total} ({status})")
                            if status in ["completed", "failed"]:
                                if status == "completed":
                                    console.print(f"[green]✓ {status_data.get('message')}[/green]")
                                else:
                                    console.print(f"[red]✗ {status_data.get('message')}[/red]")
                                break
            else:
                console.print(f"[red]Error: {resp.status_code} - {resp.text}[/red]")
                # Stop on first error for year range
                break

        except requests.exceptions.ConnectionError:
            console.print(f"[red]✗ Cannot connect to ETL service at {etl_url}[/red]")
            break
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            break
