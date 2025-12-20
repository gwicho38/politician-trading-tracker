# Supabase Edge Functions Registry

> Last Updated: 2025-12-18

## Overview

This document provides a complete inventory of all Supabase edge functions, their mapping to notebook ETL pipelines, liveness test endpoints, and periodicity configuration.

---

## Edge Functions Inventory

| Function Name | Purpose | Auth Required | Deployed | Periodicity |
|--------------|---------|---------------|----------|-------------|
| `politician-trading-collect` | Data collection from multiple sources | No | ❌ | Every 6 hours |
| `sync-data` | Sync politicians, trades, and dashboard stats | No | ❌ | Every 6 hours |
| `trading-signals` | Generate and retrieve trading signals | Partial | ❌ | On-demand |
| `alpaca-account` | Get Alpaca trading account info | Yes | ❌ | On-demand |
| `portfolio` | Get user portfolio positions | Yes | ❌ | On-demand |
| `orders` | Get trading orders | Yes | ❌ | On-demand |

---

## Function Details

### 1. politician-trading-collect

**Location:** `supabase/functions/politician-trading-collect/index.ts`

**Purpose:** Collects financial disclosure data from multiple jurisdictions.

**Endpoints:**
- `POST /` - Run full collection from all sources

**Data Sources Covered:**
| Source | Notebook Equivalent | Status |
|--------|---------------------|--------|
| US House | `01_us_house.ipynb` | ⚠️ Basic (no PDF parsing) |
| US Senate | `02_us_senate.ipynb` | ⚠️ Basic |
| QuiverQuant | `03_third_party_aggregators.ipynb` | ⚠️ Basic |
| EU Parliament | `06_eu_parliament.ipynb` | ⚠️ Basic |
| California (NetFile) | `04_us_states.ipynb` | ⚠️ Basic |

**Gap Analysis:**
- ❌ Missing UK Parliament (`05_uk_parliament.ipynb`)
- ❌ Missing EU Member States (`07_eu_member_states.ipynb`)
- ❌ Missing PDF parsing (notebooks have full pdfplumber integration)
- ❌ No ticker extraction from PDFs
- ❌ No value range parsing

**Tables Written:**
- `data_pull_jobs` - Job execution tracking
- `trading_disclosures` - Raw disclosure records

---

### 2. sync-data

**Location:** `supabase/functions/sync-data/index.ts`

**Purpose:** Synchronizes data between tables and updates statistics.

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /sync-all` | Sync all politicians |
| `POST /sync-politicians` | Alias for sync-all |
| `POST /sync-trades` | Sync trades from disclosures |
| `POST /update-stats` | Update dashboard statistics |
| `POST /sync-full` | Run all sync operations |

**Tables Read:**
- `politicians`
- `trading_disclosures`

**Tables Written:**
- `politicians` (updates totals)
- `trades` (creates from disclosures)
- `dashboard_stats`

---

### 3. trading-signals

**Location:** `supabase/functions/trading-signals/index.ts`

**Purpose:** Generate and retrieve trading signals based on politician activity.

**Endpoints:**
| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /get-signals` | No | Get active trading signals |
| `POST /generate-signals` | Yes | Generate new signals |
| `POST /get-signal-stats` | No | Get signal statistics |
| `POST /test` | No | Health check |

**Tables:**
- `trading_signals` (read/write)

---

### 4. alpaca-account

**Location:** `supabase/functions/alpaca-account/index.ts`

**Purpose:** Retrieve Alpaca trading account information.

**Endpoints:**
- `POST /` - Get account info (portfolio_value, cash, buying_power, status)

**External APIs:**
- Alpaca Markets API (`/v2/account`)

**Environment Variables Required:**
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_PAPER` (true/false)
- `ALPACA_BASE_URL`

---

### 5. portfolio

**Location:** `supabase/functions/portfolio/index.ts`

**Purpose:** Get user portfolio positions.

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /get-portfolio` | Get open positions |
| `POST /get-account-info` | Get account info (mock) |

**Tables:**
- `positions` (read)

---

### 6. orders

**Location:** `supabase/functions/orders/index.ts`

**Purpose:** Get trading orders.

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /get-orders` | Get orders with pagination/filtering |
| `POST /get-order-stats` | Get order statistics |

**Tables:**
- `trading_orders` (read)

---

## Notebook ETL Pipelines

### Pipeline Coverage

| Notebook | Description | Edge Function Coverage |
|----------|-------------|----------------------|
| `00_orchestrator.ipynb` | Master orchestrator | ❌ No equivalent |
| `01_us_house.ipynb` | US House disclosures + PDF parsing | ⚠️ Partial in `politician-trading-collect` |
| `02_us_senate.ipynb` | US Senate disclosures | ⚠️ Partial |
| `03_third_party_aggregators.ipynb` | QuiverQuant, ProPublica | ⚠️ Partial |
| `04_us_states.ipynb` | TX, NY, FL, IL, PA, MA | ⚠️ Partial (CA only) |
| `05_uk_parliament.ipynb` | UK Parliament | ❌ Missing |
| `06_eu_parliament.ipynb` | EU Parliament MEPs | ⚠️ Basic |
| `07_eu_member_states.ipynb` | DE, FR, IT, ES, NL | ❌ Missing |

### Key Notebook Features Missing in Edge Functions

1. **PDF Parsing** - Notebooks use `pdfplumber` for:
   - Asset name extraction
   - Ticker symbol extraction
   - Transaction type detection
   - Value range parsing
   - Owner information

2. **Ticker Resolution** - Uses `TickerResolver` class

3. **Value Range Parsing** - Uses `ValueRangeParser` class

4. **Comprehensive Data Model** - Full transaction records with:
   - `asset_ticker`
   - `asset_type_code`
   - `value_low` / `value_high` / `value_midpoint`
   - `owner` designation
   - `transaction_type`

---

## Periodicity Configuration

### Recommended Schedule

| Function | Schedule | Cron Expression | Rationale |
|----------|----------|-----------------|-----------|
| `politician-trading-collect` | Every 6 hours | `0 */6 * * *` | New disclosures filed daily |
| `sync-data/sync-full` | Every 6 hours (after collect) | `30 */6 * * *` | Sync after collection |
| `sync-data/update-stats` | Every hour | `0 * * * *` | Keep dashboard fresh |
| `trading-signals` | Every 2 hours | `0 */2 * * *` | Generate fresh signals |

### Supabase Cron Setup

Supabase uses `pg_cron` for scheduled jobs. Add to `supabase/migrations/`:

```sql
-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule politician-trading-collect every 6 hours
SELECT cron.schedule(
  'politician-trading-collect',
  '0 */6 * * *',
  $$
  SELECT net.http_post(
    url := 'https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/politician-trading-collect',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
    ),
    body := '{}'::jsonb
  );
  $$
);

-- Schedule sync-data every 6 hours (30 min after collect)
SELECT cron.schedule(
  'sync-data-full',
  '30 */6 * * *',
  $$
  SELECT net.http_post(
    url := 'https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/sync-data/sync-full',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
    ),
    body := '{}'::jsonb
  );
  $$
);

-- Schedule update-stats every hour
SELECT cron.schedule(
  'update-stats',
  '0 * * * *',
  $$
  SELECT net.http_post(
    url := 'https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/sync-data/update-stats',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
    ),
    body := '{}'::jsonb
  );
  $$
);
```

---

## Liveness Tests

### Test Script Location
`tests/supabase-functions/test_liveness.py`

### Test Endpoints

| Function | Test Endpoint | Expected Response |
|----------|--------------|-------------------|
| `politician-trading-collect` | `POST /` | `{"success": true}` |
| `sync-data` | `POST /update-stats` | `{"success": true}` |
| `trading-signals` | `POST /test` | `{"success": true}` |
| `alpaca-account` | `POST /` (with auth) | `{"success": true}` |
| `portfolio` | `POST /get-portfolio` (with auth) | `{"success": true}` |
| `orders` | `POST /get-orders` (with auth) | `{"success": true}` |

---

## Deployment Checklist

### Pre-Deployment
- [ ] Link Supabase project: `npx supabase link --project-ref uljsqvwkomdrlnofmlad`
- [ ] Set environment variables in Supabase Dashboard
- [ ] Run migrations for required tables

### Deploy Functions
```bash
# Deploy all functions
npx supabase functions deploy politician-trading-collect
npx supabase functions deploy sync-data
npx supabase functions deploy trading-signals
npx supabase functions deploy alpaca-account
npx supabase functions deploy portfolio
npx supabase functions deploy orders
```

### Post-Deployment
- [ ] Run liveness tests
- [ ] Verify cron jobs are scheduled
- [ ] Check function logs for errors

---

## Environment Variables Required

### All Functions
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`

### Trading Functions (alpaca-account, portfolio, orders)
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_PAPER` (true/false)
- `ALPACA_BASE_URL`

---

## Recommended Improvements

### High Priority
1. **Deploy all functions** - None are currently deployed
2. **Add PDF parsing to politician-trading-collect** - Port notebook logic
3. **Set up pg_cron scheduling** - Enable periodic execution
4. **Add comprehensive error handling** - Log to `function_logs` table

### Medium Priority
1. **Add UK Parliament source** - Missing from edge function
2. **Add EU Member States sources** - Missing from edge function
3. **Implement ticker resolution** - Port from notebooks
4. **Add rate limiting** - Prevent API abuse

### Low Priority
1. **Add webhook notifications** - Notify on new disclosures
2. **Add data quality checks** - Validate ingested data
3. **Implement incremental sync** - Only sync new records
