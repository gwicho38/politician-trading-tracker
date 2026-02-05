"""
Admin Dashboard Management Commands

Commands for managing the QuiverQuant validation admin dashboard:
- Generate and manage API keys
- Start the ETL service locally
- Open the dashboard in browser
- Check service health

@description: Admin dashboard and API key management
@version: 1.0.0
@group: admin
@requires: click, httpx, rich
"""

import os
import secrets
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Configuration
ETL_DIR = Path(__file__).parent.parent.parent / "python-etl-service"
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Service URLs
LOCAL_ETL_URL = "http://localhost:8000"
PROD_ETL_URL = os.environ.get("ETL_SERVICE_URL", "https://politician-trading-etl.fly.dev")


def load_env():
    """Load environment variables from .env file."""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)


def get_env_value(key: str) -> Optional[str]:
    """Get value from environment or .env file."""
    load_env()
    return os.environ.get(key)


def set_env_value(key: str, value: str):
    """Set or update a value in the .env file."""
    lines = []
    found = False

    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"{key}={value}\n")

    with open(ENV_FILE, "w") as f:
        f.writelines(lines)

    # Also set in current environment
    os.environ[key] = value


def generate_api_key(prefix: str = "etl") -> str:
    """Generate a secure random API key."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_sk_{random_part}"


@click.group(name="admin")
def admin():
    """Admin dashboard and API key management."""
    pass


# ============================================================================
# Key Management Commands
# ============================================================================


@admin.command("generate-key")
@click.option("--admin", "is_admin", is_flag=True, help="Generate admin key (vs regular API key)")
@click.option("--save", is_flag=True, help="Save to .env file")
@click.option("--show", is_flag=True, help="Show full key (by default, only prefix shown)")
def generate_key(is_admin: bool, save: bool, show: bool):
    """
    Generate a new API key for the ETL service.

    Examples:
        mcli run admin generate-key              # Generate regular API key
        mcli run admin generate-key --admin      # Generate admin API key
        mcli run admin generate-key --admin --save   # Generate and save to .env
    """
    prefix = "etl_admin" if is_admin else "etl"
    key = generate_api_key(prefix)
    key_type = "Admin" if is_admin else "Regular"
    env_var = "ETL_ADMIN_API_KEY" if is_admin else "ETL_API_KEY"

    console.print(f"\n[bold green]{key_type} API Key Generated[/bold green]")

    if show:
        console.print(f"[cyan]Key:[/cyan] {key}")
    else:
        console.print(f"[cyan]Key:[/cyan] {key[:20]}...")
        console.print("[dim]Use --show to see full key[/dim]")

    if save:
        set_env_value(env_var, key)
        console.print(f"\n[green]Saved to .env as {env_var}[/green]")
    else:
        console.print(f"\n[yellow]To save:[/yellow] Add to .env file:")
        console.print(f"  {env_var}={key}")
        console.print("\n[yellow]Or use lsh:[/yellow]")
        console.print(f"  lsh set {env_var} {key}")

    console.print(f"\n[dim]Full key (copy this):[/dim]")
    console.print(key)


@admin.command("show-keys")
@click.option("--full", is_flag=True, help="Show full keys (security risk!)")
def show_keys(full: bool):
    """
    Show configured API keys.

    Example: mcli run admin show-keys
    """
    load_env()

    table = Table(title="Configured API Keys")
    table.add_column("Key Type", style="cyan")
    table.add_column("Environment Variable", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Value", style="dim")

    keys = [
        ("Admin API Key", "ETL_ADMIN_API_KEY"),
        ("Regular API Key", "ETL_API_KEY"),
        ("QuiverQuant API Key", "QUIVERQUANT_API_KEY"),
    ]

    for name, env_var in keys:
        value = os.environ.get(env_var)
        if value:
            status = "[green]Configured[/green]"
            display_value = value if full else f"{value[:15]}..."
        else:
            status = "[red]Not Set[/red]"
            display_value = "-"

        table.add_row(name, env_var, status, display_value)

    console.print(table)

    if not full:
        console.print("\n[dim]Use --full to show complete key values[/dim]")


@admin.command("push-secrets")
@click.option("--app", default="politician-trading-etl", help="Fly.io app name")
@click.option("--dry-run", is_flag=True, help="Show what would be pushed without pushing")
def push_secrets(app: str, dry_run: bool):
    """
    Push API keys from .env to Fly.io secrets.

    Examples:
        mcli run admin push-secrets              # Push to default ETL app
        mcli run admin push-secrets --dry-run    # Preview what would be pushed
        mcli run admin push-secrets --app myapp  # Push to specific app
    """
    load_env()

    secrets_to_push = [
        ("ETL_ADMIN_API_KEY", os.environ.get("ETL_ADMIN_API_KEY")),
        ("ETL_API_KEY", os.environ.get("ETL_API_KEY")),
        ("QUIVERQUANT_API_KEY", os.environ.get("QUIVERQUANT_API_KEY")),
    ]

    # Filter to only configured secrets
    secrets_to_push = [(k, v) for k, v in secrets_to_push if v]

    if not secrets_to_push:
        console.print("[yellow]No secrets configured in .env to push[/yellow]")
        console.print("Run [cyan]mcli run admin setup-keys[/cyan] first")
        return

    console.print(f"\n[bold]Pushing secrets to Fly.io app: {app}[/bold]\n")

    for key, value in secrets_to_push:
        if dry_run:
            console.print(f"  [dim]Would set[/dim] {key}={value[:15]}...")
        else:
            console.print(f"  Setting {key}...", end=" ")
            result = subprocess.run(
                ["flyctl", "secrets", "set", f"{key}={value}", "-a", app],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print("[green]OK[/green]")
            else:
                console.print(f"[red]FAILED[/red]: {result.stderr}")

    if dry_run:
        console.print("\n[dim]Use without --dry-run to actually push secrets[/dim]")
    else:
        console.print("\n[green]Secrets pushed to Fly.io![/green]")


@admin.command("setup-keys")
@click.option("--force", is_flag=True, help="Overwrite existing keys")
@click.option("--push", is_flag=True, help="Also push to Fly.io after setup")
@click.option("--app", default="politician-trading-etl", help="Fly.io app name for --push")
def setup_keys(force: bool, push: bool, app: str):
    """
    Interactive setup for API keys.

    Examples:
        mcli run admin setup-keys           # Setup keys locally
        mcli run admin setup-keys --push    # Setup and push to Fly.io
    """
    load_env()

    console.print(Panel.fit(
        "[bold]API Key Setup Wizard[/bold]\n\n"
        "This will help you configure the required API keys for the admin dashboard.",
        title="Admin Setup"
    ))

    keys_changed = []

    # ETL Admin Key
    existing_admin = os.environ.get("ETL_ADMIN_API_KEY")
    if existing_admin and not force:
        console.print(f"\n[green]ETL_ADMIN_API_KEY already configured[/green]: {existing_admin[:15]}...")
    else:
        if click.confirm("\nGenerate new ETL_ADMIN_API_KEY?", default=True):
            key = generate_api_key("etl_admin")
            set_env_value("ETL_ADMIN_API_KEY", key)
            keys_changed.append("ETL_ADMIN_API_KEY")
            console.print(f"[green]Generated and saved:[/green] {key[:20]}...")
            console.print(f"[dim]Full key: {key}[/dim]")

    # ETL Regular Key
    existing_api = os.environ.get("ETL_API_KEY")
    if existing_api and not force:
        console.print(f"\n[green]ETL_API_KEY already configured[/green]: {existing_api[:15]}...")
    else:
        if click.confirm("\nGenerate new ETL_API_KEY?", default=True):
            key = generate_api_key("etl")
            set_env_value("ETL_API_KEY", key)
            keys_changed.append("ETL_API_KEY")
            console.print(f"[green]Generated and saved:[/green] {key[:20]}...")

    # QuiverQuant Key
    existing_quiver = os.environ.get("QUIVERQUANT_API_KEY")
    if existing_quiver and not force:
        console.print(f"\n[green]QUIVERQUANT_API_KEY already configured[/green]: {existing_quiver[:15]}...")
    else:
        console.print("\n[yellow]QUIVERQUANT_API_KEY is required for validation audits.[/yellow]")
        console.print("Get your API key from: https://www.quiverquant.com/")
        quiver_key = click.prompt("Enter your QuiverQuant API key (or press Enter to skip)", default="", show_default=False)
        if quiver_key:
            set_env_value("QUIVERQUANT_API_KEY", quiver_key)
            keys_changed.append("QUIVERQUANT_API_KEY")
            console.print("[green]Saved QUIVERQUANT_API_KEY[/green]")

    console.print("\n[bold green]Local setup complete![/bold green]")

    # Push to Fly.io if requested
    if push:
        console.print(f"\n[cyan]Pushing secrets to Fly.io ({app})...[/cyan]")
        load_env()  # Reload to get new values

        for key in ["ETL_ADMIN_API_KEY", "ETL_API_KEY", "QUIVERQUANT_API_KEY"]:
            value = os.environ.get(key)
            if value:
                console.print(f"  Setting {key}...", end=" ")
                result = subprocess.run(
                    ["flyctl", "secrets", "set", f"{key}={value}", "-a", app],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print("[green]OK[/green]")
                else:
                    console.print(f"[red]FAILED[/red]")

        console.print("\n[green]Secrets pushed to Fly.io![/green]")
    else:
        console.print("\nNext steps:")
        console.print("  1. Push secrets to Fly.io: [cyan]mcli run admin push-secrets[/cyan]")
        console.print("     Or use lsh: [cyan]lsh push[/cyan]")
        console.print("  2. Open dashboard: [cyan]mcli run admin dashboard[/cyan]")


# ============================================================================
# Dashboard Commands
# ============================================================================


@admin.command("dashboard")
@click.option("--local", "use_local", is_flag=True, help="Use local server (default: production)")
@click.option("--start-server", is_flag=True, help="Start local ETL server first")
@click.option("--port", default=8000, help="Port for local server")
def dashboard(use_local: bool, start_server: bool, port: int):
    """
    Open the admin dashboard in your browser.

    Examples:
        mcli run admin dashboard                    # Open production dashboard
        mcli run admin dashboard --local            # Open local dashboard
        mcli run admin dashboard --local --start-server  # Start server and open
    """
    load_env()

    # Get admin key
    admin_key = os.environ.get("ETL_ADMIN_API_KEY")
    if not admin_key:
        console.print("[red]ETL_ADMIN_API_KEY not configured![/red]")
        console.print("Run: [cyan]mcli run admin setup-keys[/cyan]")
        raise SystemExit(1)

    if use_local or start_server:
        base_url = f"http://localhost:{port}"

        if start_server:
            console.print(f"[cyan]Starting local ETL server on port {port}...[/cyan]")
            # Start in background
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)],
                cwd=str(ETL_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            console.print(f"[green]Server started (PID: {proc.pid})[/green]")
            console.print("[dim]Waiting for server to be ready...[/dim]")
            time.sleep(3)
    else:
        base_url = PROD_ETL_URL

    dashboard_url = f"{base_url}/admin?key={admin_key}"

    console.print(f"\n[bold]Opening Admin Dashboard[/bold]")
    console.print(f"URL: {base_url}/admin?key=***")

    webbrowser.open(dashboard_url)

    console.print("\n[green]Dashboard opened in browser[/green]")

    if start_server:
        console.print("\n[yellow]Server is running in background.[/yellow]")
        console.print("To stop: [cyan]mcli run admin stop-server[/cyan]")
        console.print(f"Or: [cyan]kill {proc.pid}[/cyan]")


@admin.command("start-server")
@click.option("--port", default=8000, help="Port to run on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--background", is_flag=True, help="Run in background")
def start_server(port: int, reload: bool, background: bool):
    """
    Start the ETL service locally.

    Examples:
        mcli run admin start-server                 # Start on port 8000
        mcli run admin start-server --port 8080    # Start on port 8080
        mcli run admin start-server --reload        # Start with auto-reload
        mcli run admin start-server --background    # Start in background
    """
    load_env()

    console.print(f"[cyan]Starting ETL service on port {port}...[/cyan]")

    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)]
    if reload:
        cmd.append("--reload")

    if background:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ETL_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        console.print(f"[green]Server started in background (PID: {proc.pid})[/green]")
        console.print(f"\nDashboard URL: http://localhost:{port}/admin?key=YOUR_ADMIN_KEY")
        console.print(f"\nTo stop: [cyan]kill {proc.pid}[/cyan]")
    else:
        console.print(f"\nDashboard will be available at: http://localhost:{port}/admin?key=YOUR_ADMIN_KEY")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        try:
            subprocess.run(cmd, cwd=str(ETL_DIR))
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped[/yellow]")


@admin.command("stop-server")
@click.option("--port", default=8000, help="Port the server is running on")
def stop_server(port: int):
    """
    Stop a running local ETL server.

    Example: mcli run admin stop-server
    """
    import signal

    # Find process using the port
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True,
        )
        pids = result.stdout.strip().split("\n")
        pids = [p for p in pids if p]

        if not pids:
            console.print(f"[yellow]No server running on port {port}[/yellow]")
            return

        for pid in pids:
            os.kill(int(pid), signal.SIGTERM)
            console.print(f"[green]Stopped process {pid}[/green]")

    except Exception as e:
        console.print(f"[red]Error stopping server: {e}[/red]")


@admin.command("health")
@click.option("--local", "use_local", is_flag=True, help="Check local server")
@click.option("--port", default=8000, help="Port for local server")
def health(use_local: bool, port: int):
    """
    Check ETL service health.

    Examples:
        mcli run admin health           # Check production
        mcli run admin health --local   # Check local
    """
    base_url = f"http://localhost:{port}" if use_local else PROD_ETL_URL

    console.print(f"[cyan]Checking health of {base_url}...[/cyan]")

    try:
        response = httpx.get(f"{base_url}/health", timeout=10.0)
        response.raise_for_status()
        data = response.json()

        console.print(f"\n[green]Service is healthy![/green]")
        console.print(f"Status: {data.get('status', 'unknown')}")
        console.print(f"Database: {data.get('database', 'unknown')}")

    except httpx.ConnectError:
        console.print(f"\n[red]Cannot connect to {base_url}[/red]")
        if use_local:
            console.print("Start the server with: [cyan]mcli run admin start-server[/cyan]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"\n[red]Health check failed: {e}[/red]")
        raise SystemExit(1)


@admin.command("url")
@click.option("--local", "use_local", is_flag=True, help="Get local URL")
@click.option("--port", default=8000, help="Port for local server")
@click.option("--copy", is_flag=True, help="Copy URL to clipboard")
def url(use_local: bool, port: int, copy: bool):
    """
    Get the admin dashboard URL with API key.

    Examples:
        mcli run admin url              # Get production URL
        mcli run admin url --local      # Get local URL
        mcli run admin url --copy       # Copy to clipboard
    """
    load_env()

    admin_key = os.environ.get("ETL_ADMIN_API_KEY")
    if not admin_key:
        console.print("[red]ETL_ADMIN_API_KEY not configured![/red]")
        console.print("Run: [cyan]mcli run admin setup-keys[/cyan]")
        raise SystemExit(1)

    base_url = f"http://localhost:{port}" if use_local else PROD_ETL_URL
    full_url = f"{base_url}/admin?key={admin_key}"

    console.print(f"\n[bold]Admin Dashboard URL[/bold]")
    console.print(full_url)

    if copy:
        try:
            subprocess.run(["pbcopy"], input=full_url.encode(), check=True)
            console.print("\n[green]Copied to clipboard![/green]")
        except Exception:
            console.print("\n[yellow]Could not copy to clipboard[/yellow]")


# Make the group the main entry point
cli = admin

if __name__ == "__main__":
    cli()
