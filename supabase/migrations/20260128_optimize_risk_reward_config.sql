-- Optimize Risk/Reward Configuration
-- Based on analysis of 74 closed positions:
-- - 68% hit stop-loss (closed between -10% and -5%)
-- - Only 2.7% ever reached +5% returns
-- - Mean return was -7.58%
--
-- Changes:
-- 1. Reduce stop-loss from 10% to 5% (cut losses earlier)
-- 2. Reduce take-profit from 25% to 10% (capture more wins)
-- 3. Reduce trailing stop from 8% to 4% (tighter profit protection)
-- 4. Increase confidence threshold from 0.70 to 0.75 (filter weaker signals)
-- 5. Reduce max daily trades from 10 to 5 (be more selective)

-- ============================================================================
-- 1. Update portfolio configuration
-- ============================================================================
UPDATE reference_portfolio_config
SET
    -- Tighter risk management
    default_stop_loss_pct = 5.0,     -- Was 10.0 (cut losses earlier)
    default_take_profit_pct = 10.0,  -- Was 25.0 (more achievable target)
    trailing_stop_pct = 4.0,         -- Was 8.0 (tighter trailing stop)

    -- Higher quality filters
    min_confidence_threshold = 0.75,  -- Was 0.70 (filter weak signals)
    max_daily_trades = 5,             -- Was 10 (be more selective)

    -- Document the change
    description = 'Automated paper trading portfolio. Risk parameters optimized on 2026-01-28 based on analysis of 74 closed positions. Focus on tighter risk management and higher quality signals.',

    updated_at = NOW()
WHERE id = (SELECT id FROM reference_portfolio_config LIMIT 1);

-- ============================================================================
-- 2. Update existing open positions with new risk parameters
-- ============================================================================
UPDATE reference_portfolio_positions
SET
    -- Recalculate stop-loss and take-profit from entry price
    stop_loss_price = entry_price * (1 - 0.05),      -- 5% stop-loss
    take_profit_price = entry_price * (1 + 0.10),    -- 10% take-profit
    trailing_stop_price = GREATEST(
        highest_price * (1 - 0.04),  -- 4% trailing stop from high
        entry_price * (1 - 0.05)     -- But not below 5% stop-loss
    ),
    updated_at = NOW()
WHERE is_open = true;

-- ============================================================================
-- 3. Log the configuration change (only if jobs table exists)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'jobs') THEN
        INSERT INTO jobs (name, status, metadata, created_at, updated_at)
        VALUES (
            'risk_reward_optimization_20260128',
            'completed',
            jsonb_build_object(
                'description', 'Optimized risk/reward parameters based on position analysis',
                'analysis', jsonb_build_object(
                    'closed_positions_analyzed', 74,
                    'stop_loss_hit_rate', '68%',
                    'take_profit_hit_rate', '2.7%',
                    'mean_return', '-7.58%'
                ),
                'changes', jsonb_build_object(
                    'stop_loss_pct', '10% -> 5%',
                    'take_profit_pct', '25% -> 10%',
                    'trailing_stop_pct', '8% -> 4%',
                    'confidence_threshold', '0.70 -> 0.75',
                    'max_daily_trades', '10 -> 5'
                ),
                'rationale', 'Positions rarely reach +10%, so tighter exits lock in smaller gains. Higher confidence threshold filters weak signals.'
            ),
            NOW(),
            NOW()
        );
    END IF;
END;
$$;

-- ============================================================================
-- Summary of changes:
-- Before: 10% stop / 25% profit = 2.5:1 reward/risk (but 68% hit stop)
-- After:  5% stop / 10% profit = 2:1 reward/risk (more achievable)
-- ============================================================================
