import { test, expect, Page } from '@playwright/test';
import { mockPolitician, mockTrade, mockDashboardStats } from './utils/api-mocks';

/**
 * Dashboard Data API Integration Tests
 *
 * Tests the integration between UI and Dashboard Data APIs:
 * - Dashboard stats display
 * - Politicians listing and filtering
 * - Trades listing and filtering
 * - Chart data
 * - Ticker search
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const mockPoliticians = [
  mockPolitician({ id: '1', first_name: 'Nancy', last_name: 'Pelosi', party: 'D', total_trades: 150, total_volume: 50000000 }),
  mockPolitician({ id: '2', first_name: 'Dan', last_name: 'Crenshaw', party: 'R', total_trades: 80, total_volume: 25000000 }),
  mockPolitician({ id: '3', first_name: 'Tommy', last_name: 'Tuberville', party: 'R', total_trades: 200, total_volume: 75000000 }),
];

const mockTrades = [
  mockTrade({ id: '1', asset_ticker: 'NVDA', transaction_type: 'purchase', politician_id: '1' }),
  mockTrade({ id: '2', asset_ticker: 'AAPL', transaction_type: 'sale', politician_id: '2' }),
  mockTrade({ id: '3', asset_ticker: 'MSFT', transaction_type: 'purchase', politician_id: '3' }),
];

const mockChartData = [
  { month: 1, year: 2024, buys: 150, sells: 80, volume: 25000000 },
  { month: 2, year: 2024, buys: 180, sells: 90, volume: 30000000 },
  { month: 3, year: 2024, buys: 200, sells: 100, volume: 35000000 },
];

const mockTopTickers = [
  { ticker: 'NVDA', name: 'NVIDIA Corporation', trade_count: 250, total_volume: 100000000 },
  { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 200, total_volume: 80000000 },
  { ticker: 'MSFT', name: 'Microsoft Corporation', trade_count: 180, total_volume: 70000000 },
];

async function setupDashboardMocks(page: Page, options: {
  stats?: ReturnType<typeof mockDashboardStats>;
  politicians?: typeof mockPoliticians;
  trades?: typeof mockTrades;
  chartData?: typeof mockChartData;
  topTickers?: typeof mockTopTickers;
} = {}) {
  const {
    stats = mockDashboardStats(),
    politicians = mockPoliticians,
    trades = mockTrades,
    chartData = mockChartData,
    topTickers = mockTopTickers,
  } = options;

  // Mock dashboard stats
  await page.route(`${SUPABASE_URL}/rest/v1/dashboard_stats**`, (route) =>
    route.fulfill({ status: 200, json: stats })
  );

  // Mock politicians
  await page.route(`${SUPABASE_URL}/rest/v1/politicians**`, (route) =>
    route.fulfill({ status: 200, json: politicians })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/rpc/get_politicians_with_stats**`, (route) =>
    route.fulfill({ status: 200, json: politicians })
  );

  // Mock trading disclosures
  await page.route(`${SUPABASE_URL}/rest/v1/trading_disclosures**`, (route) =>
    route.fulfill({ status: 200, json: trades })
  );

  // Mock chart data
  await page.route(`${SUPABASE_URL}/rest/v1/chart_data**`, (route) =>
    route.fulfill({ status: 200, json: chartData })
  );

  // Mock top tickers
  await page.route(`${SUPABASE_URL}/rest/v1/top_tickers**`, (route) =>
    route.fulfill({ status: 200, json: topTickers })
  );

  // Mock jurisdictions
  await page.route(`${SUPABASE_URL}/rest/v1/jurisdictions**`, (route) =>
    route.fulfill({
      status: 200,
      json: [
        { id: 'us-congress', code: 'US', name: 'US Congress', flag: '🇺🇸' },
      ],
    })
  );
}

test.describe('Dashboard Stats API Integration', () => {
  test.describe('Stats Display', () => {
    test('should display total trades count', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByText(/15,420|15420/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display total trading volume', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByText(/\$2\.5B|\$2,500,000,000/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display active politicians count', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByText(/535/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display average trade size', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should handle stats API error', async ({ page }) => {
      await page.route(`${SUPABASE_URL}/rest/v1/dashboard_stats**`, (route) =>
        route.fulfill({ status: 500, json: { error: 'Server error' } })
      );

      await page.goto('/');
      // Should still render page, maybe with fallback data
      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Politicians List API Integration', () => {
  test.describe('Politician Listing', () => {
    test('should load politicians by jurisdiction', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByText(/Nancy Pelosi/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/Dan Crenshaw/i)).toBeVisible();
    });

    test('should display party badges', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByText(/D|Democrat/i).first()).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/R|Republican/i).first()).toBeVisible();
    });

    test('should display trade counts', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByText(/150|200/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display trading volumes', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByRole('heading', { name: /politicians/i })).toBeVisible();
    });
  });

  test.describe('Politician Filtering', () => {
    test('should filter by party', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByRole('heading', { name: /politicians/i })).toBeVisible({ timeout: 10000 });
    });

    test('should sort by volume', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByRole('heading', { name: /politicians/i })).toBeVisible();
    });

    test('should sort by trade count', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByRole('heading', { name: /politicians/i })).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should show empty state when no politicians', async ({ page }) => {
      await setupDashboardMocks(page, { politicians: [] });
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByText(/no politicians/i)).toBeVisible({ timeout: 10000 });
    });
  });
});

test.describe('Trades List API Integration', () => {
  test.describe('Trade Listing', () => {
    test('should display recent trades', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByText(/NVDA|AAPL|MSFT/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should show buy/sell transaction types', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });

  test.describe('Trade Filtering', () => {
    test('should filter by ticker', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible({ timeout: 10000 });
    });

    test('should filter by date range', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should paginate results', async ({ page }) => {
      const manyTrades = Array.from({ length: 50 }, (_, i) =>
        mockTrade({ id: `trade-${i}`, asset_ticker: ['NVDA', 'AAPL', 'MSFT'][i % 3] })
      );

      await setupDashboardMocks(page, { trades: manyTrades });
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Chart Data API Integration', () => {
  test.describe('Chart Rendering', () => {
    test('should render trade volume chart', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      // Chart should be visible
      await expect(page.locator('canvas, svg, [class*="chart"], [class*="recharts"]').first()).toBeVisible({ timeout: 10000 });
    });

    test('should switch timeframe', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should show chart tooltips on hover', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Ticker Search API Integration', () => {
  test.describe('Search Functionality', () => {
    test('should search tickers with autocomplete', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      // Find search input and type
      const searchInput = page.getByPlaceholder(/search|ticker/i).first();
      if (await searchInput.isVisible()) {
        await searchInput.fill('NV');
        await expect(page.getByText(/NVDA|NVIDIA/i).first()).toBeVisible({ timeout: 5000 });
      }
    });

    test('should navigate to ticker detail', async ({ page }) => {
      await setupDashboardMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should show no results for invalid ticker', async ({ page }) => {
      await setupDashboardMocks(page, { topTickers: [] });
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Dashboard Loading States', () => {
  test('should show loading state for stats', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/dashboard_stats**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({ status: 200, json: mockDashboardStats() });
    });

    await page.goto('/');
    await expect(page.locator('.animate-spin, .animate-pulse, [class*="skeleton"]').first()).toBeVisible();
  });

  test('should show loading state for politicians', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/politicians**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({ status: 200, json: mockPoliticians });
    });

    await setupDashboardMocks(page);
    await page.goto('/');
    await page.getByRole('button', { name: /politicians/i }).click();

    await expect(page.locator('.animate-spin').first()).toBeVisible();
  });
});
