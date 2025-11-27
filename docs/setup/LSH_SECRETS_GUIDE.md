# LSH Secrets Management for Politician Trading Tracker

This guide explains how to use `lsh-framework` to manage secrets for the Politician Trading Tracker across your environment.

## What is lsh-framework?

[lsh-framework](https://www.npmjs.com/package/lsh-framework) is an encrypted secrets manager with:
- 🔐 Automatic encryption and rotation
- 👥 Team sync capabilities
- 🌍 Multi-environment support
- 🔄 CI/CD integration
- 📦 Cloud storage (Supabase)

## Installation

```bash
npm install -g lsh-framework
```

## Initial Setup

### 1. Initialize LSH Configuration

If this is your first time using lsh, initialize it:

```bash
lsh config --init
```

This will create `~/.lsh/config.json` with your configuration.

### 2. Push Politician Trading Secrets

Push the politician trading tracker environment to your encrypted cloud storage:

```bash
cd /path/to/politician-trading-tracker

# Push with environment name
lsh secrets push --environment politician-trading --file .env.politician-trading
```

### 3. Verify Upload

List all stored environments:

```bash
lsh secrets list
```

You should see `politician-trading` in the list.

## Using Secrets Across Machines

### Pull Secrets on Any Machine

```bash
# Navigate to your project
cd /path/to/politician-trading-tracker

# Pull the secrets
lsh secrets pull --environment politician-trading

# This creates/updates your .env file
```

### Show Secrets (Masked)

View secrets without exposing them:

```bash
lsh secrets show --environment politician-trading
```

### Get a Specific Secret

```bash
lsh secrets get ALPACA_API_KEY --environment politician-trading
```

### Set/Update a Secret

```bash
lsh secrets set TRADING_MIN_CONFIDENCE 0.70 --environment politician-trading
```

### Check Sync Status

See if your local .env is in sync with cloud:

```bash
lsh secrets sync --environment politician-trading
```

## Multiple Environments

You can create different environments for different purposes:

### Development Environment

```bash
# Create dev version
cp .env.politician-trading .env.politician-trading-dev

# Modify for development (e.g., lower confidence, paper trading)
# TRADING_MIN_CONFIDENCE=0.50
# ALPACA_PAPER=true

# Push to lsh
lsh secrets push --environment politician-trading-dev --file .env.politician-trading-dev
```

### Production Environment

```bash
# Push production config
lsh secrets push --environment politician-trading-prod --file .env.politician-trading
```

### Pull Specific Environment

```bash
# Pull dev
lsh secrets pull --environment politician-trading-dev --output .env

# Or pull prod
lsh secrets pull --environment politician-trading-prod --output .env
```

## Team Collaboration

### Share Secrets with Team

Your team members can pull the same secrets:

```bash
# Team member on another machine
lsh secrets pull --environment politician-trading
```

All secrets are encrypted in transit and at rest in Supabase.

### Access Control

Configure access in your lsh-framework settings:

```bash
lsh config --show
```

## Automation & CI/CD

### GitHub Actions

```yaml
name: Deploy with Secrets

on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install LSH
        run: npm install -g lsh-framework

      - name: Pull Secrets
        env:
          LSH_CONFIG: ${{ secrets.LSH_CONFIG }}
        run: |
          echo "$LSH_CONFIG" > ~/.lsh/config.json
          lsh secrets pull --environment politician-trading

      - name: Deploy
        run: streamlit run app.py
```

### Docker

```dockerfile
FROM python:3.11-slim

# Install lsh
RUN npm install -g lsh-framework

WORKDIR /app

# Copy config
COPY .lsh-config.json /root/.lsh/config.json

# Pull secrets at build time
RUN lsh secrets pull --environment politician-trading

# Copy app
COPY . .

# Install dependencies
RUN pip install -e .

# Run app
CMD ["streamlit", "run", "app.py"]
```

## Security Best Practices

### 1. Never Commit Secrets

The `.env` file is already in `.gitignore`:

```bash
# These should NEVER be committed
.env
.env.*
.env.politician-trading
~/.lsh/config.json
```

### 2. Use Environment-Specific Secrets

```bash
# Dev - safe defaults
lsh secrets push --environment dev

# Prod - real credentials, strict limits
lsh secrets push --environment prod
```

### 3. Rotate Secrets Regularly

```bash
# Update a secret
lsh secrets set ALPACA_SECRET_KEY new_key_here --environment politician-trading

# Push updated config
lsh secrets push --environment politician-trading
```

### 4. Monitor Access

Check who accessed secrets:

```bash
lsh secrets status --environment politician-trading
```

## Integration with Politician Trading Tracker

### Streamlit Cloud Deployment

When deploying to Streamlit Cloud, you have two options:

**Option 1: Use Streamlit Secrets** (Recommended for Streamlit Cloud)
```bash
# Generate Streamlit secrets format
lsh secrets show --environment politician-trading --format toml > .streamlit/secrets.toml

# Then copy contents to Streamlit Cloud dashboard
```

**Option 2: Use LSH in Streamlit**
```python
# In your Streamlit app
import subprocess
subprocess.run(["lsh", "secrets", "pull", "--environment", "politician-trading"])

# Then load .env
from dotenv import load_dotenv
load_dotenv()
```

### Local Development

```bash
# Pull latest secrets
lsh secrets pull --environment politician-trading

# Run the app
streamlit run app.py
```

### Testing Configuration

Test if secrets are properly loaded:

```bash
# After pulling secrets
python test_config.py
```

## Common Commands Cheat Sheet

```bash
# Push secrets
lsh secrets push --environment politician-trading

# Pull secrets
lsh secrets pull --environment politician-trading

# List environments
lsh secrets list

# Show secrets (masked)
lsh secrets show --environment politician-trading

# Get specific value
lsh secrets get SUPABASE_URL --environment politician-trading

# Update value
lsh secrets set TRADING_MIN_CONFIDENCE 0.75 --environment politician-trading

# Check sync status
lsh secrets sync --environment politician-trading

# Delete environment (careful!)
lsh secrets delete --environment politician-trading
```

## Troubleshooting

### LSH Not Connecting to Supabase

Ensure your lsh config has Supabase credentials:

```bash
lsh config --show
```

Check that `SUPABASE_URL` and `SUPABASE_KEY` are set in lsh config.

### Secrets Not Syncing

Force pull:

```bash
lsh secrets pull --environment politician-trading --force
```

### Can't See Environment

List all environments:

```bash
lsh secrets list
```

If empty, push again:

```bash
lsh secrets push --environment politician-trading --file .env.politician-trading
```

## Migration from .env to LSH

If you have an existing `.env` file:

```bash
# Backup current .env
cp .env .env.backup

# Push to lsh
lsh secrets push --environment politician-trading --file .env

# Delete local .env (it's now in encrypted cloud)
rm .env

# Pull from lsh to verify
lsh secrets pull --environment politician-trading
```

## Advanced: Daemon Scheduling

Schedule automatic secret rotation:

```bash
# Edit lsh daemon config
lsh config --init

# Add rotation schedule
# secrets_rotation_schedule: "0 2 * * 0"  # Weekly on Sunday 2 AM
```

## Support

- **LSH Framework**: https://www.npmjs.com/package/lsh-framework
- **GitHub**: https://github.com/gwicho38/lsh
- **Issues**: https://github.com/gwicho38/politician-trading-tracker/issues

## Summary

With lsh-framework, you can:
- ✅ Store all secrets encrypted in Supabase
- ✅ Share secrets securely with your team
- ✅ Sync secrets across all your machines
- ✅ Deploy with confidence (CI/CD integration)
- ✅ Rotate secrets automatically
- ✅ Never commit secrets to git again

Your secrets are now centrally managed and can be pulled on any machine with:

```bash
lsh secrets pull --environment politician-trading
```

That's it! 🚀
