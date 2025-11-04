# Google OAuth Setup for Streamlit

## Problem

The OAuth redirect was pointing to `localhost` even in production, causing authentication failures on Streamlit Cloud.

## Solution

### 1. Remove Hardcoded redirect_uri

Streamlit automatically determines the correct redirect URI based on the environment:
- **Local**: `http://localhost:8501/oauth2callback`
- **Production**: `https://your-app.streamlit.app/oauth2callback`

We've removed the hardcoded `redirect_uri` from `.streamlit/secrets.toml` to let Streamlit handle this automatically.

### 2. Configure Google Cloud Console

You need to add BOTH redirect URIs to your Google OAuth client:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Find your OAuth 2.0 Client ID: `293495132387-vnt9dv1u1la8jgb4oaelfpncnj2scf7k.apps.googleusercontent.com`
4. Click **Edit** on the client
5. Under **Authorized redirect URIs**, add BOTH:
   ```
   http://localhost:8501/oauth2callback
   https://politician-trading-tracker.streamlit.app/oauth2callback
   ```

   Replace `politician-trading-tracker.streamlit.app` with your actual Streamlit Cloud app URL.

6. Click **Save**

### 3. Find Your Streamlit Cloud App URL

If you're not sure of your exact app URL:

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Find your app in the list
3. Click on it to open
4. Copy the URL from your browser
5. Use that URL + `/oauth2callback` as the redirect URI

Example URLs:
- `https://politician-trading-tracker.streamlit.app/oauth2callback`
- `https://gwicho38-politician-trading-tracker-app-xyz123.streamlit.app/oauth2callback`

### 4. Update Streamlit Cloud Secrets

After updating the secrets.toml locally:

1. Run the sync script:
   ```bash
   ./scripts/sync_secrets_to_streamlit.sh
   ```

2. Or manually:
   - Go to Streamlit Cloud dashboard
   - Click ⚙️ Settings on your app
   - Navigate to "Secrets" tab
   - Paste the updated secrets
   - Click "Save"
   - Restart your app

### 5. Verify the Setup

1. Go to your Streamlit Cloud app
2. Try to log in with Google
3. You should be redirected to Google's consent screen
4. After approving, you should be redirected back to your app (not localhost!)

## Troubleshooting

### "Redirect URI mismatch" Error

If you see this error, it means:
- The redirect URI used by your app doesn't match what's configured in Google Cloud Console
- **Solution**: Add the exact redirect URI shown in the error to Google Cloud Console

### Still Redirecting to Localhost

If the app still redirects to localhost:
1. Make sure you've updated secrets on Streamlit Cloud (not just locally)
2. Restart your Streamlit Cloud app
3. Clear your browser cache and cookies
4. Try in an incognito window

### Can't Access Google Cloud Console

If you don't have access to the Google Cloud project:
1. You may need to create your own OAuth client
2. Follow [Streamlit's OAuth guide](https://docs.streamlit.io/develop/concepts/authentication)
3. Update the `client_id` and `client_secret` in secrets

## Current Configuration

**Client ID**: `293495132387-vnt9dv1u1la8jgb4oaelfpncnj2scf7k.apps.googleusercontent.com`

**Required Redirect URIs**:
- `http://localhost:8501/oauth2callback` (for local development)
- `https://politician-trading-tracker.streamlit.app/oauth2callback` (for production)

## Security Notes

- Never commit secrets to git
- Keep `client_secret` secure
- The OAuth client should restrict access to specific domains
- Consider using environment-specific OAuth clients for production vs development
