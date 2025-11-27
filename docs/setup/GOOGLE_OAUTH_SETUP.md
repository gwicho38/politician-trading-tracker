# Google OAuth Setup Guide

## Current Status ✅

**Good news!** You already have Google OAuth credentials configured in `.streamlit/secrets.toml`:
- Client ID: `293495132387-vnt9dv1u1la8jgb4oaelfpncnj2scf7k.apps.googleusercontent.com`
- Client Secret: Configured ✅

## The Fix

The Admin page was checking `os.getenv("GOOGLE_CLIENT_ID")` but your credentials are in `st.secrets["auth"]["client_id"]`.

**I've fixed this!** The Admin page now checks both locations.

## Verify It Works

1. Restart your Streamlit app
2. Go to **Admin** → **System Info** tab  
3. You should now see: ✅ `GOOGLE_CLIENT_ID: 29349513...f7k`

## When You Need New Google OAuth Credentials

You'll need to create new credentials for:
- Production deployment (Streamlit Cloud, Fly.io)
- Separate dev/staging/prod environments
- If current credentials are compromised

## Quick Setup Steps

### 1. Google Cloud Console
https://console.cloud.google.com/ → Create Project

### 2. Enable APIs
- Google+ API
- People API

### 3. OAuth Consent Screen
- External or Internal
- Add scopes: openid, email, profile

### 4. Create OAuth Client
- Web application
- Add redirect URIs:
  - `http://localhost:8501/oauth2callback` (dev)
  - `https://your-app.streamlit.app/oauth2callback` (prod)

### 5. Update secrets.toml

```toml
[auth]
client_id = "YOUR-ID.apps.googleusercontent.com"
client_secret = "GOCSPX-YOUR-SECRET"
redirect_uri = "http://localhost:8501/oauth2callback"
```

Generate cookie key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `redirect_uri_mismatch` | Add exact URI to Google Cloud Console |
| `access_denied` | Add user to test users or publish app |
| `invalid_client` | Check client_id and client_secret are correct |

## Resources

- Google Cloud Console: https://console.cloud.google.com/
- OAuth 2.0 Docs: https://developers.google.com/identity/protocols/oauth2
