-- Final cleanup of QuiverQuant records.
--
-- Previous cleanups (Feb 13, Feb 15) deleted QQ records but the Elixir
-- scheduler had a QuiverQuant ETL job config that re-imported them every
-- 6 hours. The ETL job config has been removed from application.ex in the
-- same commit as this migration.

BEGIN;

-- Remove all QuiverQuant records by source_document_id pattern
DELETE FROM trading_disclosures
WHERE source_document_id LIKE 'qq-%';

-- Remove any records with quiverquant.com source URLs
DELETE FROM trading_disclosures
WHERE source_url LIKE '%quiverquant.com%';

COMMIT;

-- Refresh materialized views after bulk deletion
SELECT refresh_top_tickers();

-- Update table statistics for query planner
ANALYZE trading_disclosures;
