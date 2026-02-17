import { test, expect, Page } from '@playwright/test';
import {
  mockPolitician,
  mockTrade,
  mockDashboardStats,
  setupPartiesMock,
  mockParty,
} from './utils/api-mocks';

/**
 * Parties API Integration Tests
 *
 * Tests the integration between UI and the parties REST API:
 * - Party data loading on dashboard
 * - Party badges rendering on politician cards
 * - Party color display
 * - Error/empty state handling
 *
 * Hook under test: useParties()
 * Endpoint: GET /rest/v1/parties
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const mockPoliticians = [
  mockPolitician({ id: '1', first_name: 'Nancy', last_name: 'Pelosi', party: 'D', total_trades: 150 }),
  mockPolitician({ id: '2', first_name: 'Dan', last_name: 'Crenshaw', party: 'R', total_trades: 80 }),
];

const mockTrades = [
  mockTrade({ id: '1', asset_ticker: 'NVDA', politician_id: '1' }),
  mockTrade({ id: '2', asset_ticker: 'AAPL', politician_id: '2' }),
];

async function setupDashboardWithParties(page: Page, options: {
  parties?: ReturnType<typeof mockParty>[];
  politicians?: typeof mockPoliticians;
} = {}) {
  const { politicians = mockPoliticians } = options;

  // Setup parties mock
  await setupPartiesMock(page, options.parties);

  // Setup dashboard data mocks
  await page.route(`${SUPABASE_URL}/rest/v1/dashboard_stats**`, (route) =>
    route.fulfill({ status: 200, json: mockDashboardStats() })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/politicians**`, (route) =>
    route.fulfill({ status: 200, json: politicians })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/rpc/get_politicians_with_stats**`, (route) =>
    route.fulfill({ status: 200, json: politicians })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/trading_disclosures**`, (route) =>
    route.fulfill({ status: 200, json: mockTrades })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/chart_data**`, (route) =>
    route.fulfill({ status: 200, json: [] })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/top_tickers**`, (route) =>
    route.fulfill({ status: 200, json: [] })
  );

  await page.route(`${SUPABASE_URL}/rest/v1/jurisdictions**`, (route) =>
    route.fulfill({
      status: 200,
      json: [{ id: 'us-congress', code: 'US', name: 'US Congress', flag: '\u{1F1FA}\u{1F1F8}' }],
    })
  );
}

test.describe('Parties API Integration', () => {
  test.describe('Party Data Loading', () => {
    test('should request parties from REST API on page load', async ({ page }) => {
      let partiesRequested = false;

      await setupDashboardWithParties(page);

      // Register tracking route AFTER setup so it takes precedence (Playwright LIFO)
      await page.route('**/rest/v1/parties**', (route) => {
        partiesRequested = true;
        return route.fulfill({
          status: 200,
          json: [
            mockParty({ code: 'D', name: 'Democratic Party' }),
            mockParty({ code: 'R', name: 'Republican Party' }),
          ],
        });
      });

      await page.goto('/');

      // Wait for dashboard stats to confirm page loaded
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
      expect(partiesRequested).toBe(true);
    });

    test('should display party badges on politician cards', async ({ page }) => {
      await setupDashboardWithParties(page);
      await page.goto('/');

      // Top Traders section shows politicians with party badges
      await expect(page.getByText(/Nancy Pelosi/i)).toBeVisible({ timeout: 10000 });
      // Party badge "D" should be visible on the politician card
      await expect(page.getByText(/^D$/)).toBeVisible();
    });

    test('should handle parties API error gracefully', async ({ page }) => {
      // Override with error response
      await page.route('**/rest/v1/parties**', (route) =>
        route.fulfill({ status: 500, json: { error: 'Internal Server Error' } })
      );

      await setupDashboardWithParties(page);
      await page.goto('/');

      // Dashboard should still render despite parties error
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should handle empty parties list', async ({ page }) => {
      await setupDashboardWithParties(page, { parties: [] });
      await page.goto('/');

      // Dashboard should still render
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Party Data on Trades', () => {
    test('should display trade entries with ticker data', async ({ page }) => {
      await setupDashboardWithParties(page);
      await page.goto('/');

      // Trade disclosures table should load with data
      await expect(page.getByText(/Politician Stock Trading/i)).toBeVisible({ timeout: 10000 });
      // Table should contain trade data
      await expect(page.locator('table').first()).toBeVisible();
    });
  });

  test.describe('Party Loading State', () => {
    test('should render page while parties are still loading', async ({ page }) => {
      await page.route('**/rest/v1/parties**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          json: [mockParty({ code: 'D' }), mockParty({ code: 'R' })],
        });
      });

      await setupDashboardWithParties(page);
      await page.goto('/');

      // Page should still render with other data while parties load
      await expect(page.getByText(/Total Trades/i).first()).toBeVisible({ timeout: 10000 });
    });
  });
});
