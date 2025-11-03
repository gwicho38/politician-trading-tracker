# Google OAuth Setup Guide

This guide walks you through setting up Google OAuth authentication for the Politician Trading Tracker app.

## Why Google OAuth?

- ✅ **Secure**: No passwords to manage or store
- ✅ **Simple**: Users log in with their existing Google account
- ✅ **Native**: Built into Streamlit - no extra dependencies
- ✅ **Modern**: Industry-standard OAuth 2.0 / OpenID Connect

## Prerequisites

- Google Cloud account
- Your app deployed (or running locally)

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project name/ID

## Step 2: Enable OAuth APIs

1. Navigate to **APIs & Services** > **Library**
2. Search for and enable:
   - **Google+ API** (for user profile information)
   - **OpenID Connect** (should be enabled by default)

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type (unless you have Google Workspace)
3. Fill in required fields:
   - **App name**: `Politician Trading Tracker`
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **Save and Continue**

### Scopes (Step 2 of consent screen)
Add these scopes:
- `openid`
- `email`
- `profile`

These are automatically included - no need to add manually.

5. Click **Save and Continue** through remaining steps

## Step 4: Create OAuth Client

1. Go to **APIs & Services** > **Credentials**
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
3. Choose **Web application**
4. Configure:
   - **Name**: `Politician Trading Tracker`
   - **Authorized JavaScript origins**:
     - For local: `http://localhost:8501`
     - For Streamlit Cloud: `https://your-app-name.streamlit.app`
   - **Authorized redirect URIs**:
     - For local: `http://localhost:8501/oauth2callback`
     - For Streamlit Cloud: `https://your-app-name.streamlit.app/oauth2callback`

5. Click **Create**
6. **IMPORTANT**: Copy your **Client ID** and **Client Secret** immediately

## Step 5: Generate Cookie Secret

Run this command to generate a secure random secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output - you'll need this for your secrets file.

## Step 6: Configure Secrets

### For Local Development

1. Create or edit `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "YOUR_GENERATED_SECRET_HERE"
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

2. Replace:
   - `YOUR_GENERATED_SECRET_HERE` with the output from Step 5
   - `YOUR_CLIENT_ID` with your Google OAuth Client ID
   - `YOUR_CLIENT_SECRET` with your Google OAuth Client Secret

### For Streamlit Cloud

1. Go to your app settings on Streamlit Cloud
2. Navigate to **Secrets**
3. Paste the same TOML configuration, but update `redirect_uri`:

```toml
[auth]
redirect_uri = "https://your-app-name.streamlit.app/oauth2callback"
cookie_secret = "YOUR_GENERATED_SECRET_HERE"
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

4. Save secrets

## Step 7: Test Authentication

### Local Testing

1. Make sure secrets are configured in `.streamlit/secrets.toml`
2. Start your app: `streamlit run app.py`
3. Navigate to `http://localhost:8501`
4. Click "Log in with Google"
5. Authenticate with your Google account
6. You should be redirected back and logged in

### Streamlit Cloud Testing

1. Push your changes to GitHub
2. Streamlit Cloud will auto-deploy
3. Navigate to your app URL
4. Test the same OAuth flow

## Troubleshooting

### "Error 400: redirect_uri_mismatch"

**Problem**: The redirect URI doesn't match what's configured in Google Cloud.

**Solution**:
1. Check the redirect URI in your error message
2. Go to Google Cloud Console > Credentials
3. Edit your OAuth client
4. Add the EXACT redirect URI to **Authorized redirect URIs**
5. Save and try again (may take a few minutes to propagate)

### "Authentication not working locally"

**Problem**: Secrets file not found or misconfigured.

**Solution**:
1. Ensure `.streamlit/secrets.toml` exists in your project root
2. Check file permissions (should be readable)
3. Verify TOML syntax (no typos in brackets or keys)
4. Restart Streamlit after changing secrets

### "Cookie errors"

**Problem**: Cookie secret is weak or missing.

**Solution**:
1. Generate a new cookie secret using the command in Step 5
2. Use a strong random secret (not "test" or "password")
3. Make sure it's at least 32 characters

### "Access blocked: This app's request is invalid"

**Problem**: OAuth consent screen not properly configured.

**Solution**:
1. Go back to OAuth consent screen settings
2. Make sure all required fields are filled
3. Add test users if your app is in "Testing" mode
4. Try publishing your consent screen if appropriate

## Security Best Practices

1. **Never commit secrets**: Add `.streamlit/secrets.toml` to `.gitignore`
2. **Use strong secrets**: Always generate random cookie secrets
3. **Rotate secrets**: Change your OAuth credentials periodically
4. **Limit redirect URIs**: Only add the exact URIs you need
5. **Monitor usage**: Check Google Cloud Console for OAuth activity

## Additional Resources

- [Streamlit Authentication Docs](https://docs.streamlit.io/develop/concepts/connections/authentication)
- [Google OAuth 2.0 Docs](https://developers.google.com/identity/protocols/oauth2)
- [OpenID Connect Docs](https://openid.net/connect/)

## Getting Help

If you're still having issues:
1. Check the Streamlit app logs
2. Review Google Cloud Console error messages
3. File an issue on the project GitHub
