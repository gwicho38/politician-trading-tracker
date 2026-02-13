-- Backfill source_url for QuiverQuant records that have NULL source_url.
--
-- QuiverQuant ETL previously set source_url to NULL because the API
-- doesn't provide direct PDF links. We now link to the official
-- government disclosure search pages based on politician chamber/role.
--
-- House Representatives -> House Clerk Financial Disclosure search
-- Senators -> Senate EFD (Electronic Financial Disclosure) search

UPDATE trading_disclosures td
SET source_url = CASE
    WHEN p.role = 'Senator' THEN 'https://efdsearch.senate.gov/search/'
    ELSE 'https://disclosures-clerk.house.gov/PublicSearch'
END
FROM politicians p
WHERE td.politician_id = p.id
  AND td.source_url IS NULL
  AND td.source_document_id LIKE 'qq-%';
