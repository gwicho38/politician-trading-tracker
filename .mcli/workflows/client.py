#!/usr/bin/env python3
# @description: Deploy and manage GovMarket client on Fly.io
# @version: 1.0.0
# @group: workflows

"""
Client deployment and management commands for GovMarket.

Usage:
    mcli run client deploy          # Deploy new version to Fly.io
    mcli run client status          # Check live status of the site
    mcli run client logs            # View recent logs
    mcli run client open            # Open site in browser
"""
import click
import subprocess
import requests
from pathlib import Path
from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console

logger = get_logger()

# Configuration
CLIENT_DIR = Path(__file__).parent.parent.parent / "client"
FLY_APP = "govmarket-client"
DOMAINS = [
    "https://govmarket.trade",
    "https://www.govmarket.trade",
    f"https://{FLY_APP}.fly.dev",
]


@click.group(name="client")
def client():
    """
    🌐 Deploy and manage GovMarket client on Fly.io.

    Commands for deploying new versions, checking status,
    and monitoring the live site.
    """
    pass


@client.command(name="deploy")
@click.option("--build-only", is_flag=True, help="Only build, don't deploy")
def deploy(build_only: bool):
    """Deploy new version to Fly.io.

    Builds the Docker image and deploys to Fly.io.
    """
    console.print(f"[cyan]📦 Deploying GovMarket client...[/cyan]")
    console.print(f"[dim]Directory: {CLIENT_DIR}[/dim]")

    if not CLIENT_DIR.exists():
        console.print(f"[red]✗ Client directory not found: {CLIENT_DIR}[/red]")
        return

    try:
        # Build first
        console.print("\n[yellow]Building...[/yellow]")
        cmd = ["flyctl", "deploy", "--now"]
        if build_only:
            cmd = ["flyctl", "deploy", "--build-only"]

        result = subprocess.run(
            cmd,
            cwd=CLIENT_DIR,
            capture_output=False,
        )

        if result.returncode == 0:
            console.print(f"\n[green]✓ Deployment successful![/green]")
            console.print(f"[dim]Visit: https://govmarket.trade[/dim]")
        else:
            console.print(f"\n[red]✗ Deployment failed (exit code {result.returncode})[/red]")

    except FileNotFoundError:
        console.print("[red]✗ flyctl not found. Install with: brew install flyctl[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@client.command(name="status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
def status(verbose: bool):
    """Check live status of the site.

    Checks all domains and SSL certificates.
    """
    console.print("[cyan]🔍 Checking GovMarket status...[/cyan]\n")

    # Check each domain
    for url in DOMAINS:
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                console.print(f"[green]✓ {url}[/green] - {resp.status_code}")
            else:
                console.print(f"[yellow]⚠ {url}[/yellow] - {resp.status_code}")
        except requests.exceptions.SSLError as e:
            console.print(f"[red]✗ {url}[/red] - SSL Error")
            if verbose:
                console.print(f"  [dim]{e}[/dim]")
        except requests.exceptions.ConnectionError:
            console.print(f"[red]✗ {url}[/red] - Connection failed")
        except Exception as e:
            console.print(f"[red]✗ {url}[/red] - {e}")

    # Check certificates
    if verbose:
        console.print("\n[cyan]📜 SSL Certificates:[/cyan]")
        try:
            result = subprocess.run(
                ["flyctl", "certs", "list", "-a", FLY_APP],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(result.stdout)
            else:
                console.print(f"[yellow]Could not fetch certs: {result.stderr}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Could not check certs: {e}[/yellow]")

    # Check Fly app status
    console.print(f"\n[cyan]🚀 Fly.io App Status:[/cyan]")
    try:
        result = subprocess.run(
            ["flyctl", "status", "-a", FLY_APP],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # Extract key info
            lines = result.stdout.strip().split("\n")
            for line in lines[:15]:  # First 15 lines have key info
                console.print(f"  {line}")
        else:
            console.print(f"[yellow]Could not get status[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Could not check Fly status: {e}[/yellow]")


@client.command(name="logs")
@click.option("--tail", "-n", default=50, help="Number of lines to show")
def logs(tail: int):
    """View recent logs from Fly.io."""
    console.print(f"[cyan]📋 Recent logs ({tail} lines)...[/cyan]\n")

    try:
        subprocess.run(
            ["flyctl", "logs", "-a", FLY_APP, "-n", str(tail)],
            cwd=CLIENT_DIR,
        )
    except FileNotFoundError:
        console.print("[red]✗ flyctl not found. Install with: brew install flyctl[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@client.command(name="open")
@click.option("--fly", is_flag=True, help="Open Fly.io dashboard instead")
def open_site(fly: bool):
    """Open site in browser."""
    import webbrowser

    if fly:
        url = f"https://fly.io/apps/{FLY_APP}"
        console.print(f"[cyan]Opening Fly.io dashboard...[/cyan]")
    else:
        url = "https://govmarket.trade"
        console.print(f"[cyan]Opening GovMarket...[/cyan]")

    webbrowser.open(url)
    console.print(f"[green]✓ Opened {url}[/green]")
