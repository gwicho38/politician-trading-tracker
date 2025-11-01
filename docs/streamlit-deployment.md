# Streamlit Cloud Deployment Guide

Complete guide for deploying the Politician Trading Tracker to Streamlit Cloud.

## Quick Deployment

### 1. Push Code to GitHub

```bash
# Make sure all changes are committed
git status

# Push to GitHub
git push origin main
```

### 2. Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click **"New app"**
3. Select your repository: `gwicho38/politician-trading-tracker`
4. Set the main file path: `app.py`
5. Click **"Deploy"**

### 3. Add Secrets (Automated)

The easiest way to add secrets is using our automated script:

```bash
# This script copies your secrets to clipboard
./scripts/copy_secrets_to_clipboard.sh
```

Then:
1. Go to your app on Streamlit Cloud
2. Click the **"⋮"** menu → **"Settings"**
3. Go to **"Secrets"** tab
4. Paste (Cmd+V / Ctrl+V)
5. Click **"Save"**
6. App automatically redeploys with secrets

**That's it!** Your app is now live with all secrets configured.

## Secrets Management

### Option 1: Automated (Recommended)

Use the clipboard script for one-command secret syncing:

```bash
# Copy secrets to clipboard
./scripts/copy_secrets_to_clipboard.sh

# Output:
# ✅ Secrets copied to clipboard!
# 📋 Next steps: [instructions for pasting to Streamlit Cloud]
```

### Option 2: Manual Generation

Generate the secrets file and copy manually:

```bash
# Generate .streamlit/secrets.toml from .env
python3 scripts/sync_secrets_to_streamlit.py

# View the generated file
cat .streamlit/secrets.toml

# Copy to clipboard manually (macOS)
cat .streamlit/secrets.toml | pbcopy
```

### Option 3: Direct Entry

Manually add secrets one by one in Streamlit Cloud web interface:

1. Go to app Settings → Secrets
2. Enter in TOML format:
   ```toml
   SUPABASE_URL = "your-url"
   SUPABASE_ANON_KEY = "your-key"
   # ... etc
   ```

## Required Secrets

### Essential (Required for app to start)

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
SUPABASE_SERVICE_KEY = "your-service-key"  # For admin operations
```

### Trading (Required for Trading Operations)

```toml
ALPACA_API_KEY = "your-alpaca-api-key"
ALPACA_SECRET_KEY = "your-alpaca-secret"
ALPACA_PAPER = "true"  # Use paper trading
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
```

### Optional (Enhanced Features)

```toml
# UK Companies House API (for UK data)
UK_COMPANIES_HOUSE_API_KEY = "your-key"

# Trading Configuration
TRADING_MIN_CONFIDENCE = "0.65"
TRADING_AUTO_EXECUTE = "false"

# Risk Management
RISK_MAX_POSITION_SIZE_PCT = "10.0"
RISK_MAX_PORTFOLIO_RISK_PCT = "2.0"
RISK_MAX_TOTAL_EXPOSURE_PCT = "80.0"
RISK_MAX_POSITION = "20"

# Scraping Configuration
SCRAPING_DELAY = "1.0"
MAX_RETRIES = "3"
TIMEOUT = "30"

# Feature Flags
ENABLE_US_CONGRESS = "true"
ENABLE_UK_PARLIAMENT = "false"
ENABLE_EU_PARLIAMENT = "false"
ENABLE_US_STATE = "false"
ENABLE_CALIFORNIA = "false"
ENABLE_MONITORING = "true"

# Logging
LOG_LEVEL = "INFO"
```

## Updating Secrets

When you update secrets in your `.env` file:

```bash
# 1. Update .env with new values
vim .env

# 2. Re-sync to secrets.toml and copy to clipboard
./scripts/copy_secrets_to_clipboard.sh

# 3. Paste into Streamlit Cloud (replaces all secrets)
# 4. Save - app auto-redeploys
```

## Deployment Configuration

### App Settings

**Main file path:** `app.py`
**Python version:** 3.10+ (automatic)
**Package manager:** pip (uses pyproject.toml)

### Custom Domain (Optional)

If you have a custom domain:

1. Go to app Settings → General
2. Enter your custom domain
3. Follow DNS configuration instructions
4. Verify and save

### Resource Limits

**Streamlit Cloud Free Tier:**
- 1 GB RAM
- 1 CPU core
- Always-on (doesn't sleep)
- Perfect for this app

**Streamlit Cloud Teams:**
- More resources
- Multiple apps
- Private apps
- Priority support

## Scheduled Jobs on Streamlit Cloud

The in-app scheduler works perfectly on Streamlit Cloud:

1. **Automatic startup**: Scheduler starts when app deploys
2. **Always running**: Streamlit Cloud keeps apps running 24/7
3. **No configuration needed**: Jobs run as configured in the UI

### Setting Up Scheduled Jobs

After deployment:

1. Navigate to **⏰ Scheduled Jobs** in the sidebar
2. Create your jobs (e.g., daily data collection)
3. Jobs will run automatically on schedule

See [In-App Scheduling Guide](./in-app-scheduling.md) for details.

## Monitoring

### App Logs

View app logs in Streamlit Cloud:

1. Go to your app
2. Click **"Manage app"** (bottom right)
3. View logs in real-time

### Application Logs

The app writes detailed logs to `logs/latest.log`, but these are not persistent on Streamlit Cloud (ephemeral filesystem).

**For persistent logging:**
- Use an external logging service (Papertrail, Loggly, etc.)
- Or implement database logging
- Or use Streamlit Cloud's log viewer

### Job Monitoring

Monitor scheduled jobs via the UI:

1. Go to **⏰ Scheduled Jobs**
2. Check **📊 Job History** tab
3. View success/failure status

## Troubleshooting

### App Won't Start

**Check secrets:**
1. Verify all required secrets are set
2. Ensure no typos in secret names
3. Check values are properly quoted in TOML format

**Check logs:**
- View app logs in Streamlit Cloud
- Look for import errors or missing dependencies

### Secrets Not Loading

**Check format:**
```toml
# Correct ✅
SUPABASE_URL = "https://your-project.supabase.co"

# Incorrect ❌
SUPABASE_URL: https://your-project.supabase.co  # Wrong syntax
```

**Regenerate:**
```bash
# Delete and regenerate
rm .streamlit/secrets.toml
python3 scripts/sync_secrets_to_streamlit.py
```

### Scheduled Jobs Not Running

1. **Check scheduler status**: Go to ⏰ Scheduled Jobs page
2. **Verify jobs are active**: Not paused
3. **Check app logs**: Look for scheduler errors
4. **Test manually**: Use "Run Now" button

### Dependencies Not Installing

**Check pyproject.toml:**
- All dependencies listed
- Correct version constraints
- No conflicting versions

**Force rebuild:**
1. Go to app Settings
2. Click "Reboot app"
3. Or make a dummy commit to trigger redeploy

## Performance Optimization

### Caching

The app uses Streamlit caching extensively:
- Database queries are cached
- Data processing is cached
- API calls are cached

### Resource Usage

Monitor resource usage:
- Check app logs for memory warnings
- Optimize heavy computations
- Use pagination for large datasets

### Speed Tips

1. **Minimize data queries**: Cache aggressively
2. **Lazy load data**: Only fetch what's needed
3. **Use pagination**: Don't load all data at once
4. **Optimize images**: Compress if using images

## Security Best Practices

### Secrets

✅ **DO:**
- Use the automated scripts (gitignored)
- Rotate secrets regularly
- Use paper trading (not live keys) for testing
- Review secrets.toml before pasting

❌ **DON'T:**
- Commit secrets.toml to git (already gitignored)
- Share secrets in chat/email
- Use production API keys for testing
- Expose secrets in logs

### API Keys

- **Supabase**: Use RLS (Row Level Security)
- **Alpaca**: Use paper trading keys for testing
- **External APIs**: Rotate regularly

### Access Control

- Keep GitHub repo private if using sensitive data
- Use Streamlit Cloud Teams for private apps
- Implement proper authentication if needed

## Continuous Deployment

### Automatic Deploys

Streamlit Cloud auto-deploys when you push to main:

```bash
git add .
git commit -m "Update feature"
git push origin main

# Streamlit Cloud automatically:
# 1. Detects the push
# 2. Rebuilds the app
# 3. Deploys new version
# 4. No downtime
```

### Manual Reboot

Force a restart without code changes:

1. Go to app Settings
2. Click "Reboot app"
3. App restarts with same code

### Rollback

To rollback to a previous version:

```bash
# Find the commit to rollback to
git log --oneline

# Reset to that commit
git reset --hard <commit-hash>

# Force push (be careful!)
git push origin main --force

# Or create a revert commit (safer)
git revert <commit-hash>
git push origin main
```

## Support

### Streamlit Cloud Issues

- Streamlit Community Forum: https://discuss.streamlit.io/
- Streamlit Docs: https://docs.streamlit.io/
- Status Page: https://streamlitstatus.com/

### App-Specific Issues

- Check logs in Streamlit Cloud
- Review app logs in `logs/latest.log`
- Check GitHub Issues
- Review documentation in `docs/`

## Quick Reference

### Deploy New App
```bash
git push origin main
# Go to share.streamlit.io → New app → Select repo → Deploy
./scripts/copy_secrets_to_clipboard.sh
# Paste secrets in Streamlit Cloud → Save
```

### Update Secrets
```bash
vim .env
./scripts/copy_secrets_to_clipboard.sh
# Paste into Streamlit Cloud → Save
```

### Update App
```bash
git add .
git commit -m "Update"
git push origin main
# Auto-deploys
```

### Monitor Jobs
```
Navigate to: ⏰ Scheduled Jobs → 📊 Job History
```

## Next Steps

After deployment:

1. ✅ Verify app loads correctly
2. ✅ Test database connection
3. ✅ Set up scheduled jobs
4. ✅ Test data collection
5. ✅ Configure trading (if using)
6. ✅ Monitor logs
7. ✅ Share with users

Your app is now live and fully automated! 🎉
