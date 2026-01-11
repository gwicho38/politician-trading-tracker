#!/usr/bin/env python3
# @description: Quiverquant command
# @version: 1.0.0
# @group: workflows

"""
quiverquant command group for mcli.
"""
import click
from typing import Optional, List
from pathlib import Path
from mcli.lib.logger.logger import get_logger

logger = get_logger()


@click.group(name="quiverquant")
def app():
    """
    Quiverquant command
    """
    pass


@app.command("hello")
@click.argument("name", default="World")
def hello(name: str):
    """Example subcommand."""
    logger.info(f"Hello, {name}!")
    click.echo(f"Hello, {name}!")
