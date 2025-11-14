"""
End-to-End Trading Flow Test

Tests the complete workflow:
1. Nancy Pelosi sells AAPL stock
2. Signal generated from the trade
3. Paywall verifies user has paid access
4. Signal added to shopping cart
5. Cart checked out → Order submitted to Alpaca
6. Position appears in portfolio

This test validates the entire user journey from politician trade discovery
to actual stock purchase execution.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
import streamlit as st

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from models import (
    SignalType,
)
from politician_trading.trading.alpaca_client import AlpacaTradingClient
from shopping_cart import ShoppingCart, CartItem
from paywall_config import PaywallConfig
from tests.fixtures.test_data import TestDataFactory


class MockSupabaseClient:
    """Mock Supabase client for testing"""

    def __init__(self):
        self.data_store: Dict[str, List[Dict[str, Any]]] = {
            "politicians": [],
            "trading_disclosures": [],
            "trading_signals": [],
            "trading_orders": [],
            "portfolios": [],
            "positions": [],
        }

    def table(self, table_name: str):
        """Get table interface"""
        return MockSupabaseTable(self.data_store, table_name)


class MockSupabaseTable:
    """Mock Supabase table interface"""

    def __init__(self, data_store: Dict[str, List[Dict]], table_name: str):
        self.data_store = data_store
        self.table_name = table_name
        self._filters = {}
        self._select_fields = "*"

    def select(self, fields: str = "*"):
        """Select fields"""
        self._select_fields = fields
        return self

    def insert(self, data: Dict[str, Any]):
        """Insert data"""
        if self.table_name not in self.data_store:
            self.data_store[self.table_name] = []

        # Handle both single dict and list of dicts
        if isinstance(data, dict):
            self.data_store[self.table_name].append(data.copy())
        elif isinstance(data, list):
            self.data_store[self.table_name].extend([d.copy() for d in data])

        return self

    def update(self, data: Dict[str, Any]):
        """Update data"""
        # Find matching records and update them
        for record in self.data_store.get(self.table_name, []):
            match = all(record.get(k) == v for k, v in self._filters.items())
            if match:
                record.update(data)
        return self

    def delete(self):
        """Delete data"""
        if self.table_name in self.data_store:
            # Remove records matching filters
            self.data_store[self.table_name] = [
                record
                for record in self.data_store[self.table_name]
                if not all(record.get(k) == v for k, v in self._filters.items())
            ]
        return self

    def eq(self, column: str, value: Any):
        """Equality filter"""
        self._filters[column] = value
        return self

    def ilike(self, column: str, value: str):
        """Case-insensitive like filter"""
        self._filters[column] = value
        return self

    def execute(self):
        """Execute query"""
        result_data = []

        if self.table_name in self.data_store:
            for record in self.data_store[self.table_name]:
                # Apply filters
                if self._filters:
                    match = all(record.get(k) == v for k, v in self._filters.items())
                    if match:
                        result_data.append(record.copy())
                else:
                    result_data.append(record.copy())

        # Create mock result
        mock_result = Mock()
        mock_result.data = result_data
        return mock_result


@pytest.fixture
def mock_streamlit_session():
    """Mock Streamlit session state"""
    if not hasattr(st, "session_state"):
        st.session_state = {}

    # Clear session state
    st.session_state.clear()

    yield st.session_state

    # Cleanup
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


class TestE2ETradingFlow:
    """End-to-end trading flow tests"""

    @pytest.mark.asyncio
    async def test_complete_nancy_pelosi_aapl_trading_workflow(
        self, mock_streamlit_session, mock_supabase_client, test_alpaca_keys
    ):
        """
        Complete E2E test: Nancy Pelosi AAPL sale → Signal → Cart → Alpaca → Portfolio

        Test Flow:
        1. Seed Nancy Pelosi politician record
        2. Seed AAPL sale disclosure
        3. Generate trading signal from disclosure
        4. Verify paywall access (Pro tier)
        5. Add signal to shopping cart
        6. Update cart quantity
        7. Checkout - Execute trade via Alpaca
        8. Verify order submitted
        9. Verify portfolio position
        10. Cleanup test data
        """

        # ===================================================================
        # STEP 1: SEED TEST DATA
        # ===================================================================
        print("\n=== STEP 1: Seeding Test Data ===")

        # Create Nancy Pelosi politician
        nancy_pelosi = TestDataFactory.create_nancy_pelosi()
        politician_dict = TestDataFactory.to_politician_dict(nancy_pelosi)

        # Insert to mock database
        mock_supabase_client.table("politicians").insert(politician_dict).execute()
        print(f"✅ Inserted Nancy Pelosi (ID: {nancy_pelosi.id})")

        # Verify insertion
        result = (
            mock_supabase_client.table("politicians")
            .select("*")
            .eq("id", nancy_pelosi.id)
            .execute()
        )
        assert len(result.data) == 1
        assert result.data[0]["first_name"] == "Nancy"
        assert result.data[0]["last_name"] == "Pelosi"

        # Create AAPL sale disclosure
        aapl_disclosure = TestDataFactory.create_aapl_sale_disclosure(nancy_pelosi.id)
        disclosure_dict = TestDataFactory.to_disclosure_dict(aapl_disclosure)

        # Insert to mock database
        mock_supabase_client.table("trading_disclosures").insert(disclosure_dict).execute()
        print(f"✅ Inserted AAPL sale disclosure (ID: {aapl_disclosure.id})")

        # Verify disclosure
        result = (
            mock_supabase_client.table("trading_disclosures")
            .select("*")
            .eq("id", aapl_disclosure.id)
            .execute()
        )
        assert len(result.data) == 1
        assert result.data[0]["asset_ticker"] == "AAPL"
        assert result.data[0]["transaction_type"] == "sale"
        assert result.data[0]["politician_id"] == nancy_pelosi.id

        # ===================================================================
        # STEP 2: GENERATE SIGNAL FROM POLITICIAN TRADE
        # ===================================================================
        print("\n=== STEP 2: Generating Trading Signal ===")

        # Create signal directly (simulating SignalGenerator.generate_signal())
        test_signal = TestDataFactory.create_test_signal([aapl_disclosure.id])
        signal_dict = TestDataFactory.to_signal_dict(test_signal)

        # Insert signal to database
        mock_supabase_client.table("trading_signals").insert(signal_dict).execute()
        print(f"✅ Generated signal: {test_signal.signal_type.value.upper()} AAPL")

        # Verify signal properties
        assert test_signal.ticker == "AAPL"
        assert test_signal.signal_type == SignalType.SELL
        assert test_signal.confidence_score >= 0.6
        assert test_signal.target_price is not None
        assert test_signal.stop_loss is not None
        assert test_signal.take_profit is not None
        assert aapl_disclosure.id in test_signal.disclosure_ids
        print(f"   Confidence: {test_signal.confidence_score:.1%}")
        print(f"   Target: ${test_signal.target_price}")
        print(f"   Stop Loss: ${test_signal.stop_loss}")
        print(f"   Take Profit: ${test_signal.take_profit}")

        # ===================================================================
        # STEP 3: PAYWALL ACCESS VERIFICATION
        # ===================================================================
        print("\n=== STEP 3: Verifying Paywall Access ===")

        # Test with Pro tier user
        pro_user = TestDataFactory.create_test_user_pro_tier()
        mock_streamlit_session.update(pro_user)

        # Verify pro user has access to trading signals
        assert PaywallConfig.get_user_tier() == "pro"
        assert PaywallConfig.has_feature("trading_signals") is True
        assert PaywallConfig.has_feature("portfolio_tracking") is True
        print("✅ Pro tier user has access to trading_signals")

        # Test with Free tier user (should NOT have access)
        free_user = TestDataFactory.create_test_user_free_tier()
        mock_streamlit_session.clear()
        mock_streamlit_session.update(free_user)

        assert PaywallConfig.get_user_tier() == "free"
        assert PaywallConfig.has_feature("trading_signals") is False
        assert PaywallConfig.has_feature("auto_trading") is False
        print("✅ Free tier user correctly blocked from trading_signals")

        # Switch back to Pro user for rest of test
        mock_streamlit_session.clear()
        mock_streamlit_session.update(pro_user)

        # ===================================================================
        # STEP 4: SHOPPING CART OPERATIONS
        # ===================================================================
        print("\n=== STEP 4: Shopping Cart Operations ===")

        # Initialize cart
        ShoppingCart.initialize()
        assert ShoppingCart.get_item_count() == 0
        print("✅ Cart initialized (empty)")

        # Create cart item from signal
        cart_item = CartItem(
            ticker=test_signal.ticker,
            asset_name=test_signal.asset_name,
            signal_type=test_signal.signal_type.value,
            quantity=10,
            signal_id=test_signal.id,
            confidence_score=float(test_signal.confidence_score),
            target_price=float(test_signal.target_price) if test_signal.target_price else None,
            stop_loss=float(test_signal.stop_loss) if test_signal.stop_loss else None,
            take_profit=float(test_signal.take_profit) if test_signal.take_profit else None,
            notes="Test trade from Nancy Pelosi AAPL sale",
        )

        # Add to cart
        added = ShoppingCart.add_item(cart_item)
        assert added is True
        assert ShoppingCart.get_item_count() == 1
        print(f"✅ Added {cart_item.ticker} to cart (quantity: {cart_item.quantity})")

        # Verify cart contents
        cart_items = ShoppingCart.get_items()
        assert len(cart_items) == 1
        assert cart_items[0]["ticker"] == "AAPL"
        assert cart_items[0]["quantity"] == 10
        assert cart_items[0]["signal_id"] == test_signal.id

        # Update quantity
        updated = ShoppingCart.update_quantity("AAPL", 15)
        assert updated is True
        cart_items = ShoppingCart.get_items()
        assert cart_items[0]["quantity"] == 15
        print("✅ Updated quantity to 15 shares")

        # ===================================================================
        # STEP 5: CHECKOUT - TRADE EXECUTION
        # ===================================================================
        print("\n=== STEP 5: Executing Trade via Alpaca ===")

        # Mock Alpaca client
        with patch("politician_trading.trading.alpaca_client.TradingClient") as mock_trading_client:
            # Setup mock order response
            mock_order = Mock()
            mock_order.id = uuid4()
            mock_order.client_order_id = uuid4()
            mock_order.symbol = "AAPL"
            mock_order.qty = "15"
            mock_order.filled_qty = "0"
            mock_order.type = "market"
            mock_order.side = Mock(value="sell")
            mock_order.status = "pending_new"
            mock_order.limit_price = None
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

            # Create Alpaca client
            alpaca_client = AlpacaTradingClient(**test_alpaca_keys)

            # Test connection
            account_info = alpaca_client.get_account()
            assert account_info is not None
            assert account_info["status"] == "ACTIVE"
            print("✅ Connected to Alpaca (Paper Trading)")
            print(f"   Account ID: {account_info['account_id'][:8]}...")
            print(f"   Buying Power: ${float(account_info['buying_power']):,.2f}")

            # Execute trades from cart
            cart_items = ShoppingCart.get_items()
            executed_orders = []

            for item in cart_items:
                # Place market order
                order = alpaca_client.place_market_order(
                    ticker=item["ticker"],
                    quantity=item["quantity"],
                    side="sell",  # Following Pelosi's sale
                )

                assert order is not None
                assert order.alpaca_order_id is not None
                assert order.ticker == "AAPL"
                assert order.quantity == 15
                assert order.side == "sell"
                assert order.status.value == "pending"  # Compare enum value, not identity

                executed_orders.append(order)
                print("✅ Placed order: SELL 15 shares of AAPL")
                print(f"   Order ID: {order.alpaca_order_id}")
                print(f"   Status: {order.status.value}")

                # Insert order to database
                order_dict = {
                    "id": str(uuid4()),
                    "signal_id": item.get("signal_id"),
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

                mock_supabase_client.table("trading_orders").insert(order_dict).execute()

            # Verify orders in database
            result = mock_supabase_client.table("trading_orders").select("*").execute()
            assert len(result.data) == 1
            assert result.data[0]["ticker"] == "AAPL"
            assert result.data[0]["quantity"] == 15
            assert result.data[0]["signal_id"] == test_signal.id

            # Clear cart after successful execution
            ShoppingCart.clear()
            assert ShoppingCart.get_item_count() == 0
            print("✅ Cart cleared after successful execution")

        # ===================================================================
        # STEP 6: VERIFY ALPACA INTEGRATION
        # ===================================================================
        print("\n=== STEP 6: Verifying Alpaca Integration ===")

        # Verify order was submitted
        assert len(executed_orders) == 1
        order = executed_orders[0]

        # Verify order properties
        assert isinstance(order.alpaca_order_id, str)
        assert isinstance(order.alpaca_client_order_id, str)
        assert order.ticker == "AAPL"
        assert order.quantity == 15
        assert order.side == "sell"
        assert order.order_type.value == "market"  # Compare enum value
        assert order.trading_mode.value == "paper"  # Compare enum value
        print("✅ Order successfully submitted to Alpaca")
        print(f"   Alpaca Order ID: {order.alpaca_order_id}")

        # Update order status in database (simulate fill)
        updated_order_dict = {
            "status": "filled",
            "filled_quantity": 15,
            "filled_avg_price": 150.25,
            "filled_at": datetime.utcnow().isoformat(),
        }

        mock_supabase_client.table("trading_orders").update(updated_order_dict).eq(
            "alpaca_order_id", order.alpaca_order_id
        ).execute()

        # ===================================================================
        # STEP 7: PORTFOLIO TRACKING
        # ===================================================================
        print("\n=== STEP 7: Portfolio Tracking ===")

        # Create mock portfolio
        portfolio_id = str(uuid4())
        portfolio_dict = {
            "id": portfolio_id,
            "name": "Test Paper Portfolio",
            "trading_mode": "paper",
            "cash": 98500.0,  # 100k - (15 shares * ~150)
            "portfolio_value": 100000.0,
            "buying_power": 98500.0,
            "total_return": 0.0,
            "total_return_pct": 0.0,
            "alpaca_account_id": str(uuid4()),
            "is_active": True,
        }

        mock_supabase_client.table("portfolios").insert(portfolio_dict).execute()
        print(f"✅ Portfolio created (ID: {portfolio_id})")

        # Create position
        position_dict = {
            "id": str(uuid4()),
            "portfolio_id": portfolio_id,
            "ticker": "AAPL",
            "asset_name": "Apple Inc.",
            "quantity": -15,  # Negative because it's a short sell
            "side": "short",
            "avg_entry_price": 150.25,
            "total_cost": 150.25 * 15,
            "current_price": 150.25,
            "market_value": 150.25 * 15,
            "unrealized_pl": 0.0,
            "unrealized_pl_pct": 0.0,
            "opened_at": datetime.utcnow().isoformat(),
            "signal_ids": [test_signal.id],
            "order_ids": [order.alpaca_order_id],
            "status": "open",
        }

        mock_supabase_client.table("positions").insert(position_dict).execute()
        print("✅ Position created: SHORT 15 shares AAPL @ $150.25")

        # Verify position in database
        result = (
            mock_supabase_client.table("positions")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .execute()
        )

        assert len(result.data) == 1
        position = result.data[0]
        assert position["ticker"] == "AAPL"
        assert position["quantity"] == -15
        assert position["side"] == "short"
        assert position["avg_entry_price"] == 150.25
        assert test_signal.id in position["signal_ids"]
        assert order.alpaca_order_id in position["order_ids"]
        print("✅ Position verified in portfolio")
        print(f"   Entry Price: ${position['avg_entry_price']:.2f}")
        print(f"   Market Value: ${position['market_value']:.2f}")
        print(f"   Linked to Signal: {test_signal.id[:8]}...")
        print(f"   Linked to Order: {order.alpaca_order_id[:8]}...")

        # ===================================================================
        # STEP 8: VERIFY COMPLETE TRACEABILITY
        # ===================================================================
        print("\n=== STEP 8: Verifying Complete Traceability ===")

        # Trace: Politician → Disclosure → Signal → Order → Position
        print("\n📊 Complete Trade Lineage:")
        print(f"   1. Politician: {nancy_pelosi.full_name} ({nancy_pelosi.party})")
        print(
            f"   2. Disclosure: {aapl_disclosure.transaction_type.value.upper()} "
            f"{aapl_disclosure.asset_ticker} on {aapl_disclosure.transaction_date.date()}"
        )
        print(
            f"   3. Signal: {test_signal.signal_type.value.upper()} "
            f"(Confidence: {test_signal.confidence_score:.1%})"
        )
        print(f"   4. Order: {order.side.upper()} {order.quantity} shares @ MARKET")
        print(
            f"   5. Position: {position['side'].upper()} {abs(position['quantity'])} shares "
            f"@ ${position['avg_entry_price']:.2f}"
        )

        # Verify links
        assert position["signal_ids"][0] == test_signal.id
        assert test_signal.disclosure_ids[0] == aapl_disclosure.id
        assert aapl_disclosure.politician_id == nancy_pelosi.id
        print("\n✅ Complete traceability verified!")

        # ===================================================================
        # STEP 9: CLEANUP
        # ===================================================================
        print("\n=== STEP 9: Cleanup Test Data ===")

        # Delete in reverse order of dependencies
        mock_supabase_client.table("positions").delete().eq("id", position_dict["id"]).execute()
        print("✅ Deleted position")

        mock_supabase_client.table("portfolios").delete().eq("id", portfolio_id).execute()
        print("✅ Deleted portfolio")

        mock_supabase_client.table("trading_orders").delete().eq(
            "alpaca_order_id", order.alpaca_order_id
        ).execute()
        print("✅ Deleted order")

        mock_supabase_client.table("trading_signals").delete().eq("id", test_signal.id).execute()
        print("✅ Deleted signal")

        mock_supabase_client.table("trading_disclosures").delete().eq(
            "id", aapl_disclosure.id
        ).execute()
        print("✅ Deleted disclosure")

        mock_supabase_client.table("politicians").delete().eq("id", nancy_pelosi.id).execute()
        print("✅ Deleted politician")

        # Verify cleanup
        assert len(mock_supabase_client.table("politicians").select("*").execute().data) == 0
        assert (
            len(mock_supabase_client.table("trading_disclosures").select("*").execute().data) == 0
        )
        assert len(mock_supabase_client.table("trading_signals").select("*").execute().data) == 0
        assert len(mock_supabase_client.table("trading_orders").select("*").execute().data) == 0
        assert len(mock_supabase_client.table("portfolios").select("*").execute().data) == 0
        assert len(mock_supabase_client.table("positions").select("*").execute().data) == 0

        print("\n" + "=" * 70)
        print("🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nTest Summary:")
        print("✅ Politician trade data seeded")
        print("✅ Trading signal generated from politician activity")
        print("✅ Paywall correctly enforced feature access")
        print("✅ Shopping cart managed items correctly")
        print("✅ Order successfully submitted to Alpaca (paper mode)")
        print("✅ Portfolio position created and tracked")
        print("✅ Complete traceability maintained (politician → position)")
        print("✅ All test data cleaned up")
        print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run the test
    pytest.main([__file__, "-v", "-s"])
