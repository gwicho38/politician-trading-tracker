# Enhanced House Financial Disclosure Parsing

## Overview
Enhance the existing House scraper to extract detailed transaction-level data from financial disclosure PDFs according to comprehensive parsing specifications.

## Current State
The House scraper currently extracts:
- Basic metadata from ZIP index (politician name, filing date, doc ID)
- Limited transaction data when `parse_pdfs=True` is enabled
- Amount ranges (min/max)
- Basic asset names

## Target State
Extract complete transaction-level data including:
- Transaction IDs and metadata
- Detailed asset information with ticker resolution
- Owner attribution (Self/Spouse/Joint)
- Transaction quantities and prices
- Comments and clarifications
- Filing period information
- Capital gains data
- Asset holdings data

---

## Phase 1: Database Schema Enhancement

### New Fields for `trading_disclosures` Table

Add to existing table:
```sql
ALTER TABLE trading_disclosures ADD COLUMN IF NOT EXISTS:
  -- Filing metadata
  filer_id VARCHAR(20),
  filing_date TIMESTAMP,
  period_start_date DATE,
  period_end_date DATE,

  -- Transaction details
  quantity DECIMAL,
  price_per_unit DECIMAL,
  is_range BOOLEAN DEFAULT false,

  -- Owner attribution
  asset_owner VARCHAR(20), -- 'SELF', 'SPOUSE', 'JOINT'

  -- Additional context
  comments TEXT,
  ticker_confidence_score DECIMAL(3,2), -- 0.00 to 1.00

  -- Validation flags
  validation_flags JSONB, -- Stores warnings/errors

  -- Raw data enhancement
  raw_pdf_text TEXT -- For debugging/reprocessing
```

### New Table: `capital_gains`

```sql
CREATE TABLE IF NOT EXISTS capital_gains (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  politician_id UUID REFERENCES politicians(id),
  disclosure_id UUID REFERENCES trading_disclosures(id),

  asset_name VARCHAR(500),
  date_acquired DATE,
  date_sold DATE,
  gain_type VARCHAR(20), -- 'SHORT_TERM', 'LONG_TERM'
  gain_amount DECIMAL(15,2),
  asset_owner VARCHAR(20),

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### New Table: `asset_holdings`

```sql
CREATE TABLE IF NOT EXISTS asset_holdings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  politician_id UUID REFERENCES politicians(id),
  filing_date DATE,

  asset_name VARCHAR(500),
  asset_type VARCHAR(10), -- [OT], [BA], [ST], etc.
  asset_ticker VARCHAR(20),
  owner VARCHAR(20), -- 'SELF', 'SPOUSE', 'DEPENDENT'

  value_low DECIMAL(15,2),
  value_high DECIMAL(15,2),

  income_type VARCHAR(100),
  current_year_income DECIMAL(15,2),
  preceding_year_income DECIMAL(15,2),

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(politician_id, filing_date, asset_name, owner)
);
```

---

## Phase 2: Enhanced PDF Parser

### 2.1 Implement Section Extractors

Create new parser methods in `CongressTradingScraper`:

```python
def _extract_transactions_section(pdf_text: str) -> List[Dict]:
    """Extract Part VII: Transactions data"""
    pass

def _extract_capital_gains_section(pdf_text: str) -> List[Dict]:
    """Extract capital gains data"""
    pass

def _extract_asset_holdings_section(pdf_text: str) -> List[Dict]:
    """Extract Part V: Assets and Unearned Income"""
    pass
```

### 2.2 Ticker Symbol Resolution

Implement intelligent ticker resolution:
```python
def _resolve_ticker_symbol(asset_name: str) -> Tuple[Optional[str], float]:
    """
    Resolve ticker from asset name using:
    1. Exact match lookup table
    2. Fuzzy matching against known companies
    3. Yahoo Finance / yfinance API

    Returns:
        (ticker_symbol, confidence_score)
    """
    pass
```

### 2.3 Value Range Parser

Enhance existing amount parser:
```python
def _parse_value_range(value_text: str) -> Dict:
    """
    Parse: "$1,001 - $15,000" -> {
        'value_low': 1001,
        'value_high': 15000,
        'is_range': True,
        'midpoint': 8000.5
    }
    """
    pass
```

### 2.4 Owner Attribution Parser

```python
def _parse_owner_designation(owner_text: str) -> str:
    """
    Parse ownership designations:
    - "JT" -> "JOINT"
    - "SP" -> "SPOUSE"
    - "Self" / blank -> "SELF"
    """
    pass
```

---

## Phase 3: Data Validation & Quality

### 3.1 Validation Rules

Implement validators:
```python
class DisclosureValidator:
    def validate_mandatory_fields(disclosure: Dict) -> List[str]:
        """Check required fields present"""

    def validate_date_sequence(disclosure: Dict) -> List[str]:
        """Verify transaction_date within filing period"""

    def check_duplicate_transactions(disclosures: List[Dict]) -> List[str]:
        """Flag potential duplicates"""

    def flag_outliers(disclosure: Dict) -> List[str]:
        """Flag transactions > $1M or unusual patterns"""
```

### 3.2 Quality Scores

Track data quality:
```python
{
  "ticker_confidence": 0.95,
  "has_all_required_fields": True,
  "date_valid": True,
  "amount_parsed": True,
  "warnings": [],
  "errors": []
}
```

---

## Phase 4: Integration & Testing

### 4.1 Update Workflow

Modify workflow to:
1. Enable PDF parsing by default (or via config flag)
2. Store enhanced data in all relevant tables
3. Log parsing statistics and quality metrics

### 4.2 Testing Strategy

1. **Unit Tests**: Test each parser component individually
2. **Integration Tests**: Test full pipeline with sample PDFs
3. **Validation Tests**: Verify data quality rules work
4. **Performance Tests**: Measure parsing speed, optimize if needed

### 4.3 Sample Test Cases

```python
def test_parse_transaction_with_ticker():
    """Test extraction of transaction with explicit ticker"""

def test_parse_transaction_without_ticker():
    """Test ticker resolution from company name"""

def test_parse_value_range():
    """Test amount range parsing"""

def test_parse_owner_attribution():
    """Test ownership designation parsing"""

def test_validate_date_sequence():
    """Test date validation logic"""
```

---

## Phase 5: Deployment & Monitoring

### 5.1 Gradual Rollout

1. Deploy schema changes
2. Enable enhanced parsing for new filings only
3. Backfill historical data in batches
4. Monitor error rates and data quality

### 5.2 Monitoring Metrics

Track:
- Parsing success rate
- Ticker resolution rate
- Average confidence scores
- Validation error frequency
- Processing time per PDF

---

## Implementation Timeline

| Phase | Tasks | Est. Time | Priority |
|-------|-------|-----------|----------|
| 1 | Database schema | 2-3 hours | HIGH |
| 2 | PDF parser enhancement | 8-10 hours | HIGH |
| 3 | Validation & quality | 4-5 hours | MEDIUM |
| 4 | Integration & testing | 6-8 hours | HIGH |
| 5 | Deployment & monitoring | 2-3 hours | MEDIUM |

**Total Estimated Time:** 22-29 hours

---

## Dependencies

### Python Libraries
- `pdfplumber` ✅ (already added)
- `yfinance` - for ticker resolution
- `fuzzywuzzy` or `rapidfuzz` - for fuzzy name matching
- `pandas` - for data manipulation

### External APIs
- Yahoo Finance API (via yfinance)
- Consider: SEC EDGAR company ticker lookup

---

## Future Enhancements

1. **OCR for scanned PDFs**: Some filings are images, not text-based
2. **Machine Learning**: Train model to extract transactions from varying formats
3. **Real-time alerts**: Notify when high-value trades are filed
4. **Historical analysis**: Track politician portfolios over time
5. **Automated ticker resolution**: Build internal ticker -> company name database

---

## Notes

- Current scraper infrastructure is solid, just needs enhancement
- Most complex part will be handling PDF format variations
- Ticker resolution will be imperfect - flag low confidence for manual review
- Start with high-quality data for recent filings, backfill carefully

