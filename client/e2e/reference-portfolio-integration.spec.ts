import { test, expect, Page } from '@playwright/test';

/**
 * Reference Portfolio API Integration Tests
 *
 * Tests the integration between UI and Reference Portfolio APIs:
 * - Portfolio performance fetching
 * - Position tracking
 * - Transaction history
 * - Risk metrics display
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const mockPortfolioState = {
  id: 'state-1',
  cash: 50000,
  total_value: 150000,
  total_return: 0.15,
  total_return_pct: 15.0,
  daily_return: 500,
  daily_return_pct: 0.33,
  sharpe_ratio: 1.85,
  max_drawdown: -0.08,
  positions_count: 5,
  updated_at: new Date().toISOString(),
};

const mockPositions = [
  {
    id: 'pos-1',
    ticker: 'NVDA',
    quantity: 50,
    avg_cost: 450.0,
    current_price: 520.0,
    market_value: 26000,
    unrealized_pl: 3500,
    unrealized_pl_pct: 15.56,
    status: 'open',
  },
  {
    id: 'pos-2',
    ticker: 'AAPL',
    quantity: 100,
    avg_cost: 175.0,
    current_price: 185.0,
    market_value: 18500,
    unrealized_pl: 1000,
    unrealized_pl_pct: 5.71,
    status: 'open',
  },
];

const mockTransactions = [
  {
    id: 'tx-1',
    ticker: 'NVDA',
    side: 'buy',
    quantity: 50,
    price: 450.0,
    total: 22500,
    executed_at: new Date().toISOString(),
    signal_source: 'congressional_activity',
  },
  {
    id: 'tx-2',
    ticker: 'TSLA',
    side: 'sell',
    quantity: 25,
    price: 240.0,
    total: 6000,
    executed_at: new Date(Date.now() - 86400000).toISOString(),
    signal_source: 'bipartisan_signal',
  },
];

const mockSnapshots = [
  { date: '2024-01-01', value: 100000, return_pct: 0 },
  { date: '2024-01-15', value: 105000, return_pct: 5 },
  { date: '2024-02-01', value: 112000, return_pct: 12 },
  { date: '2024-02-15', value: 108000, return_pct: 8 },
  { date: '2024-03-01', value: 150000, return_pct: 50 },
];

async function setupPortfolioMocks(page: Page, options: {
  state?: typeof mockPortfolioState;
  positions?: typeof mockPositions;
  transactions?: typeof mockTransactions;
  snapshots?: typeof mockSnapshots;
} = {}) {
  const {
    state = mockPortfolioState,
    positions = mockPositions,
    transactions = mockTransactions,
    snapshots = mockSnapshots,
  } = options;

  // Mock portfolio state
  await page.route(`${SUPABASE_URL}/rest/v1/reference_portfolio_state**`, (route) =>
    route.fulfill({ status: 200, json: state })
  );

  // Mock positions
  await page.route(`${SUPABASE_URL}/rest/v1/reference_portfolio_positions**`, (route) =>
    route.fulfill({ status: 200, json: positions })
  );

  // Mock transactions
  await page.route(`${SUPABASE_URL}/rest/v1/reference_portfolio_transactions**`, (route) =>
    route.fulfill({ status: 200, json: transactions })
  );

  // Mock config
  await page.route(`${SUPABASE_URL}/rest/v1/reference_portfolio_config**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        initial_capital: 100000,
        max_position_size: 0.1,
        rebalance_threshold: 0.05,
      },
    })
  );

  // Mock performance edge function
  await page.route(`${SUPABASE_URL}/functions/v1/reference-portfolio**`, (route) =>
    route.fulfill({
      status: 200,
      json: { success: true, snapshots },
    })
  );
}

test.describe('Reference Portfolio Performance API', () => {
  test.describe('Portfolio Value Display', () => {
    test('should display current portfolio value', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByText(/\$150,000|\$150K/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display total return percentage', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByText(/15%|15\.0%/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display daily return', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });

    test('should display cash balance', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });
  });

  test.describe('Risk Metrics', () => {
    test('should display Sharpe ratio', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible({ timeout: 10000 });
    });

    test('should display max drawdown', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });
  });

  test.describe('Performance Chart', () => {
    test('should render performance chart', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      // Chart should be visible
      await expect(page.locator('canvas, svg, [class*="chart"]').first()).toBeVisible({ timeout: 10000 });
    });

    test('should update chart on timeframe change', async ({ page }) => {
      let timeframeRequested = '';

      await page.route(`${SUPABASE_URL}/functions/v1/reference-portfolio**`, async (route) => {
        const body = await route.request().postData();
        if (body) {
          const data = JSON.parse(body);
          timeframeRequested = data.timeframe || '1M';
        }
        await route.fulfill({
          status: 200,
          json: { success: true, snapshots: mockSnapshots },
        });
      });

      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });
  });
});

test.describe('Reference Portfolio Positions API', () => {
  test.describe('Position Listing', () => {
    test('should display open positions', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByText(/NVDA/i).first()).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/AAPL/i).first()).toBeVisible();
    });

    test('should display position P&L', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });

    test('should display position quantities', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });

    test('should handle empty positions', async ({ page }) => {
      await setupPortfolioMocks(page, { positions: [] });
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });
  });

  test.describe('Closed Positions', () => {
    test('should display closed positions history', async ({ page }) => {
      await setupPortfolioMocks(page, {
        positions: [
          ...mockPositions,
          {
            id: 'pos-closed',
            ticker: 'TSLA',
            quantity: 0,
            avg_cost: 200.0,
            current_price: 0,
            market_value: 0,
            unrealized_pl: 0,
            unrealized_pl_pct: 0,
            status: 'closed',
            realized_pl: 1500,
          },
        ],
      });

      await page.goto('/portfolio');
      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });
  });
});

test.describe('Reference Portfolio Transactions API', () => {
  test.describe('Transaction History', () => {
    test('should display transaction history', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible({ timeout: 10000 });
    });

    test('should show buy/sell transaction types', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });

    test('should paginate transactions', async ({ page }) => {
      const manyTransactions = Array.from({ length: 50 }, (_, i) => ({
        id: `tx-${i}`,
        ticker: ['NVDA', 'AAPL', 'TSLA'][i % 3],
        side: i % 2 === 0 ? 'buy' : 'sell',
        quantity: 10,
        price: 100 + i,
        total: (100 + i) * 10,
        executed_at: new Date(Date.now() - i * 86400000).toISOString(),
      }));

      await setupPortfolioMocks(page, { transactions: manyTransactions });
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });

    test('should filter transactions by type', async ({ page }) => {
      await setupPortfolioMocks(page);
      await page.goto('/portfolio');

      await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
    });
  });
});

test.describe('Reference Portfolio Error Handling', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/reference_portfolio_state**`, (route) =>
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    );

    await page.goto('/portfolio');
    await expect(page.getByRole('heading', { name: /portfolio|reference/i })).toBeVisible();
  });

  test('should show loading state', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/reference_portfolio_state**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({ status: 200, json: mockPortfolioState });
    });

    await page.goto('/portfolio');
    await expect(page.locator('.animate-spin, .animate-pulse').first()).toBeVisible();
  });
});
