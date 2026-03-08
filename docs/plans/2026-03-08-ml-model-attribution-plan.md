# ML Model Attribution in Trade History — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show the ML model name + version in each BUY row of the trade history table, with a hover tooltip displaying accuracy, F1, precision, recall, and training date.

**Architecture:** Supabase FK traversal (`transactions → trading_signals → ml_models`) in a single query. No DB migration. SELL rows show `—` since exits are rule-based. Three files change: hook (query + type), table component (column + tooltip).

**Tech Stack:** TypeScript, React 18, Supabase JS v2, Shadcn UI Tooltip (already in project at `@/components/ui/tooltip`), Vitest

---

## Task 1: Add model types to the transaction interface

**Files:**
- Modify: `client/src/hooks/useReferencePortfolio.ts:94-118`
- Test: `client/src/hooks/useReferencePortfolio.test.ts` (create if absent)

### Step 1: Write the failing type test

Create or open `client/src/hooks/useReferencePortfolio.test.ts` and add:

```typescript
import { describe, it, expectTypeOf } from 'vitest';
import type { ReferencePortfolioTransaction } from './useReferencePortfolio';

describe('ReferencePortfolioTransaction', () => {
  it('includes optional signal.model with ML metrics', () => {
    const trade = {} as ReferencePortfolioTransaction;
    expectTypeOf(trade.signal).toEqualTypeOf<
      { model: { id: string; model_name: string; model_version: string; training_completed_at: string | null; metrics: Record<string, number> | null } | null } | null | undefined
    >();
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd client && npx vitest run src/hooks/useReferencePortfolio.test.ts
```

Expected: FAIL — `signal` does not exist on type

### Step 3: Add the nested types to the interface

In `client/src/hooks/useReferencePortfolio.ts`, insert before `ReferencePortfolioTransaction`:

```typescript
export interface TransactionModel {
  id: string;
  model_name: string;
  model_version: string;
  training_completed_at: string | null;
  metrics: Record<string, number> | null;
}

export interface TransactionSignal {
  model: TransactionModel | null;
}
```

Then add `signal` to `ReferencePortfolioTransaction` (after `realized_pl_pct`):

```typescript
  // Model attribution (BUY trades only, null for SELL)
  signal?: TransactionSignal | null;
```

### Step 4: Run test to verify it passes

```bash
cd client && npx vitest run src/hooks/useReferencePortfolio.test.ts
```

Expected: PASS

### Step 5: Commit

```bash
git add client/src/hooks/useReferencePortfolio.ts client/src/hooks/useReferencePortfolio.test.ts
git commit -m "feat: add TransactionModel and TransactionSignal types for ML attribution"
```

---

## Task 2: Update the hook query to fetch model data via FK traversal

**Files:**
- Modify: `client/src/hooks/useReferencePortfolio.ts:247-261`

### Step 1: Write test for enriched query shape

In the same test file, add:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    from: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    range: vi.fn().mockResolvedValue({
      data: [
        {
          id: 'txn-1',
          ticker: 'AAPL',
          transaction_type: 'buy',
          quantity: 10,
          price: 150,
          total_value: 1500,
          signal_id: 'sig-1',
          signal_confidence: 0.82,
          signal_type: 'buy',
          executed_at: '2026-01-01T10:00:00Z',
          status: 'executed',
          signal: {
            model: {
              id: 'model-1',
              model_name: 'congress_signal',
              model_version: 'v1.2.3',
              training_completed_at: '2025-12-01T00:00:00Z',
              metrics: { accuracy: 0.624, f1: 0.58, precision: 0.611, recall: 0.597 },
            },
          },
        },
      ],
      count: 1,
      error: null,
    }),
  },
}));

describe('useReferencePortfolioTrades query', () => {
  it('select string includes ml_models FK traversal', () => {
    const { supabase } = require('@/lib/supabase');
    // Trigger the hook call
    const selectCall = supabase.select.mock.calls[0]?.[0] ?? '';
    expect(selectCall).toContain('ml_models');
    expect(selectCall).toContain('model_name');
    expect(selectCall).toContain('model_version');
    expect(selectCall).toContain('metrics');
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd client && npx vitest run src/hooks/useReferencePortfolio.test.ts -t "select string"
```

Expected: FAIL — select does not contain `ml_models`

### Step 3: Update the query in `useReferencePortfolioTrades`

Replace the `.select('*', { count: 'exact' })` call (line 249) with:

```typescript
        .select(
          `*,
          signal:trading_signals!signal_id (
            model:ml_models!model_id (
              id,
              model_name,
              model_version,
              training_completed_at,
              metrics
            )
          )`,
          { count: 'exact' }
        )
```

Also update the cast on the return (line 259) so TypeScript is happy:

```typescript
        trades: (data || []) as ReferencePortfolioTransaction[],
```

(No change needed — the cast already covers it since `signal` is optional.)

### Step 4: Run test to verify it passes

```bash
cd client && npx vitest run src/hooks/useReferencePortfolio.test.ts
```

Expected: PASS

### Step 5: Commit

```bash
git add client/src/hooks/useReferencePortfolio.ts
git commit -m "feat: fetch ML model data via FK traversal in trades hook"
```

---

## Task 3: Add Model column to TradeHistoryTable with hover tooltip

**Files:**
- Modify: `client/src/components/reference-portfolio/TradeHistoryTable.tsx`
- Test: `client/src/components/reference-portfolio/TradeHistoryTable.test.tsx` (create)

### Step 1: Write failing render test

Create `client/src/components/reference-portfolio/TradeHistoryTable.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TradeHistoryTable } from './TradeHistoryTable';

// Mock the hook
vi.mock('@/hooks/useReferencePortfolio', () => ({
  useReferencePortfolioTrades: () => ({
    data: {
      trades: [
        {
          id: 'txn-1',
          ticker: 'AAPL',
          transaction_type: 'buy',
          quantity: 10,
          price: 150,
          total_value: 1500,
          signal_id: 'sig-1',
          signal_confidence: 0.82,
          signal_type: 'buy',
          executed_at: '2026-01-01T10:00:00Z',
          status: 'executed',
          exit_reason: null,
          realized_pl: null,
          realized_pl_pct: null,
          signal: {
            model: {
              id: 'model-1',
              model_name: 'congress_signal',
              model_version: 'v1.2.3',
              training_completed_at: '2025-12-01T00:00:00Z',
              metrics: { accuracy: 0.624, f1: 0.58, precision: 0.611, recall: 0.597 },
            },
          },
        },
        {
          id: 'txn-2',
          ticker: 'MSFT',
          transaction_type: 'sell',
          quantity: 5,
          price: 200,
          total_value: 1000,
          signal_id: null,
          signal_confidence: null,
          signal_type: null,
          executed_at: '2026-01-02T10:00:00Z',
          status: 'executed',
          exit_reason: 'stop_loss',
          realized_pl: -50,
          realized_pl_pct: -5,
          signal: null,
        },
      ],
      total: 2,
    },
    isLoading: false,
    error: null,
  }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

describe('TradeHistoryTable', () => {
  it('renders Model column header', () => {
    render(<TradeHistoryTable />, { wrapper });
    expect(screen.getByText('Model')).toBeInTheDocument();
  });

  it('shows model badge for BUY trade with model data', () => {
    render(<TradeHistoryTable />, { wrapper });
    expect(screen.getByText('congress_signal')).toBeInTheDocument();
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();
  });

  it('shows dash for SELL trade with no model', () => {
    render(<TradeHistoryTable />, { wrapper });
    // SELL row model cell should show —
    const cells = screen.getAllByText('—');
    expect(cells.length).toBeGreaterThan(0);
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd client && npx vitest run src/components/reference-portfolio/TradeHistoryTable.test.tsx
```

Expected: FAIL — "Model" column not found

### Step 3: Update `TradeHistoryTable.tsx`

**3a. Add Tooltip to imports** (after `Badge` import on line 11):

```typescript
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
```

**3b. Add `Model` table header** (after the `Signal` `<TableHead>` on line 89):

```typescript
                  <TableHead className="text-xs font-medium">Model</TableHead>
```

**3c. Add `Model` table cell** in the row map, after the Signal cell (after line 172, before the Status cell):

```typescript
                      <TableCell>
                        <ModelBadge trade={trade} />
                      </TableCell>
```

**3d. Add the `ModelBadge` component** at the top of the file, after the imports and before `TradeHistoryTableProps`:

```typescript
function formatTrainingDate(isoDate: string | null): string {
  if (!isoDate) return 'Unknown';
  return new Date(isoDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

function ModelBadge({ trade }: { trade: ReferencePortfolioTransaction }) {
  const model = trade.signal?.model;
  if (!model) return <span className="text-muted-foreground text-xs">—</span>;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="cursor-default">
            <span className="text-xs font-medium text-foreground">{model.model_name}</span>
            <span className="text-[10px] text-muted-foreground block">{model.model_version}</span>
          </div>
        </TooltipTrigger>
        <TooltipContent className="w-52 p-3 space-y-1.5">
          <p className="font-semibold text-xs">{model.model_name} {model.model_version}</p>
          <p className="text-[10px] text-muted-foreground">
            Trained {formatTrainingDate(model.training_completed_at)}
          </p>
          {model.metrics && (
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 pt-1 border-t border-border/50">
              {[
                ['Accuracy', model.metrics.accuracy],
                ['F1 Score', model.metrics.f1],
                ['Precision', model.metrics.precision],
                ['Recall', model.metrics.recall],
              ].map(([label, val]) =>
                val != null ? (
                  <div key={label as string} className="flex justify-between">
                    <span className="text-[10px] text-muted-foreground">{label}</span>
                    <span className="text-[10px] font-medium">
                      {typeof val === 'number' && val < 1
                        ? (val * 100).toFixed(1) + '%'
                        : String(val)}
                    </span>
                  </div>
                ) : null
              )}
            </div>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

### Step 4: Run test to verify it passes

```bash
cd client && npx vitest run src/components/reference-portfolio/TradeHistoryTable.test.tsx
```

Expected: PASS — all 3 tests green

### Step 5: Run full client test suite to check for regressions

```bash
cd client && npx vitest run
```

Expected: all previously passing tests still pass

### Step 6: Commit

```bash
git add client/src/components/reference-portfolio/TradeHistoryTable.tsx \
        client/src/components/reference-portfolio/TradeHistoryTable.test.tsx
git commit -m "feat: add ML model attribution column to trade history table"
```

---

## Task 4: Push and verify CI

### Step 1: Push

```bash
git push origin main
```

### Step 2: Monitor CI

```bash
gh run watch
```

Expected: all checks green

### Step 3: Smoke-test in browser (optional)

Visit `https://govmarket.trade/reference-portfolio`, scroll to Trade History. BUY rows should show a model name + version; hovering should show the metrics tooltip. SELL rows show `—`.

> **Note:** If `signal.model` comes back as `null` for all rows (i.e., the FK traversal returns nothing), check that `trading_signals.model_id` is populated for recent signals by running:
> ```sql
> SELECT id, ticker, model_id, model_version FROM trading_signals
> WHERE id IN (SELECT DISTINCT signal_id FROM reference_portfolio_transactions WHERE signal_id IS NOT NULL)
> LIMIT 5;
> ```
> If `model_id` is null on all signals, the tooltip will show `—` for all rows until the next signal regeneration cycle.
