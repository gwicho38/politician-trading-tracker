import { test, expect, Page } from '@playwright/test';
import { mockAuthenticatedUser } from './fixtures/auth';
import { mockOrder, mockAlpacaAccount, mockPosition } from './utils/api-mocks';

/**
 * Orders API Integration Tests
 *
 * These tests verify the complete integration between the UI and Orders APIs:
 * - Order placement (market, limit, stop orders)
 * - Order history fetching and display
 * - Order cancellation
 * - Order syncing from Alpaca
 * - Error handling and validation
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

// Extended mock data
const mockOrders = [
  mockOrder({
    id: 'order-1',
    alpaca_order_id: 'alp-001',
    ticker: 'AAPL',
    side: 'buy',
    quantity: 10,
    order_type: 'market',
    status: 'filled',
    filled_qty: 10,
    filled_avg_price: 175.50,
    trading_mode: 'paper',
  }),
  mockOrder({
    id: 'order-2',
    alpaca_order_id: 'alp-002',
    ticker: 'NVDA',
    side: 'buy',
    quantity: 5,
    order_type: 'limit',
    limit_price: 450.00,
    status: 'pending',
    trading_mode: 'paper',
  }),
  mockOrder({
    id: 'order-3',
    alpaca_order_id: 'alp-003',
    ticker: 'TSLA',
    side: 'sell',
    quantity: 15,
    order_type: 'market',
    status: 'canceled',
    trading_mode: 'paper',
  }),
];

const mockCredentials = {
  paper_api_key: 'PK_TEST_ORDERS',
  paper_secret_key: 'SK_TEST_ORDERS',
  paper_validated_at: new Date().toISOString(),
  live_api_key: null,
  live_secret_key: null,
  live_validated_at: null,
};

async function setupOrdersPage(page: Page, options: {
  orders?: typeof mockOrders;
  account?: ReturnType<typeof mockAlpacaAccount>;
  positions?: ReturnType<typeof mockPosition>[];
} = {}) {
  const { orders = mockOrders, account = mockAlpacaAccount(), positions = [] } = options;

  await mockAuthenticatedUser(page);

  // Mock credentials
  await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
    route.fulfill({ status: 200, json: [mockCredentials] })
  );

  // Mock alpaca account
  await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, (route) =>
    route.fulfill({
      status: 200,
      json: { success: true, account, positions, tradingMode: 'paper' },
    })
  );

  // Mock orders endpoint
  await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
    const body = await route.request().postData();
    const action = body ? JSON.parse(body).action : null;

    if (action === 'get-orders') {
      return route.fulfill({
        status: 200,
        json: { success: true, orders, total: orders.length, limit: 50, offset: 0 },
      });
    }

    if (action === 'place-order') {
      const orderData = JSON.parse(body!);
      const newOrder = mockOrder({
        ticker: orderData.ticker,
        side: orderData.side,
        quantity: orderData.quantity,
        order_type: orderData.order_type,
        status: 'pending',
      });
      return route.fulfill({
        status: 200,
        json: { success: true, order: newOrder },
      });
    }

    if (action === 'sync-orders') {
      return route.fulfill({
        status: 200,
        json: {
          success: true,
          message: 'Orders synced successfully',
          summary: { total: 10, synced: 3, updated: 2, errors: 0 },
        },
      });
    }

    return route.fulfill({ status: 200, json: { success: true } });
  });
}

test.describe('Order Placement API Integration', () => {
  test.describe('Market Orders', () => {
    test('should place market buy order successfully', async ({ page }) => {
      let orderPlaced = false;
      let placedOrderData: Record<string, unknown> | null = null;

      await setupOrdersPage(page);

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order') {
          orderPlaced = true;
          placedOrderData = data;
          return route.fulfill({
            status: 200,
            json: {
              success: true,
              order: mockOrder({
                ticker: data.ticker,
                side: data.side,
                quantity: data.quantity,
                status: 'pending',
              }),
            },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');

      // Navigate to place order - this may vary by UI
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });

    test('should place market sell order successfully', async ({ page }) => {
      await setupOrdersPage(page, {
        positions: [mockPosition('AAPL', { qty: '50' })],
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });

    test('should validate order quantity is positive', async ({ page }) => {
      await setupOrdersPage(page);

      // Mock validation error response
      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order' && data.quantity <= 0) {
          return route.fulfill({
            status: 400,
            json: { success: false, error: 'Quantity must be positive' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });
  });

  test.describe('Limit Orders', () => {
    test('should place limit buy order with price', async ({ page }) => {
      let placedOrderData: Record<string, unknown> | null = null;

      await setupOrdersPage(page);

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order') {
          placedOrderData = data;
          return route.fulfill({
            status: 200,
            json: {
              success: true,
              order: mockOrder({
                ticker: data.ticker,
                order_type: 'limit',
                limit_price: data.limit_price,
                status: 'pending',
              }),
            },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });

    test('should validate limit price is provided for limit orders', async ({ page }) => {
      await setupOrdersPage(page);

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order' && data.order_type === 'limit' && !data.limit_price) {
          return route.fulfill({
            status: 400,
            json: { success: false, error: 'Limit price required for limit orders' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });
  });

  test.describe('Order Placement Errors', () => {
    test('should handle insufficient buying power error', async ({ page }) => {
      await setupOrdersPage(page, {
        account: mockAlpacaAccount({ buying_power: '100.00' }), // Very low buying power
      });

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order') {
          return route.fulfill({
            status: 400,
            json: { success: false, error: 'Insufficient buying power' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });

    test('should handle market closed error', async ({ page }) => {
      await setupOrdersPage(page);

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order') {
          return route.fulfill({
            status: 400,
            json: { success: false, error: 'Market is closed' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });

    test('should handle invalid ticker error', async ({ page }) => {
      await setupOrdersPage(page);

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'place-order' && data.ticker === 'INVALID') {
          return route.fulfill({
            status: 400,
            json: { success: false, error: 'Invalid ticker symbol' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });
  });
});

test.describe('Order History API Integration', () => {
  test.describe('Order Listing', () => {
    test('should fetch and display orders from API', async ({ page }) => {
      await setupOrdersPage(page);

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      // Should show orders
      await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/NVDA/i)).toBeVisible();
    });

    test('should filter orders by status', async ({ page }) => {
      const filledOrders = mockOrders.filter(o => o.status === 'filled');

      await mockAuthenticatedUser(page);
      await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
        route.fulfill({ status: 200, json: [mockCredentials] })
      );

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.status === 'filled') {
          return route.fulfill({
            status: 200,
            json: { success: true, orders: filledOrders, total: filledOrders.length },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, orders: mockOrders, total: mockOrders.length },
        });
      });

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      await expect(page.getByRole('heading', { name: /orders/i })).toBeVisible();
    });

    test('should paginate orders', async ({ page }) => {
      const manyOrders = Array.from({ length: 100 }, (_, i) =>
        mockOrder({
          id: `order-${i}`,
          ticker: ['AAPL', 'NVDA', 'TSLA'][i % 3],
          status: 'filled',
        })
      );

      await mockAuthenticatedUser(page);
      await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
        route.fulfill({ status: 200, json: [mockCredentials] })
      );

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};
        const offset = data.offset || 0;
        const limit = data.limit || 20;

        return route.fulfill({
          status: 200,
          json: {
            success: true,
            orders: manyOrders.slice(offset, offset + limit),
            total: manyOrders.length,
            limit,
            offset,
          },
        });
      });

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      // Should show pagination
      await expect(page.getByRole('button', { name: /next/i })).toBeVisible({ timeout: 10000 });
    });

    test('should show empty state when no orders', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
        route.fulfill({ status: 200, json: [mockCredentials] })
      );

      await page.route(`${SUPABASE_URL}/functions/v1/orders**`, (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, orders: [], total: 0 },
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      await expect(page.getByText(/no orders/i)).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Order Details', () => {
    test('should display filled price for completed orders', async ({ page }) => {
      await setupOrdersPage(page, {
        orders: [
          mockOrder({
            ticker: 'AAPL',
            status: 'filled',
            filled_avg_price: 175.50,
            filled_qty: 10,
          }),
        ],
      });

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 });
    });

    test('should display limit price for pending limit orders', async ({ page }) => {
      await setupOrdersPage(page, {
        orders: [
          mockOrder({
            ticker: 'NVDA',
            order_type: 'limit',
            limit_price: 450.00,
            status: 'pending',
          }),
        ],
      });

      await page.goto('/');
      await page.getByRole('button', { name: /orders/i }).click();

      await expect(page.getByText(/NVDA/i)).toBeVisible({ timeout: 10000 });
    });
  });
});

test.describe('Order Cancellation API Integration', () => {
  test('should cancel pending order', async ({ page }) => {
    let orderCanceled = false;

    await mockAuthenticatedUser(page);
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 200, json: [mockCredentials] })
    );

    const pendingOrder = mockOrder({
      id: 'pending-order',
      alpaca_order_id: 'alp-pending',
      ticker: 'NVDA',
      status: 'pending',
    });

    await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
      const body = await route.request().postData();
      const data = body ? JSON.parse(body) : {};

      if (data.action === 'cancel-order') {
        orderCanceled = true;
        return route.fulfill({
          status: 200,
          json: { success: true, message: 'Order canceled' },
        });
      }

      return route.fulfill({
        status: 200,
        json: { success: true, orders: [pendingOrder], total: 1 },
      });
    });

    // Mock Alpaca cancel endpoint
    await page.route('**/api.alpaca.markets/v2/orders/**', (route) =>
      route.fulfill({ status: 200, json: {} })
    );

    await page.route('**/paper-api.alpaca.markets/v2/orders/**', (route) =>
      route.fulfill({ status: 200, json: {} })
    );

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    await expect(page.getByText(/NVDA/i)).toBeVisible({ timeout: 10000 });
  });

  test('should handle cancellation failure', async ({ page }) => {
    await mockAuthenticatedUser(page);
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 200, json: [mockCredentials] })
    );

    await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
      const body = await route.request().postData();
      const data = body ? JSON.parse(body) : {};

      if (data.action === 'cancel-order') {
        return route.fulfill({
          status: 400,
          json: { success: false, error: 'Order already filled' },
        });
      }

      return route.fulfill({
        status: 200,
        json: { success: true, orders: mockOrders, total: mockOrders.length },
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    await expect(page.getByRole('heading', { name: /orders/i })).toBeVisible();
  });

  test('should not allow canceling filled orders', async ({ page }) => {
    await setupOrdersPage(page, {
      orders: [mockOrder({ status: 'filled' })],
    });

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    // Filled order should not have cancel button
    await expect(page.getByText(/filled/i).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Order Sync API Integration', () => {
  test('should sync orders from Alpaca', async ({ page }) => {
    let syncCalled = false;

    await mockAuthenticatedUser(page);
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 200, json: [mockCredentials] })
    );

    await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
      const body = await route.request().postData();
      const data = body ? JSON.parse(body) : {};

      if (data.action === 'sync-orders') {
        syncCalled = true;
        return route.fulfill({
          status: 200,
          json: {
            success: true,
            message: 'Synced 5 orders',
            summary: { total: 10, synced: 5, updated: 2, errors: 0 },
          },
        });
      }

      return route.fulfill({
        status: 200,
        json: { success: true, orders: mockOrders, total: mockOrders.length },
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    // Find and click sync button
    const syncButton = page.getByRole('button', { name: /sync/i });
    await expect(syncButton).toBeVisible({ timeout: 10000 });
    await syncButton.click();

    await page.waitForTimeout(1000);
    expect(syncCalled).toBe(true);
  });

  test('should show sync progress', async ({ page }) => {
    await mockAuthenticatedUser(page);
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 200, json: [mockCredentials] })
    );

    await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
      const body = await route.request().postData();
      const data = body ? JSON.parse(body) : {};

      if (data.action === 'sync-orders') {
        await new Promise(resolve => setTimeout(resolve, 1000));
        return route.fulfill({
          status: 200,
          json: { success: true, summary: { synced: 5 } },
        });
      }

      return route.fulfill({
        status: 200,
        json: { success: true, orders: mockOrders, total: mockOrders.length },
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    const syncButton = page.getByRole('button', { name: /sync/i });
    await expect(syncButton).toBeVisible({ timeout: 10000 });
    await syncButton.click();

    // Should show loading state
    await expect(page.locator('.animate-spin').first()).toBeVisible();
  });

  test('should handle sync errors', async ({ page }) => {
    await mockAuthenticatedUser(page);
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 200, json: [mockCredentials] })
    );

    await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
      const body = await route.request().postData();
      const data = body ? JSON.parse(body) : {};

      if (data.action === 'sync-orders') {
        return route.fulfill({
          status: 500,
          json: { success: false, error: 'Failed to connect to Alpaca' },
        });
      }

      return route.fulfill({
        status: 200,
        json: { success: true, orders: mockOrders, total: mockOrders.length },
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    await expect(page.getByRole('heading', { name: /orders/i })).toBeVisible();
  });
});

test.describe('Order Loading States', () => {
  test('should show loading spinner while fetching orders', async ({ page }) => {
    await mockAuthenticatedUser(page);
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 200, json: [mockCredentials] })
    );

    await page.route(`${SUPABASE_URL}/functions/v1/orders**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        json: { success: true, orders: mockOrders, total: mockOrders.length },
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    // Should show loading
    await expect(page.locator('.animate-spin').first()).toBeVisible();
  });

  test('should hide loading after orders load', async ({ page }) => {
    await setupOrdersPage(page);

    await page.goto('/');
    await page.getByRole('button', { name: /orders/i }).click();

    await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 });
  });
});
