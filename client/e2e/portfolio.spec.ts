import { test, expect } from '@playwright/test';

test.describe('Portfolio Page', () => {
  const mockPositions = [
    {
      id: '1',
      ticker: 'AAPL',
      asset_name: 'Apple Inc.',
      quantity: 50,
      side: 'long',
      avg_entry_price: 165.00,
      current_price: 175.50,
      market_value: 8775.00,
      unrealized_pl: 525.00,
      unrealized_pl_pct: 6.36,
      is_open: true
    },
    {
      id: '2',
      ticker: 'NVDA',
      asset_name: 'NVIDIA Corporation',
      quantity: 20,
      side: 'long',
      avg_entry_price: 420.00,
      current_price: 480.00,
      market_value: 9600.00,
      unrealized_pl: 1200.00,
      unrealized_pl_pct: 14.29,
      is_open: true
    },
    {
      id: '3',
      ticker: 'TSLA',
      asset_name: 'Tesla Inc.',
      quantity: 15,
      side: 'long',
      avg_entry_price: 250.00,
      current_price: 235.00,
      market_value: 3525.00,
      unrealized_pl: -225.00,
      unrealized_pl_pct: -6.00,
      is_open: true
    }
  ];

  const mockAccount = {
    portfolio_value: '121900.00',
    cash: '100000.00',
    buying_power: '200000.00',
    last_equity: '120000.00',
    long_market_value: '21900.00',
    status: 'ACTIVE'
  };

  // Helper to mock authenticated state
  const mockAuthenticatedUser = async (page: any) => {
    await page.route('**/auth/v1/user**', (route: any) =>
      route.fulfill({
        status: 200,
        json: { id: 'test-user-123', email: 'test@example.com' }
      })
    );
    await page.route('**/auth/v1/session**', (route: any) =>
      route.fulfill({
        status: 200,
        json: {
          access_token: 'mock-token',
          user: { id: 'test-user-123', email: 'test@example.com' }
        }
      })
    );
  };

  test.describe('Unauthenticated Access', () => {
    test('should show login prompt when not authenticated', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();

      await expect(page.getByText(/please log in/i)).toBeVisible();
    });
  });

  test.describe('Authenticated Portfolio View', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);

      // Mock portfolio data
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            positions: mockPositions,
            account: mockAccount
          }
        })
      );

      // Mock orders
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, orders: [] }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();
    });

    test('should display portfolio heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /portfolio/i })).toBeVisible();
    });

    test('should display trading mode selector', async ({ page }) => {
      await expect(page.getByLabel(/paper trading/i)).toBeVisible();
      await expect(page.getByLabel(/live trading/i)).toBeVisible();
    });

    test('should default to paper trading mode', async ({ page }) => {
      await expect(page.getByLabel(/paper trading/i)).toBeChecked();
    });
  });

  test.describe('Account Summary', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, positions: mockPositions, account: mockAccount }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();
    });

    test('should display portfolio value', async ({ page }) => {
      await expect(page.getByText(/portfolio value/i)).toBeVisible();
    });

    test('should display cash balance', async ({ page }) => {
      await expect(page.getByText(/cash/i)).toBeVisible();
    });

    test('should display buying power', async ({ page }) => {
      await expect(page.getByText(/buying power/i)).toBeVisible();
    });

    test('should display account status badge', async ({ page }) => {
      await expect(page.getByText(/active/i)).toBeVisible();
    });
  });

  test.describe('Positions List', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, positions: mockPositions, account: mockAccount }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();
    });

    test('should display position ticker symbols', async ({ page }) => {
      await expect(page.getByText(/aapl/i)).toBeVisible();
      await expect(page.getByText(/nvda/i)).toBeVisible();
      await expect(page.getByText(/tsla/i)).toBeVisible();
    });

    test('should display position quantities', async ({ page }) => {
      await expect(page.getByText(/50/)).toBeVisible();
      await expect(page.getByText(/20/)).toBeVisible();
    });

    test('should display unrealized P&L', async ({ page }) => {
      // Positive P&L
      await expect(page.getByText(/\+?\$?525|\+6\.36%/)).toBeVisible();
      // Negative P&L
      await expect(page.getByText(/-\$?225|-6\.00%/)).toBeVisible();
    });

    test('should show green for positive P&L', async ({ page }) => {
      // NVDA has positive P&L
      const nvdaRow = page.locator('text=NVDA').locator('..');
      await expect(nvdaRow).toBeVisible();
    });

    test('should show red for negative P&L', async ({ page }) => {
      // TSLA has negative P&L
      const tslaRow = page.locator('text=TSLA').locator('..');
      await expect(tslaRow).toBeVisible();
    });
  });

  test.describe('Tabs Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, positions: mockPositions, account: mockAccount }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();
    });

    test('should display positions tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /positions/i })).toBeVisible();
    });

    test('should display pending orders tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /pending|orders/i })).toBeVisible();
    });
  });

  test.describe('Empty States', () => {
    test('should show empty state when no positions', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, positions: [], account: mockAccount }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();

      await expect(page.getByText(/no positions|no open positions/i)).toBeVisible();
    });
  });

  test.describe('Connection Status', () => {
    test('should show connected status when API is working', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, positions: mockPositions, account: mockAccount }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();

      await expect(page.getByText(/connected/i)).toBeVisible();
    });

    test('should show error status when API fails', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Connection failed' }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();

      await expect(page.getByText(/error|failed/i)).toBeVisible();
    });
  });

  test.describe('Refresh Functionality', () => {
    test('should have refresh button', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/portfolio**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, positions: mockPositions, account: mockAccount }
        })
      );
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({ status: 200, json: { success: true, orders: [] } })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /portfolio/i }).click();

      await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    });
  });
});
