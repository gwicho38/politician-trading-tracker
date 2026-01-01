-- Top Tickers View: Server-side aggregation for performance
-- Replaces client-side aggregation that fetched ALL disclosures

CREATE OR REPLACE VIEW top_tickers AS
SELECT
  UPPER(asset_ticker) as ticker,
  asset_name as name,
  COUNT(*) as trade_count,
  SUM((COALESCE(amount_range_min, 0) + COALESCE(amount_range_max, 0)) / 2) as total_volume
FROM trading_disclosures
WHERE status = 'active'
  AND asset_ticker IS NOT NULL
  AND asset_ticker != ''
GROUP BY UPPER(asset_ticker), asset_name
ORDER BY trade_count DESC;

-- Grant access to the view
GRANT SELECT ON top_tickers TO authenticated;
GRANT SELECT ON top_tickers TO anon;

COMMENT ON VIEW top_tickers IS 'Aggregated view of top tickers by trade count for dashboard performance';
