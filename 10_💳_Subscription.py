"""
Subscription Management Page
Shows current plan, features, and upgrade options
"""
import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from paywall_config import PaywallConfig, add_paywall, check_feature_access
from auth_utils_enhanced import require_authentication

# Page configuration
st.set_page_config(
    page_title="Subscription - Politician Trading Tracker",
    page_icon="💳",
    layout="wide"
)

# Require authentication first
require_authentication()

st.title("💳 Subscription Management")

# Get current user tier
current_tier = PaywallConfig.get_user_tier()
tier_data = PaywallConfig.TIERS[current_tier]

# Show current plan
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Current Plan: {tier_data['name']}")
    st.caption(tier_data["description"])

    st.markdown("### Features")
    for feature in tier_data["features"]:
        st.markdown(f"✓ {feature}")

with col2:
    # Subscription status
    is_subscribed = st.session_state.get("user_subscribed", False)

    if is_subscribed:
        st.success("✓ **Active Subscription**")

        # Show subscription details if available
        subscriptions = st.session_state.get("subscriptions", [])
        if subscriptions:
            for sub in subscriptions:
                st.info(f"**Plan:** {sub.get('plan', 'Unknown')}")
                st.caption(f"Status: {sub.get('status', 'active')}")
    else:
        st.warning("**Free Plan**")
        st.button("🚀 Upgrade Now", type="primary", use_container_width=True)

st.divider()

# Feature limits
st.subheader("📊 Usage & Limits")

limits = PaywallConfig.get_tier_limits(current_tier)

limit_cols = st.columns(3)

with limit_cols[0]:
    st.metric(
        "Data Collection Runs",
        "Unlimited" if limits["data_collection_runs"] == -1 else f"{limits['data_collection_runs']}/day",
        help="Number of times you can fetch new politician trading data per day"
    )

with limit_cols[1]:
    st.metric(
        "Scheduled Jobs",
        "Unlimited" if limits["scheduled_jobs"] == -1 else limits["scheduled_jobs"],
        help="Maximum number of automated jobs you can schedule"
    )

with limit_cols[2]:
    st.metric(
        "API Access",
        "Enabled" if limits["api_access"] else "Disabled",
        help="Programmatic access to data via REST API"
    )

# Feature access table
st.subheader("🔓 Feature Access")

feature_data = {
    "Feature": [
        "Trading Signals",
        "Automated Trading",
        "Portfolio Tracking",
        "API Access"
    ],
    "Status": [
        "✅ Enabled" if limits["trading_signals"] else "🔒 Locked",
        "✅ Enabled" if limits["auto_trading"] else "🔒 Locked",
        "✅ Enabled" if limits["portfolio_tracking"] else "🔒 Locked",
        "✅ Enabled" if limits["api_access"] else "🔒 Locked"
    ]
}

st.table(feature_data)

st.divider()

# Tier comparison
st.subheader("📋 Compare Plans")

PaywallConfig.display_tier_comparison()

st.divider()

# Example: How to use feature checks in your pages
with st.expander("👨‍💻 For Developers: How to Use Paywall"):
    st.markdown("""
    ### Integration Examples

    #### Method 1: Simple Feature Check
    ```python
    from paywall_config import check_feature_access

    if check_feature_access("trading_signals"):
        # Show trading signals
        show_trading_signals()
    else:
        st.warning("🔒 Trading Signals is a Pro feature")
    ```

    #### Method 2: Decorator
    ```python
    from paywall_config import require_feature

    @require_feature("auto_trading", "Automated Trading")
    def execute_trade():
        # This only runs if user has auto_trading access
        pass
    ```

    #### Method 3: Rate Limiting
    ```python
    from paywall_config import PaywallConfig

    # Check rate limit
    allowed, error_msg = PaywallConfig.check_rate_limit(
        "data_collection_runs",
        current_count=5
    )

    if not allowed:
        st.error(error_msg)
    ```

    #### Method 4: Add Paywall to Page
    ```python
    from paywall_config import add_paywall

    # At top of premium page
    add_paywall(
        required=True,  # Block non-subscribers
        use_sidebar=True,
        subscription_button_text="Upgrade to Access"
    )
    ```

    ### Feature Keys
    - `trading_signals` - AI-powered trading signals (Pro+)
    - `auto_trading` - Automated trade execution (Enterprise)
    - `portfolio_tracking` - Portfolio analytics (Pro+)
    - `scheduled_jobs` - Background job limit
    - `data_collection_runs` - Daily data fetch limit
    - `api_access` - REST API access (Enterprise)
    """)

# Test different tier views
if st.checkbox("🧪 Test different tier views (Developer Mode)"):
    st.warning("⚠️ This is for testing purposes only")

    test_tier = st.selectbox(
        "Simulate Tier",
        options=list(PaywallConfig.TIERS.keys()),
        format_func=lambda x: PaywallConfig.TIERS[x]["name"]
    )

    test_limits = PaywallConfig.get_tier_limits(test_tier)

    st.json(test_limits)

    st.caption(f"Trading Signals: {check_feature_access('trading_signals')}")
    st.caption(f"Auto Trading: {check_feature_access('auto_trading')}")
    st.caption(f"Portfolio: {check_feature_access('portfolio_tracking')}")
