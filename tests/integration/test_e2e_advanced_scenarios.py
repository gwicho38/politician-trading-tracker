"""
Advanced End-to-End Trading Flow Tests

Tests enhanced workflows:
1. Limit orders with price targets
2. Multiple signals in shopping cart
3. Mixed order types (market + limit)
4. Performance benchmarking
5. Real Alpaca integration (optional)

These tests validate advanced user scenarios and system performance.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import pytest
import streamlit as st

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from models import (
    Politician,
    TradingDisclosure,
    TradingSignal,
    SignalType,
    TransactionType,
    OrderType,
    OrderStatus,
    TradingMode,
)
from politician_trading.signals.signal_generator import SignalGenerator
from politician_trading.trading.alpaca_client import AlpacaTradingClient
from shopping_cart import ShoppingCart, CartItem
from paywall_config import PaywallConfig
from tests.fixtures.test_data import TestDataFactory

# Import MockSupabaseClient from the main E2E test
sys.path.insert(0, str(Path(__file__).parent))
from test_e2e_trading_flow import MockSupabaseClient, MockSupabaseTable


@pytest.fixture
def mock_streamlit_session():
    """Mock Streamlit session state"""
    if not hasattr(st, "session_state"):
        st.session_state = {}

    st.session_state.clear()
    yield st.session_state
    st.session_state.clear()


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase database client"""
    return MockSupabaseClient()


@pytest.fixture
def test_alpaca_keys():
    """Test Alpaca API keys (paper trading)"""
    return {
        "api_key": os.getenv("ALPACA_PAPER_API_KEY", "PKTEST1234567890"),
        "secret_key": os.getenv("ALPACA_PAPER_SECRET_KEY", "test_secret_key_12345"),
        "paper": True,
    }


class TestE2ELimitOrders:
    """Test limit order workflows"""

    @pytest.mark.asyncio
    async def test_limit_order_with_price_targets(
        self, mock_streamlit_session, mock_supabase_client, test_alpaca_keys
    ):
        """
        Test limit order submission with specific price targets

        Flow:
        1. Create politician trade + signal
        2. Add to cart with limit order parameters
        3. Execute limit order with target price
        4. Verify order has correct limit price
        """
        print("\n=== E2E Test: Limit Order with Price Targets ===\n")

        # Setup: Create test data
        nancy_pelosi = TestDataFactory.create_nancy_pelosi()
        politician_dict = TestDataFactory.to_politician_dict(nancy_pelosi)
        mock_supabase_client.table("politicians").insert(politician_dict).execute()

        msft_disclosure = TestDataFactory.create_aapl_sale_disclosure(nancy_pelosi.id)
        msft_disclosure.asset_name = "Microsoft Corporation"
        msft_disclosure.asset_ticker = "MSFT"
        disclosure_dict = TestDataFactory.to_disclosure_dict(msft_disclosure)
        mock_supabase_client.table("trading_disclosures").insert(disclosure_dict).execute()

        # Create SELL signal for MSFT
        msft_signal = TestDataFactory.create_test_signal([msft_disclosure.id])
        msft_signal.ticker = "MSFT"
        msft_signal.asset_name = "Microsoft Corporation"
        msft_signal.target_price = Decimal("380.00")  # Target price for limit order
        msft_signal.stop_loss = Decimal("420.00")
        signal_dict = TestDataFactory.to_signal_dict(msft_signal)
        mock_supabase_client.table("trading_signals").insert(signal_dict).execute()

        print(f"✅ Created MSFT SELL signal with target price: ${msft_signal.target_price}")

        # Setup Pro user
        pro_user = TestDataFactory.create_test_user_pro_tier()
        mock_streamlit_session.update(pro_user)

        # Add to cart
        ShoppingCart.initialize()
        cart_item = CartItem(
            ticker=msft_signal.ticker,
            asset_name=msft_signal.asset_name,
            signal_type=msft_signal.signal_type.value,
            quantity=20,
            signal_id=msft_signal.id,
            confidence_score=float(msft_signal.confidence_score),
            target_price=float(msft_signal.target_price),
            stop_loss=float(msft_signal.stop_loss),
            take_profit=float(msft_signal.take_profit) if msft_signal.take_profit else None,
        )
        ShoppingCart.add_item(cart_item)
        print(f"✅ Added MSFT to cart with quantity: 20 shares")

        # Execute limit order
        with patch("politician_trading.trading.alpaca_client.TradingClient") as mock_trading_client:
            mock_order = Mock()
            mock_order.id = uuid4()
            mock_order.client_order_id = uuid4()
            mock_order.symbol = "MSFT"
            mock_order.qty = "20"
            mock_order.filled_qty = "0"
            mock_order.type = "limit"
            mock_order.side = Mock(value="sell")
            mock_order.status = "pending_new"
            mock_order.limit_price = "380.00"  # Limit price set
            mock_order.stop_price = None
            mock_order.trail_percent = None
            mock_order.filled_avg_price = None
            mock_order.submitted_at = datetime.utcnow()
            mock_order.filled_at = None
            mock_order.canceled_at = None
            mock_order.expired_at = None

            mock_trading_client.return_value.submit_order.return_value = mock_order

            # Setup mock account
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

            alpaca_client = AlpacaTradingClient(**test_alpaca_keys)

            # Place limit order using target price
            cart_items = ShoppingCart.get_items()
            item = cart_items[0]

            order = alpaca_client.place_limit_order(
                ticker=item["ticker"],
                quantity=item["quantity"],
                side="sell",
                limit_price=float(item["target_price"]),
            )

            # Verify limit order properties
            assert order is not None
            assert order.ticker == "MSFT"
            assert order.quantity == 20
            assert order.side == "sell"
            assert order.order_type.value == "limit"
            assert order.limit_price == Decimal("380.00")
            print(f"✅ Placed LIMIT order: SELL 20 shares of MSFT @ ${order.limit_price}")
            print(f"   Order ID: {order.alpaca_order_id}")
            print(f"   Status: {order.status.value}")

            # Store order in database
            order_dict = {
                "id": str(uuid4()),
                "signal_id": item.get("signal_id"),
                "ticker": order.ticker,
                "order_type": order.order_type.value,
                "side": order.side,
                "quantity": order.quantity,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "status": order.status.value,
                "trading_mode": "paper",
                "alpaca_order_id": order.alpaca_order_id,
                "alpaca_client_order_id": order.alpaca_client_order_id,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            }
            mock_supabase_client.table("trading_orders").insert(order_dict).execute()

            # Verify order in database
            result = mock_supabase_client.table("trading_orders").select("*").execute()
            assert len(result.data) == 1
            assert result.data[0]["order_type"] == "limit"
            assert result.data[0]["limit_price"] == 380.00
            print(f"✅ Limit order stored in database with limit_price=${result.data[0]['limit_price']}")

        # Cleanup
        ShoppingCart.clear()
        print("\n✅ Limit Order Test Completed Successfully!")


class TestE2EMultipleSignals:
    """Test multiple signals in shopping cart"""

    @pytest.mark.asyncio
    async def test_multiple_signals_mixed_order_types(
        self, mock_streamlit_session, mock_supabase_client, test_alpaca_keys
    ):
        """
        Test multiple signals with mixed order types

        Flow:
        1. Create 3 different politician trades (AAPL, MSFT, TSLA)
        2. Generate signals for each
        3. Add all to cart
        4. Execute with mixed order types (market, limit, stop-limit)
        5. Verify all orders submitted correctly
        """
        print("\n=== E2E Test: Multiple Signals with Mixed Order Types ===\n")

        # Setup: Create politicians
        nancy_pelosi = TestDataFactory.create_nancy_pelosi()
        politician_dict = TestDataFactory.to_politician_dict(nancy_pelosi)
        mock_supabase_client.table("politicians").insert(politician_dict).execute()

        # Create Pro user
        pro_user = TestDataFactory.create_test_user_pro_tier()
        mock_streamlit_session.update(pro_user)

        # Create 3 different disclosures and signals
        trades = [
            {"ticker": "AAPL", "name": "Apple Inc.", "transaction": TransactionType.SALE, "signal_type": SignalType.SELL},
            {"ticker": "MSFT", "name": "Microsoft Corporation", "transaction": TransactionType.PURCHASE, "signal_type": SignalType.BUY},
            {"ticker": "TSLA", "name": "Tesla Inc.", "transaction": TransactionType.SALE, "signal_type": SignalType.SELL},
        ]

        signals = []
        for trade in trades:
            # Create disclosure
            disclosure = TestDataFactory.create_aapl_sale_disclosure(nancy_pelosi.id)
            disclosure.asset_name = trade["name"]
            disclosure.asset_ticker = trade["ticker"]
            disclosure.transaction_type = trade["transaction"]
            disclosure_dict = TestDataFactory.to_disclosure_dict(disclosure)
            mock_supabase_client.table("trading_disclosures").insert(disclosure_dict).execute()

            # Create signal
            signal = TestDataFactory.create_test_signal([disclosure.id])
            signal.ticker = trade["ticker"]
            signal.asset_name = trade["name"]
            signal.signal_type = trade["signal_type"]
            signal_dict = TestDataFactory.to_signal_dict(signal)
            mock_supabase_client.table("trading_signals").insert(signal_dict).execute()

            signals.append(signal)
            print(f"✅ Created {trade['signal_type'].value.upper()} signal for {trade['ticker']}")

        # Add all to cart
        ShoppingCart.initialize()
        for i, signal in enumerate(signals):
            cart_item = CartItem(
                ticker=signal.ticker,
                asset_name=signal.asset_name,
                signal_type=signal.signal_type.value,
                quantity=10 * (i + 1),  # 10, 20, 30 shares
                signal_id=signal.id,
                confidence_score=float(signal.confidence_score),
                target_price=float(signal.target_price) if signal.target_price else None,
                stop_loss=float(signal.stop_loss) if signal.stop_loss else None,
                take_profit=float(signal.take_profit) if signal.take_profit else None,
            )
            ShoppingCart.add_item(cart_item)

        cart_items = ShoppingCart.get_items()
        assert len(cart_items) == 3
        print(f"✅ Added {len(cart_items)} signals to cart")
        for item in cart_items:
            print(f"   • {item['ticker']}: {item['quantity']} shares ({item['signal_type'].upper()})")

        # Execute with mixed order types
        with patch("politician_trading.trading.alpaca_client.TradingClient") as mock_trading_client:
            # Setup mock account
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

            alpaca_client = AlpacaTradingClient(**test_alpaca_keys)

            executed_orders = []
            order_types_used = ["market", "limit", "limit"]  # Mix of order types

            for idx, item in enumerate(cart_items):
                order_type = order_types_used[idx]

                # Create mock order
                mock_order = Mock()
                mock_order.id = uuid4()
                mock_order.client_order_id = uuid4()
                mock_order.symbol = item["ticker"]
                mock_order.qty = str(item["quantity"])
                mock_order.filled_qty = "0"
                mock_order.type = order_type
                mock_order.side = Mock(value=item["signal_type"])
                mock_order.status = "pending_new"
                mock_order.limit_price = str(item["target_price"]) if order_type == "limit" and item.get("target_price") else None
                mock_order.stop_price = None
                mock_order.trail_percent = None
                mock_order.filled_avg_price = None
                mock_order.submitted_at = datetime.utcnow()
                mock_order.filled_at = None
                mock_order.canceled_at = None
                mock_order.expired_at = None

                mock_trading_client.return_value.submit_order.return_value = mock_order

                # Place order based on type
                if order_type == "market":
                    order = alpaca_client.place_market_order(
                        ticker=item["ticker"],
                        quantity=item["quantity"],
                        side=item["signal_type"],
                    )
                elif order_type == "limit":
                    order = alpaca_client.place_limit_order(
                        ticker=item["ticker"],
                        quantity=item["quantity"],
                        side=item["signal_type"],
                        limit_price=float(item["target_price"]) if item.get("target_price") else 100.0,
                    )

                executed_orders.append(order)
                print(f"✅ Placed {order_type.upper()} order: {order.side.upper()} {order.quantity} {order.ticker}")

            # Verify all orders
            assert len(executed_orders) == 3
            assert executed_orders[0].order_type.value == "market"
            assert executed_orders[1].order_type.value == "limit"
            assert executed_orders[2].order_type.value == "limit"

            print(f"\n✅ Successfully executed {len(executed_orders)} orders with mixed types!")

        # Cleanup
        ShoppingCart.clear()
        print("✅ Multiple Signals Test Completed Successfully!")


class TestE2EPerformance:
    """Performance benchmarking tests"""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cart_performance_with_many_signals(
        self, mock_streamlit_session, mock_supabase_client
    ):
        """
        Test shopping cart performance with many signals

        Benchmarks:
        - Adding 50 signals to cart
        - Retrieving cart items
        - Updating quantities
        - Clearing cart
        """
        print("\n=== Performance Test: Shopping Cart with 50 Signals ===\n")

        # Setup Pro user
        pro_user = TestDataFactory.create_test_user_pro_tier()
        mock_streamlit_session.update(pro_user)

        ShoppingCart.initialize()

        # Benchmark: Add 50 signals to cart
        start_time = time.time()
        for i in range(50):
            cart_item = CartItem(
                ticker=f"TICK{i}",
                asset_name=f"Test Stock {i}",
                signal_type="buy",
                quantity=10,
                signal_id=str(uuid4()),
                confidence_score=0.75,
                target_price=100.0 + i,
                stop_loss=90.0 + i,
                take_profit=110.0 + i,
            )
            ShoppingCart.add_item(cart_item)

        add_duration = time.time() - start_time
        print(f"✅ Added 50 signals in {add_duration:.4f} seconds ({add_duration/50*1000:.2f}ms per item)")

        # Benchmark: Retrieve cart items
        start_time = time.time()
        cart_items = ShoppingCart.get_items()
        retrieve_duration = time.time() - start_time
        assert len(cart_items) == 50
        print(f"✅ Retrieved 50 items in {retrieve_duration:.4f} seconds")

        # Benchmark: Update quantities
        start_time = time.time()
        for item in cart_items[:10]:
            ShoppingCart.update_quantity(item["ticker"], 20)
        update_duration = time.time() - start_time
        print(f"✅ Updated 10 quantities in {update_duration:.4f} seconds")

        # Benchmark: Clear cart
        start_time = time.time()
        ShoppingCart.clear()
        clear_duration = time.time() - start_time
        assert ShoppingCart.get_item_count() == 0
        print(f"✅ Cleared cart in {clear_duration:.4f} seconds")

        # Performance assertions
        assert add_duration < 1.0, f"Adding 50 items took too long: {add_duration}s"
        assert retrieve_duration < 0.1, f"Retrieving items took too long: {retrieve_duration}s"
        assert update_duration < 0.5, f"Updating quantities took too long: {update_duration}s"
        assert clear_duration < 0.1, f"Clearing cart took too long: {clear_duration}s"

        print("\n📊 Performance Summary:")
        print(f"   Add 50 items: {add_duration*1000:.2f}ms total, {add_duration/50*1000:.2f}ms per item")
        print(f"   Retrieve: {retrieve_duration*1000:.2f}ms")
        print(f"   Update 10: {update_duration*1000:.2f}ms")
        print(f"   Clear: {clear_duration*1000:.2f}ms")
        print("\n✅ Performance Test Passed!")


class TestE2ERealAlpacaIntegration:
    """Optional real Alpaca integration tests (requires real API keys)"""

    @pytest.mark.skip(reason="Requires real Alpaca API keys - run manually with --run-real-alpaca")
    @pytest.mark.real_alpaca
    async def test_real_alpaca_paper_trading_connection(self):
        """
        Test real connection to Alpaca paper trading API

        NOTE: This test requires real Alpaca paper trading API keys.
        Set environment variables:
        - ALPACA_PAPER_API_KEY
        - ALPACA_PAPER_SECRET_KEY

        Run with: pytest -m real_alpaca --run-real-alpaca
        """
        print("\n=== Real Alpaca Integration Test ===\n")

        # Get real API keys from environment
        api_key = os.getenv("ALPACA_PAPER_API_KEY")
        secret_key = os.getenv("ALPACA_PAPER_SECRET_KEY")

        if not api_key or not secret_key:
            pytest.skip("Real Alpaca API keys not found in environment")

        if not api_key.startswith("PK"):
            pytest.skip("Only paper trading keys (starting with PK) are allowed")

        print("⚠️  WARNING: This test will use REAL Alpaca API")
        print(f"   API Key: {api_key[:8]}...")

        # Connect to real Alpaca
        alpaca_client = AlpacaTradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=True,
        )

        # Test connection
        account_info = alpaca_client.get_account()
        assert account_info is not None
        assert account_info["status"] == "ACTIVE"

        print(f"✅ Connected to Alpaca Paper Trading")
        print(f"   Account ID: {account_info['account_id']}")
        print(f"   Status: {account_info['status']}")
        print(f"   Cash: ${float(account_info['cash']):,.2f}")
        print(f"   Buying Power: ${float(account_info['buying_power']):,.2f}")

        # Note: We do NOT place real orders in this test
        # Just verify connection works
        print("\n✅ Real Alpaca Connection Test Passed!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
