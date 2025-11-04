# Missing Components for Production Pipeline

## Current Status Summary

### ✅ Completed
- Core pipeline architecture (4 stages)
- Base classes and interfaces
- Data models (RawDisclosure, CleanedDisclosure, NormalizedDisclosure)
- Pipeline orchestrator
- 2 complete source implementations (US Senate, QuiverQuant)
- 3 transformer utilities (TickerExtractor, AmountParser, PoliticianMatcher)
- Basic end-to-end tests
- Comprehensive documentation

### ❌ Missing / Incomplete

## 1. Source Implementations (CRITICAL)

### Missing Source Files
The following source files exist but are empty (0 lines):
- `sources/california.py` - California NetFile/FPPC
- `sources/eu_parliament.py` - EU Parliament MEPs
- `sources/new_york.py` - New York Ethics Commission
- `sources/texas.py` - Texas Ethics Commission
- `sources/uk_parliament.py` - UK Parliament MPs

**Impact**: Cannot fetch data from these sources

**Priority**: Medium (US Senate & QuiverQuant cover federal data)

**Effort**: 2-4 hours per source

---

## 2. Integration Points (CRITICAL)

### A. workflow.py Integration
**File**: `src/politician_trading/workflow.py`

**Current State**: Uses old monolithic scrapers

**Needs**:
```python
# Replace this:
from politician_trading.scrapers.scrapers import CongressTradingScraper

# With this:
from politician_trading.pipeline import PipelineOrchestrator

# Update run_full_collection() to use new pipeline
async def run_full_collection(self):
    orchestrator = PipelineOrchestrator(lookback_days=self.config.lookback_days)

    results = []
    for source_name, source_type in self.enabled_sources:
        result = await orchestrator.run(source_name, source_type)
        results.append(result)

    return self._format_results(results)
```

**Impact**: Current UI won't use new pipeline

**Priority**: HIGH

**Effort**: 2-3 hours

### B. Streamlit Data Collection Page
**File**: `1_📥_Data_Collection.py` (lines 186-261)

**Current State**: Calls `PoliticianTradingWorkflow.run_full_collection()`

**Needs**: Update to use `PipelineOrchestrator`

**Impact**: Users can't trigger new pipeline from UI

**Priority**: HIGH

**Effort**: 1-2 hours

### C. Scheduled Jobs
**File**: `src/politician_trading/scheduler/jobs.py`

**Current State**: Uses old workflow

**Needs**: Update `data_collection_job()` to use new pipeline

**Impact**: Automated collection won't use new pipeline

**Priority**: MEDIUM

**Effort**: 30 minutes

---

## 3. Database Integration Issues

### A. Publishing Stage Database Client
**File**: `pipeline/publish.py` (line 91)

**Current Code**:
```python
from ..database.database import SupabaseClient
from ..config import SupabaseConfig

db_config = SupabaseConfig.from_env()
db = SupabaseClient(db_config)
```

**Issue**: This uses the OLD database client which expects different table structure

**Needs**:
- Update to use `st_supabase_connection`
- OR update old client to work with new table names (`trading_disclosures` vs `politician_trades`)

**Impact**: Publishing stage will fail when trying to insert data

**Priority**: CRITICAL

**Effort**: 2-3 hours

### B. Politician Matcher Database Access
**File**: `transformers/politician_matcher.py` (line 38)

**Current Code**:
```python
from ..database.database import SupabaseClient
response = db.client.table("politicians").select("*").execute()
```

**Issue**: Same as above - uses old database client

**Priority**: CRITICAL

**Effort**: 1 hour

---

## 4. Missing Dependencies / Imports

### A. BeautifulSoup Import Path
**Files**: `sources/us_senate.py`, `sources/quiverquant.py`

**Current**: `from bs4 import BeautifulSoup`

**Issue**: Works locally but needs to be in requirements

**Status**: ✅ Already installed (`beautifulsoup4==4.14.2`)

**Action**: None needed

### B. Missing Optional Dependencies
**Potentially Needed**:
- `selenium` - For JavaScript-heavy sites (QuiverQuant)
- `playwright` - Alternative to Selenium
- `pdfplumber` or `PyPDF2` - For parsing Senate PDFs
- `lxml` - Faster HTML parsing

**Priority**: LOW (can add as needed)

---

## 5. Error Handling & Edge Cases

### A. Missing Error Scenarios
- Network failures during ingestion
- Malformed HTML/JSON responses
- Database connection failures
- Rate limiting responses (429)
- Empty result sets
- Partial failures (some records succeed, some fail)

**Needs**: More robust try/catch blocks and retry logic

**Priority**: MEDIUM

**Effort**: Ongoing

### B. Logging
**Current**: Basic logging in each module

**Needs**:
- Centralized logging configuration
- Log levels per environment (dev/prod)
- Structured logging (JSON format)
- Log aggregation (send to Supabase?)

**Priority**: LOW

**Effort**: 2-3 hours

---

## 6. Testing Gaps

### A. Unit Tests
**Current**: Basic import and transformer tests

**Missing**:
- Individual stage tests with mocked data
- Source implementation tests with mocked HTTP
- Error handling tests
- Edge case tests (empty data, malformed input)

**Priority**: MEDIUM

**Effort**: 4-6 hours

### B. Integration Tests
**Current**: None

**Needs**:
- Full pipeline test with real database (test DB)
- Multi-source collection test
- Error recovery test
- Performance/load test

**Priority**: LOW

**Effort**: 3-4 hours

---

## 7. Configuration & Environment

### A. Environment Variables
**Needs Documentation**:
```bash
# Required
SUPABASE_URL=https://...
SUPABASE_KEY=...

# Optional
QUIVERQUANT_API_KEY=...  # For paid API access
LOG_LEVEL=INFO
PIPELINE_BATCH_SIZE=100
```

**Priority**: LOW

**Effort**: 30 minutes

### B. Configuration File
**Needs**: `pipeline_config.yaml` or similar

```yaml
sources:
  us_house:
    enabled: true
    lookback_days: 30
  us_senate:
    enabled: true
    lookback_days: 30
  quiverquant:
    enabled: false
    api_key: ${QUIVERQUANT_API_KEY}

pipeline:
  batch_size: 100
  strict_cleaning: false
  skip_duplicates: true
```

**Priority**: LOW

**Effort**: 1 hour

---

## 8. Documentation Gaps

### A. API Documentation
**Needs**: Docstrings for all public methods

**Status**: Partially complete

**Priority**: LOW

### B. Deployment Guide
**Needs**: How to deploy the new pipeline

**Priority**: LOW after integration complete

---

## 9. Performance & Optimization

### A. Caching
**Needs**:
- Cache politician lookups during normalization
- Cache ticker extractions
- Cache API responses (with TTL)

**Priority**: LOW

**Effort**: 2-3 hours

### B. Parallel Processing
**Current**: Sequential processing in orchestrator

**Possible**: Run multiple sources in parallel

**Priority**: LOW

**Effort**: 2 hours

---

## 10. Monitoring & Observability

### A. Metrics Collection
**Needs**:
- Pipeline execution time per source
- Success/failure rates
- Records processed per hour
- Error rates by type

**Priority**: LOW

**Effort**: 2-3 hours

### B. Alerting
**Needs**:
- Alert on pipeline failures
- Alert on low success rates
- Alert on missing data

**Priority**: LOW

**Effort**: 1-2 hours

---

## Critical Path to Production

### Phase 1: Core Integration (CRITICAL - 6-8 hours)
1. ✅ Fix Admin dashboard function definition bug
2. Update `pipeline/publish.py` to use correct database client
3. Update `transformers/politician_matcher.py` database access
4. Update `workflow.py` to use new pipeline
5. Test full pipeline end-to-end

### Phase 2: UI Integration (HIGH - 2-3 hours)
1. Update `1_📥_Data_Collection.py` to use new pipeline
2. Update scheduled jobs
3. Test from Streamlit UI

### Phase 3: Additional Sources (MEDIUM - 8-12 hours)
1. Implement California source
2. Implement UK Parliament source
3. Implement EU Parliament source
4. Test each source individually

### Phase 4: Hardening (MEDIUM - 4-6 hours)
1. Add comprehensive error handling
2. Add retry logic for transient failures
3. Add unit tests for all stages
4. Add integration tests

### Phase 5: Optimization (LOW - 4-6 hours)
1. Add caching
2. Add parallel processing
3. Performance tuning
4. Monitoring & alerts

---

## Immediate Next Steps (Today)

1. ✅ **DONE**: Fix Admin dashboard bug (function definition order)
2. **TODO**: Fix database client in `publish.py`
3. **TODO**: Fix database client in `politician_matcher.py`
4. **TODO**: Test pipeline end-to-end with US Senate source
5. **TODO**: Update `workflow.py` integration
6. **TODO**: Commit fixes

## Summary

**Blocking Issues**: 3
- Database client integration (publish.py)
- Database client integration (politician_matcher.py)
- workflow.py integration

**High Priority**: 2
- Streamlit UI integration
- Scheduled jobs integration

**Medium Priority**: 3
- Additional source implementations
- Error handling improvements
- Unit tests

**Low Priority**: 5
- Configuration files
- Performance optimization
- Monitoring/alerting
- Documentation polish
- Integration tests

**Estimated Time to Production-Ready**:
- Critical path: 6-8 hours
- With UI: 8-11 hours
- Fully hardened: 20-30 hours
