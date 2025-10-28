# Free Politician Trading Data Sources - 2025 Guide

**⚠️ IMPORTANT UPDATE**: ProPublica Congress API is no longer available as of 2025. This guide provides the latest free alternatives.

## Quick Start - No API Key Required!

The **easiest and fastest** way to get started is with **Senate Stock Watcher** - it's completely free and requires NO API key:

```bash
# No setup needed - just run!
python -m mcli.workflow.politician_trading.seed_database --sources senate

# Or get only recent trades (last 90 days)
python -m mcli.workflow.politician_trading.seed_database --sources senate --recent-only
```

## Available Free Sources (2025)

### 1. ✅ Senate Stock Watcher (RECOMMENDED - Free, No API Key!)

**Status**: ✅ **WORKING** - Fully implemented
**API Key**: ❌ Not required
**Cost**: 🆓 Completely free
**Coverage**: US Senate only (100 Senators)
**Data Quality**: ⭐⭐⭐⭐⭐ Excellent - Official PTR filings

**What it provides**:
- All historical Senate stock transactions
- Continuously updated from https://efdsearch.senate.gov
- Transaction details: date, ticker, amount range, type (purchase/sale)
- Senator information: name, office/state
- PTR (Personal Transaction Report) links to original filings

**How to use**:
```bash
# Get all historical Senate transactions
python -m mcli.workflow.politician_trading.seed_database --sources senate

# Get only recent transactions (last 90 days)
python -m mcli.workflow.politician_trading.seed_database --sources senate --recent-only --days 90

# Test mode (fetch but don't insert to database)
python -m mcli.workflow.politician_trading.seed_database --sources senate --test-run
```

**From Python**:
```python
from mcli.workflow.politician_trading.scrapers_free_sources import SenateStockWatcherScraper

scraper = SenateStockWatcherScraper()

# Fetch all transactions
transactions = scraper.fetch_all_transactions()  # Returns full historical dataset

# Or fetch recent only
recent = scraper.fetch_recent_transactions(days=30)  # Last 30 days

# Convert to model objects
politicians = scraper.convert_to_politicians(transactions)
disclosures = scraper.convert_to_disclosures(transactions)
```

**Data Source**: https://github.com/timothycarambat/senate-stock-watcher-data
**Raw Data URL**: https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/all_transactions.json

---

### 2. ✅ Finnhub Congressional Trading (Free API Key)

**Status**: ⚙️ **IMPLEMENTED** - Scraper ready, awaiting API key configuration
**API Key**: ✅ Required (FREE tier available)
**Cost**: 🆓 Free tier: 30 requests/second
**Coverage**: US House + Senate (535 members)
**Data Quality**: ⭐⭐⭐⭐ Very good

**How to get API key**:
1. Visit https://finnhub.io
2. Sign up for free account
3. Get API key from dashboard
4. Set environment variable: `export FINNHUB_API_KEY="your-key"`

**What it provides**:
- Congressional trading data by stock symbol
- Representative/Senator name
- Transaction date and type (Purchase/Sale)
- Amount ranges

**How to use**:
```bash
# Set API key
export FINNHUB_API_KEY="your-free-api-key"

# Use in seeding (coming soon - need to add to seed_database.py)
python -m mcli.workflow.politician_trading.seed_database --sources finnhub
```

**From Python**:
```python
from mcli.workflow.politician_trading.scrapers_free_sources import FinnhubCongressionalAPI

finnhub = FinnhubCongressionalAPI(api_key="your-key")

# Get congressional trading for a specific stock
trades = finnhub.get_congressional_trading(
    symbol="AAPL",
    from_date="2025-01-01",
    to_date="2025-10-06"
)
```

**API Documentation**: https://finnhub.io/docs/api/congressional-trading
**Rate Limit**: 30 requests/second (free tier)

---

### 3. ✅ SEC Edgar Insider Trading (Official Government Data)

**Status**: ⚙️ **IMPLEMENTED** - Ready to use
**API Key**: ❌ Not required
**Cost**: 🆓 Completely free
**Coverage**: All US public companies - insider/officer trading
**Data Quality**: ⭐⭐⭐⭐⭐ Excellent - Official SEC filings

**What it provides**:
- Form 4 insider transaction reports
- Company submissions history
- Officer/director trading activity
- Exact transaction amounts and dates

**How to use**:
```python
from mcli.workflow.politician_trading.scrapers_free_sources import SECEdgarInsiderAPI

sec = SECEdgarInsiderAPI()

# Get company submission history by CIK
submissions = sec.get_company_submissions(cik="0000320193")  # Apple Inc.

# Get insider transactions (Form 4 filings)
form4_filings = sec.get_insider_transactions(cik="0000320193")
```

**Important Notes**:
- Rate limit: 10 requests/second
- Requires proper User-Agent header (automatically set in scraper)
- CIK must be 10 digits with leading zeros

**API Documentation**: https://www.sec.gov/edgar/sec-api-documentation
**Data URL Format**: `https://data.sec.gov/submissions/CIK##########.json`

---

## Comparison Table

| Source | Free | API Key | Coverage | Update Frequency | Implementation Status |
|--------|------|---------|----------|------------------|----------------------|
| **Senate Stock Watcher** | ✅ Yes | ❌ None | Senate (100) | Continuous | ✅ **WORKING** |
| **Finnhub** | ✅ Yes | ✅ Required (free) | House + Senate (535) | Real-time | ⚙️ Scraper ready |
| **SEC Edgar** | ✅ Yes | ❌ None | All companies | Real-time | ⚙️ Scraper ready |
| StockNear | ⚠️ Limited | ❌ None | 299 politicians | Real-time | ⚠️ Needs JS rendering |
| QuiverQuant | ⚠️ Limited | ⚠️ Premium | House + Senate | Real-time | ⚠️ Premium only |
| ~~ProPublica~~ | ❌ No | ❌ Deprecated | N/A | N/A | ❌ **UNAVAILABLE** |

---

## Setup Instructions

### Option 1: Senate Stock Watcher (Easiest - No Setup!)

```bash
# Just run it - no environment variables needed!
python -m mcli.workflow.politician_trading.seed_database --sources senate
```

### Option 2: Add Finnhub (Optional - More Coverage)

```bash
# 1. Get free API key from https://finnhub.io
# 2. Set environment variable
export FINNHUB_API_KEY="your-free-api-key-here"

# 3. Run seeding with Finnhub
python -m mcli.workflow.politician_trading.seed_database --sources finnhub
```

### Option 3: Use All Free Sources

```bash
# Set optional API keys
export FINNHUB_API_KEY="your-free-api-key"  # Optional

# Run all sources
python -m mcli.workflow.politician_trading.seed_database --sources all
```

---

## Seeding Commands

```bash
# Seed from Senate Stock Watcher (no API key needed!)
python -m mcli.workflow.politician_trading.seed_database --sources senate

# Seed only recent Senate trades (last 30 days)
python -m mcli.workflow.politician_trading.seed_database --sources senate --recent-only --days 30

# Seed from all available free sources
python -m mcli.workflow.politician_trading.seed_database --sources all

# Test run (fetch but don't insert to database)
python -m mcli.workflow.politician_trading.seed_database --sources senate --test-run

# Verbose logging
python -m mcli.workflow.politician_trading.seed_database --sources senate --verbose
```

---

## Data Quality Notes

### Senate Stock Watcher
- ✅ Direct from official Senate PTR filings
- ✅ Includes all historical data (years of transactions)
- ✅ Updated continuously as new filings are published
- ✅ Includes PTR links to original source documents
- ⚠️ Senate only (no House data)

### Finnhub
- ✅ Covers both House and Senate
- ✅ Real-time updates
- ✅ Query by stock symbol
- ⚠️ Requires API key (but free tier is generous)

### SEC Edgar
- ✅ Official government source
- ✅ Includes exact transaction amounts (not ranges)
- ✅ Complete historical data
- ⚠️ Focus is company insiders, not politicians specifically
- ℹ️ Useful for cross-referencing politician holdings with company filings

---

## Migration from ProPublica

If you were using ProPublica Congress API, here's how to migrate:

### Before (ProPublica - No longer works):
```bash
export PROPUBLICA_API_KEY="your-key"
python -m mcli.workflow.politician_trading.seed_database --sources propublica
```

### After (Senate Stock Watcher - Works!):
```bash
# No API key needed!
python -m mcli.workflow.politician_trading.seed_database --sources senate
```

### Or (Finnhub - Free alternative):
```bash
# Get free API key from finnhub.io
export FINNHUB_API_KEY="your-free-key"
python -m mcli.workflow.politician_trading.seed_database --sources finnhub
```

---

## Scheduled Automated Updates

### Using cron (Senate Stock Watcher - recommended)

```bash
# Update Senate trades daily at 3 AM
0 3 * * * cd /path/to/mcli && .venv/bin/python -m mcli.workflow.politician_trading.seed_database --sources senate --recent-only >> /var/log/senate_trades.log 2>&1
```

### Using LSH Daemon

```python
def daily_senate_trades_sync():
    """Daily sync of Senate stock trades"""
    from mcli.workflow.politician_trading.seed_database import seed_from_senate_watcher, get_supabase_client

    client = get_supabase_client()
    results = seed_from_senate_watcher(
        client,
        test_run=False,
        recent_only=True,  # Only fetch recent trades for efficiency
        days=7  # Last week's trades
    )
    return results

# Schedule: 0 3 * * * (daily at 3 AM)
```

---

## Troubleshooting

### Senate Stock Watcher Not Working

```bash
# Test GitHub connectivity
curl https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/all_transactions.json | head -20

# If this works but scraper fails, check logs:
python -m mcli.workflow.politician_trading.seed_database --sources senate --verbose
```

### Finnhub API Key Issues

```bash
# Verify API key is set
echo $FINNHUB_API_KEY

# Test API key manually
curl "https://finnhub.io/api/v1/stock/congressional-trading?symbol=AAPL&token=$FINNHUB_API_KEY"
```

### SEC Edgar Rate Limiting

```python
# The scraper automatically adds delays (0.11 seconds between requests)
# If you still hit rate limits, increase the delay:

from mcli.workflow.politician_trading.scrapers_free_sources import SECEdgarInsiderAPI
import time

sec = SECEdgarInsiderAPI()
# Modify sleep time in get_company_submissions() to 0.2 seconds (5 req/sec)
```

---

## Recommended Strategy

For the **best coverage and data quality**, we recommend this approach:

1. **Start with Senate Stock Watcher** (free, no API key, immediate results)
   - Get all Senate trading data immediately
   - No setup required
   - Perfect for prototyping and development

2. **Add Finnhub** (free API key, adds House data)
   - Get free API key from finnhub.io
   - Adds House of Representatives trading data
   - Query by specific stock symbols

3. **Use SEC Edgar** (for corporate insider context)
   - Cross-reference politician holdings with company insider activity
   - Get exact transaction amounts
   - Useful for correlation analysis

---

## Next Steps

1. ✅ **Run your first seed**: `python -m mcli.workflow.politician_trading.seed_database --sources senate`
2. ✅ **Check Supabase**: Verify data in `politicians` and `trading_disclosures` tables
3. ✅ **Set up automation**: Add cron job or LSH daemon workflow
4. ⚙️ **Add Finnhub**: Get free API key for House data coverage
5. 📊 **Build dashboards**: Use the data in your ML/analytics pipelines

---

## References

- [Senate Stock Watcher GitHub](https://github.com/timothycarambat/senate-stock-watcher-data)
- [Finnhub API Documentation](https://finnhub.io/docs/api/congressional-trading)
- [SEC Edgar API Documentation](https://www.sec.gov/edgar/sec-api-documentation)
- [STOCK Act (US Law)](https://en.wikipedia.org/wiki/STOCK_Act)
- [Senate Financial Disclosures](https://efdsearch.senate.gov/search/)
- [House Financial Disclosures](https://disclosures-clerk.house.gov/)
