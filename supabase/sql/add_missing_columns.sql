-- Add missing columns expected by frontend
-- Run in Supabase SQL Editor

-- Politicians table - add missing columns
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS total_trades INTEGER DEFAULT 0;
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS total_volume DECIMAL(20,2) DEFAULT 0;
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- Jurisdictions table - add flag column
ALTER TABLE jurisdictions ADD COLUMN IF NOT EXISTS flag VARCHAR(10);

-- Update jurisdiction flags
UPDATE jurisdictions SET flag = '🇺🇸' WHERE code IN ('us_house', 'us_senate');
UPDATE jurisdictions SET flag = '🇬🇧' WHERE code = 'uk_parliament';
UPDATE jurisdictions SET flag = '🇪🇺' WHERE code = 'eu_parliament';

-- Trades table - add missing columns
ALTER TABLE trades ADD COLUMN IF NOT EXISTS company VARCHAR(200);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS trade_type VARCHAR(20);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS amount_range VARCHAR(100);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS estimated_value DECIMAL(20,2);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS filing_date TIMESTAMPTZ;

-- Copy disclosure_date to filing_date if filing_date is null
UPDATE trades SET filing_date = disclosure_date WHERE filing_date IS NULL;

-- Dashboard stats - add missing columns
ALTER TABLE dashboard_stats ADD COLUMN IF NOT EXISTS active_politicians INTEGER DEFAULT 0;
ALTER TABLE dashboard_stats ADD COLUMN IF NOT EXISTS jurisdictions_tracked INTEGER DEFAULT 0;
ALTER TABLE dashboard_stats ADD COLUMN IF NOT EXISTS average_trade_size DECIMAL(20,2) DEFAULT 0;
ALTER TABLE dashboard_stats ADD COLUMN IF NOT EXISTS recent_filings INTEGER DEFAULT 0;

-- Chart data - add missing columns (buys, sells, volume as aliases)
ALTER TABLE chart_data ADD COLUMN IF NOT EXISTS buys INTEGER DEFAULT 0;
ALTER TABLE chart_data ADD COLUMN IF NOT EXISTS sells INTEGER DEFAULT 0;
ALTER TABLE chart_data ADD COLUMN IF NOT EXISTS volume DECIMAL(20,2) DEFAULT 0;

-- Copy existing data to new columns
UPDATE chart_data SET buys = buy_count WHERE buys = 0 AND buy_count > 0;
UPDATE chart_data SET sells = sell_count WHERE sells = 0 AND sell_count > 0;
UPDATE chart_data SET volume = total_volume WHERE volume = 0 AND total_volume > 0;

-- Update dashboard stats with actual counts
UPDATE dashboard_stats SET
    active_politicians = (SELECT COUNT(*) FROM politicians),
    jurisdictions_tracked = (SELECT COUNT(*) FROM jurisdictions),
    total_trades = (SELECT COUNT(*) FROM trades),
    total_politicians = (SELECT COUNT(*) FROM politicians);

SELECT 'Columns added successfully!' as status;
