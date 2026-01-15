-- Fix top_tickers view to properly deduplicate by ticker only
-- Previously grouped by (ticker, name) which caused duplicates when
-- the same ticker had different name variations

DROP VIEW IF EXISTS top_tickers;

CREATE OR REPLACE VIEW top_tickers AS
SELECT
  ticker,
  name,
  trade_count,
  total_volume
FROM (
  SELECT
    UPPER(asset_ticker) as ticker,
    -- Pick the most common name for this ticker
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

-- Grant access to the view
GRANT SELECT ON top_tickers TO authenticated;
GRANT SELECT ON top_tickers TO anon;
GRANT SELECT ON top_tickers TO service_role;

COMMENT ON VIEW top_tickers IS 'Aggregated view of top tickers by trade count (deduplicated by ticker)';
