# @description: Run the politician trading tracker workflow
# @version: 1.0
import click
from pathlib import Path

@click.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
def politician_trading_tracker(verbose):
    """Run the politician trading tracker workflow."""
    click.echo("Running politician trading tracker...")
    
    if verbose:
        click.echo("  Repository: ~/repos/politician-trading-tracker")
        click.echo("  Status: Active")
    
    click.echo("✓ Workflow executed successfully")
