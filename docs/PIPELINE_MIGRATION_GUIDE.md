# Pipeline Migration Guide

## Overview

This guide helps you migrate from the old monolithic scraper system to the new modular pipeline architecture.

## What Changed?

### Before (Old System)

```
scrapers/scrapers.py (5000+ lines)
├── All scrapers in one file
├── Mixed ingestion/cleaning/normalization
├── Tightly coupled to database
└── Hard to test individual components
```

### After (New System)

```
pipeline/
├── ingest.py    - Raw data fetching
├── clean.py     - Data validation
├── normalize.py - Transformation
└── publish.py   - Database storage

sources/         - One file per source
transformers/    - Reusable utilities
```

## Migration Steps

### Step 1: Update Imports

**Old:**
```python
from politician_trading.scrapers.scrapers import CongressTradingScraper
from politician_trading.workflow import PoliticianTradingWorkflow
```

**New:**
```python
from politician_trading.pipeline import PipelineOrchestrator
from politician_trading.sources import get_source
```

### Step 2: Update Data Collection Code

**Old:**
```python
# In workflow.py
async def _collect_us_congress_data(self):
    scraper = CongressTradingScraper()
    house_data = await scraper.scrape_house_disclosures()
    senate_data = await scraper.scrape_senate_disclosures()

    for disclosure in house_data:
        # Manual cleaning, normalization, database insertion
        ...
```

**New:**
```python
# Using pipeline
orchestrator = PipelineOrchestrator(lookback_days=30)

# US House
house_results = await orchestrator.run(
    source_name="US House",
    source_type="us_house"
)

# US Senate
senate_results = await orchestrator.run(
    source_name="US Senate",
    source_type="us_senate"
)
```

### Step 3: Update Streamlit Data Collection Page

**Location:** `1_📥_Data_Collection.py`

**Old (lines 186-261):**
```python
from politician_trading.workflow import PoliticianTradingWorkflow

workflow = PoliticianTradingWorkflow(workflow_config)
results = asyncio.run(workflow.run_full_collection())
```

**New:**
```python
from politician_trading.pipeline import PipelineOrchestrator
import asyncio

orchestrator = PipelineOrchestrator(
    lookback_days=lookback_days,
    batch_size=100
)

# Collect from enabled sources
sources = []
if us_congress:
    sources.extend([
        ("US House", "us_house"),
        ("US Senate", "us_senate")
    ])
if uk_parliament:
    sources.append(("UK Parliament", "uk_parliament"))
if eu_parliament:
    sources.append(("EU Parliament", "eu_parliament"))
if california:
    sources.append(("California", "california"))

# Run pipeline for each source
all_results = []
for source_name, source_type in sources:
    results = await orchestrator.run(source_name, source_type)
    all_results.append(results)
```

### Step 4: Update Scheduled Jobs

**Location:** `src/politician_trading/scheduler/jobs.py`

**Old:**
```python
async def data_collection_job():
    workflow = PoliticianTradingWorkflow()
    results = await workflow.run_full_collection()
```

**New:**
```python
async def data_collection_job():
    from politician_trading.pipeline import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(lookback_days=1)  # Daily

    sources = [
        ("US House", "us_house"),
        ("US Senate", "us_senate"),
        ("UK Parliament", "uk_parliament"),
    ]

    results = []
    for source_name, source_type in sources:
        result = await orchestrator.run(source_name, source_type)
        results.append(result)

    return {
        'sources_processed': len(results),
        'total_disclosures': sum(
            r['overall_metrics']['records_output']
            for r in results
        )
    }
```

## Implementing New Sources

### 1. Create Source File

**File:** `src/politician_trading/sources/my_source.py`

```python
from typing import List, Dict, Any
from .base_source import BaseSource, SourceConfig

class MySource(BaseSource):
    def _create_default_config(self) -> SourceConfig:
        return SourceConfig(
            name="My Data Source",
            source_type="my_source",
            base_url="https://api.example.com/",
            request_delay=1.0,
            max_retries=3,
            timeout=30
        )

    async def _fetch_data(self, lookback_days: int, **kwargs):
        """Fetch from API or website"""
        url = f"{self.config.base_url}/disclosures"
        params = {
            'days': lookback_days,
            **kwargs
        }
        return await self._make_request(url, params=params)

    async def _parse_response(self, response_data) -> List[Dict[str, Any]]:
        """Parse into standard format"""
        disclosures = []

        for item in response_data['results']:
            disclosures.append({
                'politician_name': item['name'],
                'transaction_date': item['date'],
                'disclosure_date': item['filed_date'],
                'asset_name': item['security'],
                'asset_ticker': item.get('ticker'),
                'transaction_type': item['type'].lower(),
                'amount': item['amount_range'],
                'source_url': item['url']
            })

        return disclosures
```

### 2. Register Source

**File:** `src/politician_trading/sources/__init__.py`

```python
def get_source(source_type: str):
    # ... existing sources ...

    elif source_type == 'my_source':
        from .my_source import MySource
        return MySource()

    return None
```

### 3. Use in Pipeline

```python
results = await orchestrator.run(
    source_name="My Source",
    source_type="my_source",
    config={'api_key': 'xxx'}
)
```

## Testing Your Migration

### 1. Test Individual Stages

```python
import asyncio
from politician_trading.pipeline import (
    IngestionStage,
    CleaningStage,
    PipelineContext
)

async def test_ingestion():
    stage = IngestionStage(lookback_days=7)
    context = PipelineContext(
        source_name="US House",
        source_type="us_house"
    )

    result = await stage.process([], context)

    print(f"Status: {result.status}")
    print(f"Records: {result.metrics.records_output}")
    print(f"Errors: {len(result.errors)}")

    assert result.success, "Ingestion failed"
    assert result.metrics.records_output > 0, "No records fetched"

asyncio.run(test_ingestion())
```

### 2. Test Full Pipeline

```python
from politician_trading.pipeline import PipelineOrchestrator

async def test_full_pipeline():
    orchestrator = PipelineOrchestrator(lookback_days=7)

    results = await orchestrator.run(
        source_name="US House",
        source_type="us_house"
    )

    assert results['overall_status'] in ['success', 'partial_success']
    assert results['overall_metrics']['records_output'] > 0

    print(f"✅ Pipeline test passed!")
    print(f"   Output: {results['overall_metrics']['records_output']} records")

asyncio.run(test_full_pipeline())
```

### 3. Compare Results

```python
# Run both old and new systems, compare outputs
async def compare_systems():
    # Old system
    from politician_trading.workflow import PoliticianTradingWorkflow
    old_workflow = PoliticianTradingWorkflow()
    old_results = await old_workflow.run_full_collection()

    # New system
    new_orchestrator = PipelineOrchestrator()
    new_results = await new_orchestrator.run("US House", "us_house")

    print(f"Old: {old_results['summary']['total_new_disclosures']} new")
    print(f"New: {new_results['overall_metrics']['records_output']} output")
```

## Common Issues and Solutions

### Issue 1: Missing Dependencies

**Error:** `ImportError: No module named 'politician_trading.pipeline'`

**Solution:**
```bash
# Ensure new modules are in your path
cd /Users/lefv/repos/politician-trading-tracker
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Issue 2: Source Not Found

**Error:** `Unknown source type: my_source`

**Solution:**
- Check source is registered in `sources/__init__.py`
- Verify source file exists
- Check for typos in source_type

### Issue 3: Database Connection

**Error:** `supabase_key is required`

**Solution:**
```python
# Ensure environment variables or secrets.toml is configured
import os
os.environ['SUPABASE_URL'] = 'your_url'
os.environ['SUPABASE_KEY'] = 'your_key'
```

### Issue 4: No Records Fetched

**Check:**
1. Source implementation is complete
2. Lookback period is appropriate
3. Source website is accessible
4. Rate limiting isn't too aggressive

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check each stage
result = await orchestrator.run("US House", "us_house")
for stage_name, stage_data in result['stages'].items():
    print(f"{stage_name}: {stage_data['metrics']}")
```

## Performance Comparison

### Old System
- Single-threaded scraping
- No clear metrics
- Hard to identify bottlenecks

### New System
- Async/await throughout
- Per-stage metrics
- Easy to optimize individual stages

```python
# View performance breakdown
results = await orchestrator.run(...)

for stage_name, stage_data in results['stages'].items():
    metrics = stage_data['metrics']
    print(f"{stage_name}:")
    print(f"  Duration: {metrics['duration_seconds']:.2f}s")
    print(f"  Throughput: {metrics['records_output']/metrics['duration_seconds']:.1f} rec/s")
```

## Rollback Plan

If you need to revert to the old system:

1. **Keep old code intact** (don't delete `scrapers/scrapers.py`)
2. **Feature flag** in code:

```python
USE_NEW_PIPELINE = os.getenv('USE_NEW_PIPELINE', 'false').lower() == 'true'

if USE_NEW_PIPELINE:
    from politician_trading.pipeline import PipelineOrchestrator
    orchestrator = PipelineOrchestrator()
    results = await orchestrator.run(...)
else:
    from politician_trading.workflow import PoliticianTradingWorkflow
    workflow = PoliticianTradingWorkflow()
    results = await workflow.run_full_collection()
```

3. **Test both systems in parallel** initially
4. **Gradual rollout** - migrate one source at a time

## Next Steps

1. ✅ Read this migration guide
2. ⏳ Test pipeline with single source
3. ⏳ Migrate scheduled jobs
4. ⏳ Migrate Streamlit UI
5. ⏳ Implement remaining sources
6. ⏳ Add comprehensive tests
7. ⏳ Monitor production performance
8. ⏳ Deprecate old system

## Support

- **Documentation:** `/docs/PIPELINE_ARCHITECTURE.md`
- **Examples:** Test files in `/tests/pipeline/`
- **Issues:** File in GitHub repo

## Summary

The new pipeline architecture provides:
- ✅ **Modularity** - Easy to maintain and extend
- ✅ **Testability** - Each component testable in isolation
- ✅ **Observability** - Detailed metrics per stage
- ✅ **Reliability** - Better error handling
- ✅ **Performance** - Optimizable per stage

Migration is straightforward - most code changes are just import updates and using the new `PipelineOrchestrator` class.
