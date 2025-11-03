# Streamlit Cloud Authentication Setup

## Quick Setup

Your app currently shows: **"Authentication system not properly configured"**

This is because the authentication secrets haven't been added to Streamlit Cloud yet.

### Steps to Enable Authentication:

1. **Go to your Streamlit Cloud app**
   - Visit: https://politician-trading-tracker.streamlit.app
   - Click **"Manage app"** (bottom right corner)

2. **Open Secrets**
   - In the settings, click on **"Secrets"** tab
   - You'll see a text editor

3. **Add Authentication Secrets**

   Copy and paste this into the secrets editor:

```toml
[auth]
enabled = true

[auth.cookie]
name = "politician_tracker_auth"
key = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_ABC123XYZ789"
expiry_days = 30

[auth.credentials.usernames.admin]
password = "$2b$12$i6N4VplxDfyetPplLkCDueBWFGmAZdA6TqXrYB7QUSn0zomhj9VFS"
name = "Administrator"
email = "admin@example.com"
```

4. **Generate a New Cookie Key (Important!)**

   Replace the `key` value with a random secret. Run this locally:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Or use this online: https://generate-secret.now.sh/32

5. **Save and Deploy**
   - Click **"Save"**
   - Streamlit Cloud will automatically rebuild your app
   - Wait 2-3 minutes for deployment

### Default Login Credentials

After setup, you can log in with:

```
Username: admin
Password: demo123
```

### To Change the Password

1. Run locally:
   ```bash
   python scripts/generate_password_hash.py your_new_password
   ```

2. Copy the hash output

3. Update the `password` field in Streamlit Cloud secrets

4. Save and redeploy

### Adding More Users

In the Streamlit Cloud secrets editor, add:

```toml
[auth.credentials.usernames.john]
password = "$2b$12$HASH_GOES_HERE"
name = "John Doe"
email = "john@example.com"
```

## Security Notes

- ✅ Passwords are hashed with bcrypt
- ✅ Sessions expire after 30 days
- ✅ All pages require authentication
- ⚠️ Change the default admin password!
- ⚠️ Use a unique cookie key!

## Troubleshooting

### "Running without authentication"
- Secrets not added yet → Add them in Streamlit Cloud
- App still deploying → Wait a few minutes
- Syntax error in secrets → Check TOML formatting

### Can't log in
- Wrong username/password → Use admin/demo123
- Password hash wrong → Regenerate using the script
- Clear browser cookies → Try incognito mode

### Icons not showing in sidebar
- App still deploying → Wait for Streamlit Cloud to rebuild
- Clear browser cache → Hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)
- Check that emoji is in page_title for each page file

## Next Steps

After authentication is working:

1. Change the default admin password
2. Add your own users
3. Generate a unique cookie key
4. Enjoy secure access to your politician trading tracker!

---

**Need help?** Check the logs in Streamlit Cloud → Manage app → "⋮" menu → View logs
