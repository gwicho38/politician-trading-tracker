-- Migration: Create storage infrastructure for raw data
-- Purpose: Store PDFs, API responses, and parsed data
-- Date: 2025-11-04

-- ============================================================================
-- 1. CREATE STORAGE BUCKETS
-- ============================================================================

-- Bucket for raw PDF files
INSERT INTO storage.buckets (id, name, public)
VALUES ('raw-pdfs', 'raw-pdfs', false)
ON CONFLICT (id) DO NOTHING;

-- Bucket for API responses
INSERT INTO storage.buckets (id, name, public)
VALUES ('api-responses', 'api-responses', false)
ON CONFLICT (id) DO NOTHING;

-- Bucket for parsed/intermediate data
INSERT INTO storage.buckets (id, name, public)
VALUES ('parsed-data', 'parsed-data', false)
ON CONFLICT (id) DO NOTHING;

-- Bucket for HTML snapshots (debugging)
INSERT INTO storage.buckets (id, name, public)
VALUES ('html-snapshots', 'html-snapshots', false)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 2. CREATE STORED_FILES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS stored_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disclosure_id UUID REFERENCES trading_disclosures(id) ON DELETE SET NULL,

    -- File identification
    storage_bucket VARCHAR(50) NOT NULL CHECK (storage_bucket IN ('raw-pdfs', 'api-responses', 'parsed-data', 'html-snapshots')),
    storage_path TEXT NOT NULL,
    file_type VARCHAR(20) NOT NULL,

    -- File metadata
    file_size_bytes INTEGER,
    file_hash_sha256 VARCHAR(64),
    mime_type VARCHAR(100),

    -- Source information
    source_url TEXT,
    source_type VARCHAR(50),

    -- Processing metadata
    download_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    parse_status VARCHAR(20) DEFAULT 'pending' CHECK (parse_status IN ('pending', 'success', 'failed', 'skipped')),
    parse_date TIMESTAMPTZ,
    parse_error TEXT,
    transactions_found INTEGER DEFAULT 0,

    -- Lifecycle
    expires_at TIMESTAMPTZ,
    is_archived BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: One file per path per bucket
    UNIQUE(storage_bucket, storage_path)
);

-- ============================================================================
-- 3. CREATE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_stored_files_disclosure
    ON stored_files(disclosure_id);

CREATE INDEX IF NOT EXISTS idx_stored_files_bucket_path
    ON stored_files(storage_bucket, storage_path);

CREATE INDEX IF NOT EXISTS idx_stored_files_parse_status
    ON stored_files(parse_status)
    WHERE parse_status IN ('pending', 'failed');

CREATE INDEX IF NOT EXISTS idx_stored_files_source
    ON stored_files(source_type, download_date);

CREATE INDEX IF NOT EXISTS idx_stored_files_expires
    ON stored_files(expires_at)
    WHERE expires_at IS NOT NULL AND is_archived = FALSE;

-- ============================================================================
-- 4. UPDATE TRADING_DISCLOSURES TABLE
-- ============================================================================

-- Add columns to link disclosures to stored files
ALTER TABLE trading_disclosures
    ADD COLUMN IF NOT EXISTS source_file_id UUID REFERENCES stored_files(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS has_raw_pdf BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS has_parsed_data BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_disclosures_source_file
    ON trading_disclosures(source_file_id);

CREATE INDEX IF NOT EXISTS idx_disclosures_has_raw
    ON trading_disclosures(has_raw_pdf)
    WHERE has_raw_pdf = TRUE;

-- ============================================================================
-- 5. CREATE UPDATE TRIGGER
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_stored_files_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_stored_files_updated_at
    BEFORE UPDATE ON stored_files
    FOR EACH ROW
    EXECUTE FUNCTION update_stored_files_updated_at();

-- ============================================================================
-- 6. STORAGE BUCKET POLICIES
-- ============================================================================

-- raw-pdfs: Service role can insert/select
CREATE POLICY "Service role can upload PDFs"
    ON storage.objects FOR INSERT
    TO service_role
    WITH CHECK (bucket_id = 'raw-pdfs');

CREATE POLICY "Service role can read PDFs"
    ON storage.objects FOR SELECT
    TO service_role
    USING (bucket_id = 'raw-pdfs');

-- api-responses: Service role can insert/select
CREATE POLICY "Service role can upload API responses"
    ON storage.objects FOR INSERT
    TO service_role
    WITH CHECK (bucket_id = 'api-responses');

CREATE POLICY "Service role can read API responses"
    ON storage.objects FOR SELECT
    TO service_role
    USING (bucket_id = 'api-responses');

-- parsed-data: Service role can insert/select
CREATE POLICY "Service role can upload parsed data"
    ON storage.objects FOR INSERT
    TO service_role
    WITH CHECK (bucket_id = 'parsed-data');

CREATE POLICY "Service role can read parsed data"
    ON storage.objects FOR SELECT
    TO service_role
    USING (bucket_id = 'parsed-data');

-- html-snapshots: Service role can insert/select
CREATE POLICY "Service role can upload HTML"
    ON storage.objects FOR INSERT
    TO service_role
    WITH CHECK (bucket_id = 'html-snapshots');

CREATE POLICY "Service role can read HTML"
    ON storage.objects FOR SELECT
    TO service_role
    USING (bucket_id = 'html-snapshots');

-- ============================================================================
-- 7. HELPER FUNCTIONS
-- ============================================================================

-- Function to mark file as parsed
CREATE OR REPLACE FUNCTION mark_file_parsed(
    p_file_id UUID,
    p_transactions_count INTEGER DEFAULT 0
)
RETURNS VOID AS $$
BEGIN
    UPDATE stored_files
    SET parse_status = 'success',
        parse_date = NOW(),
        transactions_found = p_transactions_count
    WHERE id = p_file_id;
END;
$$ LANGUAGE plpgsql;

-- Function to mark file as failed
CREATE OR REPLACE FUNCTION mark_file_failed(
    p_file_id UUID,
    p_error_message TEXT
)
RETURNS VOID AS $$
BEGIN
    UPDATE stored_files
    SET parse_status = 'failed',
        parse_date = NOW(),
        parse_error = p_error_message
    WHERE id = p_file_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get files ready for parsing
CREATE OR REPLACE FUNCTION get_files_to_parse(
    p_bucket VARCHAR(50) DEFAULT 'raw-pdfs',
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    file_id UUID,
    storage_path TEXT,
    disclosure_id UUID,
    source_url TEXT,
    download_date TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sf.id,
        sf.storage_path,
        sf.disclosure_id,
        sf.source_url,
        sf.download_date
    FROM stored_files sf
    WHERE sf.storage_bucket = p_bucket
        AND sf.parse_status = 'pending'
        AND sf.expires_at IS NULL OR sf.expires_at > NOW()
    ORDER BY sf.download_date DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. CLEANUP FUNCTIONS
-- ============================================================================

-- Function to archive expired files
CREATE OR REPLACE FUNCTION archive_expired_files()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    UPDATE stored_files
    SET is_archived = TRUE
    WHERE expires_at IS NOT NULL
        AND expires_at < NOW()
        AND is_archived = FALSE;

    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. STATISTICS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW storage_statistics AS
SELECT
    storage_bucket,
    file_type,
    parse_status,
    COUNT(*) as file_count,
    SUM(file_size_bytes) as total_size_bytes,
    ROUND(SUM(file_size_bytes)::NUMERIC / 1024 / 1024, 2) as total_size_mb,
    MIN(download_date) as oldest_file,
    MAX(download_date) as newest_file,
    COUNT(DISTINCT disclosure_id) as unique_disclosures
FROM stored_files
WHERE is_archived = FALSE
GROUP BY storage_bucket, file_type, parse_status
ORDER BY storage_bucket, file_type, parse_status;

-- Grant access to statistics view
GRANT SELECT ON storage_statistics TO anon, authenticated, service_role;

-- ============================================================================
-- 10. COMMENTS
-- ============================================================================

COMMENT ON TABLE stored_files IS 'Tracks all files stored in Supabase Storage buckets';
COMMENT ON COLUMN stored_files.storage_bucket IS 'Bucket name: raw-pdfs, api-responses, parsed-data, html-snapshots';
COMMENT ON COLUMN stored_files.storage_path IS 'Full path within bucket, e.g., senate/2024/11/uuid_Name_20241101.pdf';
COMMENT ON COLUMN stored_files.parse_status IS 'Processing status: pending, success, failed, skipped';
COMMENT ON COLUMN stored_files.expires_at IS 'Auto-delete file after this date';

COMMENT ON FUNCTION get_files_to_parse IS 'Get list of files ready for parsing';
COMMENT ON FUNCTION archive_expired_files IS 'Mark expired files as archived (run daily)';
COMMENT ON VIEW storage_statistics IS 'Storage usage statistics by bucket and status';
