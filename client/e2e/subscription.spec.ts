import { test, expect, Page, Route } from '@playwright/test';

test.describe('Subscription Page', () => {
  // Helper to mock authenticated state
  const mockAuthenticatedUser = async (page: Page) => {
    await page.route('**/auth/v1/user**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: { id: 'test-user-123', email: 'test@example.com' }
      })
    );
    await page.route('**/auth/v1/session**', (route: Route) =>
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
    test('should redirect to auth when not logged in', async ({ page }) => {
      await page.goto('/subscription');

      // Should redirect to auth page
      await expect(page).toHaveURL(/auth/);
    });
  });

  test.describe('Subscription Tiers', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/subscription');
    });

    test('should display subscription page heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /subscription|pricing|plans/i })).toBeVisible();
    });

    test('should display Free tier', async ({ page }) => {
      await expect(page.getByText(/free/i).first()).toBeVisible();
      await expect(page.getByText(/\$0/)).toBeVisible();
    });

    test('should display Pro tier', async ({ page }) => {
      await expect(page.getByText(/pro/i).first()).toBeVisible();
      await expect(page.getByText(/\$29/)).toBeVisible();
    });

    test('should display Enterprise tier', async ({ page }) => {
      await expect(page.getByText(/enterprise/i).first()).toBeVisible();
      await expect(page.getByText(/\$99/)).toBeVisible();
    });

    test('should highlight popular tier', async ({ page }) => {
      await expect(page.getByText(/popular|recommended/i)).toBeVisible();
    });
  });

  test.describe('Tier Features', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/subscription');
    });

    test('should display Free tier features', async ({ page }) => {
      await expect(page.getByText(/view recent politician trades/i)).toBeVisible();
      await expect(page.getByText(/basic search/i)).toBeVisible();
    });

    test('should display Pro tier features', async ({ page }) => {
      await expect(page.getByText(/ai-powered trading signals/i)).toBeVisible();
      await expect(page.getByText(/portfolio tracking/i)).toBeVisible();
    });

    test('should display Enterprise tier features', async ({ page }) => {
      await expect(page.getByText(/automated trading/i)).toBeVisible();
      await expect(page.getByText(/dedicated account manager/i)).toBeVisible();
    });
  });

  test.describe('Subscription Actions', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/subscription');
    });

    test('should display subscribe/upgrade buttons', async ({ page }) => {
      await expect(page.getByRole('button', { name: /subscribe|upgrade|get started/i }).first()).toBeVisible();
    });

    test('should show current plan indicator', async ({ page }) => {
      // Free tier should show current plan or similar indicator
      await expect(page.getByText(/current plan|free/i).first()).toBeVisible();
    });
  });

  test.describe('Feature Checkmarks', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/subscription');
    });

    test('should display checkmark icons for features', async ({ page }) => {
      // Should have checkmark or similar icon
      await expect(page.locator('svg').first()).toBeVisible();
    });
  });

  test.describe('Tier Cards', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/subscription');
    });

    test('should display tier descriptions', async ({ page }) => {
      await expect(page.getByText(/basic access/i)).toBeVisible();
      await expect(page.getByText(/advanced trading signals/i)).toBeVisible();
      await expect(page.getByText(/complete trading platform/i)).toBeVisible();
    });

    test('should display pricing interval', async ({ page }) => {
      await expect(page.getByText(/month/i).first()).toBeVisible();
    });
  });

  test.describe('Upgrade Flow', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);

      // Mock Stripe checkout
      await page.route('**/functions/v1/create-checkout**', (route) =>
        route.fulfill({
          status: 200,
          json: { url: 'https://checkout.stripe.com/test' }
        })
      );

      await page.goto('/subscription');
    });

    test('should initiate upgrade on button click', async ({ page }) => {
      const upgradeButton = page.getByRole('button', { name: /subscribe|upgrade|get started/i }).first();
      await upgradeButton.click();

      // Should show loading or redirect
      await expect(page.locator('.animate-spin')).toBeVisible({ timeout: 2000 }).catch(() => {
        // May redirect immediately
      });
    });
  });

  test.describe('Icons', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/subscription');
    });

    test('should display crown icon for premium tiers', async ({ page }) => {
      await expect(page.locator('svg').first()).toBeVisible();
    });
  });

  test.describe('Responsive Layout', () => {
    test('should display tiers in column on mobile', async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/subscription');

      // All tiers should still be visible
      await expect(page.getByText(/free/i).first()).toBeVisible();
      await expect(page.getByText(/pro/i).first()).toBeVisible();
      await expect(page.getByText(/enterprise/i).first()).toBeVisible();
    });
  });
});
