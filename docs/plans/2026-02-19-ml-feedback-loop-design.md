# ML Feedback Loop: Fix & Wire Design

**Date:** 2026-02-19
**Status:** Approved
**Scope:** Connect existing ML infrastructure to create a working feedback loop from trade outcomes to model retraining

## Problem

The ML trading pipeline has a 7.41% win rate, -2.02 Sharpe ratio, and 35% max drawdown. Root causes:

1. **Dead-wired feedback loop** — `ModelFeedbackRetrainJob` (monthly) calls a non-existent `ml-training` edge function
2. **Training ignores outcomes** — model retrains weekly on disclosures + yfinance returns, never reads actual trade results from `signal_outcomes`
3. **ML has minimal influence** — blend weight reduced to 20% ML / 80% heuristic, heuristic always wins on disagreement
4. **No model comparison** — new models automatically replace old ones without performance comparison
5. **Loose signal thresholds** — 0.60 minimum confidence lets borderline signals reach the portfolio

## Architecture Overview

```
                    ┌──────────────────┐
                    │  signal_outcomes  │ ← SignalOutcomeJob (daily)
                    │  (actual P&L)    │
                    └────────┬─────────┘
                             │ read
                    ┌────────▼─────────┐
                    │  ml-training     │ ← ModelFeedbackRetrainJob (monthly)
                    │  edge function   │   MLTrainingJob (weekly)
                    │  (NEW)           │
                    └────────┬─────────┘
                             │ POST /ml/train
                    ┌────────▼─────────┐
                    │  FeaturePipeline │
                    │  + outcome data  │
                    └────────┬─────────┘
                             │ train
                    ┌────────▼─────────┐
                    │  Champion vs     │
                    │  Challenger eval │
                    └────────┬─────────┘
                             │ promote if better
                    ┌────────▼─────────┐
                    │  ml_models       │
                    │  (active model)  │
                    └────────┬─────────┘
                             │ batch-predict
                    ┌────────▼─────────┐
                    │  trading-signals │
                    │  (dynamic blend) │
                    └────────┬─────────┘
                             │ queue signals
                    ┌────────▼─────────┐
                    │  reference-      │
                    │  portfolio       │
                    │  (execute)       │
                    └────────┬─────────┘
                             │ close positions
                    ┌────────▼─────────┐
                    │  signal_outcomes  │ ← loop closes
                    └──────────────────┘
```

## Section 1: Outcome-Aware Training Pipeline

### Current Behavior

`FeaturePipeline.prepare_training_data()` fetches disclosures, computes features, then labels each data point using yfinance forward returns. The `signal_outcomes` table (populated daily by `SignalOutcomeJob`) is never read.

### Change

Add `prepare_outcome_training_data()` to `FeaturePipeline`:

1. Read `signal_outcomes` joined with `trading_signals` for original features
2. Label each record: win (return > 0.5%), loss (return < -0.5%), breakeven
3. Same feature extraction pipeline, but labels from real trade outcomes
4. Fall back to yfinance-based labeling for tickers with no outcome data
5. Weight outcome-labeled data 2x vs yfinance-labeled data during training

New `TrainingConfig` fields:
- `use_outcomes: bool = False`
- `outcome_weight: float = 2.0`

When `use_outcomes=True`, training data is a weighted blend:
- Outcome data (real trades): weight 2x
- Market data (yfinance hypothetical): weight 1x

### Files Modified

- `python-etl-service/app/services/feature_pipeline.py` — add `prepare_outcome_training_data()`
- `python-etl-service/app/models/training_config.py` — add `use_outcomes`, `outcome_weight`

## Section 2: Missing `ml-training` Edge Function

### Current Behavior

`ModelFeedbackRetrainJob` (Elixir) calls `SupabaseClient.invoke("ml-training", ...)` — function does not exist.

### Change

Create `supabase/functions/ml-training/index.ts`:

1. Accepts `{ action: "train", use_outcomes: true, outcome_window_days: 90, compare_to_current: true }`
2. Calls `POST {ETL_API_URL}/ml/train` with `use_outcomes=true`
3. If `compare_to_current=true`, after training:
   - Fetch new model's validation metrics from `ml_models` table
   - Fetch current active model's metrics
   - Only promote if accuracy or F1 improves by >= 2% (champion/challenger gate)
4. Return comparison results for Elixir logging

### Files Created

- `supabase/functions/ml-training/index.ts`

## Section 3: Champion/Challenger Model Evaluation

### Current Behavior

New models automatically replace the active model — no comparison.

### Change

Add to `feature_pipeline.py` model persistence step:

1. After training, compute validation metrics on holdout set
2. Load current `active` model, evaluate on SAME holdout set
3. Promote new model only if:
   - Accuracy improves >= 2%, OR
   - F1-weighted improves >= 3%
4. If new model is worse, save as `candidate` status for manual review
5. Log comparison to `ml_model_comparisons` table

### Database Changes

New table `ml_model_comparisons`:
- `id` UUID PK
- `new_model_id` UUID FK → ml_models
- `current_model_id` UUID FK → ml_models
- `new_accuracy` DECIMAL
- `current_accuracy` DECIMAL
- `new_f1` DECIMAL
- `current_f1` DECIMAL
- `promoted` BOOLEAN
- `reason` TEXT
- `created_at` TIMESTAMPTZ

### Files Modified

- `python-etl-service/app/services/feature_pipeline.py` — champion/challenger logic
- `python-etl-service/app/services/ml_signal_model.py` — add `evaluate_on_holdout()`
- New migration for `ml_model_comparisons` table

## Section 4: Dynamic ML Blend Weight

### Current Behavior

`ML_BLEND_WEIGHT = 0.2` hardcoded in `trading-signals/index.ts`.

### Change

Store `ml_blend_weight` in `reference_portfolio_config` table:

1. `signal-feedback/handleEvaluateModel()` already computes ML accuracy vs outcomes
2. After evaluation, adjust weight:
   - ML win rate > heuristic by 5%+: increase by 0.1 (cap 0.7)
   - ML win rate < heuristic by 5%+: decrease by 0.1 (floor 0.1)
   - Otherwise: no change
3. `trading-signals/index.ts` reads weight from config instead of constant
4. Log adjustments to `feature_importance_history`

### Files Modified

- `supabase/functions/trading-signals/index.ts` — read weight from config
- `supabase/functions/signal-feedback/index.ts` — update weight in evaluation
- Migration to add `ml_blend_weight` column to `reference_portfolio_config`

## Section 5: Tighter Signal Quality Thresholds

### Current Behavior

Minimum confidence 0.60 for signal generation, 0.70 for portfolio queue.

### Change

1. Raise signal generation minimum: 0.60 → 0.65
2. Raise portfolio queue minimum: 0.70 → 0.75
3. Filter out signals where ML and heuristic disagree on direction (buy vs sell)
4. Position-level risk check: don't enter if confidence < 0.70 AND portfolio has >= 15 open positions

### Files Modified

- `supabase/functions/trading-signals/index.ts` — threshold constants
- `supabase/functions/reference-portfolio/index.ts` — position risk check

## Section 6: Paper/Live Trading Toggle

### Current Behavior

Alpaca API URLs are hardcoded based on env vars. No explicit mode toggle.

### Change

Add `trading_mode: 'paper' | 'live'` to `reference_portfolio_config`:

1. Default: `'paper'`
2. `'paper'` → `https://paper-api.alpaca.markets`
3. `'live'` → `https://api.alpaca.markets`
4. Mode change requires admin action via dashboard
5. Admin dashboard shows current mode with warning banner in live mode

### Files Modified

- `supabase/functions/reference-portfolio/index.ts` — read mode from config, select URL
- Migration to add `trading_mode` column
- Admin dashboard UI update for mode toggle

## Implementation Order

1. Outcome-aware training (Section 1) — enables the feedback data path
2. `ml-training` edge function (Section 2) — wires up monthly retraining
3. Champion/challenger evaluation (Section 3) — safety gate for new models
4. Tighter thresholds (Section 5) — immediate win rate improvement
5. Dynamic blend weight (Section 4) — self-tuning ML influence
6. Paper/live toggle (Section 6) — operational readiness

## Success Criteria

- Win rate improves from 7.41% to > 30% within 2 retraining cycles
- Sharpe ratio improves from -2.02 to > 0
- Monthly retraining job executes successfully with outcome data
- Champion/challenger gate prevents model regressions
- ML blend weight self-adjusts based on measured performance
