-- Migration: Enhanced House Financial Disclosure Parsing
-- Issue: #16
-- Phase 1: Add new fields to trading_disclosures table and create supporting tables

-- ============================================================================
-- Part 1: Enhance trading_disclosures table
-- ============================================================================

-- Add filing metadata fields
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS filer_id VARCHAR(20),
ADD COLUMN IF NOT EXISTS filing_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS period_start_date DATE,
ADD COLUMN IF NOT EXISTS period_end_date DATE;

-- Add transaction detail fields
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS quantity DECIMAL(20,4),
ADD COLUMN IF NOT EXISTS price_per_unit DECIMAL(20,4),
ADD COLUMN IF NOT EXISTS is_range BOOLEAN DEFAULT false;

-- Add owner attribution
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS asset_owner VARCHAR(20) CHECK (asset_owner IN ('SELF', 'SPOUSE', 'JOINT', 'DEPENDENT'));

-- Add additional context fields
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS comments TEXT,
ADD COLUMN IF NOT EXISTS ticker_confidence_score DECIMAL(3,2) CHECK (ticker_confidence_score >= 0 AND ticker_confidence_score <= 1);

-- Add validation and quality tracking
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS validation_flags JSONB,
ADD COLUMN IF NOT EXISTS raw_pdf_text TEXT;

-- Add index for common queries
CREATE INDEX IF NOT EXISTS idx_disclosures_filer_id ON trading_disclosures(filer_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_filing_date ON trading_disclosures(filing_date);
CREATE INDEX IF NOT EXISTS idx_disclosures_asset_owner ON trading_disclosures(asset_owner);
CREATE INDEX IF NOT EXISTS idx_disclosures_ticker_confidence ON trading_disclosures(ticker_confidence_score)
  WHERE ticker_confidence_score IS NOT NULL;

-- ============================================================================
-- Part 2: Create capital_gains table
-- ============================================================================

CREATE TABLE IF NOT EXISTS capital_gains (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  politician_id UUID REFERENCES politicians(id) ON DELETE CASCADE,
  disclosure_id UUID REFERENCES trading_disclosures(id) ON DELETE CASCADE,

  -- Asset information
  asset_name VARCHAR(500) NOT NULL,
  asset_ticker VARCHAR(20),

  -- Transaction dates
  date_acquired DATE,
  date_sold DATE NOT NULL,

  -- Gain information
  gain_type VARCHAR(20) CHECK (gain_type IN ('SHORT_TERM', 'LONG_TERM')),
  gain_amount DECIMAL(15,2),

  -- Owner attribution
  asset_owner VARCHAR(20) CHECK (asset_owner IN ('SELF', 'SPOUSE', 'JOINT', 'DEPENDENT')),

  -- Additional context
  comments TEXT,
  raw_data JSONB,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Constraints
  CONSTRAINT valid_date_sequence CHECK (date_sold >= date_acquired OR date_acquired IS NULL)
);

-- Indexes for capital_gains
CREATE INDEX IF NOT EXISTS idx_capital_gains_politician ON capital_gains(politician_id);
CREATE INDEX IF NOT EXISTS idx_capital_gains_disclosure ON capital_gains(disclosure_id);
CREATE INDEX IF NOT EXISTS idx_capital_gains_date_sold ON capital_gains(date_sold);
CREATE INDEX IF NOT EXISTS idx_capital_gains_ticker ON capital_gains(asset_ticker)
  WHERE asset_ticker IS NOT NULL;

-- ============================================================================
-- Part 3: Create asset_holdings table
-- ============================================================================

CREATE TABLE IF NOT EXISTS asset_holdings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  politician_id UUID REFERENCES politicians(id) ON DELETE CASCADE,

  -- Filing information
  filing_date DATE NOT NULL,
  filing_doc_id VARCHAR(50),

  -- Asset information
  asset_name VARCHAR(500) NOT NULL,
  asset_type VARCHAR(10), -- [OT], [BA], [ST], [MF], etc.
  asset_ticker VARCHAR(20),
  asset_description TEXT,

  -- Owner attribution
  owner VARCHAR(20) CHECK (owner IN ('SELF', 'SPOUSE', 'JOINT', 'DEPENDENT')),

  -- Valuation
  value_low DECIMAL(15,2),
  value_high DECIMAL(15,2),
  value_category VARCHAR(50), -- e.g., "$1,001-$15,000"

  -- Income information
  income_type VARCHAR(100), -- Dividends, Interest, Rent, etc.
  current_year_income DECIMAL(15,2),
  preceding_year_income DECIMAL(15,2),

  -- Additional context
  comments TEXT,
  raw_data JSONB,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Constraints
  UNIQUE(politician_id, filing_date, asset_name, owner),
  CONSTRAINT valid_value_range CHECK (value_high >= value_low OR value_low IS NULL OR value_high IS NULL)
);

-- Indexes for asset_holdings
CREATE INDEX IF NOT EXISTS idx_asset_holdings_politician ON asset_holdings(politician_id);
CREATE INDEX IF NOT EXISTS idx_asset_holdings_filing_date ON asset_holdings(filing_date);
CREATE INDEX IF NOT EXISTS idx_asset_holdings_ticker ON asset_holdings(asset_ticker)
  WHERE asset_ticker IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_asset_holdings_asset_type ON asset_holdings(asset_type);

-- ============================================================================
-- Part 4: Create helper functions
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to capital_gains
DROP TRIGGER IF EXISTS update_capital_gains_updated_at ON capital_gains;
CREATE TRIGGER update_capital_gains_updated_at
  BEFORE UPDATE ON capital_gains
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to asset_holdings
DROP TRIGGER IF EXISTS update_asset_holdings_updated_at ON asset_holdings;
CREATE TRIGGER update_asset_holdings_updated_at
  BEFORE UPDATE ON asset_holdings
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Part 5: Add comments for documentation
-- ============================================================================

COMMENT ON COLUMN trading_disclosures.filer_id IS 'House disclosure system filer ID (e.g., 10072333)';
COMMENT ON COLUMN trading_disclosures.filing_date IS 'Date the form was filed with the House';
COMMENT ON COLUMN trading_disclosures.period_start_date IS 'Start of reporting period covered by filing';
COMMENT ON COLUMN trading_disclosures.period_end_date IS 'End of reporting period covered by filing';
COMMENT ON COLUMN trading_disclosures.quantity IS 'Number of shares/units traded';
COMMENT ON COLUMN trading_disclosures.price_per_unit IS 'Price per share (often omitted in disclosures)';
COMMENT ON COLUMN trading_disclosures.is_range IS 'Whether transaction value is reported as range vs exact amount';
COMMENT ON COLUMN trading_disclosures.asset_owner IS 'Who owns the asset: SELF, SPOUSE, JOINT, or DEPENDENT';
COMMENT ON COLUMN trading_disclosures.comments IS 'Any notes or clarifications from the filing';
COMMENT ON COLUMN trading_disclosures.ticker_confidence_score IS 'Confidence score (0-1) for automated ticker resolution';
COMMENT ON COLUMN trading_disclosures.validation_flags IS 'JSON object storing validation warnings and errors';
COMMENT ON COLUMN trading_disclosures.raw_pdf_text IS 'Raw text extracted from PDF for debugging/reprocessing';

COMMENT ON TABLE capital_gains IS 'Capital gains reported in House financial disclosures';
COMMENT ON TABLE asset_holdings IS 'Asset holdings and unearned income (Part V of disclosure forms)';
