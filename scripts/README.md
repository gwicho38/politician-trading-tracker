# Scripts Directory

Collection of utility scripts for the Politician Trading Tracker project.

## Secrets Management

### Push Secrets to Streamlit Cloud

Instead of manually copy-pasting secrets, use these scripts to automatically sync your local `.streamlit/secrets.toml` to Streamlit Cloud:

#### Method 1: Using Shell Script (Recommended)

```bash
./scripts/sync_secrets_to_streamlit.sh
```

This script will:
1. Check if you're logged in to Streamlit Cloud
2. Show you what will be pushed
3. Ask for confirmation
4. Push secrets using the official Streamlit CLI

**First-time setup:**
```bash
# Install Streamlit CLI (if not already installed)
pip install streamlit

# Login to Streamlit Cloud
streamlit login

# Push secrets
./scripts/sync_secrets_to_streamlit.sh
```

#### Method 2: Using Python Script

```bash
python scripts/push_secrets_to_streamlit.py
```

**Prerequisites:**
```bash
# Get your API token from: https://share.streamlit.io/settings/tokens
export STREAMLIT_API_TOKEN="your-token-here"

# Or store securely with lsh
lsh secrets set STREAMLIT_API_TOKEN "your-token-here"
```

#### Method 3: One-liner with Streamlit CLI

If you're already logged in:

```bash
streamlit secrets push politician-trading-tracker .streamlit/secrets.toml
```

Replace `politician-trading-tracker` with your actual app name.

---

## Data Collection Scripts

### Run QuiverQuant Pipeline

Fetch and import congressional trading data from QuiverQuant:

```bash
uv run python scripts/run_quiverquant_pipeline.py
```

**Prerequisites:**
```bash
# Set QuiverQuant API key
lsh secrets set QUIVERQUANT_API_KEY "your-api-key"
```

### Debug Cleaning Stage

Debug why records are being filtered during the cleaning stage:

```bash
uv run python scripts/debug_cleaning.py
```

---

## Database Scripts

### Seed Database

Populate the database with initial data:

```bash
politician-trading-seed
```

### Database Setup

Run database migrations and setup:

```bash
python scripts/setup_database.py
```

---

## Testing Scripts

### Test PDF Parser

Test the PDF parsing functionality:

```bash
python test_pdf_parser.py
```

### Test Pipeline End-to-End

Test the complete data pipeline:

```bash
python test_pipeline_e2e.py
```

### Test US Senate Source

Test the US Senate scraper:

```bash
python test_us_senate_source.py
```

---

## Development Scripts

### Copy Secrets to Clipboard

Copy secrets to clipboard for quick access:

```bash
./scripts/copy_secrets_to_clipboard.sh
```

---

## Notes

- Always test scripts in a development environment first
- Keep secrets secure and never commit them to version control
- Use `lsh-framework` for secure secret storage
- Check script prerequisites before running
