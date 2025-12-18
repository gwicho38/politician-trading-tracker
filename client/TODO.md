# Capitol Trades - Project TODO & Integration Guide

## 📁 Project Structure

```
├── src/
│   ├── components/
│   │   ├── ui/                    # Shadcn UI components (Button, Card, etc.)
│   │   ├── admin/                 # Admin panel components
│   │   │   ├── AdminAnalytics.tsx
│   │   │   ├── AdminContentManagement.tsx
│   │   │   ├── AdminNotifications.tsx
│   │   │   ├── AdminUserManagement.tsx
│   │   │   ├── PoliticianForm.tsx
│   │   │   └── TradeForm.tsx
│   │   ├── Dashboard.tsx          # Main dashboard with stats
│   │   ├── FilingsView.tsx        # Filings list view
│   │   ├── Header.tsx             # Top navigation with search
│   │   ├── NavLink.tsx            # Navigation link component
│   │   ├── NotificationBell.tsx   # Notification dropdown
│   │   ├── PoliticiansView.tsx    # Politicians list/grid view
│   │   ├── RecentTrades.tsx       # Recent trades widget
│   │   ├── Sidebar.tsx            # Left sidebar navigation
│   │   ├── StatsCard.tsx          # Dashboard stat cards
│   │   ├── TopTraders.tsx         # Top traders widget
│   │   ├── TradeCard.tsx          # Individual trade card
│   │   ├── TradeChart.tsx         # Buys/Sells chart
│   │   ├── TradesView.tsx         # Full trades list with filters
│   │   ├── VolumeChart.tsx        # Volume over time chart
│   │   └── WalletProvider.tsx     # Web3 wallet integration
│   ├── hooks/
│   │   ├── useSupabaseData.ts     # Main data fetching hook
│   │   ├── useAdmin.ts            # Admin role checking
│   │   ├── useWalletAuth.ts       # Wallet authentication
│   │   └── use-mobile.tsx         # Mobile detection
│   ├── integrations/
│   │   └── supabase/
│   │       ├── client.ts          # Supabase client setup
│   │       └── types.ts           # Auto-generated DB types
│   ├── lib/
│   │   ├── mockData.ts            # Fallback mock data
│   │   └── utils.ts               # Utility functions
│   ├── pages/
│   │   ├── Index.tsx              # Main app page
│   │   ├── Admin.tsx              # Admin dashboard
│   │   ├── Auth.tsx               # Authentication page
│   │   └── NotFound.tsx           # 404 page
│   └── config/
│       └── wallet.ts              # Wallet configuration
├── python/                        # Python integration files
│   ├── supabase_sync.py           # Main sync module
│   ├── streamlit_sync_page.py     # Streamlit UI for sync
│   ├── requirements.txt           # Python dependencies
│   └── README.md                  # Python setup guide
├── docs/
│   └── python-integration.md      # Detailed integration docs
└── supabase/
    ├── config.toml                # Supabase config
    └── functions/
        └── wallet-auth/           # Wallet auth edge function
```

## ✅ Completed Features

### Frontend (React/TypeScript)
- [x] Dashboard with live stats from Supabase
- [x] Politicians list with filtering by jurisdiction
- [x] Trades list with search functionality
- [x] Filings view
- [x] Charts (Trade volume, Buys/Sells)
- [x] Responsive sidebar navigation
- [x] Search functionality (searches trades by ticker, company, politician)
- [x] Jurisdiction filtering
- [x] Admin panel with CRUD operations
- [x] Notification system
- [x] Wallet-based authentication (RainbowKit)
- [x] Real-time data from Supabase

### Backend (Supabase)
- [x] Database schema with all tables
- [x] Row Level Security (RLS) policies
- [x] Public read access for trades, politicians, jurisdictions
- [x] Admin-only write access
- [x] User roles system (admin, moderator, user)
- [x] Wallet nonce authentication

### Python Integration (Ready to Use)
- [x] `CapitolTradesSync` class for all database operations
- [x] Streamlit page for manual data management
- [x] Bulk insert/upsert methods
- [x] Auto-calculation of derived stats

## 🔧 Database Tables

| Table | Purpose | Python Sync Method |
|-------|---------|-------------------|
| `politicians` | Politician profiles | `upsert_politician()` |
| `trades` | Individual stock trades | `insert_trade()`, `bulk_insert_trades()` |
| `jurisdictions` | US House, Senate, EU, etc. | `upsert_jurisdiction()` |
| `chart_data` | Monthly aggregated data | `upsert_chart_data()` |
| `dashboard_stats` | Dashboard summary stats | `update_dashboard_stats()` |
| `notifications` | User notifications | `create_notification()` |
| `profiles` | User profiles | Auto-created on auth |
| `user_roles` | Admin/moderator roles | Manual or admin panel |

## 🐍 Python Integration - What You Need To Do

### Step 1: Environment Setup

```bash
cd python
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

```bash
# For local development
export SUPABASE_URL="https://ogdwavsrcyleoxfsswbt.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# For Fly.io deployment
fly secrets set SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

**Get your service role key from:**
https://supabase.com/dashboard/project/ogdwavsrcyleoxfsswbt/settings/api

### Step 3: Integrate with Your Scraper

```python
from supabase_sync import CapitolTradesSync

sync = CapitolTradesSync()

# After scraping a filing, sync it:
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
```

### Step 4: Add to Your Streamlit App

```python
# In your existing Streamlit app
from streamlit_sync_page import render_sync_page

# Add as a page in your navigation
render_sync_page()
```

## ❌ What's Missing / TODO

### Python Side (You Need to Implement)

1. **Connect Your Scraper Output**
   - [ ] Map your scraper's data format to the `sync_filing()` format
   - [ ] Handle your specific data sources (Capitol Trades API, SEC filings, etc.)

2. **Scheduled Sync Jobs**
   - [ ] Add cron job or Fly.io scheduled task to run scraper periodically
   - [ ] Example: `fly machine run --schedule "0 */6 * * *"` for every 6 hours

3. **Error Handling & Logging**
   - [ ] Add logging to track sync operations
   - [ ] Handle API rate limits from data sources
   - [ ] Add retry logic for failed syncs

4. **Data Validation**
   - [ ] Validate scraped data before inserting
   - [ ] Handle edge cases (missing fields, invalid dates, etc.)

### Optional Enhancements

1. **Webhook Endpoint** (if you want real-time triggers)
   - [ ] Create Supabase Edge Function for webhook
   - [ ] Trigger Python sync from external events

2. **Sync Status Tracking**
   - [ ] Add `sync_logs` table to track sync history
   - [ ] Display sync status in admin panel

3. **Incremental Sync**
   - [ ] Track last sync timestamp
   - [ ] Only fetch new/updated records

## 📊 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR PYTHON APP                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Scraper   │───▶│  Processor  │───▶│  CapitolTradesSync  │ │
│  │ (your code) │    │ (your code) │    │  (supabase_sync.py) │ │
│  └─────────────┘    └─────────────┘    └──────────┬──────────┘ │
└───────────────────────────────────────────────────┼─────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                         SUPABASE                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ politicians │  │   trades    │  │  chart_data/stats       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────────────────────────────┬─────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      REACT FRONTEND                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Dashboard  │  │   Trades    │  │    Politicians          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🔑 Important Notes

1. **Service Role Key**: Never expose in client-side code. Only use in Python backend.

2. **RLS Policies**: Frontend uses `anon` key with read-only access. Python uses `service_role` key to bypass RLS for writes.

3. **Data Consistency**: Always use `sync_filing()` for new filings - it handles politician upsert + trade insert atomically.

4. **Derived Data**: Call `full_sync()` after bulk operations to recalculate `chart_data` and `dashboard_stats`.

## 📞 Quick Reference

```python
# Initialize
sync = CapitolTradesSync()

# Single filing with politician + trades
sync.sync_filing(filing_data)

# Bulk trades (faster for large imports)
sync.bulk_insert_trades(politician_id, trades_list)

# Recalculate all derived data
sync.full_sync()

# Create notification for users
sync.create_notification("New Filing", "Nancy Pelosi filed 3 trades", "trade")
```
