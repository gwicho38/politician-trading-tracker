# Paywall Integration Guide

## Overview

The Politician Trading Tracker uses `st-paywall` to integrate Stripe subscription management directly into the Streamlit application. This enables monetization with three subscription tiers: Free, Pro, and Enterprise.

## Architecture

### Components

1. **paywall_config.py** - Core paywall logic and tier management
2. **10_💳_Subscription.py** - Subscription management page
3. **.streamlit/secrets.toml** - Stripe configuration
4. **st-paywall library** - Third-party integration

### Subscription Tiers

| Tier | Features | Limits |
|------|----------|--------|
| **Free** | Basic access, 30-day data, search | 3 data runs/day, 0 scheduled jobs |
| **Pro** | Trading signals, portfolio, notifications | 50 data runs/day, 5 scheduled jobs |
| **Enterprise** | Full automation, API access, white-label | Unlimited |

## Setup Instructions

### 1. Install Dependencies

```bash
uv pip install st-paywall stripe
```

Already added to `requirements.txt`:
```
st-paywall>=1.0.1
stripe>=11.0.0
```

### 2. Configure Stripe

#### Get Stripe API Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Navigate to **Developers > API Keys**
3. Copy your **Test** and **Live** API keys

#### Create Payment Links

1. Go to **Products** in Stripe Dashboard
2. Create two products:
   - **Pro Plan** - Monthly subscription
   - **Enterprise Plan** - Monthly subscription
3. For each product, add metadata:
   ```
   tier: pro
   ```
   or
   ```
   tier: enterprise
   ```
4. Create **Payment Links** for each product
5. Copy the payment link URLs

#### Update secrets.toml

Edit `.streamlit/secrets.toml`:

```toml
# Stripe Configuration
payment_provider = "stripe"
testing_mode = true  # Set to false in production

# API Keys from: https://dashboard.stripe.com/test/apikeys
stripe_api_key_test = "sk_test_YOUR_ACTUAL_TEST_KEY"
stripe_api_key = "sk_live_YOUR_ACTUAL_LIVE_KEY"

# Payment links from: https://dashboard.stripe.com/payment-links
stripe_link_test = "https://buy.stripe.com/test_YOUR_TEST_LINK"
stripe_link = "https://buy.stripe.com/YOUR_LIVE_LINK"
```

### 3. Integrate Paywall in Pages

#### Method 1: Full Page Protection

Block entire page for non-subscribers:

```python
from paywall_config import add_paywall

# At the top of your page
add_paywall(
    required=True,
    use_sidebar=True,
    subscription_button_text="Upgrade to Access",
    button_color="#cb785c"
)

# Rest of your premium content
st.write("Premium content here")
```

#### Method 2: Feature-Level Protection

Show upgrade message for specific features:

```python
from paywall_config import check_feature_access, PaywallConfig

if check_feature_access("trading_signals"):
    # Show premium feature
    display_trading_signals()
else:
    PaywallConfig.show_upgrade_message("Trading Signals")
```

#### Method 3: Decorator

Protect individual functions:

```python
from paywall_config import require_feature

@require_feature("auto_trading", "Automated Trading")
def execute_automated_trade(symbol, quantity):
    # This only executes if user has Enterprise tier
    place_order(symbol, quantity)
```

#### Method 4: Rate Limiting

Enforce usage limits:

```python
from paywall_config import PaywallConfig

# Check if user can perform action
allowed, error_msg = PaywallConfig.check_rate_limit(
    "data_collection_runs",
    current_count=daily_runs
)

if not allowed:
    st.error(error_msg)
    st.stop()

# Proceed with action
run_data_collection()
```

## Feature Access Control

### Available Feature Keys

- `trading_signals` - AI-powered trading recommendations (Pro+)
- `auto_trading` - Automated trade execution (Enterprise)
- `portfolio_tracking` - Portfolio analytics dashboard (Pro+)
- `scheduled_jobs` - Background automation limit
- `data_collection_runs` - Daily data fetch limit
- `api_access` - REST API access (Enterprise)

### Tier Configuration

Edit `paywall_config.py` to modify tiers:

```python
TIERS = {
    "free": {
        "name": "Free",
        "limits": {
            "data_collection_runs": 3,
            "trading_signals": False,
            # ...
        }
    },
    # Add/modify tiers
}
```

## Integration with Existing Auth

The paywall works alongside the existing Google OAuth authentication:

1. **Authentication** (auth_utils_enhanced.py) - User login via Google
2. **Authorization** (paywall_config.py) - Feature access control
3. **Session Management** - Combined tracking

### Workflow

```
User visits app
↓
Google OAuth login (required)
↓
Check subscription via st-paywall
↓
Set tier: free/pro/enterprise
↓
Enforce feature access based on tier
```

## Testing

### Local Testing Mode

Keep `testing_mode = true` in secrets.toml to use Stripe test mode:

1. Use test API keys (sk_test_...)
2. Use test payment links
3. Test subscriptions with [Stripe test cards](https://stripe.com/docs/testing)

### Test Card Numbers

- **Success:** 4242 4242 4242 4242
- **Decline:** 4000 0000 0000 0002
- **Authentication Required:** 4000 0025 0000 3155

Use any future expiry date and any CVC.

### Developer Mode

Visit `/10_💳_Subscription` page and enable **Test different tier views** to simulate any tier.

## Production Deployment

### Checklist

- [ ] Set `testing_mode = false` in secrets.toml
- [ ] Replace test API keys with live keys
- [ ] Replace test payment links with live links
- [ ] Test subscription flow end-to-end
- [ ] Set up Stripe webhooks for subscription events
- [ ] Configure webhook endpoint in Stripe Dashboard
- [ ] Add webhook secret to secrets.toml
- [ ] Monitor Stripe Dashboard for subscription events

### Security Considerations

1. **Never commit secrets.toml** - Already in .gitignore
2. **Use environment variables** for production secrets
3. **Validate subscription server-side** - st-paywall handles this
4. **Monitor for subscription bypass attempts**
5. **Log all subscription changes** via action_logger

## Subscription Management Page

Users can manage their subscription at `/10_💳_Subscription`:

- View current plan and features
- See usage limits and remaining quota
- Compare all plans
- Upgrade/downgrade subscription

## Monitoring

### Track Subscription Metrics

```python
from paywall_config import PaywallConfig

# Get current tier distribution
tier = PaywallConfig.get_user_tier()
tier_data = PaywallConfig.TIERS[tier]

# Log to action_logs
log_action(
    action_type="subscription_check",
    status="completed",
    user_id=st.experimental_user.email,
    action_details={"tier": tier}
)
```

### Stripe Dashboard

Monitor in [Stripe Dashboard](https://dashboard.stripe.com/):
- Active subscriptions
- Revenue metrics
- Churn rate
- Failed payments

## Troubleshooting

### Common Issues

**Issue:** Paywall not appearing
- **Solution:** Ensure `st-paywall` is installed and secrets.toml is configured

**Issue:** Always shows "Free" tier
- **Solution:** Check Stripe product metadata includes `tier` field

**Issue:** Subscription button not working
- **Solution:** Verify payment links are correct in secrets.toml

**Issue:** Test mode not working
- **Solution:** Ensure `testing_mode = true` and using test API keys

### Debug Mode

Enable logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check session state:
```python
st.write(st.session_state.user_subscribed)
st.write(st.session_state.subscriptions)
```

## API Reference

### `add_paywall()`

```python
def add_paywall(
    required: bool = True,
    use_sidebar: bool = True,
    subscription_button_text: str = "Upgrade Now",
    button_color: str = "#cb785c",
    show_tier_info: bool = True
) -> bool
```

### `check_feature_access()`

```python
def check_feature_access(feature: str) -> bool
```

### `PaywallConfig.check_rate_limit()`

```python
def check_rate_limit(
    feature: str,
    current_count: int
) -> tuple[bool, str]
```

### `@require_feature()`

```python
@require_feature(feature: str, feature_display_name: str)
def protected_function():
    pass
```

## Resources

- [st-paywall Documentation](https://st-paywall.readthedocs.io/)
- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Test Cards](https://stripe.com/docs/testing)
- [Stripe Dashboard](https://dashboard.stripe.com/)
