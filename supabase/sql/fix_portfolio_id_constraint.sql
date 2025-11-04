-- Fix portfolio_id constraint in trading_signals table
-- This allows signals to exist independently of portfolios
-- Signals are recommendations that may or may not be acted upon

-- =============================================================================
-- Remove NOT NULL constraint from portfolio_id if it exists
-- =============================================================================

DO $$
BEGIN
    -- Check if portfolio_id column exists
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='portfolio_id') THEN

        -- Drop the NOT NULL constraint if it exists
        ALTER TABLE trading_signals ALTER COLUMN portfolio_id DROP NOT NULL;

        RAISE NOTICE 'Removed NOT NULL constraint from portfolio_id';

    ELSE
        RAISE NOTICE 'portfolio_id column does not exist - no action needed';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error: %', SQLERRM;
END $$;

-- =============================================================================
-- Add portfolio_id column as nullable if it doesn't exist
-- =============================================================================

DO $$
BEGIN
    -- Add portfolio_id column as nullable if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='portfolio_id') THEN
        ALTER TABLE trading_signals ADD COLUMN portfolio_id UUID REFERENCES portfolios(id);
        RAISE NOTICE 'Added nullable portfolio_id column';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error: %', SQLERRM;
END $$;

-- =============================================================================
-- Create index for portfolio_id if it doesn't exist
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_trading_signals_portfolio_id ON trading_signals(portfolio_id);
