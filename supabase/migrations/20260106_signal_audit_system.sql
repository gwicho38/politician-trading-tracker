-- ============================================================================
-- Signal Audit System Migration
-- ============================================================================
-- Sprint 1: Database Schema Foundation
--
-- Creates complete audit trail from signals → model → weights for full
-- reproducibility and lineage tracking. Includes order state machine support
-- and connection health monitoring.
-- ============================================================================

-- ============================================================================
-- 1. SIGNAL AUDIT TRAIL (Immutable append-only log)
-- ============================================================================
-- Records every event in a signal's lifecycle for complete auditability
CREATE TABLE IF NOT EXISTS public.signal_audit_trail (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  signal_id UUID NOT NULL REFERENCES public.trading_signals(id) ON DELETE CASCADE,

  -- Event type for the audit entry
  event_type TEXT NOT NULL CHECK (event_type IN (
    'created',        -- Signal was generated
    'updated',        -- Signal was modified
    'executed',       -- Order was placed based on signal
    'expired',        -- Signal passed valid_until
    'invalidated',    -- Signal was manually invalidated
    'archived'        -- Signal was archived (retention policy)
  )),

  event_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Snapshot of the signal at event time (for forensic analysis)
  signal_snapshot JSONB NOT NULL,

  -- Model lineage
  model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL,
  model_version TEXT,
  feature_weights_hash TEXT, -- SHA256 hash for integrity verification

  -- Origin tracking
  source_system TEXT NOT NULL DEFAULT 'unknown' CHECK (source_system IN (
    'edge_function',  -- Supabase edge function
    'python_etl',     -- Python ETL service
    'phoenix_server', -- Elixir Phoenix server
    'manual',         -- Manual intervention
    'scheduler',      -- Scheduled job
    'unknown'
  )),

  triggered_by TEXT, -- 'scheduler', 'api', 'user:{email}', etc.

  -- Additional context
  metadata JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_signal_audit_trail_signal_id
  ON public.signal_audit_trail(signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_audit_trail_event_type
  ON public.signal_audit_trail(event_type);
CREATE INDEX IF NOT EXISTS idx_signal_audit_trail_event_timestamp
  ON public.signal_audit_trail(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signal_audit_trail_model_id
  ON public.signal_audit_trail(model_id);
CREATE INDEX IF NOT EXISTS idx_signal_audit_trail_created_at
  ON public.signal_audit_trail(created_at DESC);

-- IMMUTABILITY TRIGGER: Prevent UPDATE and DELETE on audit trail
CREATE OR REPLACE FUNCTION public.prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'signal_audit_trail is immutable. UPDATE and DELETE operations are not allowed.';
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER signal_audit_trail_immutable
  BEFORE UPDATE OR DELETE ON public.signal_audit_trail
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_audit_modification();


-- ============================================================================
-- 2. FEATURE DEFINITIONS (Versioned feature engineering)
-- ============================================================================
-- Tracks different versions of feature extraction configurations
CREATE TABLE IF NOT EXISTS public.feature_definitions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Version identifier (semantic versioning)
  version TEXT NOT NULL UNIQUE,

  -- Feature configuration
  feature_names TEXT[] NOT NULL, -- Ordered list of feature names
  feature_schema JSONB NOT NULL, -- Validation schema for features
  computation_config JSONB NOT NULL DEFAULT '{}', -- Extraction parameters

  -- Default weights for this feature set (can be overridden by model)
  default_weights JSONB DEFAULT '{}',

  -- Lifecycle
  is_active BOOLEAN DEFAULT false,
  activated_at TIMESTAMPTZ,
  deprecated_at TIMESTAMPTZ,
  deprecation_reason TEXT,

  -- Metadata
  description TEXT,
  created_by TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Only one active feature definition at a time
CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_definitions_active
  ON public.feature_definitions(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_feature_definitions_version
  ON public.feature_definitions(version);


-- ============================================================================
-- 3. MODEL WEIGHTS SNAPSHOTS (Exact weights at prediction time)
-- ============================================================================
-- Stores the exact weights used for each prediction for full reproducibility
CREATE TABLE IF NOT EXISTS public.model_weights_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Link to the model
  model_id UUID NOT NULL REFERENCES public.ml_models(id) ON DELETE CASCADE,

  -- Hash for integrity verification and deduplication
  weights_hash TEXT NOT NULL UNIQUE, -- SHA256 of weights

  -- Weights storage (for small models, stored directly; larger via storage)
  weights_blob BYTEA, -- Compressed weights for small models (<10MB)
  weights_path TEXT,  -- Supabase storage path for larger models
  weights_size_bytes INTEGER,

  -- Feature definition this weights snapshot was trained with
  feature_definition_id UUID REFERENCES public.feature_definitions(id) ON DELETE SET NULL,

  -- Preprocessing state (for exact reproducibility)
  scaler_state JSONB, -- StandardScaler mean/std, etc.
  encoder_state JSONB, -- Any encoding state

  -- Validation results
  validation_metrics JSONB DEFAULT '{}',
  sample_predictions JSONB DEFAULT '{}', -- Reference predictions for verification

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_weights_snapshots_model_id
  ON public.model_weights_snapshots(model_id);
CREATE INDEX IF NOT EXISTS idx_model_weights_snapshots_hash
  ON public.model_weights_snapshots(weights_hash);
CREATE INDEX IF NOT EXISTS idx_model_weights_snapshots_feature_def
  ON public.model_weights_snapshots(feature_definition_id);


-- ============================================================================
-- 4. SIGNAL LIFECYCLE (State machine tracking)
-- ============================================================================
-- Tracks a signal through its complete lifecycle from generation to execution
CREATE TABLE IF NOT EXISTS public.signal_lifecycle (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  signal_id UUID NOT NULL REFERENCES public.trading_signals(id) ON DELETE CASCADE,

  -- State transition
  previous_state TEXT,
  current_state TEXT NOT NULL CHECK (current_state IN (
    'generated',   -- Signal created
    'active',      -- Signal is actionable
    'in_cart',     -- Added to user's cart
    'ordered',     -- Order placed
    'executed',    -- Order partially or fully filled
    'filled',      -- Order completely filled
    'expired',     -- Signal validity period ended
    'canceled',    -- User or system canceled
    'invalidated'  -- Signal marked invalid (model retrain, data issue)
  )),

  -- Related entities
  order_id UUID REFERENCES public.trading_orders(id) ON DELETE SET NULL,
  position_id UUID REFERENCES public.positions(id) ON DELETE SET NULL,

  -- Transition metadata
  transition_reason TEXT,
  transition_metadata JSONB DEFAULT '{}',
  transitioned_by TEXT, -- 'system', 'user:{id}', 'scheduler', etc.

  -- Timing
  transitioned_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_lifecycle_signal_id
  ON public.signal_lifecycle(signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_lifecycle_current_state
  ON public.signal_lifecycle(current_state);
CREATE INDEX IF NOT EXISTS idx_signal_lifecycle_order_id
  ON public.signal_lifecycle(order_id);
CREATE INDEX IF NOT EXISTS idx_signal_lifecycle_transitioned_at
  ON public.signal_lifecycle(transitioned_at DESC);


-- ============================================================================
-- 5. ORDER STATE LOG (Order state transitions)
-- ============================================================================
-- Tracks every state change for orders (for debugging and auditing)
CREATE TABLE IF NOT EXISTS public.order_state_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES public.trading_orders(id) ON DELETE CASCADE,

  -- State transition
  previous_status TEXT,
  new_status TEXT NOT NULL,

  -- Alpaca sync info
  alpaca_event_id TEXT,
  alpaca_event_timestamp TIMESTAMPTZ,

  -- Execution details at this state
  filled_qty_at_state INTEGER,
  avg_price_at_state DECIMAL(12, 4),

  -- Error info (for rejected/failed states)
  error_code TEXT,
  error_message TEXT,

  -- Metadata
  source TEXT DEFAULT 'unknown' CHECK (source IN (
    'user_action',     -- User initiated
    'alpaca_webhook',  -- Alpaca event
    'alpaca_poll',     -- Polling sync
    'system_timeout',  -- Timeout triggered
    'scheduler',       -- Scheduled job
    'unknown'
  )),

  raw_event JSONB, -- Full event payload for debugging

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_order_state_log_order_id
  ON public.order_state_log(order_id);
CREATE INDEX IF NOT EXISTS idx_order_state_log_new_status
  ON public.order_state_log(new_status);
CREATE INDEX IF NOT EXISTS idx_order_state_log_created_at
  ON public.order_state_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_state_log_alpaca_event
  ON public.order_state_log(alpaca_event_id);


-- ============================================================================
-- 6. CONNECTION HEALTH LOG (API connection monitoring)
-- ============================================================================
-- Tracks health of external API connections (Alpaca, etc.)
CREATE TABLE IF NOT EXISTS public.connection_health_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Connection identifier
  connection_type TEXT NOT NULL CHECK (connection_type IN (
    'alpaca_trading',
    'alpaca_data',
    'supabase_storage',
    'python_etl',
    'phoenix_server'
  )),

  -- Health check result
  status TEXT NOT NULL CHECK (status IN (
    'healthy',
    'degraded',
    'unhealthy',
    'unreachable'
  )),

  -- Latency measurement
  response_time_ms INTEGER,

  -- Details
  endpoint_url TEXT,
  http_status_code INTEGER,
  error_message TEXT,

  -- Additional diagnostics
  diagnostics JSONB DEFAULT '{}',

  -- Who performed the check
  checked_by TEXT DEFAULT 'scheduler', -- 'scheduler', 'user', 'startup'

  checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_connection_health_log_type
  ON public.connection_health_log(connection_type);
CREATE INDEX IF NOT EXISTS idx_connection_health_log_status
  ON public.connection_health_log(status);
CREATE INDEX IF NOT EXISTS idx_connection_health_log_checked_at
  ON public.connection_health_log(checked_at DESC);

-- Partial index for recent unhealthy connections
CREATE INDEX IF NOT EXISTS idx_connection_health_log_unhealthy_recent
  ON public.connection_health_log(connection_type, checked_at DESC)
  WHERE status IN ('unhealthy', 'unreachable');


-- ============================================================================
-- 7. ARCHIVE TABLE FOR 1-YEAR RETENTION
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.signal_audit_trail_archive (
  LIKE public.signal_audit_trail INCLUDING ALL
);

-- Remove the immutability trigger from archive (allow cleanup operations)
-- Archive table can be cleaned up after extended retention


-- ============================================================================
-- 8. ENHANCE trading_signals TABLE
-- ============================================================================
-- Add model lineage columns to trading_signals
ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL;

ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS weights_snapshot_id UUID REFERENCES public.model_weights_snapshots(id) ON DELETE SET NULL;

ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS feature_definition_id UUID REFERENCES public.feature_definitions(id) ON DELETE SET NULL;

ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS generation_context JSONB DEFAULT '{}';

ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS reproducibility_hash TEXT;

-- Index for model lineage queries
CREATE INDEX IF NOT EXISTS idx_trading_signals_model_id
  ON public.trading_signals(model_id);
CREATE INDEX IF NOT EXISTS idx_trading_signals_weights_snapshot
  ON public.trading_signals(weights_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_trading_signals_feature_def
  ON public.trading_signals(feature_definition_id);
CREATE INDEX IF NOT EXISTS idx_trading_signals_repro_hash
  ON public.trading_signals(reproducibility_hash);


-- ============================================================================
-- 9. ENHANCE trading_orders TABLE
-- ============================================================================
-- Add idempotency key and state machine support
ALTER TABLE public.trading_orders
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT UNIQUE;

ALTER TABLE public.trading_orders
  ADD COLUMN IF NOT EXISTS state_machine_version INTEGER DEFAULT 1;

ALTER TABLE public.trading_orders
  ADD COLUMN IF NOT EXISTS last_state_transition_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_trading_orders_idempotency
  ON public.trading_orders(idempotency_key);


-- ============================================================================
-- 10. RETENTION POLICY FUNCTION
-- ============================================================================
-- Archives audit records older than 1 year and cleans up archived records older than 2 years
CREATE OR REPLACE FUNCTION public.archive_old_audit_records()
RETURNS TABLE (archived_count INTEGER, deleted_from_archive INTEGER) AS $$
DECLARE
  v_archived INTEGER;
  v_deleted INTEGER;
BEGIN
  -- Move records older than 1 year to archive
  WITH moved AS (
    DELETE FROM public.signal_audit_trail
    WHERE event_timestamp < NOW() - INTERVAL '1 year'
    RETURNING *
  )
  INSERT INTO public.signal_audit_trail_archive
  SELECT * FROM moved;

  GET DIAGNOSTICS v_archived = ROW_COUNT;

  -- Delete from archive records older than 2 years (total retention)
  DELETE FROM public.signal_audit_trail_archive
  WHERE event_timestamp < NOW() - INTERVAL '2 years';

  GET DIAGNOSTICS v_deleted = ROW_COUNT;

  RETURN QUERY SELECT v_archived, v_deleted;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 11. HELPER FUNCTIONS
-- ============================================================================

-- Function to get full signal lineage
CREATE OR REPLACE FUNCTION public.get_signal_lineage(p_signal_id UUID)
RETURNS TABLE (
  signal_id UUID,
  ticker TEXT,
  signal_type TEXT,
  confidence_score DECIMAL,
  model_name TEXT,
  model_version TEXT,
  model_metrics JSONB,
  weights_hash TEXT,
  feature_version TEXT,
  audit_events JSONB
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    ts.id as signal_id,
    ts.ticker,
    ts.signal_type,
    ts.confidence_score,
    m.model_name,
    m.model_version,
    m.metrics as model_metrics,
    mws.weights_hash,
    fd.version as feature_version,
    (
      SELECT jsonb_agg(jsonb_build_object(
        'event_type', sat.event_type,
        'event_timestamp', sat.event_timestamp,
        'source_system', sat.source_system
      ) ORDER BY sat.event_timestamp)
      FROM public.signal_audit_trail sat
      WHERE sat.signal_id = ts.id
    ) as audit_events
  FROM public.trading_signals ts
  LEFT JOIN public.ml_models m ON ts.model_id = m.id
  LEFT JOIN public.model_weights_snapshots mws ON ts.weights_snapshot_id = mws.id
  LEFT JOIN public.feature_definitions fd ON ts.feature_definition_id = fd.id
  WHERE ts.id = p_signal_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record a signal audit event
CREATE OR REPLACE FUNCTION public.record_signal_audit(
  p_signal_id UUID,
  p_event_type TEXT,
  p_source_system TEXT DEFAULT 'unknown',
  p_triggered_by TEXT DEFAULT NULL,
  p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
  v_signal_snapshot JSONB;
  v_model_id UUID;
  v_model_version TEXT;
  v_weights_hash TEXT;
  v_audit_id UUID;
BEGIN
  -- Get signal snapshot
  SELECT
    to_jsonb(ts.*),
    ts.model_id,
    m.model_version,
    mws.weights_hash
  INTO v_signal_snapshot, v_model_id, v_model_version, v_weights_hash
  FROM public.trading_signals ts
  LEFT JOIN public.ml_models m ON ts.model_id = m.id
  LEFT JOIN public.model_weights_snapshots mws ON ts.weights_snapshot_id = mws.id
  WHERE ts.id = p_signal_id;

  IF v_signal_snapshot IS NULL THEN
    RAISE EXCEPTION 'Signal not found: %', p_signal_id;
  END IF;

  -- Insert audit record
  INSERT INTO public.signal_audit_trail (
    signal_id,
    event_type,
    signal_snapshot,
    model_id,
    model_version,
    feature_weights_hash,
    source_system,
    triggered_by,
    metadata
  ) VALUES (
    p_signal_id,
    p_event_type,
    v_signal_snapshot,
    v_model_id,
    v_model_version,
    v_weights_hash,
    p_source_system,
    p_triggered_by,
    p_metadata
  )
  RETURNING id INTO v_audit_id;

  RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest connection health per type
CREATE OR REPLACE FUNCTION public.get_connection_health_summary()
RETURNS TABLE (
  connection_type TEXT,
  latest_status TEXT,
  latest_response_time_ms INTEGER,
  last_checked TIMESTAMPTZ,
  unhealthy_count_24h INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT DISTINCT ON (chl.connection_type)
    chl.connection_type,
    chl.status as latest_status,
    chl.response_time_ms as latest_response_time_ms,
    chl.checked_at as last_checked,
    (
      SELECT COUNT(*)::INTEGER
      FROM public.connection_health_log chl2
      WHERE chl2.connection_type = chl.connection_type
        AND chl2.status IN ('unhealthy', 'unreachable')
        AND chl2.checked_at > NOW() - INTERVAL '24 hours'
    ) as unhealthy_count_24h
  FROM public.connection_health_log chl
  ORDER BY chl.connection_type, chl.checked_at DESC;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 12. ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all new tables
ALTER TABLE public.signal_audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_audit_trail_archive ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_weights_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_lifecycle ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_state_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.connection_health_log ENABLE ROW LEVEL SECURITY;

-- Public read access for audit and monitoring data
CREATE POLICY "signal_audit_trail_public_read" ON public.signal_audit_trail
  FOR SELECT USING (true);

CREATE POLICY "signal_audit_trail_archive_public_read" ON public.signal_audit_trail_archive
  FOR SELECT USING (true);

CREATE POLICY "feature_definitions_public_read" ON public.feature_definitions
  FOR SELECT USING (true);

CREATE POLICY "model_weights_snapshots_public_read" ON public.model_weights_snapshots
  FOR SELECT USING (true);

CREATE POLICY "signal_lifecycle_public_read" ON public.signal_lifecycle
  FOR SELECT USING (true);

CREATE POLICY "order_state_log_public_read" ON public.order_state_log
  FOR SELECT USING (true);

CREATE POLICY "connection_health_log_public_read" ON public.connection_health_log
  FOR SELECT USING (true);

-- Service role full access for all tables
CREATE POLICY "signal_audit_trail_service_all" ON public.signal_audit_trail
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "signal_audit_trail_archive_service_all" ON public.signal_audit_trail_archive
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "feature_definitions_service_all" ON public.feature_definitions
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "model_weights_snapshots_service_all" ON public.model_weights_snapshots
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "signal_lifecycle_service_all" ON public.signal_lifecycle
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "order_state_log_service_all" ON public.order_state_log
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "connection_health_log_service_all" ON public.connection_health_log
  FOR ALL USING (auth.role() = 'service_role');


-- ============================================================================
-- 13. TRIGGERS FOR updated_at
-- ============================================================================

CREATE TRIGGER update_feature_definitions_updated_at
  BEFORE UPDATE ON public.feature_definitions
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();


-- ============================================================================
-- 14. COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE public.signal_audit_trail IS
  'Immutable audit log tracking all signal lifecycle events for complete auditability';

COMMENT ON TABLE public.signal_audit_trail_archive IS
  'Archive table for audit records older than 1 year (2 year total retention)';

COMMENT ON TABLE public.feature_definitions IS
  'Versioned feature engineering configurations for reproducible ML predictions';

COMMENT ON TABLE public.model_weights_snapshots IS
  'Exact model weights at prediction time for full reproducibility';

COMMENT ON TABLE public.signal_lifecycle IS
  'State machine tracking for signals from generation through execution';

COMMENT ON TABLE public.order_state_log IS
  'Complete state transition history for trading orders';

COMMENT ON TABLE public.connection_health_log IS
  'Health monitoring log for external API connections (Alpaca, etc.)';

COMMENT ON COLUMN public.trading_signals.model_id IS
  'FK to ml_models - the model that generated this signal';

COMMENT ON COLUMN public.trading_signals.weights_snapshot_id IS
  'FK to model_weights_snapshots - exact weights used for this prediction';

COMMENT ON COLUMN public.trading_signals.feature_definition_id IS
  'FK to feature_definitions - feature config version used';

COMMENT ON COLUMN public.trading_signals.reproducibility_hash IS
  'SHA256(features + model_id + weights_hash) for verifying reproducibility';

COMMENT ON COLUMN public.trading_orders.idempotency_key IS
  'Unique key to prevent duplicate order submissions';

COMMENT ON FUNCTION public.record_signal_audit IS
  'Records an audit event for a signal with automatic snapshot capture';

COMMENT ON FUNCTION public.get_signal_lineage IS
  'Returns complete lineage for a signal including model, weights, and audit trail';

COMMENT ON FUNCTION public.archive_old_audit_records IS
  'Archives records >1 year old and deletes archived records >2 years old';
