import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock dashboard stats API
    await page.route('**/rest/v1/rpc/get_dashboard_stats**', (route) =>
      route.fulfill({
        status: 200,
        json: {
          total_trades: 1250,
          total_volume: 45000000,
          average_trade_size: 36000,
          active_politicians: 342,
          jurisdictions_tracked: 5,
          recent_filings: 89
        }
      })
    );

    // Mock recent trades
    await page.route('**/rest/v1/trading_disclosures**', (route) =>
      route.fulfill({
        status: 200,
        json: [
          {
            id: '1',
            politician_name: 'Nancy Pelosi',
            ticker: 'NVDA',
            asset_description: 'NVIDIA Corporation',
            transaction_type: 'purchase',
            transaction_date: '2024-01-15',
            amount_range: '$100,001 - $250,000',
            disclosure_date: '2024-01-20'
          },
          {
            id: '2',
            politician_name: 'Dan Crenshaw',
            ticker: 'TSLA',
            asset_description: 'Tesla Inc',
            transaction_type: 'sale',
            transaction_date: '2024-01-14',
            amount_range: '$15,001 - $50,000',
            disclosure_date: '2024-01-19'
          }
        ]
      })
    );

    // Mock top traders
    await page.route('**/rest/v1/rpc/get_top_traders**', (route) =>
      route.fulfill({
        status: 200,
        json: [
          { politician_name: 'Nancy Pelosi', total_trades: 45, total_volume: 2500000 },
          { politician_name: 'Dan Crenshaw', total_trades: 32, total_volume: 1800000 }
        ]
      })
    );

    await page.goto('/');
  });

  test.describe('Page Structure', () => {
    test('should display dashboard heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });

    test('should display jurisdiction tracking description', async ({ page }) => {
      await expect(page.getByText(/track politician trading disclosures/i)).toBeVisible();
    });
  });

  test.describe('Stats Cards', () => {
    test('should display total trades stat', async ({ page }) => {
      await expect(page.getByText(/total trades/i)).toBeVisible();
      await expect(page.getByText(/1,250/)).toBeVisible();
    });

    test('should display total volume stat', async ({ page }) => {
      await expect(page.getByText(/total volume/i)).toBeVisible();
    });

    test('should display active politicians stat', async ({ page }) => {
      await expect(page.getByText(/active politicians/i)).toBeVisible();
      await expect(page.getByText(/342/)).toBeVisible();
    });

    test('should display recent filings stat', async ({ page }) => {
      await expect(page.getByText(/recent filings/i)).toBeVisible();
      await expect(page.getByText(/89/)).toBeVisible();
    });

    test('should show loading state for stats', async ({ page }) => {
      // Create new page to control loading state
      const newPage = await page.context().newPage();

      // Delay the response
      await newPage.route('**/rest/v1/rpc/get_dashboard_stats**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          json: { total_trades: 100 }
        });
      });

      await newPage.goto('/');

      // Should show loading spinners
      await expect(newPage.locator('.animate-spin').first()).toBeVisible();

      await newPage.close();
    });
  });

  test.describe('Charts', () => {
    test('should display trade chart section', async ({ page }) => {
      await expect(page.getByText(/trading activity/i)).toBeVisible();
    });

    test('should display volume chart section', async ({ page }) => {
      await expect(page.getByText(/trading volume/i)).toBeVisible();
    });
  });

  test.describe('Recent Trades Section', () => {
    test('should display recent trades heading', async ({ page }) => {
      await expect(page.getByText(/recent trades/i).first()).toBeVisible();
    });

    test('should display trade cards with politician names', async ({ page }) => {
      await expect(page.getByText(/nancy pelosi/i)).toBeVisible();
    });

    test('should display ticker symbols', async ({ page }) => {
      await expect(page.getByText(/nvda/i)).toBeVisible();
    });

    test('should display transaction types', async ({ page }) => {
      await expect(page.getByText(/purchase/i)).toBeVisible();
    });
  });

  test.describe('Top Traders Section', () => {
    test('should display top traders heading', async ({ page }) => {
      await expect(page.getByText(/top traders/i)).toBeVisible();
    });

    test('should list top trading politicians', async ({ page }) => {
      await expect(page.getByText(/nancy pelosi/i)).toBeVisible();
      await expect(page.getByText(/dan crenshaw/i)).toBeVisible();
    });
  });

  test.describe('Sidebar Navigation', () => {
    test('should display sidebar menu', async ({ page }) => {
      await expect(page.getByRole('button', { name: /dashboard/i })).toBeVisible();
    });

    test('should navigate to trades view', async ({ page }) => {
      await page.getByRole('button', { name: /trades/i }).click();
      await expect(page.getByText(/all trades/i)).toBeVisible();
    });

    test('should navigate to politicians view', async ({ page }) => {
      await page.getByRole('button', { name: /politicians/i }).click();
      await expect(page.getByText(/politicians/i)).toBeVisible();
    });

    test('should navigate to trading signals', async ({ page }) => {
      await page.getByRole('button', { name: /trading signals/i }).click();
      await expect(page.getByText(/ai-powered/i)).toBeVisible();
    });
  });

  test.describe('Header', () => {
    test('should display application title', async ({ page }) => {
      await expect(page.getByText(/capitoltrades/i).first()).toBeVisible();
    });

    test('should display search functionality', async ({ page }) => {
      await expect(page.getByPlaceholder(/search/i)).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {
    test('should show mobile menu button on small screens', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/');

      // Mobile menu button should be visible
      await expect(page.getByRole('button', { name: /menu/i })).toBeVisible();
    });

    test('should open sidebar on mobile menu click', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/');

      await page.getByRole('button', { name: /menu/i }).click();

      // Sidebar navigation items should be visible
      await expect(page.getByRole('button', { name: /dashboard/i })).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API errors gracefully', async ({ page }) => {
      const errorPage = await page.context().newPage();

      await errorPage.route('**/rest/v1/rpc/get_dashboard_stats**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Internal server error' }
        })
      );

      await errorPage.goto('/');

      // Should not crash, should show fallback or 0 values
      await expect(errorPage.getByRole('heading', { name: /dashboard/i })).toBeVisible();

      await errorPage.close();
    });
  });

  test.describe('Footer', () => {
    test('should display data source attribution', async ({ page }) => {
      await expect(page.getByText(/data sourced from official government disclosures/i)).toBeVisible();
    });

    test('should have links to government sources', async ({ page }) => {
      await expect(page.getByRole('link', { name: /us congress/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /eu parliament/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /uk parliament/i })).toBeVisible();
    });
  });
});
