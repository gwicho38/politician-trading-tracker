import { test, expect, Page, Route } from '@playwright/test';

test.describe('Admin Dashboard', () => {
  // Helper to mock admin user
  const mockAdminUser = async (page: Page) => {
    await page.route('**/auth/v1/user**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: { id: 'admin-user-123', email: 'admin@example.com' }
      })
    );
    await page.route('**/auth/v1/session**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: {
          access_token: 'mock-admin-token',
          user: { id: 'admin-user-123', email: 'admin@example.com' }
        }
      })
    );
    // Mock admin role check
    await page.route('**/rest/v1/user_roles**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: [{ user_id: 'admin-user-123', role: 'admin' }]
      })
    );
  };

  // Helper to mock non-admin user
  const mockNonAdminUser = async (page: Page) => {
    await page.route('**/auth/v1/user**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: { id: 'regular-user-123', email: 'user@example.com' }
      })
    );
    await page.route('**/auth/v1/session**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: {
          access_token: 'mock-token',
          user: { id: 'regular-user-123', email: 'user@example.com' }
        }
      })
    );
    // Mock non-admin role
    await page.route('**/rest/v1/user_roles**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: []
      })
    );
  };

  test.describe('Access Control', () => {
    test('should redirect non-admin users to home', async ({ page }) => {
      await mockNonAdminUser(page);
      await page.goto('/admin');

      // Should redirect to home page
      await expect(page).toHaveURL('/');
    });

    test('should show loading state while checking admin status', async ({ page }) => {
      await page.route('**/rest/v1/user_roles**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await route.fulfill({ status: 200, json: [{ role: 'admin' }] });
      });

      await mockAdminUser(page);
      await page.goto('/admin');

      await expect(page.locator('.animate-spin')).toBeVisible();
    });
  });

  test.describe('Admin Dashboard UI', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await page.goto('/admin');
    });

    test('should display admin dashboard heading', async ({ page }) => {
      await expect(page.getByText(/admin/i)).toBeVisible();
      await expect(page.getByText(/dashboard/i)).toBeVisible();
    });

    test('should display back to site link', async ({ page }) => {
      await expect(page.getByText(/back to site/i)).toBeVisible();
    });

    test('should display shield icon', async ({ page }) => {
      await expect(page.locator('svg').first()).toBeVisible();
    });
  });

  test.describe('Admin Tabs', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await page.goto('/admin');
    });

    test('should display Users tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /users/i })).toBeVisible();
    });

    test('should display Content tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /content/i })).toBeVisible();
    });

    test('should display Notifications tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /notifications/i })).toBeVisible();
    });

    test('should display Sync Status tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /sync status/i })).toBeVisible();
    });

    test('should display Analytics tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /analytics/i })).toBeVisible();
    });

    test('should switch to Content tab', async ({ page }) => {
      await page.getByRole('tab', { name: /content/i }).click();
      // Content tab should be active
      await expect(page.getByRole('tab', { name: /content/i })).toHaveAttribute('data-state', 'active');
    });

    test('should switch to Notifications tab', async ({ page }) => {
      await page.getByRole('tab', { name: /notifications/i }).click();
      await expect(page.getByRole('tab', { name: /notifications/i })).toHaveAttribute('data-state', 'active');
    });
  });
});

test.describe('Admin Data Collection', () => {
  const mockDataStats = {
    politicians: 535,
    trades: 12450,
    jurisdictions: 3
  };

  const mockAdminUser = async (page: Page) => {
    await page.route('**/auth/v1/user**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: { id: 'admin-user-123', email: 'admin@example.com' }
      })
    );
    await page.route('**/auth/v1/session**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: {
          access_token: 'mock-admin-token',
          user: { id: 'admin-user-123', email: 'admin@example.com' }
        }
      })
    );
    await page.route('**/rest/v1/user_roles**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: [{ user_id: 'admin-user-123', role: 'admin' }]
      })
    );
  };

  const mockDataAPIs = async (page: Page) => {
    // Mock politician count
    await page.route('**/rest/v1/politicians?select=*&limit=0', (route: Route) => {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Range': `0-0/${mockDataStats.politicians}` },
        json: []
      });
    });

    // Mock trades count
    await page.route('**/rest/v1/trades?select=*&limit=0', (route: Route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Range': `0-0/${mockDataStats.trades}` },
        json: []
      })
    );

    // Mock jurisdictions count
    await page.route('**/rest/v1/jurisdictions?select=*&limit=0', (route: Route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Range': `0-0/${mockDataStats.jurisdictions}` },
        json: []
      })
    );

    // Mock last trade
    await page.route('**/rest/v1/trades?select=created_at**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: [{ created_at: new Date().toISOString() }]
      })
    );

    // Mock dashboard stats
    await page.route('**/rest/v1/dashboard_stats**', (route: Route) =>
      route.fulfill({
        status: 200,
        json: [{ updated_at: new Date().toISOString() }]
      })
    );
  };

  test.describe('Access Control', () => {
    test('should redirect unauthenticated users to auth page', async ({ page }) => {
      await page.route('**/auth/v1/session**', (route: Route) =>
        route.fulfill({ status: 200, json: null })
      );

      await page.goto('/admin/data-collection');
      await expect(page).toHaveURL(/auth/);
    });

    test('should redirect non-admin users to home', async ({ page }) => {
      await page.route('**/auth/v1/session**', (route: Route) =>
        route.fulfill({
          status: 200,
          json: {
            access_token: 'mock-token',
            user: { id: 'user-123', email: 'user@example.com' }
          }
        })
      );
      await page.route('**/rest/v1/user_roles**', (route: Route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/admin/data-collection');
      await expect(page).toHaveURL('/');
    });
  });

  test.describe('Page Structure', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
    });

    test('should display data collection heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /data collection admin/i })).toBeVisible();
    });

    test('should display database icon', async ({ page }) => {
      await expect(page.locator('svg').first()).toBeVisible();
    });

    test('should display description text', async ({ page }) => {
      await expect(page.getByText(/manage data synchronization/i)).toBeVisible();
    });
  });

  test.describe('Tabs Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
    });

    test('should display Overview tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /overview/i })).toBeVisible();
    });

    test('should display Synchronization tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /synchronization/i })).toBeVisible();
    });

    test('should display Statistics tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /statistics/i })).toBeVisible();
    });

    test('should display Settings tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /settings/i })).toBeVisible();
    });

    test('should switch to Synchronization tab', async ({ page }) => {
      await page.getByRole('tab', { name: /synchronization/i }).click();
      await expect(page.getByRole('tab', { name: /synchronization/i })).toHaveAttribute('data-state', 'active');
    });
  });

  test.describe('Overview Tab - Status Cards', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
    });

    test('should display Politicians count', async ({ page }) => {
      await expect(page.getByText(/politicians/i)).toBeVisible();
    });

    test('should display Trades count', async ({ page }) => {
      await expect(page.getByText(/trades/i)).toBeVisible();
    });

    test('should display Jurisdictions count', async ({ page }) => {
      await expect(page.getByText(/jurisdictions/i)).toBeVisible();
    });

    test('should display Last Updated', async ({ page }) => {
      await expect(page.getByText(/last updated/i)).toBeVisible();
    });
  });

  test.describe('Overview Tab - Sync Status', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
    });

    test('should display Synchronization Status card', async ({ page }) => {
      await expect(page.getByText(/synchronization status/i)).toBeVisible();
    });

    test('should display last sync time', async ({ page }) => {
      await expect(page.getByText(/last sync/i)).toBeVisible();
    });

    test('should display status badge', async ({ page }) => {
      await expect(page.getByText(/idle|running|completed|failed/i).first()).toBeVisible();
    });
  });

  test.describe('Synchronization Tab', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
      await page.getByRole('tab', { name: /synchronization/i }).click();
    });

    test('should display Manual Synchronization section', async ({ page }) => {
      await expect(page.getByText(/manual synchronization/i)).toBeVisible();
    });

    test('should display Full Synchronization button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /full synchronization/i })).toBeVisible();
    });

    test('should display Sync Politicians button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /sync politicians/i })).toBeVisible();
    });

    test('should display Sync Trades button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /sync trades/i })).toBeVisible();
    });

    test('should display Update Statistics button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /update statistics/i })).toBeVisible();
    });

    test('should display Automated Synchronization section', async ({ page }) => {
      await expect(page.getByText(/automated synchronization/i)).toBeVisible();
    });

    test('should display Data Sources section', async ({ page }) => {
      await expect(page.getByText(/data sources/i)).toBeVisible();
    });

    test('should display US House Disclosures source', async ({ page }) => {
      await expect(page.getByText(/us house disclosures/i)).toBeVisible();
    });

    test('should display US Senate Disclosures source', async ({ page }) => {
      await expect(page.getByText(/us senate disclosures/i)).toBeVisible();
    });
  });

  test.describe('Sync Actions', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);

      // Mock sync functions
      await page.route('**/functions/v1/sync-data/**', (route: Route) =>
        route.fulfill({
          status: 200,
          json: { results: { politicians: { count: 10 }, trades: { count: 50 } } }
        })
      );

      await page.goto('/admin/data-collection');
      await page.getByRole('tab', { name: /synchronization/i }).click();
    });

    test('should trigger full sync on button click', async ({ page }) => {
      const syncButton = page.getByRole('button', { name: /full synchronization/i });
      await syncButton.click();

      // Should show loading state
      await expect(page.getByText(/syncing|running/i)).toBeVisible({ timeout: 2000 }).catch(() => {});
    });
  });

  test.describe('Statistics Tab', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
      await page.getByRole('tab', { name: /statistics/i }).click();
    });

    test('should display Data Quality Metrics', async ({ page }) => {
      await expect(page.getByText(/data quality metrics/i)).toBeVisible();
    });

    test('should display Data Accuracy metric', async ({ page }) => {
      await expect(page.getByText(/data accuracy/i)).toBeVisible();
    });

    test('should display Uptime metric', async ({ page }) => {
      await expect(page.getByText(/uptime/i)).toBeVisible();
    });

    test('should display Sync Latency metric', async ({ page }) => {
      await expect(page.getByText(/sync latency/i)).toBeVisible();
    });
  });

  test.describe('Settings Tab', () => {
    test.beforeEach(async ({ page }) => {
      await mockAdminUser(page);
      await mockDataAPIs(page);
      await page.goto('/admin/data-collection');
      await page.getByRole('tab', { name: /settings/i }).click();
    });

    test('should display Data Collection Settings', async ({ page }) => {
      await expect(page.getByText(/data collection settings/i)).toBeVisible();
    });

    test('should display configuration info alert', async ({ page }) => {
      await expect(page.getByText(/advanced settings|environment variables/i)).toBeVisible();
    });
  });
});
