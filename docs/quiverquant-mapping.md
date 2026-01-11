# QuiverQuant API Mapping

This document maps each app data function to its QuiverQuant API equivalent for validation testing.

## QuiverQuant Data Schema

```json
{
  "Representative": "Jonathan Jackson",     // Politician full name
  "BioGuideID": "J000309",                  // Congress.gov BioGuide ID
  "ReportDate": "2026-01-08",               // Disclosure/report date
  "TransactionDate": "2025-12-22",          // Actual trade date
  "Ticker": "HOOD",                         // Stock ticker
  "Transaction": "Sale",                    // "Purchase" | "Sale" | "Sale (Partial)" | "Sale (Full)" | "Exchange"
  "Range": "$15,001 - $50,000",             // Amount range string
  "House": "Representatives",              // "Representatives" | "Senate"
  "Amount": "15001.0",                      // Numeric amount (min of range)
  "Party": "D",                             // "D" | "R" | "I"
  "last_modified": "2026-01-09",            // Data update timestamp
  "TickerType": "ST",                       // "ST" = Stock
  "Description": null,                      // Asset description
  "ExcessReturn": -6.39,                    // Performance vs SPY (%)
  "PriceChange": -5.70,                     // Actual price change (%)
  "SPYChange": 0.69                         // SPY change (%)
}
```

---

## UI Component → Data Function → QuiverQuant Mapping

### 1. Dashboard Stats Widget

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `useDashboardStats()` | `total_trades`, `total_volume`, `active_politicians` | Aggregate from all trades | `mcli run quiverquant stats` |

**QuiverQuant Test:**
```bash
# Get aggregated stats
mcli run quiverquant stats
```

**Validation:**
- `total_trades` → Count of QuiverQuant records
- `active_politicians` → Count of unique `Representative` values
- `total_volume` → Sum of `Amount` field

---

### 2. Politicians List

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `usePoliticians()` | `full_name`, `party`, `chamber`, `state`, `total_trades`, `total_volume` | Aggregate by `Representative` | `mcli run quiverquant fetch --limit 1000 --output json` |

**QuiverQuant Test:**
```bash
# Fetch all trades and aggregate by politician
mcli run quiverquant fetch --limit 1000 --output json | jq 'group_by(.Representative) | map({name: .[0].Representative, party: .[0].Party, chamber: .[0].House, trade_count: length, total_volume: (map(.Amount | tonumber) | add)})'
```

**Field Mapping:**
| App Field | QuiverQuant Field |
|-----------|------------------|
| `full_name` | `Representative` |
| `party` | `Party` (D→Democrat, R→Republican, I→Independent) |
| `chamber` | `House` (Representatives→House, Senate→Senate) |
| `bioguide_id` | `BioGuideID` |
| `total_trades` | COUNT(*) per Representative |
| `total_volume` | SUM(Amount) per Representative |

---

### 3. Trades/Filings List

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `useTradingDisclosures()` | Full trade records | Direct API response | `mcli run quiverquant fetch --limit 50` |

**QuiverQuant Test:**
```bash
# Get recent trades
mcli run quiverquant fetch --limit 50 --output json
```

**Field Mapping:**
| App Field | QuiverQuant Field |
|-----------|------------------|
| `politician_name` | `Representative` |
| `transaction_date` | `TransactionDate` |
| `disclosure_date` | `ReportDate` |
| `transaction_type` | `Transaction` (Purchase→buy, Sale*→sell) |
| `asset_ticker` | `Ticker` |
| `amount_range_min` | Parse from `Range` or use `Amount` |
| `amount_range_max` | Parse from `Range` |
| `party` | `Party` |
| `chamber` | `House` |

---

### 4. Top Tickers Widget

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `useTopTickers()` | Ticker, count, volume | Aggregate by `Ticker` | `mcli run quiverquant stats` |

**QuiverQuant Test:**
```bash
# Get top tickers from stats
mcli run quiverquant stats

# Or aggregate from raw data
mcli run quiverquant fetch --limit 1000 --output json | jq 'group_by(.Ticker) | map({ticker: .[0].Ticker, count: length}) | sort_by(-.count) | .[0:10]'
```

---

### 5. Chart Data (Monthly Aggregation)

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `useChartData()` | `month`, `year`, `buys`, `sells`, `volume` | Aggregate by TransactionDate month/year | Custom aggregation |

**QuiverQuant Test:**
```bash
# Aggregate by month
mcli run quiverquant fetch --limit 1000 --output json | jq 'group_by(.TransactionDate[0:7]) | map({month: .[0].TransactionDate[0:7], buys: [.[] | select(.Transaction | startswith("Purchase"))] | length, sells: [.[] | select(.Transaction | startswith("Sale"))] | length, volume: (map(.Amount | tonumber) | add)})'
```

---

### 6. Politician Detail Page

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `usePoliticianDetail()` | Trades for specific politician | Filter by `Representative` or `BioGuideID` | Custom filter |

**QuiverQuant Test:**
```bash
# Get trades for specific politician (by name)
mcli run quiverquant fetch --limit 1000 --output json | jq '[.[] | select(.Representative | contains("Pelosi"))]'

# Get trades by BioGuideID
mcli run quiverquant fetch --limit 1000 --output json | jq '[.[] | select(.BioGuideID == "P000197")]'
```

---

### 7. Ticker Detail Page

| App Function | Data Needed | QuiverQuant Equivalent | Test Command |
|-------------|-------------|----------------------|--------------|
| `useTickerDetail()` | Trades for specific ticker | Filter by `Ticker` | Custom filter |

**QuiverQuant Test:**
```bash
# Get trades for specific ticker
mcli run quiverquant fetch --limit 1000 --output json | jq '[.[] | select(.Ticker == "NVDA")]'
```

---

## Data Quality & Validation Tests

### Test 1: Politician Count Comparison
```bash
# QuiverQuant unique politicians
mcli run quiverquant fetch --limit 1000 --output json | jq '[.[].Representative] | unique | length'

# Compare with app database
# Expected: Similar counts for overlapping time periods
```

### Test 2: Recent Trades Validation
```bash
# Get most recent QuiverQuant trades
mcli run quiverquant fetch --limit 10 --output json | jq 'sort_by(.TransactionDate) | reverse | .[0:5]'

# Compare with app's recent filings view
```

### Test 3: Party Distribution
```bash
# QuiverQuant party breakdown
mcli run quiverquant stats

# App should show similar D/R/I percentages
```

### Test 4: Top Tickers Consistency
```bash
# QuiverQuant top tickers
mcli run quiverquant stats

# Compare MSFT, NVDA, AAPL, GOOGL rankings with app
```

---

## Features NOT Available in QuiverQuant

These app features cannot be validated against QuiverQuant:

| Feature | Reason |
|---------|--------|
| **Trading/Orders** | User-specific Alpaca integration |
| **Reference Portfolio** | Internal ML-driven portfolio |
| **Signal Generation** | Proprietary ML model |
| **Signal Playground** | Internal signal testing |
| **ML Models** | Internal training pipeline |
| **User Authentication** | App-specific |
| **Notifications** | App-specific |
| **Asset Holdings** | Not in QuiverQuant API |
| **Capital Gains** | Not in QuiverQuant API |

---

## QuiverQuant-Enhanced Features

These features can be **improved** with QuiverQuant data:

| Feature | Enhancement |
|---------|-------------|
| **ExcessReturn** | Show politician's trade performance vs SPY |
| **PriceChange** | Show actual price movement since trade |
| **SPYChange** | Compare individual trades to market benchmark |
| **Trade Timing** | Analyze disclosure delay (ReportDate - TransactionDate) |

---

## Implementation: QuiverQuant Test Commands

Add these to the mcli quiverquant command group for validation:

### `mcli run quiverquant validate-politicians`
Compare politician lists between QuiverQuant and app database.

### `mcli run quiverquant validate-trades`
Compare recent trades between sources.

### `mcli run quiverquant validate-tickers`
Compare top tickers between sources.

### `mcli run quiverquant sync`
Sync QuiverQuant data to app database as additional data source.

---

## Data Flow Diagram

```
QuiverQuant API
     │
     ▼
┌─────────────────┐
│ mcli quiverquant│ ◄── Validation layer
│    commands     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Supabase DB   │ ◄── App data storage
│  (politicians,  │
│   trades, etc.) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  React Client   │ ◄── UI presentation
│   (hooks/views) │
└─────────────────┘
```

---

## Next Steps

1. [ ] Implement `mcli run quiverquant validate` command
2. [ ] Add QuiverQuant as secondary data source in ETL
3. [ ] Create data reconciliation reports
4. [ ] Add ExcessReturn/PriceChange to trade display
5. [ ] Build automated data quality checks
