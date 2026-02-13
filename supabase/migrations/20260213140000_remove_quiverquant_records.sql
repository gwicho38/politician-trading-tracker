-- Remove QuiverQuant-sourced records from trading_disclosures.
--
-- QuiverQuant data is used internally for validation only and should
-- not be published publicly. All public disclosure data should come
-- directly from official government sources (House Clerk, Senate EFD).
--
-- Two populations of QQ records exist:
-- 1. qq-prefixed source_document_id (e.g., qq-P000197-2026-01-16-GOOGL)
-- 2. Older batch with source_url pointing to quiverquant.com

-- Remove QQ-prefixed records
DELETE FROM trading_disclosures
WHERE source_document_id LIKE 'qq-%';

-- Remove older QQ batch (source_url = quiverquant.com)
DELETE FROM trading_disclosures
WHERE source_url LIKE '%quiverquant.com%';

-- Refresh materialized views after data removal
SELECT refresh_top_tickers();

-- Update statistics
ANALYZE trading_disclosures;
