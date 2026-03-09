# Closed-Loop Trading System Design

**Date:** 2026-03-09
**Page:** `/reference-portfolio` — full trading pipeline

---

## Problem

The reference portfolio has a 12.26% win rate and a profit factor of 0.17, producing a −$113K drawdown from peak. Root causes:

1. **5% stop-loss too tight** — normal stock volatility exits good trades on noise
2. **15% fixed take-profit** — too far to reach at current win rate; math guarantees losses
3. **No validated feedback loop** — `ModelFeedbackRetrainJob` exists but trade outcomes never retrain the model
4. **Weak signal source** — all legislator trades are treated equally; post-STOCK-Act research shows alpha only survives in leadership, committee-aligned, and clustered trades
5. **Fixed position sizing** — ignores signal quality and stock volatility

**Current expected value per trade:**
```
12.26% × +15% = +1.84%   wins
87.74% × −5%  = −4.39%   losses
EV per trade  = −2.55%   ← guaranteed to lose
```

---

## Approach: Fix-and-Extend with Shadow Model Gate (Approach B)

Incrementally repair the existing system in four layers, each independently deployable. A challenger/production shadow model framework ensures no degraded model version ever reaches "production" paper trading.

---

## Section 1: Parameter Fixes

### Stop-Loss — ATR-based
Replace fixed 5% with `entry_price − (1.5 × ATR20)`.

- ATR20 is the 20-day Average True Range, fetched from price history at execution time
- Anchors the stop to actual stock volatility, not an arbitrary percentage
- `stop_loss_price` column already exists on `reference_portfolio_positions`

### Take-Profit — Trailing Stop + Time Exit
Replace fixed 15% target with:
- **Trailing stop**: exit when `current_price < highest_price × 0.80` (20% below rolling 20-day high)
- **Time exit**: force close at +60 days regardless — research shows >80% of disclosure alpha is realized within 60 days
- `highest_price` column already exists on `reference_portfolio_positions`

### Position Sizing — Half-Kelly with Volatility Adjustment
Replace fixed `base_pct` with:

```
kelly      = win_rate − (1 − win_rate) / win_loss_ratio
half_kelly = kelly × 0.5
vol_adj    = 0.20 / stock_20d_realized_vol
size_pct   = min(half_kelly × vol_adj, 0.05)   ← hard cap 5% of NAV
```

- `win_rate` and `win_loss_ratio` computed from `signal_outcomes` over rolling 90-trade window
- Cold-start fallback: fixed 1% sizing until 30 labeled outcomes exist
- Never exceeds 5% NAV per position regardless of Kelly output

---

## Section 2: New Signal Features

Six features added to `feature_pipeline.py`, computed at signal generation time.

### Tier 1 (highest research-documented impact)

| Feature | Computation | Source |
|---|---|---|
| `clustering_count` | Distinct legislators buying same ticker in trailing 30 days | `trading_disclosures` |
| `committee_sector_alignment` | 1 if legislator's committee maps to stock's GICS sector | New `politician_committees` table via Congress.gov API |
| `disclosure_recency_days` | `disclosure_date − transaction_date` in days | `trading_disclosures` |

### Tier 2 (moderate impact)

| Feature | Computation | Source |
|---|---|---|
| `days_to_earnings` | Days until next earnings release for ticker | yfinance `get_earnings_dates()` |
| `market_cap_decile` | 1–10 decile bucket by market cap | yfinance, cached |
| `politician_trailing_score` | Politician's 90-day win rate on prior closed signals | `signal_outcomes` |

### Pre-Filter Gate
Signals are only queued if they pass at least one:
- `clustering_count ≥ 2`, OR
- `committee_sector_alignment = 1`, OR
- `disclosure_recency_days ≤ 10`

This removes rank-and-file, stale, isolated trades that research shows have near-zero post-STOCK-Act alpha.

### Committee-Sector Mapping
New `politician_committees` table:
```sql
CREATE TABLE politician_committees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  politician_id UUID REFERENCES politicians(id),
  committee_name TEXT NOT NULL,
  committee_code TEXT,
  gics_sectors TEXT[],   -- GICS sectors this committee oversees
  role TEXT,             -- 'chair', 'ranking_member', 'member'
  is_leadership BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```
Populated by extending `BioguideEnrichmentJob` to fetch committee assignments from Congress.gov API.

---

## Section 3: Closed Feedback Loop

### Outcome Labeling
When a position closes, `SignalOutcomeJob` (already exists) records in `signal_outcomes`:
- `outcome_label = position_return_pct − SPY_return_over_same_period` (excess return vs benchmark)
- `confidence_at_signal = trading_signals.confidence_score`
- `features_at_signal = trading_signals.features` (JSONB snapshot — avoids lookahead bias)

Excess return over SPY removes market beta — the model trains to predict **alpha**, not direction.

### Monthly Retraining (Scheduled)
`ModelFeedbackRetrainJob` runs on the 1st of each month:
1. Pull all labeled outcomes since last training date
2. Train challenger model using **walk-forward validation** (no k-fold — temporal leakage is invalid for financial time series)
3. Store challenger in `ml_models` with `status = 'challenger'`
4. Challenger begins scoring signals in shadow alongside production

### Trigger-Based Emergency Retrain
`DailyModelEvalJob` fires an immediate retrain cycle when:
- 30-day rolling win rate drops below **35%**, OR
- **30+ new labeled outcomes** have accumulated since last retrain

Same walk-forward pipeline as monthly, triggered early.

### Cold-Start Safety
Until 30 labeled outcomes exist: fall back to rule-based heuristic signals with fixed 1% position sizing. Half-Kelly and outcome-weighted retraining only activate after sufficient history.

---

## Section 4: Shadow Model Pipeline

Every signal scored by two models simultaneously:

```
Signal generated
    ↓
Production model  → signal.confidence_score         (used for execution)
Challenger model  → signal.challenger_confidence     (shadow only)
Both recorded in signal_audit_trail
    ↓
After 30 labeled outcomes on challenger:
  if challenger_30d_win_rate > production_30d_win_rate + 0.05:
    challenger promoted to production
    old production archived
```

**Schema additions to `trading_signals`:**
- `challenger_model_id UUID REFERENCES ml_models(id)`
- `challenger_confidence_score DECIMAL(5,4)`

**Promotion rule**: challenger must outperform production by ≥5% margin over ≥30 live trades. Prevents noise-driven promotion from a lucky short run. Monthly retrain always produces a challenger — never overwrites production directly.

---

## Validation Strategy

### Task 0 (first deliverable): Full Backtest
Before any code change touches production, a backtest script replays all 396 historical trades against the new parameters:

1. **Parameter backtest**: For each closed `reference_portfolio_positions` record, compute:
   - Would ATR stop have triggered earlier/later/not-at-all vs 5% fixed?
   - Would trailing stop have captured more upside vs 15% fixed TP?
   - What would Half-Kelly sizing have done to P&L on each trade?
   - Compute hypothetical total return, win rate, profit factor

2. **Pre-filter backtest**: Of the 396 past trades, how many pass the new pre-filter? What was the win rate on passing vs. filtered-out trades?

3. **Expected value sanity check**: New parameters must show EV > 0 on historical data before any code is written.

### Unit Tests (per component)
ATR calculation, trailing stop trigger, Half-Kelly formula, each new feature, pre-filter gate, feedback loop trigger conditions.

### Integration Tests
Extend `python-etl-service/scripts/test_etl_e2e.py` with full pipeline smoke test:
`Signal → pre-filter → ML score → queue → execute → ATR stop set → exit check → outcome labeled → retrain triggered`

### Shadow Model Validation (ongoing)
Challenger model scores every live paper trade. Win rate comparison runs continuously. No manual validation step needed — the promotion gate enforces it.

---

## Files to Change

| Layer | Files |
|---|---|
| Backtest | `python-etl-service/scripts/backtest_parameters.py` (new) |
| Parameters | `supabase/functions/reference-portfolio/index.ts` |
| Exit check | `server/lib/server/scheduler/jobs/reference_portfolio_exit_check_job.ex` |
| Features | `python-etl-service/app/services/feature_pipeline.py` |
| Pre-filter | `supabase/functions/trading-signals/index.ts` |
| Committees | `supabase/migrations/YYYYMMDD_politician_committees.sql` (new) |
| Bioguide job | `server/lib/server/scheduler/jobs/bioguide_enrichment_job.ex` |
| Feedback loop | `python-etl-service/app/services/ml_signal_model.py` |
| Monthly retrain | `server/lib/server/scheduler/jobs/model_feedback_retrain_job.ex` |
| Daily eval | `server/lib/server/scheduler/jobs/daily_model_eval_job.ex` |
| Shadow model | `supabase/migrations/YYYYMMDD_shadow_model_columns.sql` (new) |
| Signal generation | `supabase/functions/trading-signals/index.ts` |

---

## Research Sources

- Ziobrowski et al. (2004) — Senate abnormal returns ~5% over 3 months pre-STOCK-Act
- CEPR/VoxEU — Leadership trades outperform by 40–50 pp/year post-STOCK-Act
- NBER w26975 — Rank-and-file senators underperform post-2012
- EPJ Data Science (2024) — ML insider trade signal features
- Heckmann (2024, FoFI) — Synthesizing information-driven insider trade signals
- Lopez de Prado (2018) — Combinatorial Purged Cross-Validation for financial ML
- QuantInsti — Walk-forward validation for low-frequency signals
