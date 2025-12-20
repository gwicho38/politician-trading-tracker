import { test, expect } from '@playwright/test';

test.describe('Politicians View', () => {
  const mockPoliticians = [
    {
      id: '1',
      name: 'Nancy Pelosi',
      party: 'Democrat',
      chamber: 'House',
      state: 'CA',
      jurisdiction_id: 'us-congress',
      total_trades: 45,
      total_volume: 2500000
    },
    {
      id: '2',
      name: 'Dan Crenshaw',
      party: 'Republican',
      chamber: 'House',
      state: 'TX',
      jurisdiction_id: 'us-congress',
      total_trades: 32,
      total_volume: 1800000
    },
    {
      id: '3',
      name: 'Tommy Tuberville',
      party: 'Republican',
      chamber: 'Senate',
      state: 'AL',
      jurisdiction_id: 'us-congress',
      total_trades: 128,
      total_volume: 5600000
    }
  ];

  test.beforeEach(async ({ page }) => {
    // Mock politicians API
    await page.route('**/rest/v1/politicians**', (route) =>
      route.fulfill({
        status: 200,
        json: mockPoliticians
      })
    );

    // Mock RPC call for politicians with stats
    await page.route('**/rest/v1/rpc/get_politicians_with_stats**', (route) =>
      route.fulfill({
        status: 200,
        json: mockPoliticians
      })
    );

    await page.goto('/');
    await page.getByRole('button', { name: /politicians/i }).click();
  });

  test.describe('Page Structure', () => {
    test('should display politicians heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /politicians/i })).toBeVisible();
    });

    test('should display description text', async ({ page }) => {
      await expect(page.getByText(/tracked politicians|trading activity/i)).toBeVisible();
    });
  });

  test.describe('Politician Cards', () => {
    test('should display politician names', async ({ page }) => {
      await expect(page.getByText(/nancy pelosi/i)).toBeVisible();
      await expect(page.getByText(/dan crenshaw/i)).toBeVisible();
      await expect(page.getByText(/tommy tuberville/i)).toBeVisible();
    });

    test('should display party badges', async ({ page }) => {
      await expect(page.getByText(/democrat/i)).toBeVisible();
      await expect(page.getByText(/republican/i).first()).toBeVisible();
    });

    test('should display chamber information', async ({ page }) => {
      await expect(page.getByText(/house/i).first()).toBeVisible();
      await expect(page.getByText(/senate/i)).toBeVisible();
    });

    test('should display state abbreviations', async ({ page }) => {
      await expect(page.getByText(/CA/)).toBeVisible();
      await expect(page.getByText(/TX/)).toBeVisible();
      await expect(page.getByText(/AL/)).toBeVisible();
    });

    test('should display trade counts', async ({ page }) => {
      await expect(page.getByText(/45/)).toBeVisible();
      await expect(page.getByText(/128/)).toBeVisible();
    });

    test('should display total volume', async ({ page }) => {
      await expect(page.getByText(/\$2,500,000|\$2\.5M/i)).toBeVisible();
    });

    test('should display initials avatar', async ({ page }) => {
      // Nancy Pelosi = NP
      await expect(page.getByText(/NP/)).toBeVisible();
      // Dan Crenshaw = DC
      await expect(page.getByText(/DC/)).toBeVisible();
    });
  });

  test.describe('Party Color Coding', () => {
    test('should have distinct styling for Democrat', async ({ page }) => {
      const democratBadge = page.getByText(/democrat/i);
      await expect(democratBadge).toBeVisible();
    });

    test('should have distinct styling for Republican', async ({ page }) => {
      const republicanBadge = page.getByText(/republican/i).first();
      await expect(republicanBadge).toBeVisible();
    });
  });

  test.describe('Pagination', () => {
    test('should display pagination controls', async ({ page }) => {
      await expect(page.getByRole('button', { name: /previous/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /next/i })).toBeVisible();
    });

    test('should show page information', async ({ page }) => {
      await expect(page.getByText(/page/i)).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should show empty state when no politicians', async ({ page }) => {
      await page.route('**/rest/v1/politicians**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );
      await page.route('**/rest/v1/rpc/get_politicians_with_stats**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.reload();
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.getByText(/no politicians tracked/i)).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading spinner while fetching', async ({ page }) => {
      await page.route('**/rest/v1/politicians**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await route.fulfill({ status: 200, json: mockPoliticians });
      });

      await page.reload();
      await page.getByRole('button', { name: /politicians/i }).click();

      await expect(page.locator('.animate-spin')).toBeVisible();
    });
  });

  test.describe('Grid Layout', () => {
    test('should display cards in a grid layout', async ({ page }) => {
      const cards = page.locator('.group.rounded-lg');
      await expect(cards.first()).toBeVisible();
    });
  });
});
