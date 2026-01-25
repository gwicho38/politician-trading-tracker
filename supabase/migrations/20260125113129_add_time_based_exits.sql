-- Migration: Add Time-Based Position Exits
-- 
-- Rationale: Politician trade disclosures are delayed 30-45 days. Holding positions
-- beyond 60 days means trading on 90-105 day old information, which is too stale.
-- This migration adds a max_hold_days parameter to automatically exit old positions.
--
-- Changes:
-- - Add max_hold_days to reference_portfolio_config (default: 60 days)
-- - Positions will be auto-closed after max_hold_days via exit check job

-- Add max_hold_days column to config table
ALTER TABLE public.reference_portfolio_config
ADD COLUMN IF NOT EXISTS max_hold_days INTEGER DEFAULT 60;

-- Set default value for existing config
UPDATE public.reference_portfolio_config
SET max_hold_days = 60
WHERE max_hold_days IS NULL;

-- Add comment explaining the parameter
COMMENT ON COLUMN public.reference_portfolio_config.max_hold_days IS 
  'Maximum number of days to hold a position before auto-closing. Default 60 days accounts for 30-45 day disclosure lag.';

-- Create index on entry_date for efficient time-based queries
CREATE INDEX IF NOT EXISTS idx_positions_entry_date_open 
ON public.reference_portfolio_positions(entry_date, is_open) 
WHERE is_open = true;

COMMENT ON INDEX idx_positions_entry_date_open IS 
  'Optimize queries for finding old positions that need time-based exits';
