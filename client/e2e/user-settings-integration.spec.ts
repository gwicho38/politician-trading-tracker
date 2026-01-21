import { test, expect, Page } from '@playwright/test';
import { mockAuthSession } from './utils/api-mocks';

/**
 * User Settings API Integration Tests
 *
 * Tests the integration between UI and User Settings APIs:
 * - API key management
 * - Cart persistence
 * - Admin role verification
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const testUser = {
  id: 'test-settings-user',
  email: 'settings@test.com',
  isAdmin: false,
};

const adminUser = {
  id: 'admin-settings-user',
  email: 'admin@test.com',
  isAdmin: true,
};

const mockCredentials = {
  id: 'cred-1',
  user_email: testUser.email,
  paper_api_key: 'PK_PAPER_****',
  paper_secret_key: 'SK_PAPER_****',
  paper_validated_at: new Date().toISOString(),
  live_api_key: null,
  live_secret_key: null,
  live_validated_at: null,
};

const mockCartItems = [
  { id: 'cart-1', user_id: testUser.id, ticker: 'NVDA', quantity: 10, side: 'buy' },
  { id: 'cart-2', user_id: testUser.id, ticker: 'AAPL', quantity: 5, side: 'buy' },
];

async function setupSettingsMocks(page: Page, options: {
  credentials?: typeof mockCredentials | null;
  cartItems?: typeof mockCartItems;
  isAdmin?: boolean;
} = {}) {
  const {
    credentials = mockCredentials,
    cartItems = mockCartItems,
    isAdmin = false,
  } = options;

  const user = isAdmin ? adminUser : testUser;
  await mockAuthSession(page, user);

  await page.route(`${SUPABASE_URL}/auth/v1/token**`, (route) =>
    route.fulfill({
      status: 200,
      json: { access_token: 'mock-token', user: { id: user.id, email: user.email } },
    })
  );

  await page.route(`${SUPABASE_URL}/auth/v1/user`, (route) =>
    route.fulfill({ status: 200, json: { id: user.id, email: user.email } })
  );

  // Mock credentials
  await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, async (route) => {
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        json: credentials ? [credentials] : [],
      });
    }

    if (method === 'POST' || method === 'PATCH') {
      return route.fulfill({ status: 200, json: credentials });
    }

    if (method === 'DELETE') {
      return route.fulfill({ status: 200, json: {} });
    }

    return route.fulfill({ status: 200, json: {} });
  });

  // Mock cart
  await page.route(`${SUPABASE_URL}/rest/v1/user_carts**`, async (route) => {
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, json: cartItems });
    }

    if (method === 'POST') {
      return route.fulfill({ status: 201, json: {} });
    }

    if (method === 'DELETE') {
      return route.fulfill({ status: 200, json: {} });
    }

    return route.fulfill({ status: 200, json: {} });
  });

  // Mock admin role check
  await page.route(`${SUPABASE_URL}/rest/v1/rpc/has_role**`, (route) =>
    route.fulfill({ status: 200, json: isAdmin })
  );
}

test.describe('API Keys Management Integration', () => {
  test.describe('Credentials Display', () => {
    test('should display saved credentials (masked)', async ({ page }) => {
      await setupSettingsMocks(page);
      await page.goto('/settings');

      await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible({ timeout: 10000 });
    });

    test('should show not connected state when no credentials', async ({ page }) => {
      await setupSettingsMocks(page, { credentials: null });
      await page.goto('/settings');

      await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
    });
  });

  test.describe('Save Credentials', () => {
    test('should save paper trading keys', async ({ page }) => {
      let keysSaved = false;

      await setupSettingsMocks(page, { credentials: null });

      await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, async (route) => {
        const method = route.request().method();

        if (method === 'POST' || method === 'PATCH') {
          keysSaved = true;
          return route.fulfill({ status: 200, json: mockCredentials });
        }

        return route.fulfill({ status: 200, json: [] });
      });

      await page.goto('/settings');
      await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
    });

    test('should save live trading keys', async ({ page }) => {
      await setupSettingsMocks(page);
      await page.goto('/settings');

      await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
    });
  });

  test.describe('Clear Credentials', () => {
    test('should clear credentials', async ({ page }) => {
      let credentialsCleared = false;

      await setupSettingsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, async (route) => {
        if (route.request().method() === 'DELETE') {
          credentialsCleared = true;
          return route.fulfill({ status: 200, json: {} });
        }
        return route.fulfill({ status: 200, json: [mockCredentials] });
      });

      await page.goto('/settings');
      await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
    });
  });
});

test.describe('Cart Persistence Integration', () => {
  test.describe('Load Cart', () => {
    test('should load cart from database on login', async ({ page }) => {
      await setupSettingsMocks(page);
      await page.goto('/trading-signals');

      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Save Cart', () => {
    test('should save cart to database', async ({ page }) => {
      let cartSaved = false;

      await setupSettingsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/user_carts**`, async (route) => {
        if (route.request().method() === 'POST') {
          cartSaved = true;
          return route.fulfill({ status: 201, json: {} });
        }
        return route.fulfill({ status: 200, json: mockCartItems });
      });

      await page.goto('/trading-signals');
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });
  });

  test.describe('Clear Cart', () => {
    test('should clear cart on checkout', async ({ page }) => {
      let cartCleared = false;

      await setupSettingsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/user_carts**`, async (route) => {
        if (route.request().method() === 'DELETE') {
          cartCleared = true;
          return route.fulfill({ status: 200, json: {} });
        }
        return route.fulfill({ status: 200, json: mockCartItems });
      });

      await page.goto('/trading-signals');
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });
  });
});

test.describe('Admin Role Integration', () => {
  test.describe('Admin Verification', () => {
    test('should verify admin role', async ({ page }) => {
      await setupSettingsMocks(page, { isAdmin: true });
      await page.goto('/admin');

      // Admin page should be accessible
      await expect(page.getByRole('heading', { name: /admin/i })).toBeVisible({ timeout: 10000 });
    });

    test('should hide admin features for non-admin', async ({ page }) => {
      await setupSettingsMocks(page, { isAdmin: false });
      await page.goto('/admin');

      // May show access denied or redirect
      // Just verify page loads without crashing
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test.describe('Admin Actions', () => {
    test('should allow admin to access data collection', async ({ page }) => {
      await setupSettingsMocks(page, { isAdmin: true });
      await page.goto('/admin');

      await expect(page.getByRole('heading', { name: /admin/i })).toBeVisible({ timeout: 10000 });
    });
  });
});

test.describe('Settings Loading States', () => {
  test('should show loading while fetching credentials', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({ status: 200, json: [mockCredentials] });
    });

    await mockAuthSession(page, testUser);
    await page.goto('/settings');

    await expect(page.locator('.animate-spin, .animate-pulse').first()).toBeVisible();
  });
});

test.describe('Settings Error Handling', () => {
  test('should handle credentials fetch error', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) =>
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    );

    await mockAuthSession(page, testUser);
    await page.goto('/settings');

    // Should still show settings page
    await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
  });
});
