-- Shadow model columns on trading_signals.
-- Every signal is scored by both production and challenger model simultaneously.
-- Challenger auto-promotes when it outperforms production by ≥5% over ≥30 trades.

ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS challenger_model_id UUID REFERENCES public.ml_models(id),
  ADD COLUMN IF NOT EXISTS challenger_confidence_score DECIMAL(5,4);

COMMENT ON COLUMN public.trading_signals.challenger_model_id IS
  'Challenger model scoring this signal in shadow. Null if no challenger active.';
COMMENT ON COLUMN public.trading_signals.challenger_confidence_score IS
  'Challenger model confidence score. Compared to confidence_score for promotion decisions.';

-- View: compare production vs challenger win rates over last 90 days
CREATE OR REPLACE VIEW public.shadow_model_comparison AS
SELECT
  so.model_id             AS production_model_id,
  ts.challenger_model_id,
  COUNT(*)                AS outcome_count,
  AVG(CASE WHEN so.outcome = 'win' THEN 1.0 ELSE 0.0 END) AS production_win_rate,
  AVG(CASE WHEN so.return_pct > 0 AND ts.challenger_confidence_score > 0.5
           THEN 1.0 ELSE 0.0 END)                           AS challenger_win_rate
FROM public.signal_outcomes so
JOIN public.trading_signals ts ON ts.id = so.signal_id
WHERE ts.challenger_model_id IS NOT NULL
  AND so.created_at >= now() - INTERVAL '90 days'
GROUP BY so.model_id, ts.challenger_model_id;
