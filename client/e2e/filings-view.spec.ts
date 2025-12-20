import { test, expect } from '@playwright/test';

test.describe('Filings View', () => {
  const mockTrades = [
    {
      id: '1',
      ticker: 'NVDA',
      company: 'NVIDIA Corporation',
      trade_type: 'buy',
      estimated_value: 250000,
      transaction_date: '2024-01-15',
      filing_date: '2024-01-20',
      politician_id: '1',
      politician: { name: 'Nancy Pelosi', party: 'Democrat' }
    },
    {
      id: '2',
      ticker: 'TSLA',
      company: 'Tesla Inc.',
      trade_type: 'sell',
      estimated_value: 150000,
      transaction_date: '2024-01-15',
      filing_date: '2024-01-20',
      politician_id: '2',
      politician: { name: 'Dan Crenshaw', party: 'Republican' }
    },
    {
      id: '3',
      ticker: 'AAPL',
      company: 'Apple Inc.',
      trade_type: 'buy',
      estimated_value: 85000,
      transaction_date: '2024-01-14',
      filing_date: '2024-01-19',
      politician_id: '3',
      politician: { name: 'Tommy Tuberville', party: 'Republican' }
    }
  ];

  test.beforeEach(async ({ page }) => {
    // Mock trades API
    await page.route('**/rest/v1/trading_disclosures**', (route) =>
      route.fulfill({
        status: 200,
        json: mockTrades
      })
    );

    await page.goto('/');
    await page.getByRole('button', { name: /filings/i }).click();
  });

  test.describe('Page Structure', () => {
    test('should display filings heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /filings/i })).toBeVisible();
    });

    test('should display description text', async ({ page }) => {
      await expect(page.getByText(/official disclosure filings/i)).toBeVisible();
    });
  });

  test.describe('Filing Groups', () => {
    test('should group trades by filing date', async ({ page }) => {
      // Should show January 20, 2024 group
      await expect(page.getByText(/january 20, 2024/i)).toBeVisible();
      // Should show January 19, 2024 group
      await expect(page.getByText(/january 19, 2024/i)).toBeVisible();
    });

    test('should display file icon for each date group', async ({ page }) => {
      // FileText icon should be visible
      await expect(page.locator('svg').first()).toBeVisible();
    });

    test('should show trade count per filing date', async ({ page }) => {
      await expect(page.getByText(/2 trades filed/i)).toBeVisible();
      await expect(page.getByText(/1 trades? filed/i)).toBeVisible();
    });
  });

  test.describe('Trade Details', () => {
    test('should display ticker symbols', async ({ page }) => {
      await expect(page.getByText(/nvda/i)).toBeVisible();
      await expect(page.getByText(/tsla/i)).toBeVisible();
      await expect(page.getByText(/aapl/i)).toBeVisible();
    });

    test('should display politician names', async ({ page }) => {
      await expect(page.getByText(/nancy pelosi/i)).toBeVisible();
      await expect(page.getByText(/dan crenshaw/i)).toBeVisible();
    });

    test('should display company names', async ({ page }) => {
      await expect(page.getByText(/nvidia corporation/i)).toBeVisible();
      await expect(page.getByText(/tesla inc/i)).toBeVisible();
    });

    test('should display trade type badges', async ({ page }) => {
      await expect(page.getByText(/buy/i).first()).toBeVisible();
      await expect(page.getByText(/sell/i)).toBeVisible();
    });

    test('should display estimated values', async ({ page }) => {
      await expect(page.getByText(/\$250,000|\$250K/i)).toBeVisible();
    });
  });

  test.describe('Pagination', () => {
    test('should display pagination controls', async ({ page }) => {
      await expect(page.getByRole('button', { name: /previous/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /next/i })).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should show empty state when no filings', async ({ page }) => {
      await page.route('**/rest/v1/trading_disclosures**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.reload();
      await page.getByRole('button', { name: /filings/i }).click();

      await expect(page.getByText(/no filings recorded/i)).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading spinner while fetching', async ({ page }) => {
      await page.route('**/rest/v1/trading_disclosures**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await route.fulfill({ status: 200, json: mockTrades });
      });

      await page.reload();
      await page.getByRole('button', { name: /filings/i }).click();

      await expect(page.locator('.animate-spin')).toBeVisible();
    });
  });

  test.describe('Date Sorting', () => {
    test('should display dates in descending order', async ({ page }) => {
      const dateHeaders = page.getByText(/january \d+, 2024/i);
      const firstDate = await dateHeaders.first().textContent();
      const secondDate = await dateHeaders.nth(1).textContent();

      // First date should be more recent (January 20 before January 19)
      expect(firstDate).toContain('20');
      expect(secondDate).toContain('19');
    });
  });

  test.describe('Hover Effects', () => {
    test('should have hover effect on trade items', async ({ page }) => {
      const tradeItem = page.locator('.hover\\:bg-secondary\\/50').first();
      await expect(tradeItem).toBeVisible();
    });
  });
});
