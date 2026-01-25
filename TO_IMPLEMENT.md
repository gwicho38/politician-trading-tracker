# Reference Portfolio Strategy Improvements

## Executive Summary

The reference portfolio is currently experiencing a -30.33% drawdown with a 2.70% win rate. Analysis reveals critical issues in the entry/exit asymmetry, signal timing lag, and ML model configuration. This document outlines immediate, medium-term, and long-term improvements to fix the strategy.

---

## Current Performance Issues

### Identified Problems
1. **Asymmetric Entry/Exit Strategy** - Aggressively buys but rarely sells
2. **Signal Timing Lag** - Trading on 30-45 day old information (disclosure delay)
3. **ML Model May Be Adding Noise** - 40% ML weight might be degrading performance
4. **No Momentum/Market Context** - Ignoring broader market conditions (set to 0)
5. **High Confidence Threshold (70%)** - Too selective, missing diversification
6. **Position Concentration Risk** - Over-allocating to losers, not trimming positions

---

## Implementation Roadmap

### Phase 1: Immediate Fixes (High Impact)

#### ✅ 1.1 Widen Stop-Loss and Take-Profit Levels
**Status**: PENDING
**Priority**: CRITICAL
**Effort**: 1 hour
**Files**: 
- `supabase/migrations/20260109_reference_portfolio.sql`
- Create new migration to update config

**Changes**:
```sql
-- Current values:
-- default_stop_loss_pct: 5.00
-- default_take_profit_pct: 15.00

-- New values:
default_stop_loss_pct: 10.00  -- Widen to account for disclosure lag
default_take_profit_pct: 25.00 -- Higher target for winners
```

**Rationale**: 5% stop-loss is too tight for politician trades with 30-90 day information lag. Stocks need more room to breathe.

---

#### ✅ 1.2 Add Trailing Stop Configuration
**Status**: PENDING
**Priority**: HIGH
**Effort**: 2 hours
**Files**:
- `supabase/migrations/` (new migration)
- `supabase/functions/reference-portfolio/index.ts`
- `server/lib/server/scheduler/jobs/reference_portfolio_exit_check_job.ex`

**Changes**:
1. Add `trailing_stop_pct` column to `reference_portfolio_config` table (default: 8.00)
2. Add `trailing_stop_price` column to `reference_portfolio_positions` table
3. Update exit check logic to handle trailing stops
4. Track highest price since entry and adjust trailing stop dynamically

**Rationale**: Protect gains by locking in profits as stock rises, while allowing upside to run.

---

#### ✅ 1.3 Implement Time-Based Position Exits
**Status**: PENDING
**Priority**: HIGH
**Effort**: 3 hours
**Files**:
- `supabase/migrations/` (new migration)
- `supabase/functions/reference-portfolio/index.ts` (handleCheckExits)

**Changes**:
1. Add `max_hold_days` to config table (default: 60)
2. Add `days_held` calculated field to position queries
3. Auto-close positions held longer than `max_hold_days`
4. Log exit reason as "time_exit"

**Rationale**: Disclosures are 30-45 days delayed. Holding beyond 60 days means trading on 90+ day old information, which is stale.

---

#### ✅ 1.4 Enable Sell Signal Queueing
**Status**: PENDING
**Priority**: CRITICAL
**Effort**: 1 hour
**Files**:
- `supabase/functions/reference-portfolio/index.ts` (queueSignalsForReferencePortfolio)

**Changes**:
```typescript
// BEFORE:
const eligibleSignals = signals.filter(signal =>
  signal.confidence_score >= config.min_confidence_threshold &&
  ['buy', 'strong_buy'].includes(signal.signal_type)
)

// AFTER:
const eligibleSignals = signals.filter(signal => {
  const isBuySignal = ['buy', 'strong_buy'].includes(signal.signal_type)
  const isSellSignal = ['sell', 'strong_sell'].includes(signal.signal_type)
  
  // Lower threshold for sell signals to exit positions faster
  const confidenceThreshold = isSellSignal 
    ? config.min_confidence_threshold * 0.85 
    : config.min_confidence_threshold
    
  return signal.confidence_score >= confidenceThreshold &&
    (isBuySignal || isSellSignal)
})
```

**Rationale**: Currently only buying, never selling based on signals. This creates massive asymmetry.

---

#### ✅ 1.5 Implement Market Momentum and Sector Performance Features
**Status**: PENDING
**Priority**: HIGH
**Effort**: 4 hours
**Files**:
- `supabase/functions/trading-signals/index.ts` (getBatchMlPredictions)
- Create new helper functions for market data fetching

**Changes**:
1. Create `getMarketMomentum(ticker)` function using Alpaca API
2. Create `getSectorPerformance(ticker)` function using sector ETF mapping
3. Replace hardcoded 0 values with actual calculations:
```typescript
// BEFORE:
market_momentum: 0,
sector_performance: 0,

// AFTER:
market_momentum: await getMarketMomentum(ticker),
sector_performance: await getSectorPerformance(ticker),
```

**Rationale**: Ignoring market context causes buying in downtrends and selling in uptrends.

**Implementation Details**:
- Market Momentum: 20-day price change percentage
- Sector Performance: Sector ETF 20-day return (SPY for general market)
- Cache results for 1 hour to reduce API calls

---

#### ✅ 1.6 Reduce ML Blend Weight (Experimental)
**Status**: PENDING
**Priority**: MEDIUM
**Effort**: 30 minutes
**Files**:
- `supabase/functions/trading-signals/index.ts`

**Changes**:
```typescript
// BEFORE:
const ML_BLEND_WEIGHT = 0.40 // 40% ML, 60% heuristic

// AFTER:
const ML_BLEND_WEIGHT = 0.20 // 20% ML, 80% heuristic
```

**Rationale**: If ML model is stale or poorly trained, it may be adding noise. Reduce weight as experiment.

**Testing**: Run A/B test with separate config for 2 weeks, compare performance.

---

### Phase 2: Medium-Term Improvements

#### ⏳ 2.1 Lower Confidence Threshold for Diversification
**Status**: PENDING
**Priority**: MEDIUM
**Effort**: 1 hour
**Files**:
- Database config update via SQL

**Changes**:
```sql
-- BEFORE:
min_confidence_threshold: 0.70

-- AFTER:
min_confidence_threshold: 0.60
```

**Rationale**: With disclosure lag, even "high confidence" signals are stale. Lower threshold allows more diversification.

---

#### ⏳ 2.2 Implement Contrarian Signal Weighting
**Status**: PENDING
**Priority**: MEDIUM
**Effort**: 6 hours
**Files**:
- `supabase/functions/trading-signals/index.ts` (new contrarian logic)
- `python-etl-service/app/services/ml_signal_model.py` (new features)

**Changes**:
1. Add `price_run_up_30d` feature (price change since average politician buy date)
2. If heavy buying AND price_run_up > 15%, flip signal to SELL
3. If heavy selling AND price_drop > 15%, flip signal to BUY
4. Add `contrarian_mode` config flag

**Rationale**: Politician trades are delayed 30-45 days. By the time we see them, price may have already moved. Contrarian approach captures mean reversion.

---

#### ⏳ 2.3 Dynamic Position Sizing Based on Volatility
**Status**: PENDING
**Priority**: MEDIUM
**Effort**: 4 hours
**Files**:
- `supabase/functions/reference-portfolio/index.ts` (calculatePositionSize)

**Changes**:
```typescript
// Add volatility calculation
const volatility = await getHistoricalVolatility(ticker, 30) // 30-day ATR
const volatilityPercentile = getPercentile(volatility, allStockVolatilities)

// Adjust position size inversely to volatility
const volatilityAdjustment = 1.0 - (volatilityPercentile * 0.5)
const adjustedSize = baseSize * multiplier * volatilityAdjustment
```

**Rationale**: Reduce size for high-volatility stocks to manage risk. Current fixed sizing doesn't account for stock-specific risk.

---

#### ⏳ 2.4 Retrain ML Model with Outcome Feedback Loop
**Status**: PENDING
**Priority**: HIGH
**Effort**: 8 hours
**Files**:
- `python-etl-service/app/services/ml_signal_model.py`
- `python-etl-service/app/routes/ml.py` (new retraining endpoint)
- New training script using `signal_outcomes` table

**Changes**:
1. Create training data from `signal_outcomes` table
2. Features should include:
   - `actual_return_30d`
   - `actual_return_60d`
   - `market_adjusted_return`
   - `sharpe_ratio`
3. Target: Binary classification (profitable vs unprofitable after 30/60 days)
4. Retrain XGBoost model monthly
5. A/B test new model vs current model

**Rationale**: Current ML model may be trained on different data distribution. Feedback loop allows continuous improvement.

---

#### ⏳ 2.5 Add Weekly Portfolio Rebalancing Job
**Status**: PENDING
**Priority**: MEDIUM
**Effort**: 5 hours
**Files**:
- `server/lib/server/scheduler/jobs/reference_portfolio_rebalance_job.ex` (new)
- `supabase/functions/reference-portfolio/index.ts` (new action)

**Changes**:
1. Run every Sunday at midnight
2. Trim winners that exceed 7% portfolio weight → sell down to 5%
3. Cut losers below -8% → close position entirely
4. Rebalance to maintain target 15-20 positions
5. Free up capital from concentrated positions

**Rationale**: Current strategy doesn't rebalance, leading to over-concentration in losing positions.

---

### Phase 3: Long-Term Enhancements

#### 🔮 3.1 Ensemble Strategy with Multiple Signal Sources
**Status**: PENDING
**Priority**: LOW
**Effort**: 20 hours
**Files**:
- New `ensemble_signals` table
- New `ensemble_strategy_config` table
- `supabase/functions/trading-signals/index.ts` (major refactor)

**Changes**:
1. Create modular signal generators:
   - **Politician Signals** (60% weight)
   - **Technical Breakouts** (20% weight) - RSI, MACD, Bollinger Bands
   - **Earnings Momentum** (20% weight) - Post-earnings drift
2. Combine signals with weighted average
3. Allow configurable weights per strategy component

**Rationale**: Don't rely solely on politician trades. Diversify signal sources to reduce strategy-specific risk.

---

#### 🔮 3.2 Advanced Risk Management Dashboard
**Status**: PENDING
**Priority**: LOW
**Effort**: 12 hours
**Files**:
- `client/src/pages/ReferencePortfolioDashboard.tsx` (enhance)
- New risk metrics calculation endpoints

**Changes**:
1. Add real-time risk metrics:
   - Value at Risk (VaR) 95th percentile
   - Expected Shortfall (CVaR)
   - Beta to S&P 500
   - Correlation matrix of holdings
2. Position heat map by sector/politician
3. Alerts for concentration risk, correlated holdings

**Rationale**: Better visibility into portfolio risk beyond simple P&L.

---

#### 🔮 3.3 Backtesting Framework
**Status**: PENDING
**Priority**: MEDIUM
**Effort**: 16 hours
**Files**:
- New `backtesting/` directory
- Python backtesting engine using historical data
- Supabase function to run backtests

**Changes**:
1. Historical data ingestion (past 2 years of politician trades)
2. Simulate strategy with different parameters
3. Walk-forward optimization
4. Compare multiple strategy variants
5. Generate backtest reports with Sharpe, max drawdown, win rate

**Rationale**: Test improvements before deploying to live paper trading. Essential for ML model validation.

---

## Testing & Validation Plan

### Quick Validation Test (2 Weeks)

**Configuration**:
```json
{
  "ml_blend_weight": 0,
  "min_confidence_threshold": 0.60,
  "default_stop_loss_pct": 10.00,
  "default_take_profit_pct": 25.00,
  "max_hold_days": 60,
  "enable_sell_signals": true
}
```

**Success Metrics**:
- Win rate > 40% (currently 2.70%)
- Max drawdown < 20% (currently 30.33%)
- Sharpe ratio > 0.5
- Avg winning trade > Avg losing trade

**Decision Point**: If metrics improve, proceed with remaining phases. If not, revisit ML model entirely.

---

## Risk Mitigation

### Rollback Plan
1. All changes implemented as feature flags in config
2. Keep previous config as "baseline" strategy
3. Run both strategies in parallel for 2 weeks
4. Compare performance before full rollover

### Monitoring
1. Daily performance review
2. Alert if drawdown exceeds 35%
3. Auto-pause trading if 5 consecutive losing trades
4. Weekly review of closed positions and outcomes

---

## Implementation Priority Order

### Week 1 (Critical Fixes)
1. ✅ 1.1 Widen Stop-Loss and Take-Profit
2. ✅ 1.4 Enable Sell Signal Queueing
3. ✅ 1.3 Time-Based Position Exits

### Week 2 (High Impact)
4. ✅ 1.5 Market Momentum Features
5. ✅ 1.2 Trailing Stop Implementation
6. ✅ 1.6 Reduce ML Blend Weight

### Week 3 (Medium Priority)
7. ⏳ 2.1 Lower Confidence Threshold
8. ⏳ 2.4 ML Model Retraining

### Week 4 (Enhancement)
9. ⏳ 2.3 Dynamic Position Sizing
10. ⏳ 2.5 Weekly Rebalancing

### Future (Long-term)
11. 🔮 3.3 Backtesting Framework
12. 🔮 3.1 Ensemble Strategy
13. 🔮 3.2 Risk Dashboard

---

## Success Criteria

### Immediate (2 Weeks)
- [ ] Win rate > 40%
- [ ] Max drawdown < 20%
- [ ] At least 10 closed positions for statistical significance

### Medium-term (1 Month)
- [ ] Sharpe ratio > 0.5
- [ ] Positive total return
- [ ] Profit factor > 1.5

### Long-term (3 Months)
- [ ] Consistent outperformance vs S&P 500
- [ ] Sharpe ratio > 1.0
- [ ] Max drawdown < 15%
- [ ] Win rate 50-60%

---

## Notes

- Each item includes file references for easy implementation
- Status indicators: ✅ (Week 1-2), ⏳ (Week 3-4), 🔮 (Future)
- Effort estimates are approximate
- Some items may require additional research/testing
- All changes should be reversible via config flags

---

**Last Updated**: 2026-01-25
**Owner**: Development Team
**Review Cadence**: Weekly
