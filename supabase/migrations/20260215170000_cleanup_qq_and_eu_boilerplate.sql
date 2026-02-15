-- Clean up stale QuiverQuant records and EU Parliament boilerplate disclosures.
--
-- Two issues addressed:
--
-- 1. QuiverQuant records (source_document_id LIKE 'qq-%') re-appeared after
--    the Feb 13 cleanup migration because the QQ ETL ran again on Feb 11-12.
--    These records have null source_url and show "-" in the frontend Source column.
--
-- 2. EU Parliament DPI records (source_document_id LIKE 'DPI-%') were ingested
--    before the multilingual boilerplate fix (PR #167) was deployed, so
--    Croatian/Spanish/French column headers leaked into asset_name fields.
--    Rather than surgically identifying bad records, we delete ALL EU records
--    and re-trigger the EU ETL with the fixed parser for a clean re-ingestion.

BEGIN;

-- 1. Remove QuiverQuant records (re-inserted after previous cleanup)
DELETE FROM trading_disclosures
WHERE source_document_id LIKE 'qq-%';

-- Remove any older QQ batch with quiverquant.com source URLs
DELETE FROM trading_disclosures
WHERE source_url LIKE '%quiverquant.com%';

-- 2. Remove ALL EU Parliament DPI records for clean re-ingestion
DELETE FROM trading_disclosures
WHERE source_document_id LIKE 'DPI-%';

COMMIT;

-- Refresh materialized views after bulk deletion
SELECT refresh_top_tickers();

-- Update table statistics for query planner
ANALYZE trading_disclosures;
