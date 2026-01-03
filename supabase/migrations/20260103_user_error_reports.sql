-- Migration: Create user_error_reports table for data quality feedback
-- Allows authenticated users to report discrepancies between parsed data and source PDFs

-- Create the user_error_reports table
CREATE TABLE IF NOT EXISTS public.user_error_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  disclosure_id UUID NOT NULL REFERENCES trading_disclosures(id) ON DELETE CASCADE,

  -- Error details
  error_type VARCHAR(50) NOT NULL CHECK (
    error_type IN ('wrong_amount', 'wrong_date', 'wrong_ticker', 'wrong_politician', 'other')
  ),
  description TEXT NOT NULL,

  -- Snapshot of disclosure data at report time (for reference when reviewing)
  disclosure_snapshot JSONB NOT NULL DEFAULT '{}',

  -- Status tracking (for admin review in Supabase dashboard)
  status VARCHAR(20) DEFAULT 'pending' CHECK (
    status IN ('pending', 'reviewed', 'fixed', 'invalid')
  ),
  admin_notes TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_user_error_reports_disclosure_id
  ON public.user_error_reports(disclosure_id);

CREATE INDEX IF NOT EXISTS idx_user_error_reports_user_id
  ON public.user_error_reports(user_id);

CREATE INDEX IF NOT EXISTS idx_user_error_reports_status
  ON public.user_error_reports(status);

CREATE INDEX IF NOT EXISTS idx_user_error_reports_created_at
  ON public.user_error_reports(created_at DESC);

-- Conditional index for pending reports (most common admin query)
CREATE INDEX IF NOT EXISTS idx_user_error_reports_pending
  ON public.user_error_reports(created_at DESC)
  WHERE status = 'pending';

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_user_error_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_error_reports_updated_at
  ON public.user_error_reports;

CREATE TRIGGER trigger_update_user_error_reports_updated_at
  BEFORE UPDATE ON public.user_error_reports
  FOR EACH ROW
  EXECUTE FUNCTION update_user_error_reports_updated_at();

-- Enable Row Level Security
ALTER TABLE public.user_error_reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Users can view their own reports
DROP POLICY IF EXISTS "Users can view their own error reports" ON public.user_error_reports;
CREATE POLICY "Users can view their own error reports"
  ON public.user_error_reports
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can create their own reports
DROP POLICY IF EXISTS "Users can create their own error reports" ON public.user_error_reports;
CREATE POLICY "Users can create their own error reports"
  ON public.user_error_reports
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Service role has full access (for Supabase dashboard admin review)
DROP POLICY IF EXISTS "Service role has full access to error reports" ON public.user_error_reports;
CREATE POLICY "Service role has full access to error reports"
  ON public.user_error_reports
  FOR ALL
  USING (auth.role() = 'service_role');

-- Add comment to table for documentation
COMMENT ON TABLE public.user_error_reports IS
  'User-submitted error reports for data quality issues in trading disclosures. Review in Supabase dashboard.';

COMMENT ON COLUMN public.user_error_reports.disclosure_snapshot IS
  'Snapshot of the disclosure data at report time for reference during review';

COMMENT ON COLUMN public.user_error_reports.error_type IS
  'Category of error: wrong_amount, wrong_date, wrong_ticker, wrong_politician, or other';
