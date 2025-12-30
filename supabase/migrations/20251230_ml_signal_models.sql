-- ============================================================================
-- ML Signal Models Schema
-- ============================================================================
-- Tables for ML-enhanced signal generation:
-- 1. ml_models - Model registry with metadata and metrics
-- 2. ml_training_data - Training dataset snapshots with labels
-- 3. ml_predictions_cache - Cache for ML predictions
-- ============================================================================

-- ============================================================================
-- ML Models Registry
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.ml_models (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  model_type TEXT NOT NULL CHECK (model_type IN ('xgboost', 'lightgbm', 'gradient_boosting')),

  -- Training timestamps
  training_started_at TIMESTAMPTZ,
  training_completed_at TIMESTAMPTZ,

  -- Model status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'training', 'active', 'archived', 'failed')),

  -- Model metrics (accuracy, precision, recall, f1, auc, etc.)
  metrics JSONB DEFAULT '{}',

  -- Feature importance for explainability
  feature_importance JSONB DEFAULT '{}',

  -- Hyperparameters used for training
  hyperparameters JSONB DEFAULT '{}',

  -- Path to serialized model artifact (S3/GCS/Supabase Storage)
  model_artifact_path TEXT,

  -- Training data statistics
  training_samples INTEGER,
  validation_samples INTEGER,

  -- Error message if training failed
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for finding active models
CREATE INDEX IF NOT EXISTS idx_ml_models_status ON public.ml_models(status);
CREATE INDEX IF NOT EXISTS idx_ml_models_type ON public.ml_models(model_type);

-- ============================================================================
-- ML Training Data
-- ============================================================================
-- Stores feature vectors and labels for model training
CREATE TABLE IF NOT EXISTS public.ml_training_data (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Link to model (null for pending training data)
  model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL,

  -- Ticker and date for the data point
  ticker TEXT NOT NULL,
  disclosure_date DATE NOT NULL,

  -- Feature vector as JSON for flexibility
  feature_vector JSONB NOT NULL,

  -- Target label: -2 (strong_sell), -1 (sell), 0 (hold), 1 (buy), 2 (strong_buy)
  label INTEGER CHECK (label >= -2 AND label <= 2),

  -- Actual returns for backtesting and label validation
  actual_return_7d NUMERIC,
  actual_return_30d NUMERIC,

  -- Price data at disclosure time
  price_at_disclosure NUMERIC,
  price_7d_later NUMERIC,
  price_30d_later NUMERIC,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_ml_training_data_ticker ON public.ml_training_data(ticker);
CREATE INDEX IF NOT EXISTS idx_ml_training_data_date ON public.ml_training_data(disclosure_date);
CREATE INDEX IF NOT EXISTS idx_ml_training_data_model ON public.ml_training_data(model_id);
CREATE INDEX IF NOT EXISTS idx_ml_training_data_unlabeled ON public.ml_training_data(label) WHERE label IS NULL;

-- ============================================================================
-- ML Predictions Cache
-- ============================================================================
-- Cache layer for ML predictions to reduce API calls
CREATE TABLE IF NOT EXISTS public.ml_predictions_cache (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Link to the model that made the prediction
  model_id UUID REFERENCES public.ml_models(id) ON DELETE CASCADE,

  -- Ticker being predicted
  ticker TEXT NOT NULL,

  -- Hash of feature vector for cache lookup
  feature_hash TEXT NOT NULL,

  -- Prediction results
  prediction INTEGER CHECK (prediction >= -2 AND prediction <= 2),
  confidence NUMERIC CHECK (confidence >= 0 AND confidence <= 1),

  -- Full prediction details
  prediction_details JSONB DEFAULT '{}',

  -- Cache expiration
  expires_at TIMESTAMPTZ NOT NULL,

  created_at TIMESTAMPTZ DEFAULT now(),

  -- Unique constraint for cache lookup
  UNIQUE(ticker, feature_hash)
);

-- Indexes for cache lookup and cleanup
CREATE INDEX IF NOT EXISTS idx_ml_predictions_cache_lookup
  ON public.ml_predictions_cache(ticker, feature_hash);
CREATE INDEX IF NOT EXISTS idx_ml_predictions_cache_expires
  ON public.ml_predictions_cache(expires_at);

-- ============================================================================
-- ML Training Jobs
-- ============================================================================
-- Track training job execution history
CREATE TABLE IF NOT EXISTS public.ml_training_jobs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Link to resulting model
  model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL,

  -- Job configuration
  job_type TEXT NOT NULL CHECK (job_type IN ('full_train', 'incremental', 'retrain')),
  config JSONB DEFAULT '{}',

  -- Job status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

  -- Timing
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,

  -- Progress tracking
  progress_pct NUMERIC DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
  current_step TEXT,

  -- Results
  result_summary JSONB DEFAULT '{}',
  error_message TEXT,

  -- Who triggered the job
  triggered_by TEXT, -- 'scheduler', 'manual', 'api'

  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for finding active jobs
CREATE INDEX IF NOT EXISTS idx_ml_training_jobs_status ON public.ml_training_jobs(status);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get the currently active model
CREATE OR REPLACE FUNCTION public.get_active_ml_model(p_model_type TEXT DEFAULT 'xgboost')
RETURNS TABLE (
  id UUID,
  model_name TEXT,
  model_version TEXT,
  model_artifact_path TEXT,
  metrics JSONB,
  feature_importance JSONB
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.model_name,
    m.model_version,
    m.model_artifact_path,
    m.metrics,
    m.feature_importance
  FROM public.ml_models m
  WHERE m.status = 'active'
    AND m.model_type = p_model_type
  ORDER BY m.training_completed_at DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION public.cleanup_ml_predictions_cache()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM public.ml_predictions_cache
  WHERE expires_at < now();

  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Row Level Security
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.ml_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_training_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_predictions_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_training_jobs ENABLE ROW LEVEL SECURITY;

-- Public read access for models and predictions
CREATE POLICY "ml_models_public_read" ON public.ml_models
  FOR SELECT USING (true);

CREATE POLICY "ml_predictions_cache_public_read" ON public.ml_predictions_cache
  FOR SELECT USING (true);

-- Service role full access for all tables
CREATE POLICY "ml_models_service_all" ON public.ml_models
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "ml_training_data_service_all" ON public.ml_training_data
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "ml_predictions_cache_service_all" ON public.ml_predictions_cache
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "ml_training_jobs_service_all" ON public.ml_training_jobs
  FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- Triggers
-- ============================================================================

-- Update updated_at on ml_models
CREATE OR REPLACE FUNCTION public.update_ml_models_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ml_models_updated_at
  BEFORE UPDATE ON public.ml_models
  FOR EACH ROW
  EXECUTE FUNCTION public.update_ml_models_updated_at();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE public.ml_models IS 'Registry of trained ML models for signal prediction';
COMMENT ON TABLE public.ml_training_data IS 'Feature vectors and labels for ML model training';
COMMENT ON TABLE public.ml_predictions_cache IS 'Cache for ML predictions to reduce API latency';
COMMENT ON TABLE public.ml_training_jobs IS 'Training job execution history and status';

COMMENT ON COLUMN public.ml_training_data.label IS 'Target label: -2=strong_sell, -1=sell, 0=hold, 1=buy, 2=strong_buy';
COMMENT ON COLUMN public.ml_models.metrics IS 'Model performance metrics: accuracy, precision, recall, f1, auc';
COMMENT ON COLUMN public.ml_models.feature_importance IS 'Feature importance scores for explainability';
