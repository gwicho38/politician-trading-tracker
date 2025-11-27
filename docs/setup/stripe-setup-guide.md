# Stripe Subscription Setup Guide

This guide explains how to configure Stripe for the subscription/paywall feature in Politician Trading Tracker.

## Overview

The application uses `st-paywall` to integrate Stripe subscriptions. The "Upgrade Now" button on the Subscription page will redirect users to a Stripe checkout page where they can subscribe to Pro or Enterprise plans.

## Prerequisites

1. A Stripe account (sign up at https://stripe.com)
2. Access to the Streamlit Cloud dashboard (for production deployment)

## Step 1: Get Stripe API Keys

1. Log in to your Stripe Dashboard: https://dashboard.stripe.com/
2. Click on "Developers" in the left sidebar
3. Go to "API keys"
4. Copy the following keys:
   - **Test mode**: `sk_test_...` (for development)
   - **Live mode**: `sk_live_...` (for production)

⚠️ **Important**: Never commit these keys to git. They should only be in `.streamlit/secrets.toml` locally and in Streamlit Cloud secrets.

## Step 2: Create Stripe Payment Links

You need to create subscription products and payment links in Stripe:

### Create Subscription Products

1. Go to https://dashboard.stripe.com/products
2. Click "Add product"
3. Create two products:
   - **Pro Plan** ($X/month)
   - **Enterprise Plan** ($Y/month)

### Add Metadata to Products

For each product, add metadata to identify the tier:
1. Click on the product
2. Scroll to "Metadata" section
3. Add metadata: `tier` = `pro` or `tier` = `enterprise`

This metadata is used by the app to determine the user's tier level.

### Create Payment Links

1. Go to https://dashboard.stripe.com/payment-links
2. Click "New payment link"
3. For each product (Pro and Enterprise):
   - Select the product
   - Configure the link settings
   - Copy the payment link URL (format: `https://buy.stripe.com/...`)

You'll need both test and live payment links.

## Step 3: Configure Local Development

Update `.streamlit/secrets.toml` with your Stripe credentials:

```toml
# Stripe Subscription Configuration
payment_provider = "stripe"
testing_mode = true  # Set to false for production

# Test mode credentials
stripe_api_key_test = "sk_test_YOUR_ACTUAL_TEST_KEY"
stripe_link_test = "https://buy.stripe.com/test_YOUR_ACTUAL_TEST_LINK"

# Live mode credentials (for production)
stripe_api_key = "sk_live_YOUR_ACTUAL_LIVE_KEY"
stripe_link = "https://buy.stripe.com/YOUR_ACTUAL_LIVE_LINK"
```

## Step 4: Configure Streamlit Cloud (Production)

To configure the deployed app at https://politician-trading-tracker.streamlit.app:

1. Go to https://share.streamlit.io/
2. Find your app in the dashboard
3. Click on the app settings (⚙️ icon)
4. Go to the "Secrets" section
5. Add the Stripe configuration:

```toml
# Add or update these values in the Streamlit Cloud secrets editor
payment_provider = "stripe"
testing_mode = false  # Use live mode in production
stripe_api_key = "sk_live_YOUR_ACTUAL_LIVE_KEY"
stripe_link = "https://buy.stripe.com/YOUR_ACTUAL_LIVE_LINK"

# Optional: Keep test credentials for testing
stripe_api_key_test = "sk_test_YOUR_ACTUAL_TEST_KEY"
stripe_link_test = "https://buy.stripe.com/test_YOUR_ACTUAL_TEST_LINK"
```

6. Click "Save"
7. The app will automatically redeploy with the new secrets

## Step 5: Test the Integration

### Local Testing

1. Start the app locally: `streamlit run app.py`
2. Navigate to the Subscription page
3. Click the "🚀 Upgrade Now" button
4. Verify you're redirected to the Stripe checkout page
5. Use a test card (e.g., `4242 4242 4242 4242`) to complete a test purchase
6. After payment, verify the subscription status updates in the app

### Production Testing

1. Before going live, use `testing_mode = true` in production temporarily
2. Test with Stripe test cards
3. Once verified, switch to `testing_mode = false` and update with live credentials
4. Monitor the Stripe dashboard for real subscriptions

## Troubleshooting

### "Subscription system not configured" Error

This means `st-paywall` couldn't load properly. Check:
- Is `st-paywall>=1.0.1` installed? Run `uv pip list | grep paywall`
- Are the Stripe secrets configured in `secrets.toml`?

### Button doesn't redirect to Stripe

- Verify the `stripe_link` or `stripe_link_test` URL is correct
- Check that `testing_mode` matches your desired environment
- Look for errors in the Streamlit logs

### Subscription status not updating after payment

- Ensure Stripe webhooks are configured (advanced feature)
- Check that product metadata includes the `tier` field
- Verify the Stripe API key has the correct permissions

## Subscription Tiers

The app supports three tiers defined in `paywall_config.py`:

| Tier | Features |
|------|----------|
| **Free** | Basic data viewing, limited to 30 days history |
| **Pro** | AI trading signals, portfolio tracking, 50 data collection runs/day |
| **Enterprise** | Automated trading, unlimited runs, API access |

## Security Best Practices

1. **Never commit secrets to git** - Use `.gitignore` for `.streamlit/secrets.toml`
2. **Use test mode first** - Always test with `testing_mode = true` before going live
3. **Rotate keys regularly** - Update Stripe API keys periodically
4. **Monitor Stripe dashboard** - Watch for suspicious activity
5. **Use environment-specific keys** - Different keys for dev/staging/prod

## Next Steps

After setting up Stripe:

1. Decide on pricing for Pro and Enterprise tiers
2. Configure Stripe webhooks for real-time subscription updates (optional)
3. Set up email notifications for new subscribers
4. Add analytics to track conversion rates
5. Consider adding a trial period for Pro tier

## Support

For Stripe-specific issues:
- Stripe Documentation: https://stripe.com/docs
- Stripe Support: https://support.stripe.com/

For st-paywall issues:
- st-paywall Documentation: https://st-paywall.readthedocs.io/
- GitHub: https://github.com/tylerjrichards/st-paywall
