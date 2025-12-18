# Capitol Trades - Python Integration

This folder contains Python code to sync data from your scraper/processor to the Supabase database used by the React frontend.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export SUPABASE_URL="https://ogdwavsrcyleoxfsswbt.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

### 3. Use in your code

```python
from supabase_sync import CapitolTradesSync

sync = CapitolTradesSync()

# Sync a complete filing
sync.sync_filing({
    "politician": {
        "name": "Nancy Pelosi",
        "party": "D",
        "chamber": "House",
        "jurisdiction_id": "us-house",
        "state": "CA"
    },
    "trades": [
        {
            "ticker": "NVDA",
            "company": "NVIDIA Corporation",
            "type": "buy",
            "amount_range": "$500,001 - $1,000,000",
            "estimated_value": 750000,
            "filing_date": "2024-01-15",
            "transaction_date": "2024-01-10"
        }
    ]
})

# Recalculate all stats
sync.full_sync()
```

## Files

| File | Description |
|------|-------------|
| `supabase_sync.py` | Main sync module with all database operations |
| `streamlit_sync_page.py` | Ready-to-use Streamlit page for manual data management |
| `requirements.txt` | Python dependencies |

## Streamlit Integration

Add to your existing Streamlit app:

```python
# In your main app
from streamlit_sync_page import render_sync_page

# Add as a page
st.sidebar.page_link("pages/sync.py", label="Data Sync")

# Or render directly
render_sync_page()
```

Or run standalone:

```bash
streamlit run streamlit_sync_page.py
```

## Fly.io Deployment

Add to your `fly.toml`:

```toml
[env]
  SUPABASE_URL = "https://ogdwavsrcyleoxfsswbt.supabase.co"
```

Set the secret:

```bash
fly secrets set SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

## Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Python Scraper │────▶│    Supabase     │◀────│  React Frontend │
│   (Fly.io)      │     │   (Database)    │     │   (Lovable)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │   supabase-py         │    @supabase/js       │
        │   (write data)        │    (read data)        │
        └───────────────────────┴───────────────────────┘
```

## Getting the Service Role Key

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/ogdwavsrcyleoxfsswbt/settings/api)
2. Navigate to Settings → API
3. Copy the `service_role` key (keep this secret!)

> ⚠️ **Security**: The service role key bypasses RLS. Never expose it in client-side code.
