"""
Paywall Configuration for Politician Trading Tracker
Integrates st-paywall with Stripe for subscription management
"""
import streamlit as st
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)


class PaywallConfig:
    """Centralized paywall configuration and management"""

    # Subscription tier definitions
    TIERS = {
        "free": {
            "name": "Free",
            "description": "Basic access to public politician trading data",
            "features": [
                "View recent politician trades",
                "Basic search and filtering",
                "Limited historical data (30 days)"
            ],
            "limits": {
                "data_collection_runs": 3,  # per day
                "trading_signals": False,
                "auto_trading": False,
                "portfolio_tracking": False,
                "scheduled_jobs": 0,
                "api_access": False
            }
        },
        "pro": {
            "name": "Pro",
            "description": "Advanced trading signals and automation",
            "features": [
                "Full historical data access",
                "AI-powered trading signals",
                "Manual trading operations",
                "Portfolio tracking and analytics",
                "Email notifications",
                "Priority support"
            ],
            "limits": {
                "data_collection_runs": 50,  # per day
                "trading_signals": True,
                "auto_trading": False,
                "portfolio_tracking": True,
                "scheduled_jobs": 5,
                "api_access": False
            }
        },
        "enterprise": {
            "name": "Enterprise",
            "description": "Full automation and API access",
            "features": [
                "Everything in Pro",
                "Automated trading execution",
                "Unlimited scheduled jobs",
                "API access",
                "Custom strategies",
                "Dedicated support",
                "White-label options"
            ],
            "limits": {
                "data_collection_runs": -1,  # unlimited
                "trading_signals": True,
                "auto_trading": True,
                "portfolio_tracking": True,
                "scheduled_jobs": -1,  # unlimited
                "api_access": True
            }
        }
    }

    @staticmethod
    def get_user_tier() -> str:
        """Get current user's subscription tier"""
        if not st.session_state.get("user_subscribed", False):
            return "free"

        # Check subscription details from st-paywall
        subscriptions = st.session_state.get("subscriptions", [])
        if not subscriptions:
            return "free"

        # Determine tier based on subscription metadata
        # This assumes Stripe subscription metadata includes a 'tier' field
        for sub in subscriptions:
            metadata = sub.get("metadata", {})
            tier = metadata.get("tier", "pro")  # Default to pro if subscribed
            if tier in PaywallConfig.TIERS:
                return tier

        return "pro"  # Default for any subscription

    @staticmethod
    def get_tier_limits(tier: Optional[str] = None) -> dict:
        """Get limits for a specific tier"""
        if tier is None:
            tier = PaywallConfig.get_user_tier()
        return PaywallConfig.TIERS.get(tier, PaywallConfig.TIERS["free"])["limits"]

    @staticmethod
    def has_feature(feature: str) -> bool:
        """Check if current user has access to a specific feature"""
        tier = PaywallConfig.get_user_tier()
        limits = PaywallConfig.get_tier_limits(tier)

        # Check feature access
        if feature in limits:
            value = limits[feature]
            if isinstance(value, bool):
                return value
            elif isinstance(value, int):
                return value != 0

        return False

    @staticmethod
    def check_rate_limit(feature: str, current_count: int) -> tuple[bool, str]:
        """
        Check if user has exceeded rate limit for a feature

        Returns:
            tuple[bool, str]: (is_allowed, error_message)
        """
        tier = PaywallConfig.get_user_tier()
        limits = PaywallConfig.get_tier_limits(tier)

        if feature not in limits:
            return True, ""

        limit = limits[feature]

        # -1 means unlimited
        if limit == -1:
            return True, ""

        # Check if exceeded
        if current_count >= limit:
            return False, f"Rate limit exceeded for {feature}. Upgrade to access more."

        return True, ""

    @staticmethod
    def show_upgrade_message(feature_name: str, use_sidebar: bool = False):
        """Display upgrade message for locked features"""
        tier = PaywallConfig.get_user_tier()

        # Find which tier unlocks this feature
        unlock_tier = None
        for tier_name, tier_data in PaywallConfig.TIERS.items():
            if tier_name != "free" and tier_name != tier:
                # Check if this tier has the feature
                # This is simplified - you'd check the actual limits
                if tier_name != "free":
                    unlock_tier = tier_data["name"]
                    break

        msg = f"🔒 **{feature_name}** is a premium feature."
        if unlock_tier:
            msg += f" Upgrade to **{unlock_tier}** to unlock."

        if use_sidebar:
            st.sidebar.warning(msg)
        else:
            st.warning(msg)

    @staticmethod
    def display_tier_comparison():
        """Display a comparison table of all tiers"""
        st.subheader("Subscription Tiers")

        cols = st.columns(len(PaywallConfig.TIERS))

        for i, (tier_key, tier_data) in enumerate(PaywallConfig.TIERS.items()):
            with cols[i]:
                st.markdown(f"### {tier_data['name']}")
                st.caption(tier_data["description"])

                st.markdown("**Features:**")
                for feature in tier_data["features"]:
                    st.markdown(f"✓ {feature}")

                # Show current tier badge
                if PaywallConfig.get_user_tier() == tier_key:
                    st.success("Current Plan")


def add_paywall(
    required: bool = True,
    use_sidebar: bool = True,
    subscription_button_text: str = "Upgrade Now",
    button_color: str = "#cb785c",  # Match theme primary color
    show_tier_info: bool = True
) -> bool:
    """
    Add paywall to current page

    Args:
        required: If True, halt app for non-subscribers
        use_sidebar: Show button in sidebar
        subscription_button_text: Custom button text
        button_color: Button color (hex)
        show_tier_info: Show current tier info

    Returns:
        bool: True if user is subscribed
    """
    try:
        from st_paywall import add_auth

        # Call st-paywall's add_auth
        add_auth(
            required=required,
            show_redirect_button=True,
            subscription_button_text=subscription_button_text,
            button_color=button_color,
            use_sidebar=use_sidebar
        )

        # Show tier information
        if show_tier_info:
            tier = PaywallConfig.get_user_tier()
            tier_data = PaywallConfig.TIERS[tier]

            container = st.sidebar if use_sidebar else st

            with container:
                st.info(f"**Current Plan:** {tier_data['name']}")

                if tier != "enterprise":
                    with st.expander("📊 See all plans"):
                        PaywallConfig.display_tier_comparison()

        return st.session_state.get("user_subscribed", False)

    except ImportError:
        logger.error("st-paywall not installed. Run: uv pip install st-paywall")
        st.error("Subscription system not configured. Please contact support.")
        return False
    except Exception as e:
        logger.error(f"Paywall error: {e}")
        st.error(f"Error loading subscription system: {e}")
        return False


def require_feature(feature: str, feature_display_name: Optional[str] = None):
    """
    Decorator to require a specific feature/tier

    Usage:
        @require_feature("auto_trading", "Automated Trading")
        def execute_trade():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not PaywallConfig.has_feature(feature):
                display_name = feature_display_name or feature.replace("_", " ").title()
                PaywallConfig.show_upgrade_message(display_name)
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator


def check_feature_access(feature: str) -> bool:
    """
    Simple function to check if user has access to a feature

    Usage:
        if check_feature_access("trading_signals"):
            show_trading_signals()
    """
    return PaywallConfig.has_feature(feature)
