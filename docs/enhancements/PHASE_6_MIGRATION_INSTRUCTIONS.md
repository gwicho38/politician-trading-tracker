# Phase 6: Database Migration Instructions

## Overview

Phase 6 integrates the enhanced PDF parsing capabilities from Phase 5 into the database layer. This requires applying a database migration to add new columns for enhanced disclosure data.

## Migration File

Location: `/Users/lefv/repos/politician-trading-tracker/migrations/001_enhanced_disclosure_fields.sql`

## What the Migration Does

1. **Adds 12 new columns to `trading_disclosures` table:**
   - `filer_id` - House disclosure document ID
   - `filing_date` - Date the disclosure was filed
   - `quantity` - Number of shares/units (if specified)
   - `ticker_confidence_score` - Confidence score for ticker resolution (0.0-1.0)
   - `asset_owner` - Who owns the asset (SELF, SPOUSE, JOINT, DEPENDENT)
   - `specific_owner_text` - Specific owner text from disclosure (e.g., "DG Trust")
   - `asset_type_code` - House disclosure asset type code ([ST], [MF], etc.)
   - `notification_date` - Date transaction was notified
   - `filing_status` - Filing status (New, Amendment, etc.)
   - `value_low` - Lower bound of value range
   - `value_high` - Upper bound of value range
   - `is_range` - Whether value is a range or exact amount

2. **Creates two new tables:**
   - `capital_gains` - Capital gains from House financial disclosures
   - `asset_holdings` - Asset holdings from Part V of disclosures

## How to Apply

### Option 1: Supabase Dashboard (Recommended)

1. Go to your Supabase Dashboard
2. Navigate to: **SQL Editor**
3. Click **New query**
4. Copy the contents of `/migrations/001_enhanced_disclosure_fields.sql`
5. Paste into the SQL Editor
6. Click **Run**

### Option 2: psql Command Line

```bash
# Get your Supabase connection details from the dashboard
# Database Settings → Connection Info → Connection String

psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres" \
  -f /Users/lefv/repos/politician-trading-tracker/migrations/001_enhanced_disclosure_fields.sql
```

### Option 3: Programmatic (via Python)

The migration cannot be applied programmatically via the Supabase Python client because it doesn't support direct SQL execution. You must use Option 1 or 2.

## Verification

After applying the migration, verify it worked:

```sql
-- Check that new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'trading_disclosures'
  AND column_name IN (
    'filer_id', 'filing_date', 'ticker_confidence_score',
    'asset_owner', 'asset_type_code', 'notification_date'
  );

-- Check that new tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('capital_gains', 'asset_holdings');
```

## What Changes Were Made to Code

### 1. Models (`src/models.py`)

Added 9 new fields to the `TradingDisclosure` dataclass:
- `filer_id`
- `filing_date`
- `ticker_confidence_score`
- `asset_owner`
- `specific_owner_text`
- `asset_type_code`
- `notification_date`
- `filing_status`
- `quantity`

### 2. Database Layer (`src/politician_trading/scrapers/seed_database.py`)

Updated `upsert_trading_disclosures()` function to include enhanced fields when inserting/updating records.

### 3. Scraper Integration (`src/politician_trading/scrapers/scrapers.py`)

Updated `scrape_house_disclosures()` to pass enhanced fields when creating `TradingDisclosure` objects from parsed transaction data.

## Testing

After applying the migration, run the integration test:

```bash
python /tmp/test_phase6_integration.py
```

This will:
1. Scrape 5 House disclosures with enhanced parsing
2. Create TradingDisclosure objects with enhanced fields
3. Upsert to database
4. Verify enhanced fields are persisted

## Expected Results

- Enhanced parser extracts tickers, asset types, owners, dates, and amounts
- TradingDisclosure objects contain all enhanced fields
- Database stores all enhanced fields
- Query results show populated enhanced columns

## Rollback (if needed)

If you need to rollback the migration:

```sql
-- Remove new columns
ALTER TABLE trading_disclosures
  DROP COLUMN IF EXISTS filer_id,
  DROP COLUMN IF EXISTS filing_date,
  DROP COLUMN IF EXISTS quantity,
  DROP COLUMN IF EXISTS ticker_confidence_score,
  DROP COLUMN IF EXISTS asset_owner,
  DROP COLUMN IF EXISTS specific_owner_text,
  DROP COLUMN IF EXISTS asset_type_code,
  DROP COLUMN IF EXISTS notification_date,
  DROP COLUMN IF EXISTS filing_status,
  DROP COLUMN IF EXISTS value_low,
  DROP COLUMN IF EXISTS value_high,
  DROP COLUMN IF EXISTS is_range;

-- Remove new tables
DROP TABLE IF EXISTS capital_gains;
DROP TABLE IF EXISTS asset_holdings;
```

## Next Steps

After Phase 6 is complete:

1. Enable `parse_pdfs=True` in production workflow
2. Set `max_pdfs_per_run` to control rate (e.g., 100 PDFs per run)
3. Schedule background worker for continuous PDF parsing
4. Monitor database for enhanced field population
5. Use enhanced fields in UI and analytics

## Files Modified

- ✅ `/migrations/001_enhanced_disclosure_fields.sql` - Migration SQL
- ✅ `/src/models.py` - Added enhanced fields to TradingDisclosure
- ✅ `/src/politician_trading/scrapers/seed_database.py` - Updated upsert logic
- ✅ `/src/politician_trading/scrapers/scrapers.py` - Updated disclosure creation
- ✅ `/tmp/test_phase6_integration.py` - Integration test script
- ✅ `/tmp/phase6_migration_instructions.md` - This file

## Support

If you encounter issues:

1. Check Supabase Dashboard → Database → Logs for errors
2. Verify migration SQL syntax
3. Ensure you have proper database permissions
4. Contact Supabase support if connection issues persist
