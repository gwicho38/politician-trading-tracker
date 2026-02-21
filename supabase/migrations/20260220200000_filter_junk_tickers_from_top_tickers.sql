-- Filter non-stock asset codes and filing metadata from top_tickers materialized view.
-- Junk tickers (IRA, MF, RP, OT, etc.) dominate the "Most Traded Tickers" dashboard
-- because House/Senate filings encode asset type codes in the asset_ticker field.

-- Step 1: Drop existing materialized view and indexes
DROP MATERIALIZED VIEW IF EXISTS top_tickers;

-- Step 2: Recreate with filters excluding junk tickers
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
      'MF',    -- Mutual Fund (category code, not ticker)
      'RP',    -- Rental Property
      'OT',    -- Other
      'OF',    -- Filing status / Other Financial
      'EF',    -- Exchange Fund (category code, not ticker)
      'WU',    -- Whole/Universal Life Insurance
      'SEP',   -- SEP IRA
      'CT',    -- Crypto Token (category code)
      'IH',    -- Investment Holding (category code)
      'ST',    -- Stock category tag (not a ticker)
      'JT',    -- Joint Trust ownership prefix
      'SP'     -- Sub-holding / Special Purpose prefix
    )
    -- Exclude location codes (name starts with "L:" or "LOCATION:")
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

-- Step 3: Recreate indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_top_tickers_ticker ON top_tickers(ticker);
CREATE INDEX IF NOT EXISTS idx_top_tickers_trade_count ON top_tickers(trade_count DESC);

-- Step 4: Grant access
GRANT SELECT ON top_tickers TO authenticated;
GRANT SELECT ON top_tickers TO anon;
GRANT SELECT ON top_tickers TO service_role;

-- Step 5: Refresh function (unchanged)
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

COMMENT ON MATERIALIZED VIEW top_tickers IS 'Pre-computed top tickers by trade count, excluding non-stock asset codes (IRA, MF, RP, etc.) and filing metadata. Refresh with: SELECT refresh_top_tickers()';
