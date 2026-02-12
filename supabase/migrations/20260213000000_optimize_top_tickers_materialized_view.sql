-- Fix production 500 errors caused by statement timeout on top_tickers view
-- Root cause: The regular VIEW must aggregate ALL 133K+ rows with MODE() on every query.
-- Under anon role's strict timeout limits, this consistently exceeds the threshold.
-- Solution: Convert to MATERIALIZED VIEW (pre-computed) with periodic refresh.

-- Step 1: Drop the regular view
DROP VIEW IF EXISTS top_tickers;

-- Step 2: Create materialized view (pre-computes the aggregation)
CREATE MATERIALIZED VIEW IF NOT EXISTS top_tickers AS
SELECT
  ticker,
  name,
  trade_count,
  total_volume
FROM (
  SELECT
    UPPER(asset_ticker) as ticker,
    MODE() WITHIN GROUP (ORDER BY asset_name) as name,
    COUNT(*) as trade_count,
    SUM((COALESCE(amount_range_min, 0) + COALESCE(amount_range_max, 0)) / 2) as total_volume
  FROM trading_disclosures
  WHERE status = 'active'
    AND asset_ticker IS NOT NULL
    AND asset_ticker != ''
  GROUP BY UPPER(asset_ticker)
) subq
ORDER BY trade_count DESC;

-- Step 3: Add unique index on ticker (required for REFRESH CONCURRENTLY)
CREATE UNIQUE INDEX IF NOT EXISTS idx_top_tickers_ticker ON top_tickers(ticker);

-- Step 4: Add index on trade_count for ORDER BY performance
CREATE INDEX IF NOT EXISTS idx_top_tickers_trade_count ON top_tickers(trade_count DESC);

-- Step 5: Grant access (same as before)
GRANT SELECT ON top_tickers TO authenticated;
GRANT SELECT ON top_tickers TO anon;
GRANT SELECT ON top_tickers TO service_role;

-- Step 6: Add compound indexes on trading_disclosures for common frontend query patterns
-- Covers: WHERE status='active' ORDER BY disclosure_date DESC (main listing query)
CREATE INDEX IF NOT EXISTS idx_disclosures_status_disclosure_date
  ON trading_disclosures(status, disclosure_date DESC);

-- Covers: WHERE status='active' AND asset_ticker IS NOT NULL (top_tickers refresh)
CREATE INDEX IF NOT EXISTS idx_disclosures_status_ticker
  ON trading_disclosures(status, asset_ticker)
  WHERE asset_ticker IS NOT NULL AND asset_ticker != '';

-- Covers: WHERE status='active' AND (amount_range_min IS NOT NULL OR amount_range_max IS NOT NULL)
-- Partial index for the OR condition used by the frontend amount filter
CREATE INDEX IF NOT EXISTS idx_disclosures_status_has_amount
  ON trading_disclosures(status, disclosure_date DESC)
  WHERE amount_range_min IS NOT NULL OR amount_range_max IS NOT NULL;

-- Step 7: Create a function to refresh the materialized view (callable from ETL or cron)
CREATE OR REPLACE FUNCTION refresh_top_tickers()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY top_tickers;
END;
$$;

-- Grant execute to service_role (ETL uses this role)
GRANT EXECUTE ON FUNCTION refresh_top_tickers() TO service_role;

-- Step 8: Update table statistics for the query planner
ANALYZE trading_disclosures;
ANALYZE politicians;

COMMENT ON MATERIALIZED VIEW top_tickers IS 'Pre-computed aggregation of top tickers by trade count. Refresh with: SELECT refresh_top_tickers()';
