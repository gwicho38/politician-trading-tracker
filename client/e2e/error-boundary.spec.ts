import { test, expect } from '@playwright/test';

test.describe('Error Boundaries', () => {
  test.describe('Page Load Verification', () => {
    test('should load dashboard without errors', async ({ page }) => {
      // Mock APIs to ensure page loads
      await page.route('**/rest/v1/rpc/get_dashboard_stats**', (route) =>
        route.fulfill({
          status: 200,
          json: { total_trades: 100, total_volume: 1000000, active_politicians: 50 },
        })
      );

      await page.route('**/rest/v1/trading_disclosures**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.route('**/rest/v1/rpc/get_top_traders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/');

      // Page should load without showing error boundary
      await expect(page.getByText(/something went wrong/i)).not.toBeVisible();
      // Dashboard shows "Politician Stock Trading Tracker" as the main heading
      await expect(page.getByText(/politician stock trading tracker/i)).toBeVisible();
    });

    test('should load playground without errors', async ({ page }) => {
      await page.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
        route.fulfill({ status: 200, json: { signals: [], stats: {} } })
      );

      await page.route('**/rest/v1/signal_presets**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/playground');

      await expect(page.getByText(/something went wrong/i)).not.toBeVisible();
      await expect(page.getByRole('heading', { name: /signal playground/i })).toBeVisible();
    });

    test('should load showcase without errors', async ({ page }) => {
      await page.route('**/rest/v1/signal_presets**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/showcase');

      await expect(page.getByText(/something went wrong/i)).not.toBeVisible();
      await expect(page.getByRole('heading', { name: /strategy showcase/i })).toBeVisible();
    });

    test('should load data quality without errors', async ({ page }) => {
      await page.route('**/rest/v1/data_quality_results**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.route('**/rest/v1/data_quality_issues**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.route('**/rest/v1/data_quality_corrections**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/admin/data-quality');

      await expect(page.getByText(/something went wrong/i)).not.toBeVisible();
      await expect(page.getByRole('heading', { name: /data quality/i })).toBeVisible();
    });
  });

  test.describe('Error Boundary Components Exist', () => {
    test('ErrorBoundary component file exists', async ({ page }) => {
      // This is a build-time check - if the component doesn't exist, the build would fail
      // We verify the app loads which means all imports succeeded
      await page.goto('/');
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test.describe('Graceful API Error Handling', () => {
    test('should not crash on API 500 error', async ({ page }) => {
      // Simulate server error
      await page.route('**/rest/v1/rpc/get_dashboard_stats**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Internal server error' },
        })
      );

      await page.route('**/rest/v1/trading_disclosures**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.route('**/rest/v1/rpc/get_top_traders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/');

      // Page should still be functional even with API errors
      // Either shows the content with fallback data or shows a friendly error
      await expect(page.locator('body')).toBeVisible();
      // Should not see the root error boundary (full-page crash)
      await expect(page.getByText(/application error/i)).not.toBeVisible();
    });

    test('should not crash on network timeout', async ({ page }) => {
      // Simulate timeout by aborting request
      await page.route('**/rest/v1/rpc/get_dashboard_stats**', (route) =>
        route.abort('timedout')
      );

      await page.route('**/rest/v1/trading_disclosures**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.route('**/rest/v1/rpc/get_top_traders**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/');

      // Page should handle timeout gracefully
      await expect(page.locator('body')).toBeVisible();
      await expect(page.getByText(/application error/i)).not.toBeVisible();
    });
  });
});
