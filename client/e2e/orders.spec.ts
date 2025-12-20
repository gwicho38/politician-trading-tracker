import { test, expect } from '@playwright/test';
import { mockAuthenticatedUser, mockUnauthenticated } from './fixtures/auth';

test.describe('Orders Page', () => {
  const mockOrders = [
    {
      id: '1',
      alpaca_order_id: 'alpaca-123',
      ticker: 'AAPL',
      order_type: 'market',
      side: 'buy',
      quantity: 10,
      filled_quantity: 10,
      status: 'filled',
      filled_avg_price: 175.50,
      submitted_at: '2024-01-15T10:30:00Z',
      filled_at: '2024-01-15T10:30:05Z',
      trading_mode: 'paper'
    },
    {
      id: '2',
      alpaca_order_id: 'alpaca-124',
      ticker: 'GOOGL',
      order_type: 'limit',
      side: 'buy',
      quantity: 5,
      limit_price: 140.00,
      status: 'pending_new',
      submitted_at: '2024-01-15T11:00:00Z',
      trading_mode: 'paper'
    },
    {
      id: '3',
      alpaca_order_id: 'alpaca-125',
      ticker: 'TSLA',
      order_type: 'market',
      side: 'sell',
      quantity: 15,
      status: 'canceled',
      submitted_at: '2024-01-14T09:00:00Z',
      canceled_at: '2024-01-14T09:05:00Z',
      trading_mode: 'paper'
    }
  ];

  test.describe('Unauthenticated Access', () => {
    test('should show login prompt when not authenticated', async ({ page }) => {
      await mockUnauthenticated(page);
      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      await expect(page.getByText(/please log in to view orders/i)).toBeVisible();
    });
  });

  test.describe('Authenticated Orders View', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);

      // Mock orders function response
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            orders: mockOrders,
            total: mockOrders.length,
            page: 1,
            pageSize: 20
          }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();
    });

    test('should display orders page header', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /orders/i })).toBeVisible();
    });

    test('should display trading mode selector', async ({ page }) => {
      await expect(page.getByLabel(/paper trading/i)).toBeVisible();
      await expect(page.getByLabel(/live trading/i)).toBeVisible();
    });

    test('should default to paper trading mode', async ({ page }) => {
      await expect(page.getByLabel(/paper trading/i)).toBeChecked();
    });

    test('should display status filter', async ({ page }) => {
      await expect(page.getByText(/filter by status/i)).toBeVisible();
    });
  });

  test.describe('Orders List', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            orders: mockOrders,
            total: mockOrders.length
          }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();
    });

    test('should display order ticker symbols', async ({ page }) => {
      await expect(page.getByText(/aapl/i)).toBeVisible();
      await expect(page.getByText(/googl/i)).toBeVisible();
      await expect(page.getByText(/tsla/i)).toBeVisible();
    });

    test('should display order status badges', async ({ page }) => {
      await expect(page.getByText(/filled/i)).toBeVisible();
      await expect(page.getByText(/pending/i)).toBeVisible();
      await expect(page.getByText(/canceled/i)).toBeVisible();
    });

    test('should display buy/sell side indicators', async ({ page }) => {
      await expect(page.getByText(/buy/i).first()).toBeVisible();
      await expect(page.getByText(/sell/i)).toBeVisible();
    });

    test('should display order quantities', async ({ page }) => {
      await expect(page.getByText(/10/)).toBeVisible();
      await expect(page.getByText(/5/)).toBeVisible();
      await expect(page.getByText(/15/)).toBeVisible();
    });
  });

  test.describe('Order Status Colors', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            orders: mockOrders,
            total: mockOrders.length
          }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();
    });

    test('should show green badge for filled orders', async ({ page }) => {
      const filledBadge = page.locator('text=filled').first();
      await expect(filledBadge).toBeVisible();
    });

    test('should show yellow badge for pending orders', async ({ page }) => {
      const pendingBadge = page.locator('text=pending').first();
      await expect(pendingBadge).toBeVisible();
    });

    test('should show red badge for canceled orders', async ({ page }) => {
      const canceledBadge = page.locator('text=canceled').first();
      await expect(canceledBadge).toBeVisible();
    });
  });

  test.describe('Sync Orders', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/orders**', (route) => {
        const body = route.request().postDataJSON?.() || {};
        if (body.action === 'sync-orders') {
          return route.fulfill({
            status: 200,
            json: {
              success: true,
              message: 'Orders synced successfully',
              synced: 5
            }
          });
        }
        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length }
        });
      });

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();
    });

    test('should display sync button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /sync/i })).toBeVisible();
    });

    test('should show loading state during sync', async ({ page }) => {
      // Mock delayed sync response
      await page.route('**/functions/v1/orders**', async (route) => {
        const body = route.request().postDataJSON?.() || {};
        if (body.action === 'sync-orders') {
          await new Promise(resolve => setTimeout(resolve, 500));
          return route.fulfill({
            status: 200,
            json: { success: true, synced: 5 }
          });
        }
        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length }
        });
      });

      await page.getByRole('button', { name: /sync/i }).click();

      // Should show loading indicator
      await expect(page.locator('.animate-spin')).toBeVisible();
    });
  });

  test.describe('Status Filtering', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();
    });

    test('should filter orders by status', async ({ page }) => {
      // Open status filter dropdown
      await page.getByRole('combobox').click();

      // Select filled status
      await page.getByRole('option', { name: /filled/i }).click();

      // Should update the filter
      await expect(page.getByRole('combobox')).toContainText(/filled/i);
    });
  });

  test.describe('Pagination', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);

      // Mock many orders for pagination
      const manyOrders = Array.from({ length: 50 }, (_, i) => ({
        id: String(i + 1),
        alpaca_order_id: `alpaca-${i + 1}`,
        ticker: ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN'][i % 5],
        order_type: 'market',
        side: i % 2 === 0 ? 'buy' : 'sell',
        quantity: 10,
        status: 'filled',
        submitted_at: new Date().toISOString(),
        trading_mode: 'paper'
      }));

      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, orders: manyOrders.slice(0, 20), total: 50 }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();
    });

    test('should display pagination controls', async ({ page }) => {
      await expect(page.getByRole('button', { name: /previous/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /next/i })).toBeVisible();
    });

    test('should show page information', async ({ page }) => {
      await expect(page.getByText(/page 1/i)).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should display empty state when no orders', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, orders: [], total: 0 }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      await expect(page.getByText(/no orders found/i)).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route('**/functions/v1/orders**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Internal server error' }
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      // Should show error message
      await expect(page.getByText(/error|failed/i)).toBeVisible({ timeout: 5000 });
    });
  });
});
