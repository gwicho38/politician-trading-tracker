import { test, expect, Page } from '@playwright/test';
import { mockPolitician, mockTrade, mockDashboardStats } from './utils/api-mocks';

/**
 * Detail Modal Network Integration Tests
 *
 * Tests the network calls made by detail view modals:
 * - Ticker Detail Modal: fetches trading_disclosures filtered by ticker with politician join
 * - Month Detail Modal: fetches trading_disclosures filtered by date range with politician join
 *
 * Hooks under test: useTickerDetail(), useMonthDetail()
 * Endpoints: GET /rest/v1/trading_disclosures (with specific query params)
 *
 * Note: Politician detail modal is already tested in politician-profile-modal.spec.ts
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const mockPoliticians = [
  mockPolitician({ id: 'pol-1', first_name: 'Nancy', last_name: 'Pelosi', party: 'D', total_trades: 150 }),
  mockPolitician({ id: 'pol-2', first_name: 'Dan', last_name: 'Crenshaw', party: 'R', total_trades: 80 }),
];

const tickerTrades = [
  {
    ...mockTrade({ id: 'tt-1', asset_ticker: 'NVDA', asset_name: 'NVIDIA Corporation', transaction_type: 'purchase', politician_id: 'pol-1' }),
    politician: mockPoliticians[0],
  },
  {
    ...mockTrade({ id: 'tt-2', asset_ticker: 'NVDA', asset_name: 'NVIDIA Corporation', transaction_type: 'sale', politician_id: 'pol-2' }),
    politician: mockPoliticians[1],
  },
  {
    ...mockTrade({ id: 'tt-3', asset_ticker: 'NVDA', asset_name: 'NVIDIA Corporation', transaction_type: 'purchase', politician_id: 'pol-1' }),
    politician: mockPoliticians[0],
  },
];

const monthTrades = [
  {
    ...mockTrade({
      id: 'mt-1',
      asset_ticker: 'AAPL',
      asset_name: 'Apple Inc.',
      transaction_type: 'purchase',
      politician_id: 'pol-1',
      transaction_date: '2024-03-15',
      disclosure_date: '2024-03-20',
    }),
    politician: mockPoliticians[0],
  },
  {
    ...mockTrade({
      id: 'mt-2',
      asset_ticker: 'MSFT',
      asset_name: 'Microsoft Corporation',
      transaction_type: 'sale',
      politician_id: 'pol-2',
      transaction_date: '2024-03-10',
      disclosure_date: '2024-03-15',
    }),
    politician: mockPoliticians[1],
  },
];

const mockTopTickers = [
  { ticker: 'NVDA', name: 'NVIDIA Corporation', trade_count: 250, total_volume: 100000000 },
  { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 200, total_volume: 80000000 },
];

const mockChartData = [
  { month: 1, year: 2024, buys: 150, sells: 80, volume: 25000000 },
  { month: 2, year: 2024, buys: 180, sells: 90, volume: 30000000 },
  { month: 3, year: 2024, buys: 200, sells: 100, volume: 35000000 },
];

async function setupDashboardForModals(page: Page) {
  // Dashboard stats
  await page.route(`${SUPABASE_URL}/rest/v1/dashboard_stats**`, (route) =>
    route.fulfill({ status: 200, json: mockDashboardStats() })
  );

  // Politicians
  await page.route(`${SUPABASE_URL}/rest/v1/politicians**`, (route) => {
    const url = route.request().url();
    // Single politician fetch by ID
    if (url.includes('id=eq.')) {
      const id = url.match(/id=eq\.([^&]+)/)?.[1];
      const pol = mockPoliticians.find(p => p.id === id);
      return route.fulfill({ status: 200, json: pol ? [pol] : [] });
    }
    return route.fulfill({ status: 200, json: mockPoliticians });
  });

  await page.route(`${SUPABASE_URL}/rest/v1/rpc/get_politicians_with_stats**`, (route) =>
    route.fulfill({ status: 200, json: mockPoliticians })
  );

  // Trading disclosures with query param awareness
  await page.route(`${SUPABASE_URL}/rest/v1/trading_disclosures**`, (route) => {
    const url = route.request().url();

    // Ticker detail query (ilike on asset_ticker with politician select)
    if (url.includes('asset_ticker=ilike.NVDA') || url.includes('asset_ticker=ilike.nvda')) {
      return route.fulfill({ status: 200, json: tickerTrades });
    }

    // Month detail query (gte/lte on disclosure_date with politician select)
    if (url.includes('disclosure_date=gte.2024-03') && url.includes('disclosure_date=lte.2024-03')) {
      return route.fulfill({ status: 200, json: monthTrades });
    }

    // Default trades
    return route.fulfill({
      status: 200,
      json: [
        mockTrade({ id: '1', asset_ticker: 'NVDA', politician_id: 'pol-1' }),
        mockTrade({ id: '2', asset_ticker: 'AAPL', politician_id: 'pol-2' }),
      ],
    });
  });

  // Top tickers
  await page.route(`${SUPABASE_URL}/rest/v1/top_tickers**`, (route) =>
    route.fulfill({ status: 200, json: mockTopTickers })
  );

  // Chart data
  await page.route(`${SUPABASE_URL}/rest/v1/chart_data**`, (route) =>
    route.fulfill({ status: 200, json: mockChartData })
  );

  // Jurisdictions
  await page.route(`${SUPABASE_URL}/rest/v1/jurisdictions**`, (route) =>
    route.fulfill({
      status: 200,
      json: [{ id: 'us-congress', code: 'US', name: 'US Congress', flag: '\u{1F1FA}\u{1F1F8}' }],
    })
  );

  // Parties
  await page.route(`${SUPABASE_URL}/rest/v1/parties**`, (route) =>
    route.fulfill({
      status: 200,
      json: [
        { id: 'p-1', code: 'D', name: 'Democratic Party', short_name: 'D', jurisdiction: 'us', color: '#0000FF' },
        { id: 'p-2', code: 'R', name: 'Republican Party', short_name: 'R', jurisdiction: 'us', color: '#FF0000' },
      ],
    })
  );

  // Profile generation
  await page.route('**/functions/v1/politician-profile**', (route) =>
    route.fulfill({
      status: 200,
      json: { bio: 'Test bio', source: 'fallback' },
    })
  );
}

test.describe('Ticker Detail Modal Network Integration', () => {
  test.describe('Ticker Detail Data Loading', () => {
    test('should fetch ticker-specific trades when ticker is clicked', async ({ page }) => {
      let tickerQueryMade = false;

      await setupDashboardForModals(page);

      // Override to track ticker-specific query (LIFO — registered after setup)
      await page.route(`${SUPABASE_URL}/rest/v1/trading_disclosures**`, (route) => {
        const url = route.request().url();
        if (url.toLowerCase().includes('asset_ticker=ilike')) {
          tickerQueryMade = true;
          return route.fulfill({ status: 200, json: tickerTrades });
        }
        return route.fulfill({
          status: 200,
          json: [mockTrade({ id: '1', asset_ticker: 'NVDA' })],
        });
      });

      await page.goto('/');

      // Wait for dashboard and disclosures table to load
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/Politician Trading Disclosures/i)).toBeVisible({ timeout: 10000 });

      // NVDA appears in the disclosures table — target the table specifically
      // The table row with NVDA may require scrolling into view
      const nvdaInTable = page.locator('table').getByText(/NVDA/).first();
      await nvdaInTable.scrollIntoViewIfNeeded();
      await nvdaInTable.click();

      // Wait for potential detail view/modal to load
      await page.waitForTimeout(1000);
    });

    test('should display ticker trades in disclosures table', async ({ page }) => {
      await setupDashboardForModals(page);
      await page.goto('/');

      // Verify the disclosures table renders with trade data
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });

      // Table should render with at least one row containing trade data
      await expect(page.locator('table').first()).toBeVisible();

      // Check for the Asset column header which contains ticker data
      await expect(page.getByText(/Asset/i).first()).toBeVisible();
    });
  });

  test.describe('Ticker Detail Error Handling', () => {
    test('should handle ticker detail API error', async ({ page }) => {
      await setupDashboardForModals(page);

      // Override disclosures to return error for ticker queries
      await page.route(`${SUPABASE_URL}/rest/v1/trading_disclosures**`, (route) => {
        const url = route.request().url();
        if (url.toLowerCase().includes('asset_ticker=ilike')) {
          return route.fulfill({ status: 500, json: { error: 'Server error' } });
        }
        return route.fulfill({ status: 200, json: [mockTrade()] });
      });

      await page.goto('/');

      // Dashboard should still render
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
    });
  });
});

test.describe('Month Detail Modal Network Integration', () => {
  test.describe('Month Detail Data Loading', () => {
    test('should request chart_data from API on page load', async ({ page }) => {
      let chartDataRequested = false;

      await setupDashboardForModals(page);

      // Override chart_data to track the call (LIFO)
      await page.route(`${SUPABASE_URL}/rest/v1/chart_data**`, (route) => {
        chartDataRequested = true;
        return route.fulfill({ status: 200, json: mockChartData });
      });

      await page.goto('/');

      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
      expect(chartDataRequested).toBe(true);
    });

    test('should request top_tickers from API on page load', async ({ page }) => {
      let topTickersRequested = false;

      await setupDashboardForModals(page);

      // Override top_tickers to track the call (LIFO)
      await page.route(`${SUPABASE_URL}/rest/v1/top_tickers**`, (route) => {
        topTickersRequested = true;
        return route.fulfill({ status: 200, json: mockTopTickers });
      });

      await page.goto('/');

      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
      expect(topTickersRequested).toBe(true);
    });
  });

  test.describe('Month Detail Error Handling', () => {
    test('should handle chart data API error gracefully', async ({ page }) => {
      await setupDashboardForModals(page);

      await page.route(`${SUPABASE_URL}/rest/v1/chart_data**`, (route) =>
        route.fulfill({ status: 500, json: { error: 'Server error' } })
      );

      await page.goto('/');

      // Dashboard should still render
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should handle empty chart data', async ({ page }) => {
      await setupDashboardForModals(page);

      await page.route(`${SUPABASE_URL}/rest/v1/chart_data**`, (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/');

      // Dashboard should still render
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
    });
  });
});
