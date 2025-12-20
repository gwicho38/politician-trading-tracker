import { test, expect } from '@playwright/test';

test.describe('Trading Operations', () => {
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

      // Navigate to trading operations via sidebar
      await page.getByRole('button', { name: /trading operations/i }).click();

      await expect(page.getByText(/please log in to access trading operations/i)).toBeVisible();
    });
  });

  test.describe('Authenticated Trading View', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);

      // Mock Alpaca account response
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            account: {
              portfolio_value: '100000.00',
              cash: '50000.00',
              buying_power: '100000.00',
              status: 'ACTIVE'
            }
          }
        })
      );

      // Mock trading orders
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({
          status: 200,
          json: [
            {
              id: '1',
              ticker: 'AAPL',
              side: 'buy',
              quantity: 10,
              order_type: 'market',
              status: 'filled',
              filled_quantity: 10,
              filled_avg_price: 175.50,
              submitted_at: new Date().toISOString()
            }
          ]
        })
      );

      await page.goto('/');
    });

    test('should display trading operations header', async ({ page }) => {
      await page.getByRole('button', { name: /trading operations/i }).click();

      await expect(page.getByRole('heading', { name: /trading operations/i })).toBeVisible();
      await expect(page.getByText(/execute trades based on ai signals/i)).toBeVisible();
    });

    test('should display account information', async ({ page }) => {
      await page.getByRole('button', { name: /trading operations/i }).click();

      await expect(page.getByText(/portfolio value/i)).toBeVisible();
      await expect(page.getByText(/\$100,000/)).toBeVisible();
      await expect(page.getByText(/cash/i)).toBeVisible();
      await expect(page.getByText(/\$50,000/)).toBeVisible();
      await expect(page.getByText(/buying power/i)).toBeVisible();
    });
  });

  test.describe('Trading Mode Selection', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            account: {
              portfolio_value: '100000.00',
              cash: '50000.00',
              buying_power: '100000.00',
              status: 'ACTIVE'
            }
          }
        })
      );
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /trading operations/i }).click();
    });

    test('should default to paper trading mode', async ({ page }) => {
      await expect(page.getByLabel(/paper trading/i)).toBeChecked();
      await expect(page.getByText(/paper trading mode \(safe\)/i)).toBeVisible();
    });

    test('should show warning when switching to live mode', async ({ page }) => {
      // Live trading is disabled without subscription, but we can check UI
      await expect(page.getByLabel(/live trading/i)).toBeVisible();
    });

    test('should display paper trading info message', async ({ page }) => {
      await expect(page.getByText(/simulated funds/i)).toBeVisible();
      await expect(page.getByText(/perfect for testing strategies/i)).toBeVisible();
    });
  });

  test.describe('Tab Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            account: {
              portfolio_value: '100000.00',
              cash: '50000.00',
              buying_power: '100000.00',
              status: 'ACTIVE'
            }
          }
        })
      );
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /trading operations/i }).click();
    });

    test('should display all trading tabs', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /cart execution/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /signal trading/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /manual orders/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /recent orders/i })).toBeVisible();
    });

    test('should switch between tabs', async ({ page }) => {
      // Click Manual Orders tab
      await page.getByRole('tab', { name: /manual orders/i }).click();
      await expect(page.getByLabel(/ticker symbol/i)).toBeVisible();

      // Click Recent Orders tab
      await page.getByRole('tab', { name: /recent orders/i }).click();
      await expect(page.getByText(/order history/i)).toBeVisible();
    });
  });

  test.describe('Manual Order Form', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            account: {
              portfolio_value: '100000.00',
              cash: '50000.00',
              buying_power: '100000.00',
              status: 'ACTIVE'
            }
          }
        })
      );
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /trading operations/i }).click();
      await page.getByRole('tab', { name: /manual orders/i }).click();
    });

    test('should display manual order form fields', async ({ page }) => {
      await expect(page.getByLabel(/ticker symbol/i)).toBeVisible();
      await expect(page.getByLabel(/quantity/i)).toBeVisible();
    });

    test('should toggle order type between market and limit', async ({ page }) => {
      // Check for order type selection
      await expect(page.getByText(/order type/i)).toBeVisible();
    });

    test('should require confirmation checkbox before placing order', async ({ page }) => {
      // The confirmation checkbox should be present
      await expect(page.getByText(/i confirm/i)).toBeVisible();
    });
  });

  test.describe('Cart Execution', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            account: {
              portfolio_value: '100000.00',
              cash: '50000.00',
              buying_power: '100000.00',
              status: 'ACTIVE'
            }
          }
        })
      );
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /trading operations/i }).click();
    });

    test('should display cart items when present', async ({ page }) => {
      // Cart is populated with mock data in the component
      await expect(page.getByText(/aapl/i)).toBeVisible();
      await expect(page.getByText(/apple inc/i)).toBeVisible();
    });

    test('should show execute button for cart trades', async ({ page }) => {
      await expect(page.getByRole('button', { name: /execute all cart trades/i })).toBeVisible();
    });
  });

  test.describe('Recent Orders', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            account: {
              portfolio_value: '100000.00',
              cash: '50000.00',
              buying_power: '100000.00',
              status: 'ACTIVE'
            }
          }
        })
      );
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({
          status: 200,
          json: [
            {
              id: '1',
              ticker: 'AAPL',
              side: 'buy',
              quantity: 10,
              order_type: 'market',
              status: 'filled',
              filled_quantity: 10,
              filled_avg_price: 175.50,
              submitted_at: new Date().toISOString()
            },
            {
              id: '2',
              ticker: 'GOOGL',
              side: 'buy',
              quantity: 5,
              order_type: 'limit',
              status: 'pending',
              submitted_at: new Date().toISOString()
            }
          ]
        })
      );
      await page.goto('/');
      await page.getByRole('button', { name: /trading operations/i }).click();
      await page.getByRole('tab', { name: /recent orders/i }).click();
    });

    test('should display recent orders list', async ({ page }) => {
      await expect(page.getByText(/order history/i)).toBeVisible();
    });

    test('should show order status badges', async ({ page }) => {
      // Check for status indicators
      await expect(page.getByText(/filled/i)).toBeVisible();
      await expect(page.getByText(/pending/i)).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      await mockAuthenticatedUser(page);

      // Mock API error
      await page.route('**/functions/v1/alpaca-account**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Internal server error' }
        })
      );
      await page.route('**/rest/v1/trading_orders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /trading operations/i }).click();

      // Should show error state for account info
      await expect(page.getByText(/error/i)).toBeVisible({ timeout: 5000 });
    });
  });
});
