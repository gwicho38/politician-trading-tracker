"""
Unit tests for Alpaca trading client
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4


# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from politician_trading.trading.alpaca_client import AlpacaTradingClient


class TestAlpacaClientUUIDSerialization:
    """Test that UUIDs from Alpaca API are properly converted to strings"""

    @patch("politician_trading.trading.alpaca_client.TradingClient")
    def test_get_account_converts_uuid_to_string(self, mock_trading_client):
        """Test that account.id UUID is converted to string"""
        # Setup mock
        mock_account = Mock()
        mock_account.id = uuid4()
        mock_account.status = "ACTIVE"
        mock_account.cash = "100000"
        mock_account.portfolio_value = "100000"
        mock_account.buying_power = "100000"
        mock_account.equity = "100000"
        mock_account.last_equity = "100000"
        mock_account.long_market_value = "0"
        mock_account.short_market_value = "0"
        mock_account.currency = "USD"
        mock_account.pattern_day_trader = False
        mock_account.trading_blocked = False
        mock_account.transfers_blocked = False
        mock_account.account_blocked = False

        mock_trading_client.return_value.get_account.return_value = mock_account

        # Create client
        client = AlpacaTradingClient(api_key="test_key", secret_key="test_secret", paper=True)

        # Get account
        account_info = client.get_account()

        # Verify account_id is a string
        assert isinstance(account_info["account_id"], str)
        assert account_info["account_id"] == str(mock_account.id)

        # Verify it can be JSON serialized
        json.dumps(account_info)  # Should not raise

    @patch("politician_trading.trading.alpaca_client.TradingClient")
    def test_place_order_converts_uuid_to_string(self, mock_trading_client):
        """Test that order IDs are converted to strings"""
        # Setup mock
        mock_order = Mock()
        mock_order.id = uuid4()
        mock_order.client_order_id = uuid4()
        mock_order.symbol = "AAPL"
        mock_order.qty = "10"
        mock_order.filled_qty = "0"
        mock_order.type = "market"
        mock_order.side = Mock(value="buy")
        mock_order.status = "new"
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.trail_percent = None
        mock_order.filled_avg_price = None
        mock_order.submitted_at = datetime.utcnow()
        mock_order.filled_at = None
        mock_order.canceled_at = None
        mock_order.expired_at = None

        mock_trading_client.return_value.submit_order.return_value = mock_order

        # Create client
        client = AlpacaTradingClient(api_key="test_key", secret_key="test_secret", paper=True)

        # Place order
        order = client.place_market_order("AAPL", 10, "buy")

        # Verify order IDs are strings
        assert isinstance(order.alpaca_order_id, str)
        assert order.alpaca_order_id == str(mock_order.id)
        assert isinstance(order.alpaca_client_order_id, str)
        assert order.alpaca_client_order_id == str(mock_order.client_order_id)

    @patch("politician_trading.trading.alpaca_client.TradingClient")
    def test_order_json_serialization(self, mock_trading_client):
        """Test that TradingOrder with UUID strings can be JSON serialized"""
        # Setup mock
        mock_order = Mock()
        mock_order.id = uuid4()
        mock_order.client_order_id = uuid4()
        mock_order.symbol = "AAPL"
        mock_order.qty = "10"
        mock_order.filled_qty = "0"
        mock_order.type = "market"
        mock_order.side = Mock(value="buy")
        mock_order.status = "new"
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.trail_percent = None
        mock_order.filled_avg_price = None
        mock_order.submitted_at = datetime.utcnow()
        mock_order.filled_at = None
        mock_order.canceled_at = None
        mock_order.expired_at = None

        mock_trading_client.return_value.submit_order.return_value = mock_order

        # Create client
        client = AlpacaTradingClient(api_key="test_key", secret_key="test_secret", paper=True)

        # Place order
        order = client.place_market_order("AAPL", 10, "buy")

        # Create dict representation (similar to what happens in Streamlit page)
        order_data = {
            "ticker": order.ticker,
            "order_type": order.order_type.value,
            "side": order.side,
            "quantity": order.quantity,
            "status": order.status.value,
            "trading_mode": "paper",
            "alpaca_order_id": order.alpaca_order_id,
            "alpaca_client_order_id": order.alpaca_client_order_id,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        }

        # This should not raise "Object of type UUID is not JSON serializable"
        json_str = json.dumps(order_data)
        assert json_str  # Should successfully serialize

        # Verify deserialization works
        deserialized = json.loads(json_str)
        assert deserialized["alpaca_order_id"] == str(mock_order.id)
        assert deserialized["alpaca_client_order_id"] == str(mock_order.client_order_id)
