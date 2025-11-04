-- Fix trading_signals table schema issues
-- This migration handles multiple schema inconsistencies between production and local schemas:
-- 1. portfolio_id should be nullable (signals exist independently of portfolios)
-- 2. symbol column should be nullable (redundant with ticker)
-- 3. confidence column should be nullable (redundant with confidence_score)
-- 4. strength column should be nullable (redundant with signal_strength)

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
-- Handle symbol column issue
-- =============================================================================

DO $$
BEGIN
    -- Check if symbol column exists
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='symbol') THEN

        -- Drop the NOT NULL constraint from symbol if it exists
        ALTER TABLE trading_signals ALTER COLUMN symbol DROP NOT NULL;

        RAISE NOTICE 'Removed NOT NULL constraint from symbol column';
        RAISE NOTICE 'Note: The application uses ticker field, symbol column may be deprecated';

    ELSE
        RAISE NOTICE 'symbol column does not exist - no action needed';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error handling symbol column: %', SQLERRM;
END $$;

-- =============================================================================
-- Create indexes if they don't exist
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_trading_signals_portfolio_id ON trading_signals(portfolio_id);

-- If symbol column exists and is used, ensure it has an index
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='symbol') THEN
        CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
        RAISE NOTICE 'Created index on symbol column';
    END IF;
END $$;

-- =============================================================================
-- Handle confidence column issue
-- =============================================================================

DO $$
BEGIN
    -- Check if confidence column exists
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='confidence') THEN

        -- Drop the NOT NULL constraint from confidence if it exists
        ALTER TABLE trading_signals ALTER COLUMN confidence DROP NOT NULL;

        RAISE NOTICE 'Removed NOT NULL constraint from confidence column';
        RAISE NOTICE 'Note: The application uses confidence_score field, confidence column may be deprecated';

    ELSE
        RAISE NOTICE 'confidence column does not exist - no action needed';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error handling confidence column: %', SQLERRM;
END $$;

-- If confidence column exists, ensure it has an index for performance
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='confidence') THEN
        CREATE INDEX IF NOT EXISTS idx_trading_signals_confidence ON trading_signals(confidence);
        RAISE NOTICE 'Created index on confidence column';
    END IF;
END $$;

-- =============================================================================
-- Handle strength column issue
-- =============================================================================

DO $$
BEGIN
    -- Check if strength column exists
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='strength') THEN

        -- Drop the NOT NULL constraint from strength if it exists
        ALTER TABLE trading_signals ALTER COLUMN strength DROP NOT NULL;

        RAISE NOTICE 'Removed NOT NULL constraint from strength column';
        RAISE NOTICE 'Note: The application uses signal_strength field, strength column may be deprecated';

    ELSE
        RAISE NOTICE 'strength column does not exist - no action needed';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error handling strength column: %', SQLERRM;
END $$;

-- If strength column exists, ensure it has an index for performance
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='trading_signals' AND column_name='strength') THEN
        CREATE INDEX IF NOT EXISTS idx_trading_signals_strength ON trading_signals(strength);
        RAISE NOTICE 'Created index on strength column';
    END IF;
END $$;
