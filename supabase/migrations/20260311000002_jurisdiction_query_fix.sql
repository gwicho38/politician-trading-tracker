-- Jurisdiction query fix: fast count RPC + covering indexes
-- Addresses 500 errors on trading_disclosures inner join for US (3238 politicians)
-- The inner join COUNT(*) was timing out (8s+); this replaces it with a fast subquery count.

-- ============================================================
-- 1. Index on politicians(role) for fast jurisdiction lookups.
--    Supabase FK constraints don't automatically create indexes on the
--    referenced column in the child table, but the role column on politicians
--    itself has no index. This allows fast "get all US politicians" lookups.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_politicians_role
  ON politicians(role);

-- ============================================================
-- 2. Partial index on trading_disclosures(disclosure_date DESC) for active rows.
--    Allows PostgreSQL to use an index-scan for ORDER BY disclosure_date DESC
--    LIMIT 15 queries without scanning all 131K rows. Combined with the
--    inner join, PostgreSQL can stop after finding 15 matching rows.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_td_active_disclosure_date
  ON trading_disclosures(disclosure_date DESC)
  WHERE status = 'active';

-- ============================================================
-- 3. Count function for jurisdiction-filtered disclosures.
--    PostgREST's implicit COUNT(*) on inner-join queries scans all rows
--    and times out for US (43K+ matching rows). This dedicated function
--    uses a subquery with the role index, which the planner can hash-join
--    efficiently. LANGUAGE sql (not plpgsql) avoids procedure overhead.
-- ============================================================
CREATE OR REPLACE FUNCTION count_disclosures_by_roles(
  p_roles          text[],
  p_transaction_type text  DEFAULT NULL,
  p_ticker         text    DEFAULT NULL,
  p_search         text    DEFAULT NULL,
  p_date_from      text    DEFAULT NULL,
  p_date_to        text    DEFAULT NULL
)
RETURNS bigint
LANGUAGE sql
STABLE
SECURITY DEFINER
SET statement_timeout = '8s'
AS $$
  SELECT COUNT(*)::bigint
  FROM trading_disclosures td
  WHERE td.politician_id IN (
    SELECT id FROM politicians WHERE role = ANY(p_roles)
  )
    AND td.status = 'active'
    AND (td.amount_range_min IS NOT NULL OR td.amount_range_max IS NOT NULL)
    AND (
      p_transaction_type IS NOT NULL AND td.transaction_type = p_transaction_type
      OR
      p_transaction_type IS NULL AND td.transaction_type NOT IN ('unknown', 'Unknown')
    )
    AND (p_ticker IS NULL OR td.asset_ticker ILIKE '%' || p_ticker || '%')
    AND (
      p_search IS NULL
      OR td.asset_ticker ILIKE '%' || p_search || '%'
      OR td.asset_name   ILIKE '%' || p_search || '%'
    )
    AND (p_date_from IS NULL OR td.disclosure_date >= p_date_from::date)
    AND (p_date_to   IS NULL OR td.disclosure_date <= p_date_to::date)
$$;

GRANT EXECUTE ON FUNCTION count_disclosures_by_roles(text[], text, text, text, text, text) TO anon;
GRANT EXECUTE ON FUNCTION count_disclosures_by_roles(text[], text, text, text, text, text) TO authenticated;
