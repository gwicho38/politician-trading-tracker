-- Migration: Backfill legacy signals with heuristic model reference
-- This migration creates a legacy model reference and backfills existing signals

-- Step 1: Create the legacy heuristic model reference if it doesn't exist
DO $$
DECLARE
    legacy_model_id UUID;
BEGIN
    -- Check if legacy model already exists
    SELECT id INTO legacy_model_id
    FROM ml_models
    WHERE model_name = 'heuristic'
      AND model_version = 'v2.1-service'
    LIMIT 1;

    -- If not exists, create it
    IF legacy_model_id IS NULL THEN
        INSERT INTO ml_models (
            id,
            model_name,
            model_version,
            model_type,
            status,
            training_completed_at,
            metrics,
            feature_importance,
            hyperparameters,
            training_samples
        ) VALUES (
            gen_random_uuid(),
            'heuristic',
            'v2.1-service',
            'gradient_boosting',  -- Using gradient_boosting as placeholder for rule-based
            'active',
            NOW(),
            jsonb_build_object(
                'type', 'heuristic',
                'description', 'Rule-based signal generation using politician trading patterns',
                'migrated_at', NOW()
            ),
            jsonb_build_object(
                'buy_sell_ratio', 0.25,
                'politician_count', 0.20,
                'bipartisan_agreement', 0.15,
                'recent_activity', 0.15,
                'net_volume', 0.10,
                'activity_acceleration', 0.10,
                'buying_momentum', 0.05
            ),
            jsonb_build_object(
                'type', 'rule_based',
                'version', 'v2.1-service'
            ),
            0
        )
        RETURNING id INTO legacy_model_id;

        RAISE NOTICE 'Created legacy heuristic model: %', legacy_model_id;
    ELSE
        RAISE NOTICE 'Legacy heuristic model already exists: %', legacy_model_id;
    END IF;

    -- Step 2: Backfill existing signals with null model_id
    UPDATE trading_signals
    SET
        model_id = legacy_model_id,
        generation_context = COALESCE(generation_context, '{}') || jsonb_build_object(
            'backfilled', true,
            'backfill_timestamp', NOW(),
            'original_model_version', model_version
        )
    WHERE model_id IS NULL;

    RAISE NOTICE 'Backfilled % signals with legacy model reference',
        (SELECT COUNT(*) FROM trading_signals WHERE model_id = legacy_model_id);

    -- Step 3: Create audit trail entries for backfilled signals
    INSERT INTO signal_audit_trail (
        id,
        signal_id,
        event_type,
        signal_snapshot,
        model_id,
        model_version,
        source_system,
        triggered_by,
        metadata
    )
    SELECT
        gen_random_uuid(),
        ts.id,
        'created',
        jsonb_build_object(
            'ticker', ts.ticker,
            'signal_type', ts.signal_type,
            'confidence_score', ts.confidence_score,
            'generated_at', ts.generated_at,
            'backfilled', true
        ),
        legacy_model_id,
        ts.model_version,
        'manual',  -- Using 'manual' for migration backfill
        'backfill_migration',
        jsonb_build_object(
            'migration', '20260104_backfill_legacy_signals',
            'backfill_reason', 'Legacy signals without model lineage'
        )
    FROM trading_signals ts
    WHERE ts.model_id = legacy_model_id
      AND NOT EXISTS (
          SELECT 1 FROM signal_audit_trail sat
          WHERE sat.signal_id = ts.id AND sat.event_type = 'created'
      );

    RAISE NOTICE 'Created audit trail entries for backfilled signals';

    -- Step 4: Create lifecycle entries for backfilled signals
    INSERT INTO signal_lifecycle (
        id,
        signal_id,
        previous_state,
        current_state,
        transition_reason,
        transitioned_by
    )
    SELECT
        gen_random_uuid(),
        ts.id,
        NULL,
        CASE
            WHEN ts.is_active THEN 'generated'
            ELSE 'expired'
        END,
        'Backfilled during legacy signal migration',
        'migration'
    FROM trading_signals ts
    WHERE ts.model_id = legacy_model_id
      AND NOT EXISTS (
          SELECT 1 FROM signal_lifecycle sl WHERE sl.signal_id = ts.id
      );

    RAISE NOTICE 'Created lifecycle entries for backfilled signals';
END $$;

-- Verify backfill results
SELECT
    'Signals with model_id' as metric,
    COUNT(*) FILTER (WHERE model_id IS NOT NULL) as with_model,
    COUNT(*) FILTER (WHERE model_id IS NULL) as without_model,
    COUNT(*) as total
FROM trading_signals;

SELECT
    'Audit trail entries' as metric,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE triggered_by = 'backfill_migration') as backfilled
FROM signal_audit_trail;

SELECT
    'Lifecycle entries' as metric,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE transitioned_by = 'migration') as backfilled
FROM signal_lifecycle;
