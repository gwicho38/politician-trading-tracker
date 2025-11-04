# Ingestion Pipeline Architecture

## Overview

The new ingestion pipeline provides a modular, extensible architecture for collecting, cleaning, normalizing, and publishing politician trading disclosures from multiple sources.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Sources                                  │
│  (US House, US Senate, UK Parliament, EU Parliament, etc.)          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 1: INGESTION                                 │
│                                                                       │
│  • Fetches raw data from sources                                    │
│  • Handles rate limiting and retries                                │
│  • Supports batch mode for large datasets                           │
│  • Output: List[RawDisclosure]                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: CLEANING                                 │
│                                                                       │
│  • Validates required fields                                         │
│  • Removes duplicates                                                │
│  • Cleans text (trim, normalize)                                    │
│  • Validates dates and types                                        │
│  • Output: List[CleanedDisclosure]                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STAGE 3: NORMALIZATION                              │
│                                                                       │
│  • Parses politician names                                           │
│  • Matches to existing politicians                                   │
│  • Extracts ticker symbols                                           │
│  • Parses amount ranges                                              │
│  • Enriches with metadata                                           │
│  • Output: List[NormalizedDisclosure]                               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 4: PUBLISHING                                │
│                                                                       │
│  • Checks for duplicates in database                                │
│  • Creates new politician records if needed                         │
│  • Inserts/updates disclosure records                               │
│  • Handles batch operations                                         │
│  • Output: Publication metrics                                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   Supabase Database  │
                │                       │
                │  • politicians        │
                │  • trading_disclosures│
                └──────────────────────┘
```

## Directory Structure

```
src/politician_trading/
├── pipeline/                      # Core pipeline stages
│   ├── __init__.py
│   ├── base.py                    # Base classes, data models
│   ├── ingest.py                  # Ingestion stage
│   ├── clean.py                   # Cleaning stage
│   ├── normalize.py               # Normalization stage
│   ├── publish.py                 # Publishing stage
│   └── orchestrator.py            # Pipeline orchestration
│
├── sources/                       # Disclosure source implementations
│   ├── __init__.py                # Source factory
│   ├── base_source.py             # Abstract base class
│   ├── us_house.py                # US House disclosures
│   ├── us_senate.py               # US Senate disclosures
│   ├── uk_parliament.py           # UK Parliament
│   ├── eu_parliament.py           # EU Parliament
│   ├── california.py              # California disclosures
│   ├── new_york.py                # New York
│   ├── texas.py                   # Texas
│   └── quiverquant.py             # QuiverQuant aggregator
│
└── transformers/                  # Data transformation utilities
    ├── __init__.py
    ├── ticker_extractor.py        # Ticker symbol extraction
    ├── amount_parser.py           # Amount range parsing
    └── politician_matcher.py      # Politician matching
```

## Key Components

### Pipeline Stages

#### 1. Ingestion Stage (`pipeline/ingest.py`)

**Purpose**: Fetch raw data from sources

**Input**: Empty list (fetches from source directly)

**Output**: `List[RawDisclosure]`

**Features**:
- Standard and batch ingestion modes
- Rate limiting and retry logic
- Source-specific configuration
- Error handling and metrics

**Example**:
```python
from politician_trading.pipeline import IngestionStage, PipelineContext

stage = IngestionStage(lookback_days=30)
context = PipelineContext(
    source_name="US House",
    source_type="us_house"
)

result = await stage.process([], context)
print(f"Fetched {len(result.data)} disclosures")
```

#### 2. Cleaning Stage (`pipeline/clean.py`)

**Purpose**: Validate and clean raw data

**Input**: `List[RawDisclosure]`

**Output**: `List[CleanedDisclosure]`

**Features**:
- Required field validation
- Duplicate detection and removal
- Text normalization
- Date parsing and validation
- Transaction type normalization

**Example**:
```python
from politician_trading.pipeline import CleaningStage

stage = CleaningStage(
    remove_duplicates=True,
    strict_validation=False
)

result = await stage.process(raw_disclosures, context)
print(f"Cleaned {result.metrics.records_output} of {result.metrics.records_input}")
```

#### 3. Normalization Stage (`pipeline/normalize.py`)

**Purpose**: Transform into database-ready format

**Input**: `List[CleanedDisclosure]`

**Output**: `List[NormalizedDisclosure]`

**Features**:
- Name parsing (first, last, full)
- Politician matching to database
- Ticker symbol extraction
- Amount range parsing
- Role/party/state inference

**Transformers Used**:
- `TickerExtractor` - Extract ticker from asset name
- `AmountParser` - Parse amount ranges
- `PoliticianMatcher` - Match to existing politicians

**Example**:
```python
from politician_trading.pipeline import NormalizationStage

stage = NormalizationStage(auto_create_politicians=True)

result = await stage.process(cleaned_disclosures, context)
print(f"Normalized {result.metrics.records_output} disclosures")
```

#### 4. Publishing Stage (`pipeline/publish.py`)

**Purpose**: Store in database

**Input**: `List[NormalizedDisclosure]`

**Output**: `List[Dict[str, Any]]` (publication metadata)

**Features**:
- Duplicate checking
- Politician creation
- Batch insertion/updates
- Transaction safety
- Detailed metrics

**Example**:
```python
from politician_trading.pipeline import PublishingStage

stage = PublishingStage(
    batch_size=100,
    skip_duplicates=True,
    update_existing=True
)

result = await stage.process(normalized_disclosures, context)
summary = result.data[0]['summary']
print(f"Inserted: {summary['disclosures_inserted']}, Updated: {summary['disclosures_updated']}")
```

### Pipeline Orchestrator

**Purpose**: Coordinates all stages

**Location**: `pipeline/orchestrator.py`

**Features**:
- Automatic stage sequencing
- Error handling between stages
- Overall metrics aggregation
- Status tracking

**Example**:
```python
from politician_trading.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator(
    lookback_days=30,
    batch_ingestion=False,
    strict_cleaning=False,
    skip_duplicates=True
)

results = await orchestrator.run(
    source_name="US House",
    source_type="us_house",
    config={'custom_param': 'value'}
)

print(f"Pipeline status: {results['overall_status']}")
print(f"Output: {results['overall_metrics']['records_output']} records")
```

### Data Sources

#### Base Source Class (`sources/base_source.py`)

All source implementations inherit from `BaseSource`:

```python
class BaseSource(ABC):
    @abstractmethod
    async def _fetch_data(self, lookback_days: int, **kwargs) -> Any:
        """Fetch raw data from source"""
        pass

    @abstractmethod
    async def _parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """Parse response into disclosure dicts"""
        pass

    async def fetch(self, lookback_days: int = 30, **kwargs) -> List[Dict[str, Any]]:
        """Main fetch method (implemented in base class)"""
        pass
```

**Features**:
- HTTP session management
- Retry logic with exponential backoff
- Rate limiting
- Context manager support

#### Implementing a New Source

1. Create file in `sources/` (e.g., `sources/my_source.py`)
2. Inherit from `BaseSource`
3. Implement required methods

```python
from .base_source import BaseSource, SourceConfig

class MySource(BaseSource):
    def _create_default_config(self) -> SourceConfig:
        return SourceConfig(
            name="My Data Source",
            source_type="my_source",
            base_url="https://api.example.com/",
            request_delay=1.0
        )

    async def _fetch_data(self, lookback_days: int, **kwargs):
        url = f"{self.config.base_url}/disclosures"
        return await self._make_request(url)

    async def _parse_response(self, response_data):
        disclosures = []
        for item in response_data['results']:
            disclosures.append({
                'politician_name': item['name'],
                'transaction_date': item['date'],
                # ... map fields ...
            })
        return disclosures
```

4. Register in `sources/__init__.py`:

```python
def get_source(source_type: str):
    if source_type == 'my_source':
        from .my_source import MySource
        return MySource()
    # ...
```

### Data Models

#### Data Flow Models

1. **RawDisclosure** - Straight from source
   ```python
   @dataclass
   class RawDisclosure:
       source: str
       source_type: str
       raw_data: Dict[str, Any]
       scraped_at: datetime
       source_url: Optional[str]
   ```

2. **CleanedDisclosure** - After validation
   ```python
   @dataclass
   class CleanedDisclosure:
       source: str
       politician_name: str
       transaction_date: datetime
       disclosure_date: datetime
       asset_name: str
       transaction_type: str
       # ... optional fields ...
   ```

3. **NormalizedDisclosure** - Ready for database
   ```python
   @dataclass
   class NormalizedDisclosure:
       politician_id: Optional[str]
       politician_first_name: str
       politician_last_name: str
       politician_role: str
       transaction_date: datetime
       asset_name: str
       asset_ticker: Optional[str]
       amount_range_min: Optional[float]
       amount_range_max: Optional[float]
       # ... all database fields ...
   ```

## Usage Examples

### Simple Pipeline Execution

```python
from politician_trading.pipeline import run_pipeline_for_source

# Run pipeline for single source
results = await run_pipeline_for_source(
    source_name="US Senate",
    source_type="us_senate",
    lookback_days=7
)

print(f"Status: {results['overall_status']}")
print(f"Records: {results['overall_metrics']['records_output']}")
```

### Multi-Source Execution

```python
from politician_trading.pipeline import PipelineOrchestrator
import asyncio

async def run_all_sources():
    sources = [
        ("US House", "us_house"),
        ("US Senate", "us_senate"),
        ("UK Parliament", "uk_parliament"),
    ]

    orchestrator = PipelineOrchestrator(lookback_days=30)

    results = []
    for name, source_type in sources:
        result = await orchestrator.run(name, source_type)
        results.append(result)

    return results

results = asyncio.run(run_all_sources())
```

### Custom Pipeline Configuration

```python
orchestrator = PipelineOrchestrator(
    lookback_days=60,           # Fetch 60 days of data
    batch_ingestion=True,       # Use batch mode
    batch_size=50,              # 50 records per batch
    strict_cleaning=True,       # Strict validation
    skip_duplicates=True        # Skip existing records
)

results = await orchestrator.run(
    source_name="California",
    source_type="california",
    config={
        'api_key': 'your_key',
        'region': 'state'
    }
)
```

## Error Handling

### Pipeline Errors

Each stage returns a `PipelineResult` with status:
- `SUCCESS` - All records processed
- `PARTIAL_SUCCESS` - Some failures
- `FAILED` - Stage failed completely

```python
result = await stage.process(data, context)

if result.failed:
    print("Stage failed:")
    for error in result.errors:
        print(f"  - {error}")
    for error_msg in result.metrics.errors:
        print(f"  - {error_msg}")
else:
    print(f"Success rate: {result.metrics.success_rate():.1f}%")
```

### Source Errors

Sources handle retries automatically:

```python
# Configured in SourceConfig
config = SourceConfig(
    max_retries=3,
    timeout=30,
    request_delay=2.0
)
```

## Metrics and Monitoring

### Pipeline Metrics

Each stage tracks:
- `records_input` - Records received
- `records_output` - Records produced
- `records_skipped` - Records skipped
- `records_failed` - Records that failed
- `duration_seconds` - Processing time
- `errors` - List of errors
- `warnings` - List of warnings

### Overall Metrics

```python
results = await orchestrator.run(...)

metrics = results['overall_metrics']
print(f"Input: {metrics['records_input']}")
print(f"Output: {metrics['records_output']}")
print(f"Failed: {metrics['records_failed']}")
print(f"Success Rate: {metrics['success_rate']:.1f}%")
print(f"Duration: {metrics['duration_seconds']:.2f}s")
```

## Migration from Old System

### Old System (workflow.py)

```python
from politician_trading.workflow import PoliticianTradingWorkflow

workflow = PoliticianTradingWorkflow()
results = await workflow.run_full_collection()
```

### New System (pipeline)

```python
from politician_trading.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator(lookback_days=30)

# Run for each source
sources = ['us_house', 'us_senate', 'uk_parliament']
for source_type in sources:
    results = await orchestrator.run(
        source_name=source_type.replace('_', ' ').title(),
        source_type=source_type
    )
```

## Benefits of New Architecture

### Modularity
- Each stage is independent
- Easy to test individual stages
- Can run stages separately

### Extensibility
- Simple to add new sources
- Easy to add new transformation steps
- Pluggable validators and enrichers

### Maintainability
- Clear separation of concerns
- Single responsibility per module
- Type-safe data models

### Observability
- Detailed metrics per stage
- Error tracking and reporting
- Success rate monitoring

### Reusability
- Transformers can be used independently
- Sources can be tested in isolation
- Pipeline stages are composable

## Testing

### Unit Tests

```python
# Test individual stage
from politician_trading.pipeline import CleaningStage

stage = CleaningStage()
result = await stage.process(test_data, test_context)

assert result.success
assert result.metrics.records_output > 0
```

### Integration Tests

```python
# Test full pipeline
from politician_trading.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
results = await orchestrator.run(
    source_name="Test Source",
    source_type="test"
)

assert results['overall_status'] == 'success'
```

## Next Steps

1. ✅ Core pipeline stages implemented
2. ✅ Base source class created
3. ✅ Transformers implemented
4. ⏳ Complete source implementations
5. ⏳ Integration with workflow.py
6. ⏳ Unit tests for all components
7. ⏳ Integration tests
8. ⏳ Performance benchmarking
9. ⏳ Documentation updates

## See Also

- [Database Schema](../supabase/README.md)
- [CRUD Guide](DATABASE_CRUD_GUIDE.md)
- [Data Sources](../src/politician_trading/data_sources.py)
