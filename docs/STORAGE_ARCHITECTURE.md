# Primary Data Storage Architecture

## Overview

Store all raw source data (PDFs, API responses, HTML pages) in Supabase Storage for:
- **Audit Trail**: Historical record of what we collected
- **Reprocessing**: Re-parse without re-downloading
- **Compliance**: Legal requirement to retain source documents
- **Cost Optimization**: Don't re-fetch from external APIs
- **Debugging**: Compare parsed data with source

## Storage Buckets

### 1. `raw-pdfs` Bucket
**Purpose**: Store PDF files from Senate/House disclosures

**Structure**:
```
raw-pdfs/
├── senate/
│   ├── 2024/
│   │   ├── 11/
│   │   │   ├── {disclosure_id}_{politician_last_name}.pdf
│   │   │   └── metadata.json
│   │   └── 12/
│   ├── 2025/
│   └── ...
└── house/
    └── [same structure]
```

**Naming Convention**:
- `{disclosure_id}_{politician_last_name}_{YYYYMMDD}.pdf`
- Example: `e4bb7531-7230-49bb-8c51-87d58069a0bf_Blumenthal_20201202.pdf`

**Metadata JSON** (per file):
```json
{
  "disclosure_id": "uuid",
  "politician_id": "uuid",
  "politician_name": "Richard Blumenthal",
  "source_url": "https://efdsearch.senate.gov/...",
  "download_date": "2025-11-04T16:30:00Z",
  "file_size_bytes": 245680,
  "file_hash_sha256": "abc123...",
  "parse_status": "pending|success|failed",
  "parse_date": "2025-11-04T16:35:00Z",
  "transactions_found": 5
}
```

### 2. `api-responses` Bucket
**Purpose**: Store raw API responses (QuiverQuant, House APIs, etc.)

**Structure**:
```
api-responses/
├── quiverquant/
│   ├── 2025/
│   │   ├── 11/
│   │   │   ├── 04/
│   │   │   │   ├── batch_1_20251104_163000.json
│   │   │   │   └── batch_2_20251104_170000.json
│   │   │   └── metadata.json
│   └── ...
├── house-xml/
└── senate-api/
```

**Naming Convention**:
- `batch_{number}_{YYYYMMDD}_{HHMMSS}.json`
- Example: `batch_1_20251104_163000.json`

**Metadata**:
```json
{
  "source": "quiverquant",
  "endpoint": "/congresstrading",
  "fetch_date": "2025-11-04T16:30:00Z",
  "record_count": 150,
  "lookback_days": 30,
  "response_size_bytes": 45680,
  "success": true
}
```

### 3. `parsed-data` Bucket
**Purpose**: Store intermediate parsed data before database insertion

**Structure**:
```
parsed-data/
├── senate/
│   ├── 2025/
│   │   ├── 11/
│   │   │   ├── {disclosure_id}_parsed.json
│   │   │   └── batch_20251104_parsed.json
└── quiverquant/
```

**Parsed Data Format**:
```json
{
  "source_file": "raw-pdfs/senate/2024/11/e4bb7531_Blumenthal_20201202.pdf",
  "parse_date": "2025-11-04T16:35:00Z",
  "parser_version": "1.0.0",
  "transactions": [
    {
      "transaction_date": "2020-12-01",
      "asset_name": "Apple Inc.",
      "asset_ticker": "AAPL",
      "transaction_type": "purchase",
      "amount_range_min": 15001,
      "amount_range_max": 50000,
      "confidence": 0.95
    }
  ],
  "parse_metadata": {
    "extraction_method": "pdfplumber",
    "pages_processed": 3,
    "warnings": []
  }
}
```

### 4. `html-snapshots` Bucket
**Purpose**: Store HTML pages for debugging and replay

**Structure**:
```
html-snapshots/
├── senate/
│   ├── search_results/
│   │   └── 20251104_163000.html
│   └── disclosure_pages/
│       └── {disclosure_id}.html
```

## Database Schema Extension

### New Table: `stored_files`

```sql
CREATE TABLE stored_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    disclosure_id UUID REFERENCES trading_disclosures(id),

    -- File identification
    storage_bucket VARCHAR(50) NOT NULL,  -- 'raw-pdfs', 'api-responses', etc.
    storage_path TEXT NOT NULL,           -- Full path in bucket
    file_type VARCHAR(20) NOT NULL,       -- 'pdf', 'json', 'html'

    -- File metadata
    file_size_bytes INTEGER,
    file_hash_sha256 VARCHAR(64),
    mime_type VARCHAR(100),

    -- Source information
    source_url TEXT,
    source_type VARCHAR(50),              -- 'senate_pdf', 'quiverquant_api', etc.

    -- Processing metadata
    download_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    parse_status VARCHAR(20),             -- 'pending', 'success', 'failed', 'skipped'
    parse_date TIMESTAMPTZ,
    parse_error TEXT,

    -- Lifecycle
    expires_at TIMESTAMPTZ,               -- Auto-delete after X days
    is_archived BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_stored_files_disclosure ON stored_files(disclosure_id);
CREATE INDEX idx_stored_files_bucket_path ON stored_files(storage_bucket, storage_path);
CREATE INDEX idx_stored_files_parse_status ON stored_files(parse_status);
CREATE INDEX idx_stored_files_source ON stored_files(source_type, download_date);
```

### Update: `trading_disclosures` Table

Add columns to link to stored files:
```sql
ALTER TABLE trading_disclosures
ADD COLUMN source_file_id UUID REFERENCES stored_files(id),
ADD COLUMN has_raw_pdf BOOLEAN DEFAULT FALSE,
ADD COLUMN has_parsed_data BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_disclosures_source_file ON trading_disclosures(source_file_id);
```

## Implementation

### 1. Storage Manager Class

```python
# src/politician_trading/storage/storage_manager.py

from supabase import create_client
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import json

class StorageManager:
    """Manage file storage in Supabase Storage"""

    def __init__(self, supabase_client):
        self.client = supabase_client

    async def save_pdf(
        self,
        pdf_content: bytes,
        disclosure_id: str,
        politician_name: str,
        source_url: str,
        transaction_date: datetime
    ) -> str:
        """
        Save PDF to storage and return storage path

        Returns:
            str: Storage path (e.g., 'senate/2024/11/uuid_Name_20241101.pdf')
        """
        # Generate path
        year = transaction_date.year
        month = f"{transaction_date.month:02d}"
        date_str = transaction_date.strftime("%Y%m%d")
        filename = f"{disclosure_id}_{politician_name}_{date_str}.pdf"
        path = f"senate/{year}/{month}/{filename}"

        # Calculate hash
        file_hash = hashlib.sha256(pdf_content).hexdigest()

        # Upload to storage
        self.client.storage.from_('raw-pdfs').upload(
            path,
            pdf_content,
            {'content-type': 'application/pdf'}
        )

        # Save metadata to database
        metadata = {
            'disclosure_id': disclosure_id,
            'storage_bucket': 'raw-pdfs',
            'storage_path': path,
            'file_type': 'pdf',
            'file_size_bytes': len(pdf_content),
            'file_hash_sha256': file_hash,
            'mime_type': 'application/pdf',
            'source_url': source_url,
            'source_type': 'senate_pdf',
            'parse_status': 'pending'
        }

        self.client.table('stored_files').insert(metadata).execute()

        return path

    async def save_api_response(
        self,
        response_data: dict,
        source: str,
        endpoint: str
    ) -> str:
        """Save API response JSON"""
        # Generate path with timestamp
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"batch_{timestamp}.json"
        path = f"{source}/{date_path}/{filename}"

        # Convert to JSON
        json_content = json.dumps(response_data, indent=2)
        json_bytes = json_content.encode('utf-8')

        # Upload
        self.client.storage.from_('api-responses').upload(
            path,
            json_bytes,
            {'content-type': 'application/json'}
        )

        # Save metadata
        metadata = {
            'storage_bucket': 'api-responses',
            'storage_path': path,
            'file_type': 'json',
            'file_size_bytes': len(json_bytes),
            'source_type': f'{source}_api',
            'parse_status': 'pending'
        }

        self.client.table('stored_files').insert(metadata).execute()

        return path

    async def get_pdf(self, storage_path: str) -> bytes:
        """Retrieve PDF from storage"""
        response = self.client.storage.from_('raw-pdfs').download(storage_path)
        return response

    async def get_api_response(self, storage_path: str) -> dict:
        """Retrieve API response from storage"""
        response = self.client.storage.from_('api-responses').download(storage_path)
        return json.loads(response)
```

### 2. Usage in PDF Parser

```python
# In pdf_parser.py

async def parse_pdf_url(self, pdf_url: str, politician_name: str) -> List[Dict]:
    # Download PDF
    pdf_content = await self._download_pdf(pdf_url)

    if pdf_content:
        # Save to storage FIRST
        storage_path = await self.storage_manager.save_pdf(
            pdf_content,
            disclosure_id,
            politician_name,
            pdf_url,
            transaction_date
        )

        # Then parse
        transactions = await self._parse_pdf_content(pdf_content, ...)

        # Update parse status
        await self.storage_manager.update_parse_status(
            storage_path,
            'success',
            transactions_count=len(transactions)
        )

    return transactions
```

### 3. Usage in QuiverQuant Source

```python
# In sources/quiverquant.py

async def fetch(self, lookback_days: int) -> List[Dict]:
    # Fetch from API
    response_data = await self._fetch_via_api(...)

    # Save raw response FIRST
    storage_path = await self.storage_manager.save_api_response(
        response_data,
        source='quiverquant',
        endpoint='/congresstrading'
    )

    # Then parse
    disclosures = self._parse_api_response(response_data)

    return disclosures
```

## Retention Policy

### Auto-Deletion Rules

```sql
-- Delete API responses older than 90 days (we have parsed data)
UPDATE stored_files
SET expires_at = download_date + INTERVAL '90 days'
WHERE storage_bucket = 'api-responses';

-- Keep PDFs for 1 year (legal requirement)
UPDATE stored_files
SET expires_at = download_date + INTERVAL '1 year'
WHERE storage_bucket = 'raw-pdfs';

-- Keep parsed data for 2 years
UPDATE stored_files
SET expires_at = download_date + INTERVAL '2 years'
WHERE storage_bucket = 'parsed-data';
```

### Storage Cost Estimates

**Supabase Storage Pricing**:
- Free tier: 1 GB
- Pro: $0.021/GB/month

**Estimated Usage**:
- Average PDF: 200 KB
- 447 PDFs: ~90 MB
- API responses: ~50 MB/month
- Total first year: ~700 MB

**Cost**: Free tier sufficient initially, ~$0.015/month if exceeded

## Benefits

1. **Audit Trail**: Complete record of source data
2. **Reprocessing**: Re-parse without re-downloading (saves API costs)
3. **Debugging**: Compare parsed vs raw data
4. **Compliance**: Retain source documents for legal reasons
5. **Cost Savings**: Don't hit external APIs repeatedly
6. **Reliability**: Local copy if source is down
7. **Performance**: Faster reprocessing from storage than from web

## Security

### Bucket Policies

```sql
-- raw-pdfs: Private (service role only)
CREATE POLICY "Service role can insert PDFs"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'raw-pdfs');

-- api-responses: Private (service role only)
CREATE POLICY "Service role can insert API responses"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'api-responses');

-- No public access to source data
```

## Migration Path

1. ✅ Create storage buckets in Supabase
2. ✅ Create `stored_files` table
3. ✅ Update `trading_disclosures` table
4. ✅ Implement `StorageManager` class
5. ✅ Update PDF parser to use storage
6. ✅ Update QuiverQuant source to use storage
7. ✅ Test with sample data
8. ✅ Deploy to production

## Summary

This storage architecture gives us:
- **Complete data lineage**: Raw → Parsed → Database
- **Reproducibility**: Re-run parsing anytime
- **Cost optimization**: Don't re-fetch data
- **Compliance**: Retain source documents
- **Debugging**: Compare outputs with inputs

**Next Step**: Create the buckets and implement StorageManager.
