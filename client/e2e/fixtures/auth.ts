import { Page } from '@playwright/test';

/**
 * Shared authentication fixtures and helpers for Playwright tests
 */

export interface MockUser {
  id: string;
  email: string;
  role?: string;
}

export const defaultMockUser: MockUser = {
  id: 'test-user-123',
  email: 'test@example.com',
  role: 'authenticated'
};

/**
 * Mock authenticated user session
 */
export async function mockAuthenticatedUser(page: Page, user: MockUser = defaultMockUser) {
  await page.route('**/auth/v1/user**', (route) =>
    route.fulfill({
      status: 200,
      json: user
    })
  );

  await page.route('**/auth/v1/session**', (route) =>
    route.fulfill({
      status: 200,
      json: {
        access_token: 'mock-access-token-' + user.id,
        refresh_token: 'mock-refresh-token',
        user
      }
    })
  );

  // Also mock the getSession call
  await page.route('**/auth/v1/token**', (route) =>
    route.fulfill({
      status: 200,
      json: {
        access_token: 'mock-access-token-' + user.id,
        user
      }
    })
  );
}

/**
 * Mock unauthenticated state
 */
export async function mockUnauthenticated(page: Page) {
  await page.route('**/auth/v1/user**', (route) =>
    route.fulfill({
      status: 401,
      json: { error: 'Not authenticated' }
    })
  );

  await page.route('**/auth/v1/session**', (route) =>
    route.fulfill({
      status: 200,
      json: { session: null }
    })
  );
}

/**
 * Mock admin user
 */
export async function mockAdminUser(page: Page) {
  await mockAuthenticatedUser(page, {
    id: 'admin-user-123',
    email: 'admin@example.com',
    role: 'admin'
  });
}

/**
 * Mock subscription status
 */
export async function mockSubscription(page: Page, tier: 'free' | 'basic' | 'pro') {
  await page.route('**/rest/v1/user_subscriptions**', (route) =>
    route.fulfill({
      status: 200,
      json: [{
        id: 'sub-123',
        tier,
        status: 'active',
        created_at: new Date().toISOString()
      }]
    })
  );
}
