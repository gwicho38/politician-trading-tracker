-- Fix: Revert generic search page URLs on QuiverQuant validation records.
--
-- QuiverQuant is used for validation only, not as a primary data source.
-- The previous migration incorrectly set generic search page URLs on QQ
-- records. The real source_url should come from direct House/Senate ETL
-- scraping which provides actual PDF disclosure links.
--
-- Step 1: Revert generic URLs back to NULL for QQ records
-- Step 2: For QQ records that have a matching House/Senate counterpart
--         (same politician, date, ticker, type), copy the real PDF URL

-- Step 1: Clear the generic search page URLs from QQ records
UPDATE trading_disclosures
SET source_url = NULL
WHERE source_document_id LIKE 'qq-%'
  AND (
    source_url = 'https://disclosures-clerk.house.gov/PublicSearch'
    OR source_url = 'https://efdsearch.senate.gov/search/'
  );

-- Step 2: Copy real PDF URLs from matching House/Senate records
-- Match on: same politician, same transaction date, same ticker, same type
UPDATE trading_disclosures qq
SET source_url = match.source_url
FROM trading_disclosures match
WHERE qq.source_document_id LIKE 'qq-%'
  AND qq.source_url IS NULL
  AND match.source_document_id NOT LIKE 'qq-%'
  AND match.source_url IS NOT NULL
  AND qq.politician_id = match.politician_id
  AND qq.transaction_date = match.transaction_date
  AND qq.asset_ticker = match.asset_ticker
  AND qq.transaction_type = match.transaction_type;
