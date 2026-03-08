# ML Model Attribution in Trade History

**Date:** 2026-03-08
**Page:** `/reference-portfolio` — Trade History section

---

## Problem

The trade history table shows signal confidence but gives no indication of which ML model generated each signal. Users cannot connect a trade outcome to the model version that drove it.

---

## Approach

**Supabase FK traversal** — no DB migration required. The linkage already exists:

```
reference_portfolio_transactions.signal_id
  → trading_signals.model_id
  → ml_models (model_name, model_version, training_completed_at, metrics)
```

SELL trades have `signal_id = null` (exits are triggered by stop-loss/take-profit, not ML signals). Those rows render `—` in the model column.

---

## Data Layer

Update `useReferencePortfolioTrades` hook query:

```ts
supabase.from('reference_portfolio_transactions').select(`
  *,
  signal:trading_signals!signal_id (
    model:ml_models!model_id (
      id, model_name, model_version, training_completed_at, metrics
    )
  )
`)
```

No migration. No new API surface. Single round-trip.

---

## UI

Add a **Model** column to `TradeHistoryTable` between `Signal Confidence` and `Status`.

- **BUY rows with model data:** Render a badge `congress_signal_v1.2.3` with a Shadcn `<Tooltip>` on hover:
  ```
  congress_signal_v1.2.3
  Trained: Dec 2025
  ──────────────────
  Accuracy    62.4%
  F1 Score    0.58
  Precision   61.1%
  Recall      59.7%
  ```
- **SELL rows / null model:** Render `—`, no tooltip.

Use existing Shadcn `Tooltip`, `TooltipContent`, `TooltipProvider` components (already in the project).

---

## Files to Change

| File | Change |
|------|--------|
| `client/src/hooks/useReferencePortfolio.ts` | Update select query with FK traversal |
| `client/src/types/referencePortfolio.ts` (or inline) | Add `signal.model` shape to transaction type |
| `client/src/components/reference-portfolio/TradeHistoryTable.tsx` | Add Model column + Tooltip |

---

## Out of Scope

- SELL trade model attribution (exits are rule-based, not model-driven)
- Model metrics page / dedicated model card
- Backfilling model data for historical transactions with `signal_id = null`
