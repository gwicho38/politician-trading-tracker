-- v2: Additional junk ticker filters (ST, JT, SP, LOCATION: prefix)
-- The v1 migration missed these patterns found in production data.

DROP MATERIALIZED VIEW IF EXISTS top_tickers;

CREATE MATERIALIZED VIEW top_tickers AS
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
    -- Exclude known non-stock asset category codes
    AND UPPER(asset_ticker) NOT IN (
      'IRA',   -- Individual Retirement Account
      'MF',    -- Mutual Fund (category code)
      'RP',    -- Rental Property
      'OT',    -- Other
      'OF',    -- Filing status / Other Financial
      'EF',    -- Exchange Fund (category code)
      'WU',    -- Whole/Universal Life Insurance
      'SEP',   -- SEP IRA
      'CT',    -- Crypto Token (category code)
      'IH',    -- Investment Holding (category code)
      'ST',    -- Stock category tag (not a ticker)
      'JT',    -- Joint Trust ownership prefix
      'SP'     -- Sub-holding / Special Purpose prefix
    )
    -- Exclude location codes
    AND asset_name NOT LIKE 'L:%'
    AND asset_name NOT ILIKE 'location:%'
    -- Exclude filing metadata leaked into asset_name
    AND asset_name NOT ILIKE '%filing status%'
    AND asset_name NOT ILIKE 'description:%'
    AND asset_name NOT LIKE 'D: %'
    -- Exclude bracket-only names like "[MF]", "[OT]"
    AND asset_name !~ '^\[[A-Z]{2,4}\]$'
    -- Exclude joint trust / sub-holding prefixed names
    AND asset_name NOT ILIKE 'JT %'
    AND asset_name NOT ILIKE 'SP %'
  GROUP BY UPPER(asset_ticker)
) subq
ORDER BY trade_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_top_tickers_ticker ON top_tickers(ticker);
CREATE INDEX IF NOT EXISTS idx_top_tickers_trade_count ON top_tickers(trade_count DESC);

GRANT SELECT ON top_tickers TO authenticated;
GRANT SELECT ON top_tickers TO anon;
GRANT SELECT ON top_tickers TO service_role;

CREATE OR REPLACE FUNCTION refresh_top_tickers()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY top_tickers;
END;
$$;

GRANT EXECUTE ON FUNCTION refresh_top_tickers() TO service_role;
