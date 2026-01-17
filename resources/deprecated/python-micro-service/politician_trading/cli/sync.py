"""
CLI commands for synchronizing data with the capital trades frontend.
"""

import click
from ..sync.capital_trades_sync import CapitalTradesSync


@click.group()
def sync():
    """Commands for synchronizing data with capital trades frontend."""
    pass


@sync.command()
def politicians():
    """Sync all politicians from complex to simplified schema."""
    click.echo("Starting politician synchronization...")
    sync_service = CapitalTradesSync()
    count = sync_service.sync_all_politicians()
    click.echo(f"Successfully synchronized {count} politicians.")


@sync.command()
@click.argument('politician_id')
def politician_trades(politician_id):
    """Sync trades for a specific politician."""
    click.echo(f"Syncing trades for politician {politician_id}...")
    sync_service = CapitalTradesSync()
    count = sync_service.sync_politician_trades(politician_id)
    click.echo(f"Successfully synchronized {count} trades.")


@sync.command()
def trades():
    """Sync all trades from complex to simplified schema."""
    click.echo("Starting trade synchronization...")
    sync_service = CapitalTradesSync()
    count = sync_service.sync_all_trades()
    click.echo(f"Successfully synchronized {count} trades.")


@sync.command()
def stats():
    """Update dashboard statistics."""
    click.echo("Updating dashboard statistics...")
    sync_service = CapitalTradesSync()
    sync_service.update_dashboard_stats()
    click.echo("Dashboard statistics updated.")


@sync.command()
def all():
    """Run complete synchronization (politicians, trades, stats)."""
    click.echo("Starting complete synchronization...")
    sync_service = CapitalTradesSync()

    click.echo("Step 1: Syncing politicians...")
    politician_count = sync_service.sync_all_politicians()

    click.echo("Step 2: Syncing trades...")
    trade_count = sync_service.sync_all_trades()

    click.echo("Step 3: Updating dashboard statistics...")
    sync_service.update_dashboard_stats()

    click.echo(f"Synchronization complete! Synced {politician_count} politicians and {trade_count} trades.")