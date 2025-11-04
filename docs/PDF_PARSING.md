# PDF Parsing Infrastructure for Senate Disclosures

## Problem Statement

Many Senate disclosure records in the database are placeholders that reference scanned PDF documents. These records contain minimal information:

```
asset_name: "This filing was disclosed via scanned PDF..."
asset_ticker: "N/A"
asset_type: "PDF Disclosed Filing"
ptr_link: "https://efdsearch.senate.gov/search/view/paper/[ID]/"
```

Example from database:
- **47,000+ records** from 2012-2014 are PDF-only placeholders
- They have `status='processed'` but contain no actual transaction data
- Each has a `ptr_link` to the Senate EFD search system

## Solution Architecture

### 1. PDF Parser (`transformers/pdf_parser.py`)

**Purpose**: Download and parse Senate PTR (Periodic Transaction Report) PDFs to extract actual transaction data.

**Features**:
- Async PDF downloading with aiohttp
- HTML page parsing to find embedded PDF links (BeautifulSoup)
- PDF text extraction using pdfplumber
- Regex-based transaction pattern matching
- Fallback handling for unparseable PDFs

**Key Classes**:
- `SenatePDFParser`: Main parser class with async context manager support

**Dependencies**:
```bash
uv pip install pdfplumber beautifulsoup4 aiohttp
```

### 2. Marking Script (`scripts/mark_pdf_records.py`)

**Purpose**: Identify and flag existing PDF-only records in the database.

**Usage**:
```bash
uv run python scripts/mark_pdf_records.py
```

**What it does**:
1. Queries for records with PDF indicators:
   - `asset_type = 'PDF Disclosed Filing'`
   - `asset_ticker = 'N/A'`
   - `asset_name LIKE '%scanned PDF%'`
2. Shows sample records for review
3. Prompts for confirmation
4. Updates matching records to `status='needs_pdf_parsing'`
5. Shows updated statistics

### 3. Integration Points

#### A. Pipeline Integration (Future)

The PDF parser can be integrated into the normalization stage:

```python
# In NormalizationStage
from ..transformers.pdf_parser import SenatePDFParser

async def process(self, data, context):
    pdf_parser = SenatePDFParser()

    for disclosure in data:
        if pdf_parser.should_parse_pdf(disclosure):
            # Extract PDF URL from raw_data
            pdf_url = self._get_pdf_url(disclosure)

            # Parse PDF
            transactions = await pdf_parser.parse_pdf_url(
                pdf_url,
                disclosure.politician_name
            )

            # Create new disclosures from extracted transactions
            for transaction in transactions:
                # Add to normalized data
                ...
```

#### B. Background Job (Recommended)

Create a scheduled job to reprocess PDF records:

```python
# In scheduler/jobs.py
async def pdf_reprocessing_job():
    """Process PDF-only records in batches"""

    # Query for needs_pdf_parsing status
    records = db.query_pdf_records(limit=50)

    async with SenatePDFParser() as parser:
        for record in records:
            try:
                transactions = await parser.parse_pdf_url(...)

                # Update database with extracted data
                if transactions:
                    db.replace_pdf_placeholder(record.id, transactions)
                    db.update_status(record.id, 'processed')
                else:
                    db.update_status(record.id, 'pdf_parse_failed')

            except Exception as e:
                logger.error(f"PDF parsing failed: {e}")
                db.update_status(record.id, 'pdf_parse_error')
```

### 4. Challenges & Limitations

#### Current Challenges:

1. **Website Structure Changes**:
   - Old PDF links (2012-2014) may be broken or restructured
   - Senate website may have changed URL patterns
   - Some PDFs may require authentication or session cookies

2. **PDF Quality**:
   - Many old disclosures are scanned images (not text)
   - OCR would be required for image-based PDFs
   - Text extraction quality varies by document

3. **Volume**:
   - 47,000+ records need reprocessing
   - Rate limiting required to avoid blocking
   - Processing time: ~5-10 seconds per PDF = **65-130 hours** total

4. **Parsing Complexity**:
   - PTR forms have varied formats across years
   - Transaction patterns are inconsistent
   - Regex patterns may miss edge cases

#### Recommended Approach:

**Prioritize NEW data sources** instead of parsing old PDFs:

1. ✅ **QuiverQuant**: Already has structured, parsed data from all sources
2. ✅ **House Disclosures**: Modern XML/JSON APIs available
3. ⚠️  **Senate PDFs**: Keep parser infrastructure for spot-checking, but don't bulk-process old records

**For historical data**: Consider using QuiverQuant's API (paid) which has already parsed these PDFs.

## Status Workflow

### Record Statuses:

```
active           → Standard processed record with data
needs_pdf_parsing → Identified as PDF placeholder, queued for processing
pdf_parsing      → Currently being processed
processed        → Successfully parsed PDF and extracted data
pdf_parse_failed → No transactions found in PDF
pdf_parse_error  → Technical error during PDF processing
```

### Status Transitions:

```
Initial: asset_type='PDF Disclosed Filing' + status='processed'
         ↓
Step 1:  Run mark_pdf_records.py
         ↓
         status='needs_pdf_parsing'
         ↓
Step 2:  Background job picks up record
         ↓
         status='pdf_parsing'
         ↓
Success: Extract transactions → Create new records → status='processed'
Failure: No data found → status='pdf_parse_failed'
Error:   Exception → status='pdf_parse_error'
```

## Usage Examples

### Test Single PDF:

```python
import asyncio
from politician_trading.transformers.pdf_parser import SenatePDFParser

async def test():
    async with SenatePDFParser() as parser:
        transactions = await parser.parse_pdf_url(
            "https://efdsearch.senate.gov/search/view/paper/CDFDAF62-18EA-4298-B0C5-62085A6EC3CD/",
            "Benjamin L Cardin"
        )
        print(f"Found {len(transactions)} transactions")
        for t in transactions:
            print(f"  {t['transaction_date']}: {t['asset_ticker']} - {t['transaction_type']}")

asyncio.run(test())
```

### Check If Record Needs Parsing:

```python
from politician_trading.transformers.pdf_parser import SenatePDFParser

parser = SenatePDFParser()

disclosure = {
    'asset_type': 'PDF Disclosed Filing',
    'asset_ticker': 'N/A',
    'raw_data': {'ptr_link': 'https://...'}
}

if parser.should_parse_pdf(disclosure):
    print("This record needs PDF parsing")
```

### Batch Process Records:

```python
# In a background job
from politician_trading.transformers.pdf_parser import SenatePDFParser
from politician_trading.database import get_pdf_records

async def process_pdf_batch(batch_size=50):
    records = get_pdf_records(status='needs_pdf_parsing', limit=batch_size)

    async with SenatePDFParser() as parser:
        for record in records:
            # Extract PDF URL
            pdf_url = record.raw_data.get('ptr_link')

            if not pdf_url:
                continue

            # Parse PDF
            transactions = await parser.parse_pdf_url(pdf_url, record.politician_name)

            # Update database...
```

## Installation

```bash
# Install dependencies
uv pip install pdfplumber beautifulsoup4

# Test parser
uv run python test_pdf_parser.py

# Mark existing records
uv run python scripts/mark_pdf_records.py
```

## Future Enhancements

1. **OCR Support**: Add pytesseract for scanned PDFs
2. **Caching**: Cache downloaded PDFs to avoid re-downloading
3. **Rate Limiting**: Add exponential backoff for Senate website
4. **ML-based Extraction**: Use ML models for better transaction detection
5. **Validation**: Cross-check extracted data with other sources
6. **Monitoring**: Track success/failure rates and processing times

## Summary

The PDF parsing infrastructure is **built and ready** but:

- ✅ Parser code complete with HTML/PDF handling
- ✅ Marking script ready to flag records
- ✅ Integration points defined
- ⚠️  **Old PDFs (2012-2014) may not be accessible**
- ⚠️  **Bulk processing would take 65-130 hours**
- ✅  **Better strategy: Use QuiverQuant for historical data**

**Recommendation**: Keep this infrastructure for NEW Senate disclosures going forward, but rely on QuiverQuant API for historical backfill.
