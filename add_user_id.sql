-- Add user_id column to trading_signals table
ALTER TABLE trading_signals ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
