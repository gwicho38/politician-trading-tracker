"""
Shopping Cart Module - For tracking and executing trading signals
"""

import streamlit as st
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass, asdict
import json


@dataclass
class CartItem:
    """Represents an item in the shopping cart."""
    ticker: str
    asset_name: str
    signal_type: str  # "buy", "sell", "strong_buy", "strong_sell"
    quantity: int
    signal_id: Optional[str] = None
    confidence_score: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CartItem":
        """Create from dictionary."""
        return cls(**data)


class ShoppingCart:
    """Manages the trading shopping cart in session state."""

    SESSION_KEY = "trading_cart"

    @classmethod
    def initialize(cls):
        """Initialize the cart in session state if not already present."""
        if cls.SESSION_KEY not in st.session_state:
            st.session_state[cls.SESSION_KEY] = {
                "items": [],
                "collapsed": False,  # Start expanded
            }

    @classmethod
    def add_item(cls, item: CartItem) -> bool:
        """
        Add an item to the cart.

        Args:
            item: CartItem to add

        Returns:
            True if added, False if already exists
        """
        cls.initialize()

        # Check if item already exists
        for existing_item in st.session_state[cls.SESSION_KEY]["items"]:
            if existing_item["ticker"] == item.ticker:
                # Update quantity instead of adding duplicate
                existing_item["quantity"] += item.quantity
                return False

        # Add new item
        st.session_state[cls.SESSION_KEY]["items"].append(item.to_dict())
        return True

    @classmethod
    def remove_item(cls, ticker: str) -> bool:
        """
        Remove an item from the cart by ticker.

        Args:
            ticker: Stock ticker to remove

        Returns:
            True if removed, False if not found
        """
        cls.initialize()

        items = st.session_state[cls.SESSION_KEY]["items"]
        for i, item in enumerate(items):
            if item["ticker"] == ticker:
                items.pop(i)
                return True
        return False

    @classmethod
    def update_quantity(cls, ticker: str, quantity: int) -> bool:
        """
        Update the quantity for an item.

        Args:
            ticker: Stock ticker
            quantity: New quantity

        Returns:
            True if updated, False if not found
        """
        cls.initialize()

        for item in st.session_state[cls.SESSION_KEY]["items"]:
            if item["ticker"] == ticker:
                item["quantity"] = quantity
                return True
        return False

    @classmethod
    def clear(cls):
        """Clear all items from the cart."""
        cls.initialize()
        st.session_state[cls.SESSION_KEY]["items"] = []

    @classmethod
    def get_items(cls) -> List[Dict[str, Any]]:
        """Get all items in the cart."""
        cls.initialize()
        return st.session_state[cls.SESSION_KEY]["items"]

    @classmethod
    def get_item_count(cls) -> int:
        """Get the number of items in the cart."""
        cls.initialize()
        return len(st.session_state[cls.SESSION_KEY]["items"])

    @classmethod
    def is_collapsed(cls) -> bool:
        """Check if cart is collapsed."""
        cls.initialize()
        return st.session_state[cls.SESSION_KEY]["collapsed"]

    @classmethod
    def set_collapsed(cls, collapsed: bool):
        """Set cart collapsed state."""
        cls.initialize()
        st.session_state[cls.SESSION_KEY]["collapsed"] = collapsed

    @classmethod
    def toggle_collapsed(cls):
        """Toggle cart collapsed state."""
        cls.initialize()
        st.session_state[cls.SESSION_KEY]["collapsed"] = not st.session_state[cls.SESSION_KEY]["collapsed"]


def render_shopping_cart_sidebar():
    """
    Render a compact shopping cart indicator in the regular sidebar.
    The full cart can be accessed via a popover or separate page.
    """
    ShoppingCart.initialize()

    item_count = ShoppingCart.get_item_count()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛒 Trading Cart")

    if item_count > 0:
        st.sidebar.success(f"**{item_count} items** in cart")

        # Show quick summary
        items = ShoppingCart.get_items()
        for item in items[:3]:  # Show first 3 items
            st.sidebar.caption(f"• {item['ticker']} ({item['quantity']})")

        if item_count > 3:
            st.sidebar.caption(f"... and {item_count - 3} more")

        # Quick action buttons
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🚀 Execute", key="sidebar_execute", use_container_width=True):
                st.switch_page("3_💼_Trading_Operations.py")
        with col2:
            if st.button("🗑️ Clear", key="sidebar_clear", use_container_width=True):
                ShoppingCart.clear()
                st.rerun()
    else:
        st.sidebar.info("Cart is empty")


def render_shopping_cart():
    """
    Render the full shopping cart experience.
    This can be called on specific pages or in a dedicated cart view.
    """
    ShoppingCart.initialize()

    st.markdown("## 🛒 Shopping Cart")

    items = ShoppingCart.get_items()

    if not items:
        st.info("Your cart is empty. Add signals from the Trading Signals page to get started!")
        return

    st.success(f"You have **{len(items)}** items in your cart")

    # Display each item
    for item in items:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"### {item['ticker']}")
                st.caption(item['asset_name'])

            with col2:
                # Signal type badge
                signal_type = item["signal_type"]
                signal_color = {
                    "strong_buy": "🟢",
                    "buy": "🟡",
                    "hold": "🔵",
                    "sell": "🟠",
                    "strong_sell": "🔴",
                }.get(signal_type, "⚪")

                st.markdown(f"{signal_color} **{signal_type.upper().replace('_', ' ')}**")
                if item.get("confidence_score"):
                    st.caption(f"Confidence: {item['confidence_score']:.1%}")

            with col3:
                # Quantity input
                new_quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=item["quantity"],
                    key=f"qty_{item['ticker']}",
                )

                if new_quantity != item["quantity"]:
                    ShoppingCart.update_quantity(item["ticker"], new_quantity)
                    st.rerun()

            with col4:
                # Remove button
                if st.button("🗑️", key=f"remove_{item['ticker']}", help="Remove from cart"):
                    ShoppingCart.remove_item(item["ticker"])
                    st.rerun()

            # Price targets if available
            if item.get("target_price") or item.get("stop_loss") or item.get("take_profit"):
                with st.expander("📊 Price Targets"):
                    col1, col2, col3 = st.columns(3)
                    if item.get("target_price"):
                        col1.metric("Target", f"${item['target_price']:.2f}")
                    if item.get("stop_loss"):
                        col2.metric("Stop Loss", f"${item['stop_loss']:.2f}")
                    if item.get("take_profit"):
                        col3.metric("Take Profit", f"${item['take_profit']:.2f}")

            st.divider()

    # Action buttons
    st.markdown("### Actions")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Execute All Trades", key="execute_all", use_container_width=True, type="primary"):
            st.session_state["execute_cart"] = True
            st.switch_page("3_💼_Trading_Operations.py")

    with col2:
        if st.button("🗑️ Clear Cart", key="clear_cart", use_container_width=True):
            ShoppingCart.clear()
            st.rerun()


def add_to_cart_button(
    ticker: str,
    asset_name: str,
    signal_type: str,
    default_quantity: int = 10,
    signal_id: Optional[str] = None,
    confidence_score: Optional[float] = None,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    notes: Optional[str] = None,
    key: Optional[str] = None,
) -> bool:
    """
    Render an "Add to Cart" button for a signal.

    Args:
        ticker: Stock ticker
        asset_name: Full asset name
        signal_type: Type of signal
        default_quantity: Default quantity to add
        signal_id: Optional signal ID reference
        confidence_score: Signal confidence
        target_price: Target price
        stop_loss: Stop loss price
        take_profit: Take profit price
        notes: Additional notes
        key: Unique key for button

    Returns:
        True if button was clicked
    """
    ShoppingCart.initialize()

    button_key = key or f"add_cart_{ticker}"

    if st.button("🛒 Add to Cart", key=button_key):
        item = CartItem(
            ticker=ticker,
            asset_name=asset_name,
            signal_type=signal_type,
            quantity=default_quantity,
            signal_id=signal_id,
            confidence_score=confidence_score,
            target_price=target_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            notes=notes,
        )

        added = ShoppingCart.add_item(item)

        if added:
            st.success(f"✅ Added {ticker} to cart!")
        else:
            st.info(f"📝 Updated {ticker} quantity in cart")

        return True

    return False
