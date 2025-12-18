# Python/Fly.io Integration Guide

This document explains how to integrate your Python application with the CapitolTrades Supabase database.

## Installation

```bash
pip install supabase
```

## Configuration

Add these environment variables to your Fly.io app:

```bash
fly secrets set SUPABASE_URL="https://ogdwavsrcyleoxfsswbt.supabase.co"
fly secrets set SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

> **Important**: Use the service role key (not anon key) to bypass RLS for data sync operations.

## Python Client Setup

```python
import os
from supabase import create_client, Client
from datetime import datetime
from typing import Optional, List, Dict, Any

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ogdwavsrcyleoxfsswbt.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
```

## Data Models

### Politicians

```python
def upsert_politician(
    name: str,
    party: str,  # 'D', 'R', 'I', or 'Other'
    chamber: str,  # e.g., 'House', 'Senate'
    jurisdiction_id: str,  # e.g., 'us-house', 'us-senate'
    state: Optional[str] = None,
    avatar_url: Optional[str] = None,
    total_trades: int = 0,
    total_volume: int = 0
) -> Dict[str, Any]:
    """
    Insert or update a politician record.
    Returns the upserted record.
    """
    data = {
        "name": name,
        "party": party,
        "chamber": chamber,
        "jurisdiction_id": jurisdiction_id,
        "state": state,
        "avatar_url": avatar_url,
        "total_trades": total_trades,
        "total_volume": total_volume,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Check if politician exists by name
    existing = supabase.table("politicians").select("id").eq("name", name).execute()
    
    if existing.data:
        # Update existing
        result = supabase.table("politicians").update(data).eq("id", existing.data[0]["id"]).execute()
    else:
        # Insert new
        result = supabase.table("politicians").insert(data).execute()
    
    return result.data[0] if result.data else None
```

### Trades

```python
def insert_trade(
    politician_id: str,
    ticker: str,
    company: str,
    trade_type: str,  # 'buy' or 'sell'
    amount_range: str,  # e.g., '$1,001 - $15,000'
    estimated_value: int,
    filing_date: str,  # 'YYYY-MM-DD'
    transaction_date: str  # 'YYYY-MM-DD'
) -> Dict[str, Any]:
    """
    Insert a new trade record.
    """
    data = {
        "politician_id": politician_id,
        "ticker": ticker,
        "company": company,
        "trade_type": trade_type.lower(),  # Must be lowercase
        "amount_range": amount_range,
        "estimated_value": estimated_value,
        "filing_date": filing_date,
        "transaction_date": transaction_date
    }
    
    result = supabase.table("trades").insert(data).execute()
    return result.data[0] if result.data else None


def bulk_insert_trades(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Insert multiple trades at once.
    """
    # Ensure trade_type is lowercase
    for trade in trades:
        trade["trade_type"] = trade["trade_type"].lower()
    
    result = supabase.table("trades").insert(trades).execute()
    return result.data
```

### Jurisdictions

```python
def upsert_jurisdiction(
    id: str,  # e.g., 'us-house', 'eu-parliament'
    name: str,
    flag: str  # Emoji flag, e.g., '🇺🇸'
) -> Dict[str, Any]:
    """
    Insert or update a jurisdiction.
    """
    data = {
        "id": id,
        "name": name,
        "flag": flag
    }
    
    result = supabase.table("jurisdictions").upsert(data).execute()
    return result.data[0] if result.data else None
```

### Chart Data (Monthly Aggregates)

```python
def upsert_chart_data(
    year: int,
    month: str,  # e.g., 'Jan', 'Feb'
    buys: int,
    sells: int,
    volume: int
) -> Dict[str, Any]:
    """
    Insert or update monthly chart data.
    """
    data = {
        "year": year,
        "month": month,
        "buys": buys,
        "sells": sells,
        "volume": volume
    }
    
    # Check if exists
    existing = supabase.table("chart_data").select("id").eq("year", year).eq("month", month).execute()
    
    if existing.data:
        result = supabase.table("chart_data").update(data).eq("id", existing.data[0]["id"]).execute()
    else:
        result = supabase.table("chart_data").insert(data).execute()
    
    return result.data[0] if result.data else None
```

### Dashboard Stats

```python
def update_dashboard_stats(
    total_trades: int,
    total_volume: int,
    active_politicians: int,
    jurisdictions_tracked: int,
    average_trade_size: int,
    recent_filings: int
) -> Dict[str, Any]:
    """
    Update the dashboard statistics.
    """
    data = {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "active_politicians": active_politicians,
        "jurisdictions_tracked": jurisdictions_tracked,
        "average_trade_size": average_trade_size,
        "recent_filings": recent_filings,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Get existing stats record or create one
    existing = supabase.table("dashboard_stats").select("id").limit(1).execute()
    
    if existing.data:
        result = supabase.table("dashboard_stats").update(data).eq("id", existing.data[0]["id"]).execute()
    else:
        result = supabase.table("dashboard_stats").insert(data).execute()
    
    return result.data[0] if result.data else None
```

### Notifications

```python
def create_notification(
    title: str,
    message: str,
    notification_type: str = "info",  # 'info', 'success', 'warning', 'error'
    user_id: Optional[str] = None  # None for global notifications
) -> Dict[str, Any]:
    """
    Create a notification visible to all users or a specific user.
    """
    data = {
        "title": title,
        "message": message,
        "type": notification_type,
        "user_id": user_id,
        "read": False
    }
    
    result = supabase.table("notifications").insert(data).execute()
    return result.data[0] if result.data else None
```

## Complete Sync Example

```python
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import random

# Initialize
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ogdwavsrcyleoxfsswbt.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def sync_politician_trades(scraped_data: dict):
    """
    Main sync function - call this from your Streamlit app or scraper.
    
    Expected scraped_data format:
    {
        "politician": {
            "name": "Nancy Pelosi",
            "party": "D",
            "chamber": "House",
            "state": "CA"
        },
        "trades": [
            {
                "ticker": "NVDA",
                "company": "NVIDIA Corporation",
                "type": "buy",
                "amount": "$500,001 - $1,000,000",
                "estimated_value": 750000,
                "filing_date": "2024-01-15",
                "transaction_date": "2024-01-10"
            }
        ]
    }
    """
    # Upsert politician
    politician = upsert_politician(
        name=scraped_data["politician"]["name"],
        party=scraped_data["politician"]["party"],
        chamber=scraped_data["politician"]["chamber"],
        jurisdiction_id="us-house",  # or determine from chamber
        state=scraped_data["politician"].get("state")
    )
    
    if not politician:
        print(f"Failed to upsert politician: {scraped_data['politician']['name']}")
        return
    
    # Insert trades
    for trade in scraped_data["trades"]:
        insert_trade(
            politician_id=politician["id"],
            ticker=trade["ticker"],
            company=trade["company"],
            trade_type=trade["type"],
            amount_range=trade["amount"],
            estimated_value=trade["estimated_value"],
            filing_date=trade["filing_date"],
            transaction_date=trade["transaction_date"]
        )
    
    # Update politician totals
    update_politician_totals(politician["id"])
    
    # Update dashboard stats
    recalculate_dashboard_stats()
    
    # Create notification
    create_notification(
        title="New Filing",
        message=f"{scraped_data['politician']['name']} filed {len(scraped_data['trades'])} new trade(s)",
        notification_type="info"
    )


def update_politician_totals(politician_id: str):
    """
    Recalculate a politician's total trades and volume.
    """
    trades = supabase.table("trades").select("estimated_value").eq("politician_id", politician_id).execute()
    
    if trades.data:
        total_trades = len(trades.data)
        total_volume = sum(t["estimated_value"] for t in trades.data)
        
        supabase.table("politicians").update({
            "total_trades": total_trades,
            "total_volume": total_volume,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", politician_id).execute()


def recalculate_dashboard_stats():
    """
    Recalculate all dashboard statistics from the data.
    """
    # Get counts
    politicians = supabase.table("politicians").select("id", count="exact").execute()
    trades = supabase.table("trades").select("estimated_value").execute()
    jurisdictions = supabase.table("jurisdictions").select("id", count="exact").execute()
    
    # Recent filings (last 7 days)
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = supabase.table("trades").select("id", count="exact").gte("filing_date", week_ago).execute()
    
    total_volume = sum(t["estimated_value"] for t in trades.data) if trades.data else 0
    total_trades = len(trades.data) if trades.data else 0
    avg_trade_size = total_volume // total_trades if total_trades > 0 else 0
    
    update_dashboard_stats(
        total_trades=total_trades,
        total_volume=total_volume,
        active_politicians=politicians.count or 0,
        jurisdictions_tracked=jurisdictions.count or 0,
        average_trade_size=avg_trade_size,
        recent_filings=recent.count or 0
    )
```

## Streamlit Integration Example

```python
import streamlit as st
from supabase_sync import sync_politician_trades, recalculate_dashboard_stats

st.title("Capitol Trades Data Sync")

# Manual sync button
if st.button("Sync Latest Data"):
    with st.spinner("Syncing..."):
        # Your scraping logic here
        scraped_data = scrape_latest_filings()  # Your function
        
        for filing in scraped_data:
            sync_politician_trades(filing)
        
        recalculate_dashboard_stats()
    
    st.success("Sync complete!")

# Display sync status
st.subheader("Database Status")
col1, col2, col3 = st.columns(3)

with col1:
    politicians = supabase.table("politicians").select("id", count="exact").execute()
    st.metric("Politicians", politicians.count)

with col2:
    trades = supabase.table("trades").select("id", count="exact").execute()
    st.metric("Total Trades", trades.count)

with col3:
    from datetime import datetime, timedelta
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = supabase.table("trades").select("id", count="exact").gte("filing_date", week_ago).execute()
    st.metric("Recent Filings", recent.count)
```

## Database Schema Reference

### Tables

| Table | Purpose |
|-------|---------|
| `jurisdictions` | Geographic regions (US House, EU Parliament, etc.) |
| `politicians` | Politician profiles with trading totals |
| `trades` | Individual trade records |
| `chart_data` | Monthly aggregated data for charts |
| `dashboard_stats` | Cached dashboard statistics |
| `notifications` | User/global notifications |

### Key Constraints

- `politicians.party`: Must be 'D', 'R', 'I', or 'Other'
- `trades.trade_type`: Must be 'buy' or 'sell' (lowercase)
- `jurisdictions.id`: Text ID like 'us-house', 'eu-parliament'

## Getting the Service Role Key

1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy the `service_role` key (keep this secret!)

## Fly.io Deployment

```toml
# fly.toml
[env]
  SUPABASE_URL = "https://ogdwavsrcyleoxfsswbt.supabase.co"

# Set secret via CLI:
# fly secrets set SUPABASE_SERVICE_ROLE_KEY="your-key"
```
