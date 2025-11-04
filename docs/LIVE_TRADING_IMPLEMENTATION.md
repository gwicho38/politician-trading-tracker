# Live Trading Implementation Guide

## Current Status ✅

Your app is correctly architected for live trading:
- Users manage their own Alpaca accounts
- Users provide their own API keys
- App executes trades on user's behalf
- Money stays in user's Alpaca account
- You don't hold or transfer user funds

## What You Need to Add

### 1. Settings Page Enhancement

Add a dedicated section for Alpaca account setup:

```python
# In Settings page
st.markdown("### 🔑 Alpaca API Configuration")

tab1, tab2 = st.tabs(["Paper Trading", "Live Trading"])

with tab1:
    st.info("Paper trading uses simulated funds - perfect for testing")
    paper_api_key = st.text_input("Paper API Key", type="password")
    paper_secret_key = st.text_input("Paper Secret Key", type="password")

with tab2:
    st.warning("⚠️ **Live Trading** - Real money will be used!")

    st.markdown("""
    **Before you start:**
    1. Create an Alpaca account at [alpaca.markets](https://alpaca.markets/)
    2. Complete identity verification
    3. Fund your account (minimum $500 for margin)
    4. Generate live API keys
    """)

    live_api_key = st.text_input("Live API Key", type="password")
    live_secret_key = st.text_input("Live Secret Key", type="password")
```

### 2. User Onboarding Flow

Create a guided onboarding page:

**Step 1: Create Alpaca Account**
- Link to Alpaca signup
- Explain verification process
- Show expected timeline (2-3 days)

**Step 2: Fund Account**
- Explain ACH transfer (3-5 days)
- Wire transfer option (same day)
- Minimum funding requirements

**Step 3: Generate API Keys**
- Step-by-step screenshots
- How to get paper vs live keys
- Security best practices

**Step 4: Configure in App**
- Where to paste keys
- How to test connection
- How to switch between paper/live

### 3. Disclaimers and Risk Warnings

**Legal disclaimers you MUST include:**

```markdown
## Investment Disclaimer

This application provides trading signals and portfolio management tools.
By using this application, you acknowledge:

- **Not Financial Advice**: Information provided is for educational purposes
  only and should not be construed as financial advice.

- **Trading Risks**: Trading stocks involves substantial risk of loss. You
  may lose some or all of your invested capital.

- **Past Performance**: Past performance does not guarantee future results.

- **Your Responsibility**: You are solely responsible for your own investment
  decisions and trades executed through your Alpaca account.

- **Independent Platform**: We are not affiliated with Alpaca Markets. We
  provide software that interfaces with your Alpaca account via API.

- **No Fund Management**: We do not hold, manage, or have access to your
  funds. All funds remain in your Alpaca brokerage account.

- **Account Security**: Keep your API keys secure. Never share them with
  anyone.

By clicking "I Accept", you confirm you understand and accept these terms.
```

### 4. Subscription Model (Stripe Integration)

**What Stripe IS for:**
- 💳 Monthly subscription ($9.99/month Basic, $29.99/month Pro)
- 💳 Premium features (advanced signals, unlimited trades, etc.)
- 💳 App access fees

**What Stripe is NOT for:**
- ❌ Trading capital
- ❌ Fund transfers
- ❌ Holding user money
- ❌ Commission payments

**Implementation:**

```python
# In Subscription page
import stripe

stripe.api_key = st.secrets["stripe_api_key"]

# Subscription tiers
PLANS = {
    "free": {
        "price": 0,
        "features": [
            "Paper trading only",
            "Basic signals",
            "10 trades per month",
        ]
    },
    "basic": {
        "price": 9.99,
        "stripe_price_id": "price_xxx",
        "features": [
            "Live trading enabled",
            "All trading signals",
            "Unlimited trades",
            "Email notifications",
        ]
    },
    "pro": {
        "price": 29.99,
        "stripe_price_id": "price_yyy",
        "features": [
            "Everything in Basic",
            "Advanced ML signals",
            "Real-time alerts",
            "Priority support",
            "API access",
        ]
    }
}
```

### 5. Security Best Practices

**API Key Storage:**
```python
# Users should store keys in Streamlit secrets or environment variables
# NEVER hardcode API keys in the app

# For Streamlit Cloud users:
# Settings → Secrets → Add:
[alpaca]
ALPACA_API_KEY = "user's key"
ALPACA_SECRET_KEY = "user's secret"
```

**Key Rotation:**
- Provide button to test keys
- Show when keys were last validated
- Allow users to update keys easily
- Warn if keys appear invalid

### 6. Account Connection Testing

```python
def validate_alpaca_keys(api_key: str, secret_key: str, paper: bool = True):
    """Validate Alpaca API keys by testing connection"""
    try:
        client = AlpacaTradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        test = client.test_connection()

        if test["success"]:
            account = client.get_account()
            return {
                "valid": True,
                "account_id": account["account_id"],
                "status": account["status"],
                "buying_power": account["buying_power"],
            }
        else:
            return {
                "valid": False,
                "error": test.get("error")
            }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }
```

### 7. Regulatory Compliance

**What you need:**
- ✅ Terms of Service (ToS)
- ✅ Privacy Policy
- ✅ Investment Disclaimer
- ✅ User Agreement

**What you DON'T need:**
- ❌ Broker-dealer license (Alpaca is the broker)
- ❌ Money transmitter license (you don't hold funds)
- ❌ Investment advisor license (if you're clear it's not advice)

**Important:**
- State clearly you're providing **tools**, not **advice**
- Don't guarantee returns
- Don't manage user funds
- Don't recommend specific trades (provide signals/data only)

### 8. Feature Gating by Subscription Tier

```python
def check_subscription_tier(user_email: str) -> str:
    """Check user's subscription tier from database"""
    # Query your database or Stripe API
    # Return: "free", "basic", "pro"
    pass

def require_subscription(min_tier: str):
    """Decorator to gate features by subscription"""
    user_tier = check_subscription_tier(st.user.email)

    tier_levels = {"free": 0, "basic": 1, "pro": 2}

    if tier_levels[user_tier] < tier_levels[min_tier]:
        st.warning(f"This feature requires {min_tier} subscription")
        st.info("Upgrade your plan to unlock this feature")
        st.stop()
```

## Recommended Rollout Plan

### Phase 1: Foundation
1. ✅ Add Settings page for API key management
2. ✅ Create onboarding guide
3. ✅ Add legal disclaimers
4. ✅ Test live trading mode

### Phase 2: Subscription (Stripe)
1. Set up Stripe account
2. Create subscription products
3. Implement paywall
4. Gate live trading behind subscription
5. Add subscription management page

### Phase 3: Enhanced Features
1. Trade history tracking
2. Performance analytics
3. Tax reporting (1099 support)
4. Advanced risk management
5. Automated rebalancing

## Cost Structure Example

**Free Tier:**
- Paper trading only
- Basic signals
- Limited features

**Basic ($9.99/month):**
- Live trading enabled
- All signals
- Unlimited trades
- Email alerts

**Pro ($29.99/month):**
- Everything in Basic
- Advanced ML signals
- Real-time WebSocket updates
- API access
- Priority support

## Legal Template

**Recommended legal pages:**
1. **Terms of Service** - governs app usage
2. **Privacy Policy** - GDPR/CCPA compliance
3. **Investment Disclaimer** - protects you from liability
4. **Acceptable Use Policy** - prevents abuse

**Where to get templates:**
- TermsFeed.com (free generators)
- Rocket Lawyer (affordable legal templates)
- Consult with attorney (recommended for final version)

## Important Notes

1. **You are a software provider**, not a financial advisor
2. **Users manage their own money** through their Alpaca accounts
3. **Stripe is for app subscriptions**, not trading capital
4. **Make disclaimers prominent** - users must accept before trading
5. **Keep detailed logs** - useful for support and compliance
6. **Consider insurance** - E&O insurance for software companies

## Questions to Consider

1. Will you offer a free tier or paid-only?
2. What features will be premium vs free?
3. Will you charge per trade or flat subscription?
4. Will you support both paper and live, or live-only for paid users?
5. What's your customer support model?

## Resources

- **Alpaca API Docs**: https://alpaca.markets/docs/
- **Stripe Integration**: https://stripe.com/docs/billing
- **Legal Templates**: https://termsfeed.com/
- **Compliance Guide**: Consult with securities attorney
