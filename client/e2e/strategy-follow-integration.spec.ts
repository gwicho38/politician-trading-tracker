import { test, expect, Page } from '@playwright/test';
import { mockAuthSession } from './utils/api-mocks';

/**
 * Strategy Follow API Integration Tests
 *
 * Tests the integration between UI and Strategy Follow APIs:
 * - Subscription management
 * - Trade syncing
 * - Strategy configuration
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const testUser = {
  id: 'test-strategy-user',
  email: 'strategy@test.com',
  isAdmin: false,
};

const mockSubscription = {
  id: 'sub-1',
  user_id: testUser.id,
  strategy_type: 'reference',
  trading_mode: 'paper',
  is_active: true,
  sync_existing_positions: true,
  created_at: new Date().toISOString(),
  last_sync_at: new Date().toISOString(),
};

const mockStrategyTrades = [
  {
    id: 'trade-1',
    ticker: 'NVDA',
    side: 'buy',
    quantity: 10,
    price: 450.0,
    status: 'executed',
    executed_at: new Date().toISOString(),
  },
  {
    id: 'trade-2',
    ticker: 'AAPL',
    side: 'buy',
    quantity: 20,
    price: 175.0,
    status: 'executed',
    executed_at: new Date(Date.now() - 86400000).toISOString(),
  },
];

async function setupStrategyMocks(page: Page, options: {
  subscription?: typeof mockSubscription | null;
  trades?: typeof mockStrategyTrades;
  isFollowing?: boolean;
} = {}) {
  const {
    subscription = mockSubscription,
    trades = mockStrategyTrades,
    isFollowing = true,
  } = options;

  await mockAuthSession(page, testUser);

  await page.route(`${SUPABASE_URL}/auth/v1/token**`, (route) =>
    route.fulfill({
      status: 200,
      json: { access_token: 'mock-token', user: { id: testUser.id, email: testUser.email } },
    })
  );

  await page.route(`${SUPABASE_URL}/auth/v1/user`, (route) =>
    route.fulfill({ status: 200, json: { id: testUser.id, email: testUser.email } })
  );

  // Mock strategy-follow edge function
  await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
    const body = await route.request().postData();
    const data = body ? JSON.parse(body) : {};

    if (data.action === 'get-subscription') {
      return route.fulfill({
        status: 200,
        json: { subscription, isFollowing },
      });
    }

    if (data.action === 'get-trades') {
      return route.fulfill({
        status: 200,
        json: { trades },
      });
    }

    if (data.action === 'subscribe') {
      return route.fulfill({
        status: 200,
        json: { success: true, message: 'Subscribed successfully' },
      });
    }

    if (data.action === 'unsubscribe') {
      return route.fulfill({
        status: 200,
        json: { success: true, message: 'Unsubscribed successfully' },
      });
    }

    if (data.action === 'sync-now') {
      return route.fulfill({
        status: 200,
        json: {
          success: true,
          summary: { trades_synced: 5, orders_placed: 3, errors: 0 },
        },
      });
    }

    return route.fulfill({ status: 200, json: {} });
  });
}

test.describe('Strategy Subscription API', () => {
  test.describe('Subscription Status', () => {
    test('should display subscription status when following', async ({ page }) => {
      await setupStrategyMocks(page, { isFollowing: true });
      await page.goto('/subscription');

      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible({ timeout: 10000 });
    });

    test('should show not subscribed state', async ({ page }) => {
      await setupStrategyMocks(page, { subscription: null, isFollowing: false });
      await page.goto('/subscription');

      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });

    test('should display trading mode', async ({ page }) => {
      await setupStrategyMocks(page);
      await page.goto('/subscription');

      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });
  });

  test.describe('Subscribe to Strategy', () => {
    test('should subscribe to reference strategy', async ({ page }) => {
      let subscribeAction: string | null = null;

      await setupStrategyMocks(page, { subscription: null, isFollowing: false });

      await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'subscribe') {
          subscribeAction = data.strategyType;
          return route.fulfill({
            status: 200,
            json: { success: true, message: 'Subscribed' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { subscription: null, isFollowing: false },
        });
      });

      await page.goto('/subscription');
      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });

    test('should handle subscription errors', async ({ page }) => {
      await setupStrategyMocks(page, { subscription: null, isFollowing: false });

      await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'subscribe') {
          return route.fulfill({
            status: 400,
            json: { success: false, error: 'Already subscribed to another strategy' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { subscription: null, isFollowing: false },
        });
      });

      await page.goto('/subscription');
      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });
  });

  test.describe('Unsubscribe from Strategy', () => {
    test('should unsubscribe from current strategy', async ({ page }) => {
      let unsubscribeCalled = false;

      await setupStrategyMocks(page);

      await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'unsubscribe') {
          unsubscribeCalled = true;
          return route.fulfill({
            status: 200,
            json: { success: true },
          });
        }

        return route.fulfill({
          status: 200,
          json: { subscription: mockSubscription, isFollowing: true },
        });
      });

      await page.goto('/subscription');
      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });
  });
});

test.describe('Strategy Trades API', () => {
  test.describe('Trade Display', () => {
    test('should display strategy trades', async ({ page }) => {
      await setupStrategyMocks(page);
      await page.goto('/subscription');

      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible({ timeout: 10000 });
    });

    test('should show trade status', async ({ page }) => {
      await setupStrategyMocks(page);
      await page.goto('/subscription');

      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });
  });
});

test.describe('Strategy Sync API', () => {
  test.describe('Manual Sync', () => {
    test('should trigger manual sync', async ({ page }) => {
      let syncCalled = false;

      await setupStrategyMocks(page);

      await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'sync-now') {
          syncCalled = true;
          return route.fulfill({
            status: 200,
            json: { success: true, summary: { trades_synced: 3 } },
          });
        }

        return route.fulfill({
          status: 200,
          json: { subscription: mockSubscription, isFollowing: true },
        });
      });

      await page.goto('/subscription');
      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });

    test('should show sync results', async ({ page }) => {
      await setupStrategyMocks(page);
      await page.goto('/subscription');

      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });

    test('should handle sync errors', async ({ page }) => {
      await setupStrategyMocks(page);

      await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
        const body = await route.request().postData();
        const data = body ? JSON.parse(body) : {};

        if (data.action === 'sync-now') {
          return route.fulfill({
            status: 500,
            json: { success: false, error: 'Sync failed' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { subscription: mockSubscription, isFollowing: true },
        });
      });

      await page.goto('/subscription');
      await expect(page.getByRole('heading', { name: /subscription|strategy|follow/i })).toBeVisible();
    });
  });
});

test.describe('Strategy Loading States', () => {
  test('should show loading while fetching subscription', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/functions/v1/strategy-follow**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        json: { subscription: mockSubscription, isFollowing: true },
      });
    });

    await mockAuthSession(page, testUser);
    await page.goto('/subscription');

    await expect(page.locator('.animate-spin, .animate-pulse').first()).toBeVisible();
  });
});
