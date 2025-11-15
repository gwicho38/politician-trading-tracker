# Politician Trading Tracker - Scraper Implementation Guide

## Overview

This document provides a comprehensive guide to the scraping infrastructure, including architecture, implementation status, and guidelines for adding new scrapers.

## Table of Contents

1. [Architecture](#architecture)
2. [Implementation Status](#implementation-status)
3. [Adding New Scrapers](#adding-new-scrapers)
4. [Error Handling & Resilience](#error-handling--resilience)
5. [Monitoring & Observability](#monitoring--observability)
6. [Data Validation](#data-validation)
7. [Testing](#testing)
8. [Deployment](#deployment)

---

## Architecture

### Base Scraper Framework

All scrapers inherit from `BaseScraper` which provides:

- **Async HTTP Client**: Built on `aiohttp` for concurrent requests
- **Rate Limiting**: Configurable delays between requests
- **Retry Logic**: Exponential backoff for transient failures
- **Circuit Breaker**: Prevents cascading failures
- **Error Handling**: Comprehensive exception handling

```python
from politician_trading.scrapers import BaseScraper
from politician_trading.config import ScrapingConfig

class MyScraper(BaseScraper):
    def __init__(self, config: ScrapingConfig):
        super().__init__(config, circuit_breaker_name="MyScraper")

    async def scrape_data(self):
        async with self:  # Context manager handles session lifecycle
            html = await self.fetch_page("https://example.com")
            # Process data...
```

### Circuit Breaker Pattern

The circuit breaker protects against repeated calls to failing services:

**States:**
- **CLOSED**: Normal operation
- **OPEN**: Service failing, blocking requests
- **HALF_OPEN**: Testing if service recovered

**Configuration:**
```python
from politician_trading.utils import get_circuit_breaker

breaker = get_circuit_breaker(
    name="MyService",
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=120,     # Wait 2 minutes before retry
)
```

### Monitoring System

The monitoring system tracks scraper health and triggers alerts:

```python
from politician_trading.monitoring import (
    record_scraper_success,
    record_scraper_failure,
    get_scraper_health_summary
)

# Record metrics
record_scraper_success("MyScraper", records_scraped=150, duration_seconds=45.2)
record_scraper_failure("MyScraper", "Connection timeout")

# Get health status
health = get_scraper_health_summary()
```

---

## Implementation Status

### ✅ Production-Ready Scrapers

#### US Congress (House + Senate)
- **Location**: `src/politician_trading/scrapers/scrapers.py::CongressTradingScraper`
- **Status**: Fully implemented and tested
- **Features**:
  - House: ZIP index download with PDF parsing (pdfplumber + OCR fallback)
  - Senate: EFD database scraping
  - Transaction extraction with enhanced parsing
  - Capital gains and asset holdings parsing
  - Ticker resolution with confidence scoring
  - Politician name extraction
- **Data Source**: https://disclosures-clerk.house.gov, https://efdsearch.senate.gov
- **Update Frequency**: Daily
- **Test Coverage**: Comprehensive

#### UK Parliament
- **Location**: `src/politician_trading/scrapers/scrapers_uk.py::UKParliamentScraper`
- **Status**: Implemented, needs production validation
- **Features**:
  - Official UK Parliament Register of Interests API
  - Financial interest category filtering
  - MP profile scraping
- **Data Source**: https://interests-api.parliament.uk
- **Test Coverage**: Basic integration tests

#### EU Parliament
- **Location**: `src/politician_trading/scrapers/scrapers.py::EUParliamentScraper`
- **Status**: Implemented, needs production validation
- **Features**:
  - MEP financial declaration scraping
  - Profile-based interest extraction
- **Data Source**: https://www.europarl.europa.eu
- **Test Coverage**: Basic integration tests

### ⚠️ Partial Implementation (Scaffolds)

These scrapers have framework code but return mock data and need real implementation:

#### California NetFile
- **Location**: `src/politician_trading/scrapers/scrapers_california.py`
- **Status**: Architecture in place, needs implementation
- **Planned Sources**:
  - NetFile public portals (county-level)
  - Cal-Access state data
- **Next Steps**: Implement actual portal scraping logic

#### US States
- **Location**: `src/politician_trading/scrapers/scrapers_us_states.py`
- **Status**: Skeleton classes, return sample data
- **States Planned**:
  - Texas Ethics Commission
  - New York JCOPE
  - Florida Commission on Ethics
  - Illinois Ethics
  - Pennsylvania Ethics
  - Massachusetts Ethics
- **Next Steps**: Implement real scraping for each state system

#### EU Member States
- **Location**: `src/politician_trading/scrapers/scrapers_eu.py`
- **Status**: Skeleton classes, return sample data
- **Countries Planned**:
  - German Bundestag
  - French Assemblée Nationale
  - Italian Parliament
  - Spanish Congreso
  - Dutch Tweede Kamer
- **Next Steps**: Implement real scraping for each country's system

---

## Adding New Scrapers

### Step 1: Create Scraper Class

```python
# src/politician_trading/scrapers/my_scraper.py
import asyncio
from typing import List
from politician_trading.scrapers import BaseScraper
from politician_trading.models import TradingDisclosure
from politician_trading.config import ScrapingConfig

class MyNewScraper(BaseScraper):
    """Scraper for [Source Name]"""

    def __init__(self, config: ScrapingConfig):
        super().__init__(config, circuit_breaker_name="MyNewScraper")
        self.base_url = "https://example.gov"

    async def scrape_disclosures(self) -> List[TradingDisclosure]:
        """Main scraping method"""
        disclosures = []

        async with self:  # Initialize HTTP session
            # Fetch data
            html = await self.fetch_page(f"{self.base_url}/disclosures")

            if not html:
                logger.warning("Failed to fetch disclosures page")
                return []

            # Parse data
            soup = BeautifulSoup(html, "html.parser")
            # ... parsing logic ...

            # Rate limiting
            await asyncio.sleep(self.config.request_delay)

        return disclosures
```

### Step 2: Add Validation

```python
from politician_trading.parsers.validation import DisclosureValidator
from politician_trading.utils import validate_ticker

validator = DisclosureValidator()

# Validate transaction
validation_result = validator.validate_transaction(transaction_dict)
if not validation_result["is_valid"]:
    logger.error(f"Invalid transaction: {validation_result['errors']}")

# Validate ticker
is_valid, reason, confidence = validate_ticker(ticker)
if not is_valid:
    logger.warning(f"Invalid ticker {ticker}: {reason}")
```

### Step 3: Add Monitoring

```python
from politician_trading.monitoring import (
    record_scraper_success,
    record_scraper_failure
)
import time

start_time = time.time()
try:
    disclosures = await scraper.scrape_disclosures()
    duration = time.time() - start_time
    record_scraper_success("MyNewScraper", len(disclosures), duration)
except Exception as e:
    duration = time.time() - start_time
    record_scraper_failure("MyNewScraper", str(e), duration)
    raise
```

### Step 4: Add Tests

```python
# tests/integration/test_my_scraper.py
import pytest
from politician_trading.scrapers.my_scraper import MyNewScraper
from politician_trading.config import WorkflowConfig

@pytest.mark.asyncio
async def test_my_scraper():
    config = WorkflowConfig.default().scraping
    scraper = MyNewScraper(config)

    disclosures = await scraper.scrape_disclosures()

    assert len(disclosures) > 0
    assert all(d.asset_name for d in disclosures)
    assert all(d.transaction_date for d in disclosures)
```

### Step 5: Register Workflow Function

```python
# In scrapers/__init__.py or scrapers.py
async def run_my_new_scraper_workflow(config: ScrapingConfig) -> List[TradingDisclosure]:
    """Run MyNewScraper data collection workflow"""
    logger.info("Starting MyNewScraper collection")
    try:
        async with MyNewScraper(config) as scraper:
            disclosures = await scraper.scrape_disclosures()
        logger.info(f"Successfully collected {len(disclosures)} disclosures")
        return disclosures
    except Exception as e:
        logger.error(f"MyNewScraper collection failed: {e}")
        return []
```

---

## Error Handling & Resilience

### 1. Circuit Breaker Pattern

**Automatic Protection:**
- Prevents repeated calls to failing services
- Automatically opens after threshold failures
- Tests service recovery after timeout

**Manual Control:**
```python
from politician_trading.utils import get_circuit_breaker

breaker = get_circuit_breaker("MyScraper")
breaker.reset()  # Manually reset circuit
state = breaker.get_state()  # Get current state
```

### 2. Retry Logic

**Built into BaseScraper:**
- Configurable max retries (default: 3)
- Exponential backoff
- Special handling for rate limits (429)

**Configuration:**
```python
config = ScrapingConfig(
    request_delay=1.0,    # 1 second between requests
    max_retries=3,        # Retry up to 3 times
    timeout=30            # 30 second timeout
)
```

### 3. Error Recovery

**Best Practices:**
- Always use async context managers (`async with scraper:`)
- Log errors with context (politician name, URL, etc.)
- Return empty lists rather than raising on total failure
- Continue processing remaining items after individual failures

```python
for item in items:
    try:
        result = process_item(item)
        results.append(result)
    except Exception as e:
        logger.error(f"Failed to process {item}: {e}")
        # Continue with next item
        continue
```

---

## Monitoring & Observability

### Health Checks

**Get Overall Health:**
```python
from politician_trading.monitoring import get_scraper_health_summary

health = get_scraper_health_summary()
print(f"Overall Status: {health['overall_status']}")
print(f"Total Scrapers: {health['summary']['total_scrapers']}")
print(f"Healthy: {health['summary']['healthy']}")
print(f"Failing: {health['summary']['failing']}")
```

**Health Status Levels:**
- `HEALTHY`: Operating normally
- `DEGRADED`: Some issues, still functional
- `FAILING`: High failure rate or stale data
- `DOWN`: Multiple consecutive failures
- `UNKNOWN`: No metrics available

### Metrics

**Tracked Metrics:**
- Total runs
- Successful runs
- Failed runs
- Records scraped
- Success rate
- Average duration
- Last success time
- Consecutive failures

**Export Metrics:**
```python
from politician_trading.monitoring import get_monitor

monitor = get_monitor()
metrics_json = monitor.export_metrics(format="json")
metrics_prometheus = monitor.export_metrics(format="prometheus")
```

### Alerts

**Alert Types:**
- Consecutive failures (3+)
- Low success rate (<50%)
- Stale data (>24 hours)
- Circuit breaker open

**Get Active Alerts:**
```python
monitor = get_monitor()
alerts = monitor.get_alerts(limit=10)
for alert in alerts:
    print(f"[{alert['severity']}] {alert['scraper_name']}: {alert['message']}")
```

---

## Data Validation

### Transaction Validation

```python
from politician_trading.parsers.validation import DisclosureValidator

validator = DisclosureValidator()

# Validate transaction
result = validator.validate_transaction({
    "transaction_type": "PURCHASE",
    "asset_name": "Apple Inc",
    "ticker": "AAPL",
    "transaction_date": datetime(2024, 1, 15),
    "value_low": Decimal("1000"),
    "value_high": Decimal("15000"),
})

if not result["is_valid"]:
    print(f"Validation errors: {result['errors']}")
if result["warnings"]:
    print(f"Validation warnings: {result['warnings']}")
print(f"Quality score: {result['quality_score']}")
```

### Ticker Validation

```python
from politician_trading.utils import validate_ticker, get_ticker_suggestions

is_valid, reason, confidence = validate_ticker("AAPL")
# (True, "Ticker found in known symbols", 1.0)

is_valid, reason, confidence = validate_ticker("INVALID")
# (False, "Ticker length out of range", 0.3)

# Get suggestions for invalid ticker
suggestions = get_ticker_suggestions("APPL")
# ["AAPL"]
```

### Duplicate Detection

```python
duplicates = validator.check_duplicate_transactions(transactions)
for dup in duplicates:
    print(f"Potential duplicate: Transaction {dup['index1']} and {dup['index2']}")
    print(f"Similarity: {dup['similarity']:.2%}")
```

### Outlier Detection

```python
outliers = validator.flag_outliers(transactions)
for outlier in outliers:
    print(f"Transaction {outlier['index']}: {', '.join(outlier['flags'])}")
```

---

## Testing

### Unit Tests

Located in `tests/unit/`:
- `test_enhanced_parsers.py` - PDF parser tests
- `test_analytics_parsing.py` - Analytics tests
- `test_supabase_connection_usage.py` - DB tests

### Integration Tests

Located in `tests/integration/`:
- `test_congress_scraper.py` - US Congress scraper
- `test_uk_scraper.py` - UK Parliament scraper
- `test_california_scraper.py` - California scraper
- `test_us_states_scraper.py` - US states scraper

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/integration/test_congress_scraper.py

# Run with markers
uv run pytest -m integration
uv run pytest -m slow
```

---

## Deployment

### Automated Scraping

**Scheduler**: APScheduler with database persistence

**Configuration**: In `scripts/scheduled_data_collection.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Run every 6 hours
scheduler.add_job(
    run_congress_scraper,
    trigger='cron',
    hour='*/6',
    id='congress_scraper'
)
```

### Environment Variables

Required environment variables:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key
- `LOG_LEVEL` - Logging level (default: INFO)

Optional:
- `REQUEST_DELAY` - Delay between requests (default: 1.0)
- `MAX_RETRIES` - Max retry attempts (default: 3)

### Database Schema

See `docs/schema.sql` for complete schema.

Key tables:
- `politicians` - Politician records
- `trading_disclosures` - Trading transactions
- `capital_gains` - Capital gains data
- `asset_holdings` - Asset holdings (Part V)
- `data_pull_jobs` - Job tracking
- `data_sources` - Source configuration

### Monitoring Dashboard

A Streamlit dashboard is available at `pages/5_⏰_Scheduled_Jobs.py` showing:
- Scraper health status
- Recent job runs
- Error logs
- Performance metrics

---

## Best Practices

### 1. Rate Limiting
- Always respect `robots.txt`
- Use appropriate delays (1-2 seconds minimum)
- Add exponential backoff for failures
- Use circuit breakers for protection

### 2. Data Quality
- Validate all extracted data
- Check ticker symbols against known lists
- Flag outliers and anomalies
- Preserve raw data for debugging

### 3. Error Handling
- Log errors with full context
- Continue processing after individual failures
- Use circuit breakers to prevent cascading failures
- Record metrics for all runs

### 4. Testing
- Test with real data samples
- Mock external APIs in unit tests
- Use integration tests for E2E flows
- Test error conditions

### 5. Monitoring
- Track success rates
- Monitor scraper health
- Set up alerts for failures
- Export metrics for analysis

---

## Support

For questions or issues:
- GitHub Issues: https://github.com/gwicho38/politician-trading-tracker/issues
- Documentation: `/docs/` directory
- Code Examples: `tests/` directory
