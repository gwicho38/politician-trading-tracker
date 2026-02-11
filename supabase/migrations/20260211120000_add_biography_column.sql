-- Add biography columns to politicians table
-- Stores AI-generated or template-based biographies to avoid
-- re-generating them on every modal open in the UI.

ALTER TABLE politicians
ADD COLUMN IF NOT EXISTS biography TEXT,
ADD COLUMN IF NOT EXISTS biography_updated_at TIMESTAMPTZ;

COMMENT ON COLUMN politicians.biography IS 'AI-generated or template-based biography';
COMMENT ON COLUMN politicians.biography_updated_at IS 'When the biography was last generated';
