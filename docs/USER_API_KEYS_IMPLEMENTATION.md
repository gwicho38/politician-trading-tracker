# User-Specific API Keys Implementation

## Overview

We've implemented a user-specific API key management system that allows each user to connect their own Alpaca trading account to the application. This architecture ensures:

- ✅ Users manage their own funds (stays in their Alpaca account)
- ✅ No regulatory issues (we're a software provider, not a broker-dealer)
- ✅ Minimal legal liability
- ✅ Secure encrypted storage of API keys
- ✅ Separation between paper and live trading
- ✅ Subscription-based access control for live trading

## What Was Implemented

### 1. Database Schema (`supabase/migrations/004_create_user_api_keys_table.sql`)

Created a new `user_api_keys` table that stores:
- User email (unique identifier)
- Paper trading API keys (encrypted)
- Live trading API keys (encrypted)
- Subscription tier and status
- Stripe customer/subscription IDs
- Validation timestamps

**Security Features:**
- Row Level Security (RLS) enabled - users can only access their own keys
- API keys are encrypted before storage
- Keys tied to authenticated user email

### 2. User API Keys Manager (`user_api_keys.py`)

Created a Python class to manage user API keys with:

**Key Methods:**
- `get_user_keys(user_email)` - Retrieve and decrypt user's API keys
- `save_user_keys(...)` - Encrypt and save user's API keys
- `validate_and_save_keys(...)` - Test connection and save if valid
- `get_alpaca_client(user_email, use_paper)` - Get configured Alpaca client for user
- `has_live_access(user_email)` - Check if user has paid subscription

**Encryption:**
- Uses Fernet symmetric encryption (cryptography library)
- Encryption key stored in environment variable `API_ENCRYPTION_KEY`
- Keys encrypted before storage, decrypted on retrieval

### 3. Enhanced Settings Page (`6_⚙️_Settings.py`)

Added comprehensive API key configuration UI:

**Paper Trading Tab:**
- Input fields for paper API key and secret
- Test connection button
- Save keys button
- Validation status display
- Account info display on successful connection

**Live Trading Tab:**
- Subscription gate (requires Basic/Pro tier)
- Warning about real money trading
- Input fields for live API keys
- Test connection button
- Save keys button
- Clear instructions about Alpaca account setup

**Security Section:**
- Best practices for key management
- Key rotation guidelines
- Compromise response procedures

### 4. Updated Trading Pages

Modified all trading pages to use user-specific API keys:

**Portfolio Page (`4_📈_Portfolio.py`):**
- Gets user email from `st.user.email`
- Fetches user's API keys from database
- Displays appropriate keys based on selected mode (paper/live)
- Disables live mode if user doesn't have subscription or keys
- Shows helpful messages about upgrading or configuring keys

**Orders Page (`4.5_📋_Orders.py`):**
- Same user-specific key retrieval
- Mode selection with subscription checks
- Links to Settings for configuration

**Trading Operations Page (`3_💼_Trading_Operations.py`):**
- User-specific key retrieval
- Subscription-gated live trading
- Clear upgrade prompts for free users

### 5. Migration Script (`scripts/run_migration.py`)

Created a script to display migration SQL and instructions for running it in Supabase SQL Editor.

## How It Works

### For End Users:

1. **Sign Up**: User authenticates with Google OAuth
2. **Get Alpaca Account**: User signs up at alpaca.markets
3. **Generate API Keys**: User creates paper (and optionally live) API keys in Alpaca dashboard
4. **Configure in App**: User goes to Settings page and enters their keys
5. **Test Connection**: User tests connection to validate keys
6. **Trade**: User can now trade using their own Alpaca account

### For Paper Trading (Free):

```
User → Settings → Enter Paper Keys → Test → Save → Trade on Portfolio/Trading Operations pages
```

### For Live Trading (Requires Subscription):

```
User → Subscription Page → Upgrade to Basic/Pro → Settings → Enter Live Keys → Test → Save → Trade with real money
```

## Architecture Benefits

### User-Managed Accounts
- **User funds stay in Alpaca**: We never hold or transfer user money
- **User controls everything**: They can deposit, withdraw, and manage their account directly with Alpaca
- **We're just a tool**: App executes trades on behalf of user via API

### Regulatory Compliance
- ❌ No broker-dealer license needed (Alpaca is the broker)
- ❌ No money transmitter license needed (we don't hold funds)
- ❌ No investment advisor license needed (providing tools, not advice)
- ✅ Just need clear disclaimers about risks

### Subscription Model
- **Stripe for app access**: Users pay monthly subscription for app features
- **Not for trading capital**: Stripe is NOT used to fund trades
- **Feature gating**: Live trading requires paid subscription
- **Paper trading free**: Users can test for free with paper trading

## Database Migration

To apply the database migration:

1. Go to Supabase SQL Editor:
   ```
   https://supabase.com/dashboard/project/uljsqvwkomdrlnofmlad/sql/new
   ```

2. Run the migration script to see the SQL:
   ```bash
   python3 scripts/run_migration.py
   ```

3. Copy the displayed SQL and run it in Supabase SQL Editor

4. Verify the table was created:
   ```sql
   SELECT * FROM user_api_keys LIMIT 1;
   ```

## Security Considerations

### Encryption (AES-256-GCM)

API keys are encrypted at rest using **AES-256-GCM** (Authenticated Encryption):

- **Algorithm**: AES-256-GCM provides both confidentiality and integrity
- **Key Derivation**: PBKDF2 with 100,000 iterations from master secret
- **Random IV**: Each encryption uses a unique 12-byte IV (prevents pattern analysis)
- **Backwards Compatible**: Unencrypted legacy data is handled gracefully
- **Prefix Marker**: Encrypted values start with `enc:` for easy identification

The encryption is implemented in `supabase/functions/_shared/crypto.ts` and is used by all Edge Functions that handle credentials.

#### Generating an Encryption Key

Use the Deno runtime or any secure random generator:

```typescript
// In Deno:
const key = crypto.getRandomValues(new Uint8Array(32));
console.log(btoa(String.fromCharCode(...key)));
```

Or use OpenSSL:
```bash
openssl rand -base64 32
```

#### Setting the Encryption Key

Set the `API_ENCRYPTION_KEY` secret in Supabase:

1. Go to Supabase Dashboard → Settings → Edge Functions
2. Add secret: `API_ENCRYPTION_KEY` = your generated key
3. Deploy Edge Functions to apply changes

**Important**: Without `API_ENCRYPTION_KEY`, credentials are stored unencrypted (backwards compatibility mode with warning logged).

### Row Level Security (RLS)
- Supabase RLS ensures users can only access their own keys
- Policies enforce user_email matching authenticated user
- No admin override needed - handled at database level

### Best Practices
- Users should enable 2FA on Alpaca account
- Users should rotate keys periodically
- Users should revoke compromised keys immediately
- App never logs API keys

## Environment Variables Needed

### Supabase Edge Function Secrets

Add to Supabase Dashboard → Settings → Edge Functions → Secrets:

```
# For API key encryption (generate with: openssl rand -base64 32)
API_ENCRYPTION_KEY = "<your-32-byte-base64-encoded-key>"

# Alpaca credentials (system fallback)
ALPACA_API_KEY = "<your-alpaca-api-key>"
ALPACA_SECRET_KEY = "<your-alpaca-secret-key>"
ALPACA_PAPER = "true"
```

### Client Environment Variables

Add to `.env` or environment:

```bash
VITE_SUPABASE_URL = "https://your-project.supabase.co"
VITE_SUPABASE_PUBLISHABLE_KEY = "your-anon-key"
```

## Next Steps

### Remaining Implementation Tasks:

1. **Create Onboarding Guide** (docs/ALPACA_ONBOARDING.md)
   - Step-by-step Alpaca account setup
   - Screenshots and tutorials
   - Common issues and troubleshooting

2. **Add Investment Disclaimers**
   - Legal disclaimer page
   - Risk warnings
   - User acceptance flow
   - Terms of service

3. **Implement Stripe Subscription**
   - Create Stripe products (Basic, Pro)
   - Payment flow
   - Subscription management
   - Webhook handling

4. **Feature Gating**
   - Enforce subscription checks
   - Show upgrade prompts
   - Disable features for non-paying users

## Testing Checklist

- [ ] Run database migration in Supabase
- [ ] Generate and set `API_ENCRYPTION_KEY`
- [ ] Create test Alpaca paper account
- [ ] Configure paper keys in Settings
- [ ] Test connection validation
- [ ] Verify keys are encrypted in database
- [ ] Test trading with paper keys
- [ ] Verify RLS (try accessing another user's keys - should fail)
- [ ] Test subscription gating for live trading

## Files Modified/Created

### New Files:
- `supabase/migrations/004_create_user_api_keys_table.sql` - Database schema
- `user_api_keys.py` - API key management class
- `scripts/run_migration.py` - Migration helper script
- `docs/USER_API_KEYS_IMPLEMENTATION.md` - This documentation

### Modified Files:
- `6_⚙️_Settings.py` - Added API key configuration UI
- `4_📈_Portfolio.py` - Uses user-specific keys
- `4.5_📋_Orders.py` - Uses user-specific keys
- `3_💼_Trading_Operations.py` - Uses user-specific keys with subscription gating

## Support

If users encounter issues:

1. **Keys not working**: Test connection in Settings
2. **Can't access live trading**: Check subscription status
3. **Keys compromised**: Revoke in Alpaca dashboard, generate new ones
4. **Lost access**: User can reset keys through Alpaca dashboard

## Future Enhancements

- Key rotation reminders (every 90 days)
- Read-only mode (for monitoring without trading)
- Multiple Alpaca account support
- Shared account management (family accounts)
- API key strength validator
- Usage analytics per user
