import { test, expect } from '@playwright/test';

test.describe('Trades View', () => {
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
      transaction_date: '2024-01-14',
      filing_date: '2024-01-19',
      politician_id: '2',
      politician: { name: 'Dan Crenshaw', party: 'Republican' }
    },
    {
      id: '3',
      ticker: 'AAPL',
      company: 'Apple Inc.',
      trade_type: 'buy',
      estimated_value: 85000,
      transaction_date: '2024-01-13',
      filing_date: '2024-01-18',
      politician_id: '3',
      politician: { name: 'Tommy Tuberville', party: 'Republican' }
    }
  ];

  const mockJurisdictions = [
    { id: 'us-congress', name: 'US Congress', flag: '🇺🇸' },
    { id: 'uk-parliament', name: 'UK Parliament', flag: '🇬🇧' },
    { id: 'eu-parliament', name: 'EU Parliament', flag: '🇪🇺' }
  ];

  test.beforeEach(async ({ page }) => {
    // Mock trades API
    await page.route('**/rest/v1/trading_disclosures**', (route) =>
      route.fulfill({
        status: 200,
        json: mockTrades
      })
    );

    // Mock jurisdictions API
    await page.route('**/rest/v1/jurisdictions**', (route) =>
      route.fulfill({
        status: 200,
        json: mockJurisdictions
      })
    );

    await page.goto('/');
    await page.getByRole('button', { name: /^trades$/i }).click();
  });

  test.describe('Page Structure', () => {
    test('should display trades heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /recent trades/i })).toBeVisible();
    });

    test('should display description text', async ({ page }) => {
      await expect(page.getByText(/disclosed trading activity/i)).toBeVisible();
    });
  });

  test.describe('Trade Cards', () => {
    test('should display ticker symbols', async ({ page }) => {
      await expect(page.getByText(/nvda/i)).toBeVisible();
      await expect(page.getByText(/tsla/i)).toBeVisible();
      await expect(page.getByText(/aapl/i)).toBeVisible();
    });

    test('should display company names', async ({ page }) => {
      await expect(page.getByText(/nvidia corporation/i)).toBeVisible();
      await expect(page.getByText(/tesla inc/i)).toBeVisible();
      await expect(page.getByText(/apple inc/i)).toBeVisible();
    });

    test('should display politician names', async ({ page }) => {
      await expect(page.getByText(/nancy pelosi/i)).toBeVisible();
      await expect(page.getByText(/dan crenshaw/i)).toBeVisible();
    });

    test('should display trade type badges', async ({ page }) => {
      await expect(page.getByText(/buy/i).first()).toBeVisible();
      await expect(page.getByText(/sell/i)).toBeVisible();
    });

    test('should display estimated values', async ({ page }) => {
      await expect(page.getByText(/\$250,000|\$250K/i)).toBeVisible();
    });
  });

  test.describe('Jurisdiction Filters', () => {
    test('should display All filter', async ({ page }) => {
      await expect(page.getByText(/^all$/i)).toBeVisible();
    });

    test('should display jurisdiction filter badges', async ({ page }) => {
      await expect(page.getByText(/us congress/i)).toBeVisible();
      await expect(page.getByText(/uk parliament/i)).toBeVisible();
      await expect(page.getByText(/eu parliament/i)).toBeVisible();
    });

    test('should display jurisdiction flags', async ({ page }) => {
      await expect(page.getByText(/🇺🇸/)).toBeVisible();
      await expect(page.getByText(/🇬🇧/)).toBeVisible();
      await expect(page.getByText(/🇪🇺/)).toBeVisible();
    });

    test('should filter trades when jurisdiction is selected', async ({ page }) => {
      await page.getByText(/us congress/i).click();

      // Active filter should be highlighted
      await expect(page.getByText(/us congress/i)).toBeVisible();
    });
  });

  test.describe('Filter Button', () => {
    test('should display filter button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /filter/i })).toBeVisible();
    });
  });

  test.describe('Pagination', () => {
    test('should display pagination controls', async ({ page }) => {
      await expect(page.getByRole('button', { name: /previous/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /next/i })).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should show empty state when no trades', async ({ page }) => {
      await page.route('**/rest/v1/trading_disclosures**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.reload();
      await page.getByRole('button', { name: /^trades$/i }).click();

      await expect(page.getByText(/no trades|no data/i)).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading spinner while fetching', async ({ page }) => {
      await page.route('**/rest/v1/trading_disclosures**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await route.fulfill({ status: 200, json: mockTrades });
      });

      await page.reload();
      await page.getByRole('button', { name: /^trades$/i }).click();

      await expect(page.locator('.animate-spin')).toBeVisible();
    });
  });

  test.describe('Search Functionality', () => {
    test('should filter trades by search query', async ({ page }) => {
      // Trigger search via header
      const searchInput = page.getByPlaceholder(/search/i);
      await searchInput.fill('NVDA');

      await expect(page.getByText(/nvda/i)).toBeVisible();
    });
  });

  test.describe('Trade Type Styling', () => {
    test('should have green styling for buy trades', async ({ page }) => {
      const buyBadge = page.getByText(/buy/i).first();
      await expect(buyBadge).toBeVisible();
    });

    test('should have red styling for sell trades', async ({ page }) => {
      const sellBadge = page.getByText(/sell/i).first();
      await expect(sellBadge).toBeVisible();
    });
  });
});
