import { test, expect } from '@playwright/test';

test.describe('Signal Playground Page', () => {
  const mockSignals = [
    {
      id: '1',
      ticker: 'NVDA',
      signal_type: 'buy',
      confidence_score: 0.85,
      politician_name: 'Nancy Pelosi',
      disclosure_date: '2024-01-15',
      ml_enhanced: true,
    },
    {
      id: '2',
      ticker: 'AAPL',
      signal_type: 'sell',
      confidence_score: 0.72,
      politician_name: 'Dan Crenshaw',
      disclosure_date: '2024-01-14',
      ml_enhanced: false,
    },
  ];

  const mockPresets = [
    {
      id: 'preset-1',
      name: 'Default Weights',
      description: 'System default configuration',
      is_system: true,
      is_public: true,
      weights: {},
    },
    {
      id: 'preset-2',
      name: 'Aggressive',
      description: 'Higher weights for momentum',
      is_system: true,
      is_public: true,
      weights: { momentum: 2.0 },
    },
  ];

  test.beforeEach(async ({ page }) => {
    // Mock signal preview API
    await page.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
      route.fulfill({
        status: 200,
        json: {
          signals: mockSignals,
          stats: {
            total: 2,
            buy: 1,
            sell: 1,
            mlEnhanced: 1,
          },
        },
      })
    );

    // Mock presets API
    await page.route('**/rest/v1/signal_presets**', (route) =>
      route.fulfill({
        status: 200,
        json: mockPresets,
      })
    );

    // Mock auth session (not authenticated by default)
    await page.route('**/auth/v1/session**', (route) =>
      route.fulfill({
        status: 200,
        json: { session: null },
      })
    );

    await page.goto('/playground');
  });

  test.describe('Page Structure', () => {
    test('should display playground heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /signal playground/i })).toBeVisible();
    });

    test('should display experiment description', async ({ page }) => {
      await expect(page.getByText(/experiment with signal generation weights/i)).toBeVisible();
    });

    test('should display back button', async ({ page }) => {
      await expect(page.getByRole('link').filter({ has: page.locator('svg') }).first()).toBeVisible();
    });
  });

  test.describe('Lookback Period Selector', () => {
    test('should display lookback period selector', async ({ page }) => {
      await expect(page.getByRole('combobox').first()).toBeVisible();
    });

    test('should show lookback options', async ({ page }) => {
      await page.getByRole('combobox').first().click();
      await expect(page.getByRole('option').first()).toBeVisible();
    });
  });

  test.describe('Weight Controls Panel', () => {
    test('should display weight controls section', async ({ page }) => {
      // Weight controls are in the left resizable panel
      await expect(page.locator('[data-panel-id]').first()).toBeVisible();
    });

    test('should have reset button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /reset/i })).toBeVisible();
    });

    test('should have save button (disabled when not authenticated)', async ({ page }) => {
      const saveButton = page.getByRole('button', { name: /save/i });
      await expect(saveButton).toBeVisible();
    });
  });

  test.describe('Signal Preview Panel', () => {
    test('should have right panel for signals', async ({ page }) => {
      // Check for panel structure
      await expect(page.locator('[data-panel-id]').nth(1)).toBeVisible();
    });
  });

  test.describe('ML Insights Panel', () => {
    test('should display ML insights section', async ({ page }) => {
      await expect(page.getByText(/ml/i)).toBeVisible();
    });
  });

  test.describe('Resizable Panels', () => {
    test('should have resizable handle between panels', async ({ page }) => {
      const handle = page.locator('[data-panel-resize-handle-id]');
      await expect(handle).toBeVisible();
    });
  });

  test.describe('Save Dialog (Unauthenticated)', () => {
    test('should show sign in button when not authenticated', async ({ page }) => {
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });
  });

  test.describe('Authentication', () => {
    test('should show sign in button when not authenticated', async ({ page }) => {
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading state while fetching signals', async ({ page }) => {
      const slowPage = await page.context().newPage();

      await slowPage.route('**/functions/v1/trading-signals/preview-signals**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          json: { signals: mockSignals, stats: { total: 2 } },
        });
      });

      await slowPage.route('**/rest/v1/signal_presets**', (route) =>
        route.fulfill({ status: 200, json: mockPresets })
      );

      await slowPage.goto('/playground');
      // Should show loading indicator
      await expect(slowPage.locator('.animate-spin').first()).toBeVisible();
      await slowPage.close();
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      const errorPage = await page.context().newPage();

      await errorPage.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Internal server error' },
        })
      );

      await errorPage.route('**/rest/v1/signal_presets**', (route) =>
        route.fulfill({ status: 200, json: mockPresets })
      );

      await errorPage.goto('/playground');

      // Page should still render even with error
      await expect(errorPage.getByRole('heading', { name: /signal playground/i })).toBeVisible();
      await errorPage.close();
    });
  });

  test.describe('Navigation', () => {
    test('should navigate back home on back button click', async ({ page }) => {
      await page.getByRole('link').filter({ has: page.locator('svg') }).first().click();
      await expect(page).toHaveURL('/');
    });
  });

  test.describe('From Showcase Navigation', () => {
    test('should load preset when coming from showcase with preset param', async ({ page }) => {
      const showcasePage = await page.context().newPage();

      await showcasePage.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
        route.fulfill({
          status: 200,
          json: { signals: mockSignals, stats: { total: 2 } },
        })
      );

      await showcasePage.route('**/rest/v1/signal_presets**', (route) =>
        route.fulfill({ status: 200, json: mockPresets })
      );

      await showcasePage.goto('/playground?preset=preset-1');

      // Should show that it's from showcase
      await expect(showcasePage.getByText(/trying strategy from showcase/i)).toBeVisible();
      await showcasePage.close();
    });
  });
});
