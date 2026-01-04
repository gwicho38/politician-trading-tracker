import { test, expect } from '@playwright/test';

test.describe('Showcase Page', () => {
  const mockStrategies = [
    {
      id: '1',
      name: 'Conservative Growth',
      description: 'Focus on insider expertise and volume consistency',
      user_id: 'user-1',
      is_public: true,
      likes_count: 42,
      user_has_liked: false,
      weights: { insiderExpertise: 2.0, volumeConsistency: 1.5 },
      created_at: '2024-01-15T10:00:00Z',
      profiles: { display_name: 'TraderJoe' },
    },
    {
      id: '2',
      name: 'Momentum Chaser',
      description: 'High weights on recent activity signals',
      user_id: 'user-2',
      is_public: true,
      likes_count: 28,
      user_has_liked: true,
      weights: { recentActivity: 2.5, trendStrength: 2.0 },
      created_at: '2024-01-10T10:00:00Z',
      profiles: { display_name: 'CryptoKing' },
    },
  ];

  test.beforeEach(async ({ page }) => {
    // Mock strategies API
    await page.route('**/rest/v1/signal_presets**', (route) =>
      route.fulfill({
        status: 200,
        json: mockStrategies,
      })
    );

    // Mock auth session (not authenticated by default)
    await page.route('**/auth/v1/session**', (route) =>
      route.fulfill({
        status: 200,
        json: { session: null },
      })
    );

    await page.goto('/showcase');
  });

  test.describe('Page Structure', () => {
    test('should display showcase heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /strategy showcase/i })).toBeVisible();
    });

    test('should display community description', async ({ page }) => {
      await expect(page.getByText(/community-created signal strategies/i)).toBeVisible();
    });

    test('should display back button', async ({ page }) => {
      await expect(page.getByRole('link').filter({ has: page.locator('svg') }).first()).toBeVisible();
    });

    test('should display create strategy button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /create strategy/i })).toBeVisible();
    });
  });

  test.describe('Sort Controls', () => {
    test('should display sort selector', async ({ page }) => {
      await expect(page.getByRole('combobox')).toBeVisible();
    });

    test('should allow sorting by most recent', async ({ page }) => {
      await page.getByRole('combobox').click();
      await expect(page.getByRole('option', { name: /most recent/i })).toBeVisible();
    });

    test('should allow sorting by most liked', async ({ page }) => {
      await page.getByRole('combobox').click();
      await expect(page.getByText(/most liked/i)).toBeVisible();
    });
  });

  test.describe('Strategy Cards', () => {
    test('should display page heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /strategy showcase/i })).toBeVisible();
    });

    test('should display create strategy button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /create strategy/i })).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading skeletons while fetching', async ({ page }) => {
      const slowPage = await page.context().newPage();

      await slowPage.route('**/rest/v1/signal_presets**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({ status: 200, json: mockStrategies });
      });

      await slowPage.goto('/showcase');
      await expect(slowPage.locator('.animate-pulse').first()).toBeVisible();
      await slowPage.close();
    });
  });

  test.describe('Page States', () => {
    test('should handle page load', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /strategy showcase/i })).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should navigate to playground on create strategy click', async ({ page }) => {
      await page.getByRole('button', { name: /create strategy/i }).click();
      await expect(page).toHaveURL('/playground');
    });

    test('should navigate back home on back button click', async ({ page }) => {
      await page.getByRole('link').filter({ has: page.locator('svg') }).first().click();
      await expect(page).toHaveURL('/');
    });
  });

  test.describe('Footer', () => {
    test('should display footer message', async ({ page }) => {
      await expect(page.getByText(/share your strategies with the community/i)).toBeVisible();
    });
  });
});
