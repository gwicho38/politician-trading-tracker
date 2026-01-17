"""
Capital Trades Synchronization Module

This module handles synchronization between the complex politician_trading schema
and the simplified capital_trades schema used by the React frontend.
"""

from .capital_trades_sync import CapitalTradesSync

__all__ = ["CapitalTradesSync"]