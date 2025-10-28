-- Politician Trading Data Schema for Supabase
-- Execute this in your Supabase SQL editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Politicians table
CREATE TABLE IF NOT EXISTS politicians (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL,
    party VARCHAR(50),
    state_or_country VARCHAR(100),
    district VARCHAR(50),
    term_start TIMESTAMPTZ,
    term_end TIMESTAMPTZ,
    bioguide_id VARCHAR(20),
    eu_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trading disclosures table
CREATE TABLE IF NOT EXISTS trading_disclosures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politician_id UUID NOT NULL REFERENCES politicians(id),
    transaction_date TIMESTAMPTZ NOT NULL,
    disclosure_date TIMESTAMPTZ NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    asset_name VARCHAR(200) NOT NULL,
    asset_ticker VARCHAR(20),
    asset_type VARCHAR(50),
    amount_range_min DECIMAL(15,2),
    amount_range_max DECIMAL(15,2),
    amount_exact DECIMAL(15,2),
    source_url VARCHAR(500),
    source_document_id VARCHAR(100),
    raw_data JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    processing_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data pull jobs table
CREATE TABLE IF NOT EXISTS data_pull_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    records_found INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_new INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    config_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    region VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_successful_pull TIMESTAMPTZ,
    last_attempt TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    request_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_politicians_name ON politicians(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_politicians_role ON politicians(role);
CREATE INDEX IF NOT EXISTS idx_politicians_bioguide ON politicians(bioguide_id);

CREATE INDEX IF NOT EXISTS idx_disclosures_politician ON trading_disclosures(politician_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_transaction_date ON trading_disclosures(transaction_date);
CREATE INDEX IF NOT EXISTS idx_disclosures_disclosure_date ON trading_disclosures(disclosure_date);
CREATE INDEX IF NOT EXISTS idx_disclosures_asset_ticker ON trading_disclosures(asset_ticker);
CREATE INDEX IF NOT EXISTS idx_disclosures_status ON trading_disclosures(status);

CREATE INDEX IF NOT EXISTS idx_jobs_type ON data_pull_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON data_pull_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON data_pull_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_sources_region ON data_sources(region);
CREATE INDEX IF NOT EXISTS idx_sources_active ON data_sources(is_active);

-- Unique constraints to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_politicians_unique 
ON politicians(first_name, last_name, role, state_or_country);

CREATE UNIQUE INDEX IF NOT EXISTS idx_disclosures_unique
ON trading_disclosures(politician_id, transaction_date, asset_name, transaction_type, disclosure_date);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
DROP TRIGGER IF EXISTS update_politicians_updated_at ON politicians;
CREATE TRIGGER update_politicians_updated_at 
    BEFORE UPDATE ON politicians 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_disclosures_updated_at ON trading_disclosures;
CREATE TRIGGER update_disclosures_updated_at 
    BEFORE UPDATE ON trading_disclosures 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sources_updated_at ON data_sources;
CREATE TRIGGER update_sources_updated_at 
    BEFORE UPDATE ON data_sources 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data sources
INSERT INTO data_sources (name, url, source_type, region, request_config) VALUES
('US House Financial Disclosures', 'https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure', 'official', 'us', '{}'),
('US Senate Financial Disclosures', 'https://efdsearch.senate.gov/search/', 'official', 'us', '{}'),
('EU Parliament Declarations', 'https://www.europarl.europa.eu/meps/en/declarations', 'official', 'eu', '{}')
ON CONFLICT DO NOTHING;

-- Create a view for recent trading activity
CREATE OR REPLACE VIEW recent_trading_activity AS
SELECT 
    p.full_name,
    p.role,
    p.party,
    p.state_or_country,
    td.transaction_date,
    td.disclosure_date,
    td.transaction_type,
    td.asset_name,
    td.asset_ticker,
    td.amount_range_min,
    td.amount_range_max,
    td.amount_exact,
    td.created_at
FROM trading_disclosures td
JOIN politicians p ON td.politician_id = p.id
ORDER BY td.disclosure_date DESC, td.created_at DESC;

-- Create a view for job status summary
CREATE OR REPLACE VIEW job_status_summary AS
SELECT 
    job_type,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_jobs,
    MAX(started_at) as last_run,
    SUM(records_new) as total_new_records,
    SUM(records_updated) as total_updated_records
FROM data_pull_jobs
GROUP BY job_type;

-- RLS (Row Level Security) policies - customize based on your needs
ALTER TABLE politicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_disclosures ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_pull_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (adjust as needed)
CREATE POLICY "Allow all for authenticated users" ON politicians
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON trading_disclosures
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON data_pull_jobs
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON data_sources
    FOR ALL USING (auth.role() = 'authenticated');

-- Grant permissions to anon role for read access
GRANT SELECT ON recent_trading_activity TO anon;
GRANT SELECT ON job_status_summary TO anon;

-- Comments for documentation
COMMENT ON TABLE politicians IS 'Stores information about politicians whose trading we are tracking';
COMMENT ON TABLE trading_disclosures IS 'Individual trading disclosures/transactions by politicians';
COMMENT ON TABLE data_pull_jobs IS 'Tracks the status and results of data pulling jobs';
COMMENT ON TABLE data_sources IS 'Configuration and status of various data sources';

COMMENT ON COLUMN politicians.bioguide_id IS 'US Congress biographical guide identifier';
COMMENT ON COLUMN politicians.eu_id IS 'EU Parliament member identifier';
COMMENT ON COLUMN trading_disclosures.raw_data IS 'Original data from source for debugging/audit';
COMMENT ON COLUMN data_pull_jobs.config_snapshot IS 'Configuration used for this job run';