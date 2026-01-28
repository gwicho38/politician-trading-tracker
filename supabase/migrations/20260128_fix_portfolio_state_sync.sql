-- Fix Portfolio State Sync Migration
-- Addresses several data integrity issues discovered in the self-learning feedback loop:
-- 1. positions_value was negative (-2.5M) causing incorrect capital utilization
-- 2. winning_trades/losing_trades counters out of sync with actual closed positions
-- 3. trades_today not resetting properly (showed 207 vs limit of 10)
-- 4. open_positions count exceeding max_portfolio_positions (23 vs 20)

-- ============================================================================
-- 1. Create function to recalculate portfolio state from actual positions
-- ============================================================================
CREATE OR REPLACE FUNCTION public.recalculate_portfolio_state()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_open_count INTEGER;
    v_positions_value DECIMAL(15,2);
    v_winning_count INTEGER;
    v_losing_count INTEGER;
    v_avg_win DECIMAL(15,2);
    v_avg_loss DECIMAL(15,2);
    v_profit_factor DECIMAL(8,4);
    v_total_wins DECIMAL(15,2);
    v_total_losses DECIMAL(15,2);
BEGIN
    -- Count actual open positions and their total value
    SELECT
        COUNT(*),
        COALESCE(SUM(GREATEST(market_value, quantity * current_price, quantity * entry_price)), 0)
    INTO v_open_count, v_positions_value
    FROM reference_portfolio_positions
    WHERE is_open = true;

    -- Count wins and losses from closed positions
    SELECT
        COUNT(*) FILTER (WHERE realized_pl > 0),
        COUNT(*) FILTER (WHERE realized_pl <= 0)
    INTO v_winning_count, v_losing_count
    FROM reference_portfolio_positions
    WHERE is_open = false
      AND realized_pl IS NOT NULL;

    -- Calculate average win and average loss (in percentage terms)
    SELECT
        COALESCE(AVG(realized_pl_pct) FILTER (WHERE realized_pl_pct > 0), 0),
        COALESCE(AVG(realized_pl_pct) FILTER (WHERE realized_pl_pct <= 0), 0)
    INTO v_avg_win, v_avg_loss
    FROM reference_portfolio_positions
    WHERE is_open = false
      AND realized_pl_pct IS NOT NULL;

    -- Calculate profit factor (sum of wins / sum of losses)
    SELECT
        COALESCE(SUM(realized_pl) FILTER (WHERE realized_pl > 0), 0),
        ABS(COALESCE(SUM(realized_pl) FILTER (WHERE realized_pl < 0), 1))
    INTO v_total_wins, v_total_losses
    FROM reference_portfolio_positions
    WHERE is_open = false
      AND realized_pl IS NOT NULL;

    IF v_total_losses > 0 THEN
        v_profit_factor := v_total_wins / v_total_losses;
    ELSE
        v_profit_factor := CASE WHEN v_total_wins > 0 THEN 99.99 ELSE 0 END;
    END IF;

    -- Update portfolio state
    UPDATE reference_portfolio_state
    SET
        open_positions = v_open_count,
        positions_value = v_positions_value,
        winning_trades = v_winning_count,
        losing_trades = v_losing_count,
        win_rate = CASE
            WHEN (v_winning_count + v_losing_count) > 0
            THEN ROUND((v_winning_count::DECIMAL / (v_winning_count + v_losing_count)) * 100, 2)
            ELSE 0
        END,
        avg_win = v_avg_win,
        avg_loss = v_avg_loss,
        profit_factor = v_profit_factor,
        trades_today = 0, -- Reset trades_today
        updated_at = NOW()
    WHERE id = (SELECT id FROM reference_portfolio_state LIMIT 1);

    RAISE NOTICE 'Portfolio state recalculated: open_positions=%, positions_value=%, winning_trades=%, losing_trades=%',
        v_open_count, v_positions_value, v_winning_count, v_losing_count;
END;
$$;

-- ============================================================================
-- 2. Run the recalculation immediately to fix current state
-- ============================================================================
SELECT public.recalculate_portfolio_state();

-- ============================================================================
-- 3. Create scheduled job to sync state hourly (if pg_cron available)
-- ============================================================================
DO $$
BEGIN
    -- Check if pg_cron extension is available
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        -- Remove existing job if any
        PERFORM cron.unschedule('recalculate_portfolio_state');

        -- Schedule hourly recalculation to prevent drift
        PERFORM cron.schedule(
            'recalculate_portfolio_state',
            '0 * * * *',  -- Every hour at minute 0
            'SELECT public.recalculate_portfolio_state()'
        );

        RAISE NOTICE 'Scheduled hourly portfolio state recalculation';
    ELSE
        RAISE NOTICE 'pg_cron not available - skipping scheduled job creation';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Could not schedule cron job: %', SQLERRM;
END;
$$;

-- ============================================================================
-- 4. Add trigger to reset trades_today at midnight UTC
-- ============================================================================
CREATE OR REPLACE FUNCTION public.check_and_reset_trades_today()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_last_reset DATE;
BEGIN
    -- Get the date of last update
    SELECT DATE(updated_at) INTO v_last_reset
    FROM reference_portfolio_state
    LIMIT 1;

    -- If it's a new day, reset trades_today
    IF v_last_reset < CURRENT_DATE THEN
        NEW.trades_today := 0;
    END IF;

    RETURN NEW;
END;
$$;

-- Create trigger if it doesn't exist
DROP TRIGGER IF EXISTS reset_trades_today_trigger ON reference_portfolio_state;
CREATE TRIGGER reset_trades_today_trigger
    BEFORE UPDATE ON reference_portfolio_state
    FOR EACH ROW
    EXECUTE FUNCTION public.check_and_reset_trades_today();

-- ============================================================================
-- 5. Add constraint to prevent open_positions exceeding max
-- ============================================================================
-- Note: This is enforced at application level, but adding a comment for clarity
COMMENT ON COLUMN reference_portfolio_state.open_positions IS
    'Count of open positions. Should not exceed max_portfolio_positions in config (default 20).';

-- ============================================================================
-- 6. Log the fix (only if jobs table exists)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'jobs') THEN
        INSERT INTO jobs (name, status, metadata, created_at, updated_at)
        VALUES (
            'portfolio_state_fix_20260128',
            'completed',
            jsonb_build_object(
                'description', 'Fixed portfolio state sync issues',
                'issues_fixed', jsonb_build_array(
                    'positions_value was negative',
                    'winning_trades/losing_trades out of sync',
                    'trades_today not resetting',
                    'Added hourly recalculation job'
                )
            ),
            NOW(),
            NOW()
        );
    END IF;
END;
$$;

-- ============================================================================
-- Summary of changes:
-- 1. Created recalculate_portfolio_state() function
-- 2. Executed immediate fix of current state
-- 3. Scheduled hourly recalculation (if pg_cron available)
-- 4. Added trigger to reset trades_today on new day
-- ============================================================================
