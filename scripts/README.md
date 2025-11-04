# Scripts Directory

Collection of utility scripts for the Politician Trading Tracker project.

## Secrets Management

### Copy Secrets to Streamlit Cloud (Recommended)

Instead of manually typing secrets, use this script to copy your local `.streamlit/secrets.toml` to clipboard:

```bash
./scripts/sync_secrets_to_streamlit.sh
```

Or:

```bash
./scripts/copy_secrets_for_streamlit.sh
```

This script will:
1. Copy your `.streamlit/secrets.toml` to clipboard
2. Show you the next steps to paste into Streamlit Cloud

**Then manually paste in Streamlit Cloud:**
1. Go to: https://share.streamlit.io/
2. Open your app settings → Secrets tab
3. Paste (Cmd+V) the clipboard contents
4. Save and restart your app

**Why not automatic?** The Streamlit CLI no longer has `streamlit login` or `streamlit secrets push` commands. The web interface is now the official way to manage secrets.

### Alternative: Python API Script

If you have a Streamlit Management API token:

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

**Note:** This uses an unofficial API and may break in future Streamlit updates.

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
