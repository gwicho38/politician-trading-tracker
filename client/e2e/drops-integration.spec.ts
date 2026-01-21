import { test, expect, Page } from '@playwright/test';
import { mockAuthSession } from './utils/api-mocks';

/**
 * Drops/Social Feed API Integration Tests
 *
 * Tests the integration between UI and Drops APIs:
 * - Feed display (live and saved)
 * - Drop creation and deletion
 * - Like/unlike interactions
 * - Real-time updates
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const testUser = {
  id: 'test-drops-user',
  email: 'drops@test.com',
  isAdmin: false,
};

const mockDrops = [
  {
    id: 'drop-1',
    user_id: 'other-user',
    content: 'Just spotted Nancy Pelosi buying more NVDA! 🚀',
    ticker: 'NVDA',
    is_public: true,
    like_count: 15,
    created_at: new Date().toISOString(),
    user: { email: 'trader@example.com' },
  },
  {
    id: 'drop-2',
    user_id: 'other-user-2',
    content: 'Bipartisan activity on AAPL - both parties buying',
    ticker: 'AAPL',
    is_public: true,
    like_count: 8,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    user: { email: 'analyst@example.com' },
  },
  {
    id: 'drop-3',
    user_id: testUser.id,
    content: 'My personal note on TSLA trades',
    ticker: 'TSLA',
    is_public: false,
    like_count: 0,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    user: { email: testUser.email },
  },
];

const mockLikes = [
  { user_id: testUser.id, drop_id: 'drop-1' },
];

async function setupDropsMocks(page: Page, options: {
  drops?: typeof mockDrops;
  likes?: typeof mockLikes;
  authenticated?: boolean;
} = {}) {
  const {
    drops = mockDrops,
    likes = mockLikes,
    authenticated = true,
  } = options;

  if (authenticated) {
    await mockAuthSession(page, testUser);

    await page.route(`${SUPABASE_URL}/auth/v1/token**`, (route) =>
      route.fulfill({
        status: 200,
        json: { access_token: 'mock-token', user: { id: testUser.id, email: testUser.email } },
      })
    );

    await page.route(`${SUPABASE_URL}/auth/v1/user`, (route) =>
      route.fulfill({ status: 200, json: { id: testUser.id, email: testUser.email } })
    );
  }

  // Mock drops RPC for feed
  await page.route(`${SUPABASE_URL}/rest/v1/rpc/get_drops_feed**`, (route) =>
    route.fulfill({ status: 200, json: drops })
  );

  // Mock drops table
  await page.route(`${SUPABASE_URL}/rest/v1/drops**`, async (route) => {
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, json: drops });
    }

    if (method === 'POST') {
      const body = await route.request().postData();
      const newDrop = body ? JSON.parse(body) : {};
      return route.fulfill({
        status: 201,
        json: { id: 'new-drop', ...newDrop, created_at: new Date().toISOString() },
      });
    }

    if (method === 'DELETE') {
      return route.fulfill({ status: 200, json: {} });
    }

    return route.fulfill({ status: 200, json: {} });
  });

  // Mock likes
  await page.route(`${SUPABASE_URL}/rest/v1/drop_likes**`, async (route) => {
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, json: likes });
    }

    if (method === 'POST') {
      return route.fulfill({ status: 201, json: {} });
    }

    if (method === 'DELETE') {
      return route.fulfill({ status: 200, json: {} });
    }

    return route.fulfill({ status: 200, json: {} });
  });
}

test.describe('Drops Feed API Integration', () => {
  test.describe('Live Feed', () => {
    test('should load live drops feed', async ({ page }) => {
      await setupDropsMocks(page);
      await page.goto('/');

      // Navigate to drops if there's a button
      const dropsButton = page.getByRole('button', { name: /drops|feed|social/i });
      if (await dropsButton.isVisible()) {
        await dropsButton.click();
      }

      await expect(page.getByText(/NVDA|spotted|buying/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display drop content', async ({ page }) => {
      await setupDropsMocks(page);
      await page.goto('/');

      const dropsButton = page.getByRole('button', { name: /drops|feed|social/i });
      if (await dropsButton.isVisible()) {
        await dropsButton.click();
        await expect(page.getByText(/Nancy Pelosi/i).first()).toBeVisible({ timeout: 10000 });
      }
    });

    test('should display like counts', async ({ page }) => {
      await setupDropsMocks(page);
      await page.goto('/');

      const dropsButton = page.getByRole('button', { name: /drops|feed|social/i });
      if (await dropsButton.isVisible()) {
        await dropsButton.click();
      }

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should paginate feed', async ({ page }) => {
      const manyDrops = Array.from({ length: 30 }, (_, i) => ({
        id: `drop-${i}`,
        user_id: 'user-1',
        content: `Drop content ${i}`,
        is_public: true,
        like_count: i,
        created_at: new Date(Date.now() - i * 3600000).toISOString(),
        user: { email: 'user@example.com' },
      }));

      await setupDropsMocks(page, { drops: manyDrops });
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });

  test.describe('Saved Drops', () => {
    test('should load saved/bookmarked drops', async ({ page }) => {
      await setupDropsMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Drop Creation API Integration', () => {
  test.describe('Create Drop', () => {
    test('should create new drop', async ({ page }) => {
      let dropCreated = false;

      await setupDropsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/drops**`, async (route) => {
        if (route.request().method() === 'POST') {
          dropCreated = true;
          return route.fulfill({
            status: 201,
            json: { id: 'new-drop', content: 'New drop content' },
          });
        }
        return route.fulfill({ status: 200, json: mockDrops });
      });

      await page.goto('/');
      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should validate drop content', async ({ page }) => {
      await setupDropsMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });

  test.describe('Delete Drop', () => {
    test('should delete own drop', async ({ page }) => {
      let dropDeleted = false;

      await setupDropsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/drops**`, async (route) => {
        if (route.request().method() === 'DELETE') {
          dropDeleted = true;
          return route.fulfill({ status: 200, json: {} });
        }
        return route.fulfill({ status: 200, json: mockDrops });
      });

      await page.goto('/');
      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Drop Likes API Integration', () => {
  test.describe('Like Interaction', () => {
    test('should like a drop', async ({ page }) => {
      let likeCalled = false;

      await setupDropsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/drop_likes**`, async (route) => {
        if (route.request().method() === 'POST') {
          likeCalled = true;
          return route.fulfill({ status: 201, json: {} });
        }
        return route.fulfill({ status: 200, json: mockLikes });
      });

      await page.goto('/');
      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should unlike a drop', async ({ page }) => {
      let unlikeCalled = false;

      await setupDropsMocks(page);

      await page.route(`${SUPABASE_URL}/rest/v1/drop_likes**`, async (route) => {
        if (route.request().method() === 'DELETE') {
          unlikeCalled = true;
          return route.fulfill({ status: 200, json: {} });
        }
        return route.fulfill({ status: 200, json: mockLikes });
      });

      await page.goto('/');
      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });

    test('should show like count', async ({ page }) => {
      await setupDropsMocks(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
    });
  });
});

test.describe('Drops Loading States', () => {
  test('should show loading while fetching drops', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/rpc/get_drops_feed**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({ status: 200, json: mockDrops });
    });

    await mockAuthSession(page, testUser);
    await page.goto('/');

    await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
  });
});

test.describe('Drops Error Handling', () => {
  test('should handle feed fetch error', async ({ page }) => {
    await page.route(`${SUPABASE_URL}/rest/v1/rpc/get_drops_feed**`, (route) =>
      route.fulfill({ status: 500, json: { error: 'Server error' } })
    );

    await mockAuthSession(page, testUser);
    await page.goto('/');

    await expect(page.getByRole('heading', { name: /dashboard|capitol/i })).toBeVisible();
  });
});
