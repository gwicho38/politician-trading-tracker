"""
Trading module for executing trades via Alpaca API
"""

from politician_trading.trading.alpaca_client import AlpacaTradingClient
from politician_trading.trading.strategy import TradingStrategy
from politician_trading.trading.risk_manager import RiskManager

__all__ = ["AlpacaTradingClient", "TradingStrategy", "RiskManager"]
