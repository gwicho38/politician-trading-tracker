# Politician Trading Data Seeding Guide

This guide explains how to seed the Supabase database with politician trading data from multiple sources.

## Overview

The seeding system provides a unified way to pull politician trading data from various sources into your Supabase database. It supports:

- **ProPublica Congress API** (free tier: 5000 requests/day)
- **StockNear Politicians** (299 politicians tracked)
- **QuiverQuant Congressional Trading** (free web scraping + premium API)
- **Barchart Politician Insider Trading** (60-day historical data)
- **Official government sources** (House/Senate disclosures)
- **EU Parliament disclosures**

## Architecture

### Components

1. **Data Sources Configuration** (`data_sources.py`)
   - Comprehensive mapping of all available data sources
   - Metadata about each source (URL, access method, rate limits, etc.)
   - 20+ configured sources across US federal, state, EU, and third-party aggregators

2. **Scrapers** (`scrapers_third_party.py`)
   - `ProPublicaAPI`: Full-featured client for ProPublica Congress API
   - `StockNearScraper`: StockNear.com scraper (requires JavaScript rendering)
   - `ThirdPartyDataFetcher`: Unified interface for all third-party sources

3. **Seeding Script** (`seed_database.py`)
   - CLI tool for seeding database from configured sources
   - Job tracking via `data_pull_jobs` table
   - Automatic deduplication using unique constraints
   - Statistics reporting

4. **Data Models** (`models.py`)
   - `Politician`: Politician information with bioguide_id support
   - `TradingDisclosure`: Individual stock transactions
   - `DataPullJob`: Job tracking and statistics

## Setup

### 1. Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required: Supabase connection
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"  # or SUPABASE_KEY

# Optional: API keys for third-party sources
export PROPUBLICA_API_KEY="your-propublica-api-key"  # Free at https://www.propublica.org/datastore/api/propublica-congress-api
export QUIVERQUANT_API_KEY="your-quiverquant-key"  # Premium subscription required
```

### 2. Database Schema

Ensure your Supabase database has the required schema:

```bash
# Run the schema SQL in your Supabase SQL editor
cat src/mcli/workflow/politician_trading/schema.sql
```

This creates:
- `politicians` table
- `trading_disclosures` table
- `data_pull_jobs` table (for job tracking)
- `data_sources` table (for source configuration)
- Indexes and unique constraints
- RLS policies

### 3. Get API Keys

#### ProPublica Congress API (Recommended - Free)

1. Visit https://www.propublica.org/datastore/api/propublica-congress-api
2. Register for a free API key
3. Set `PROPUBLICA_API_KEY` environment variable
4. Free tier: 5000 requests/day

#### QuiverQuant API (Premium - Optional)

1. Visit https://www.quiverquant.com/
2. Subscribe to a premium plan
3. Get your API key from account settings
4. Set `QUIVERQUANT_API_KEY` environment variable

## Usage

### Basic Seeding Commands

```bash
# Seed from all available sources
python -m mcli.workflow.politician_trading.seed_database --sources all

# Seed from specific source
python -m mcli.workflow.politician_trading.seed_database --sources propublica

# Test run (fetch but don't insert to database)
python -m mcli.workflow.politician_trading.seed_database --sources propublica --test-run

# Verbose logging
python -m mcli.workflow.politician_trading.seed_database --sources all --verbose
```

### From Python Code

```python
from mcli.workflow.politician_trading.seed_database import (
    get_supabase_client,
    seed_from_propublica,
    seed_from_all_sources
)

# Get Supabase client
client = get_supabase_client()

# Seed from ProPublica
stats = seed_from_propublica(client, test_run=False)
print(f"Inserted {stats['records_new']} new records")

# Seed from all sources
results = seed_from_all_sources(client, test_run=False)
for source, stats in results.items():
    print(f"{source}: {stats}")
```

### Using Third-Party Fetchers Directly

```python
from mcli.workflow.politician_trading.scrapers_third_party import (
    ThirdPartyDataFetcher,
    ProPublicaAPI
)

# Initialize fetcher with API key
fetcher = ThirdPartyDataFetcher(propublica_api_key="your-key")

# Fetch from ProPublica
data = fetcher.fetch_from_propublica(
    fetch_members=True,        # Get current Congress members
    fetch_transactions=True    # Get recent stock transactions
)

print(f"Fetched {len(data['politicians'])} politicians")
print(f"Fetched {len(data['disclosures'])} disclosures")

# Use ProPublica API directly
propublica = ProPublicaAPI(api_key="your-key")

# Get House members
house_members = propublica.list_current_members("house", congress=118)

# Get recent transactions
transactions = propublica.get_recent_stock_transactions(congress=118)

# Get specific member's disclosures
member_disclosures = propublica.get_member_financial_disclosures(
    member_id="P000197",  # Nancy Pelosi's bioguide ID
    congress=118
)
```

## Data Sources

### Currently Implemented

| Source | Type | API Key Required | Rate Limit | Status |
|--------|------|-----------------|------------|---------|
| ProPublica Congress API | API | Yes (free) | 5000/day | ✅ Active |
| StockNear Politicians | Web Scraping | No | None | ⚠️ Requires JS rendering |
| QuiverQuant Web | Web Scraping | No | Standard | ⚠️ Planned |
| QuiverQuant API | API | Yes (premium) | Varies | ⚠️ Planned |
| Barchart | Web Scraping | No | Standard | ⚠️ Planned |

### Planned Implementations

The following sources are configured in `data_sources.py` but require scraper implementation:

- **US House Financial Disclosures** (official source)
- **US Senate Financial Disclosures** (official source)
- **OpenSecrets Personal Finances** (requires API key)
- **California FPPC Form 700** (NetFile API)
- **UK Parliament Register of Interests** (free API)
- **EU Parliament Financial Declarations** (PDF parsing)

## Job Tracking

All seeding operations are tracked in the `data_pull_jobs` table:

```sql
SELECT
    job_type,
    status,
    records_found,
    records_new,
    records_updated,
    started_at,
    completed_at
FROM data_pull_jobs
ORDER BY created_at DESC
LIMIT 10;
```

You can also query the job status view:

```sql
SELECT * FROM job_status_summary;
```

## Deduplication

The system automatically handles duplicates using unique constraints:

### Politicians
Unique constraint on: `(first_name, last_name, role, state_or_country)`

### Trading Disclosures
Unique constraint on: `(politician_id, transaction_date, asset_name, transaction_type, disclosure_date)`

When running seeding multiple times:
- **Existing records**: Updated with latest data
- **New records**: Inserted
- **Duplicates**: Skipped (based on unique constraints)

## Data Quality

### Field Mapping

The seeding system handles various data formats and maps them to a unified schema:

| ProPublica Field | Database Field | Notes |
|-----------------|----------------|-------|
| `first_name` | `first_name` | Direct mapping |
| `last_name` | `last_name` | Direct mapping |
| `id` | `bioguide_id` | ProPublica uses bioguide IDs |
| `party` | `party` | "D", "R", "I" |
| `state` | `state_or_country` | Two-letter state codes |
| `transaction_date` | `transaction_date` | ISO 8601 format |
| `amount` | `amount_range_min/max` | Parsed from ranges like "$1,001 - $15,000" |

### Amount Range Parsing

ProPublica provides transaction amounts as ranges:
- "$1,001 - $15,000" → `amount_range_min=1001, amount_range_max=15000`
- "$15,001 - $50,000" → `amount_range_min=15001, amount_range_max=50000`
- Single amounts also supported

## Monitoring and Logging

Logs are written to:
- **stdout**: Real-time progress
- **`/tmp/seed_database.log`**: Persistent log file

Log format:
```
2025-10-07 12:00:00 - seed_database - INFO - Fetched 535 politicians, 1247 disclosures
2025-10-07 12:00:05 - seed_database - INFO - Upserted 535 politicians (412 new, 123 updated)
2025-10-07 12:00:10 - seed_database - INFO - Upserted 1247 disclosures (1053 new, 194 updated, 0 skipped)
```

## Scheduling Automated Seeding

### Using cron

```bash
# Run daily at 3 AM
0 3 * * * /path/to/venv/bin/python -m mcli.workflow.politician_trading.seed_database --sources all >> /var/log/politician_seeding.log 2>&1
```

### Using LSH Daemon (Recommended)

Create a workflow job in your LSH daemon configuration:

```python
from mcli.workflow.politician_trading.seed_database import seed_from_all_sources
from supabase import create_client
import os

def daily_politician_data_sync():
    """Daily sync of politician trading data"""
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    results = seed_from_all_sources(client, test_run=False)
    return results

# Schedule in LSH daemon
# Schedule: 0 3 * * * (daily at 3 AM)
```

## Extending with New Sources

To add a new data source:

### 1. Add to `data_sources.py`

```python
DataSource(
    name="Your New Source",
    jurisdiction="US-Federal",
    institution="Third-party aggregator",
    url="https://example.com/api/trades",
    disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
    access_method=AccessMethod.API,
    update_frequency="Real-time",
    data_format="json",
    api_key_required=True,
    rate_limits="1000 requests/hour",
    notes="Description of the source",
    status="active",
)
```

### 2. Create Scraper in `scrapers_third_party.py`

```python
class YourSourceScraper:
    """Scraper for your new source"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()

    def fetch_trading_data(self) -> List[Dict]:
        """Fetch trading data from source"""
        response = self.session.get("https://example.com/api/trades")
        return response.json()
```

### 3. Add to `seed_database.py`

```python
def seed_from_your_source(client: Client, test_run: bool = False) -> Dict[str, int]:
    """Seed from your new source"""
    job_id = create_data_pull_job(client, "your_source_seed")

    try:
        # Fetch data
        scraper = YourSourceScraper(api_key=os.getenv("YOUR_SOURCE_API_KEY"))
        raw_data = scraper.fetch_trading_data()

        # Convert to models
        politicians = [...]  # Convert to Politician objects
        disclosures = [...]  # Convert to TradingDisclosure objects

        # Upsert
        politician_map = upsert_politicians(client, politicians)
        stats = upsert_trading_disclosures(client, disclosures, politician_map)

        update_data_pull_job(client, job_id, "completed", stats)
        return stats

    except Exception as e:
        update_data_pull_job(client, job_id, "failed", error=str(e))
        raise
```

## Troubleshooting

### ProPublica API Key Not Working

```bash
# Verify API key is set
echo $PROPUBLICA_API_KEY

# Test API key
curl -H "X-API-Key: $PROPUBLICA_API_KEY" \
  "https://api.propublica.org/congress/v1/118/house/members.json"
```

### Supabase Connection Errors

```bash
# Verify Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY  # Should start with "eyJ..."

# Test connection
python -c "from supabase import create_client; import os; client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY')); print(client.table('politicians').select('*').limit(1).execute())"
```

### Unique Constraint Violations

If you see unique constraint errors, it means:
1. The data already exists (this is expected - will update instead)
2. You're trying to insert duplicate data in the same batch

The seeding script handles this automatically by checking for existing records before inserting.

### Rate Limiting

If you hit rate limits:

**ProPublica** (5000/day):
- Run seeding less frequently
- Fetch only incremental updates instead of full dataset
- Use pagination and offset parameters

**Web Scraping Sources**:
- Add delays between requests (`time.sleep(1)`)
- Use rotating proxies if necessary
- Respect robots.txt

## Best Practices

1. **Start with ProPublica**: It's free, reliable, and has comprehensive data
2. **Run test mode first**: Use `--test-run` to verify data before inserting
3. **Check job logs**: Review `data_pull_jobs` table to monitor success/failure
4. **Schedule regular updates**: Daily or weekly syncs to keep data fresh
5. **Monitor API quotas**: Track your API usage to avoid hitting rate limits
6. **Use verbose logging**: Enable `--verbose` for debugging

## References

- [ProPublica Congress API Documentation](https://projects.propublica.org/api-docs/congress-api/)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)
- [Stock Act (US Law)](https://en.wikipedia.org/wiki/STOCK_Act)
- [House Financial Disclosures](https://disclosures-clerk.house.gov/)
- [Senate eFilings](https://efdsearch.senate.gov/search/)
