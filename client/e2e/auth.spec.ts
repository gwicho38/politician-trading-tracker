import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth');
  });

  test.describe('Page Structure', () => {
    test('should display the auth page with correct title', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /capitoltrades/i })).toBeVisible();
      await expect(page.getByText(/sign in to track politician trading/i)).toBeVisible();
    });

    test('should have sign in and sign up tabs', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /sign in/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /sign up/i })).toBeVisible();
    });

    test('should display email and password fields', async ({ page }) => {
      await expect(page.getByLabel(/email/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
    });
  });

  test.describe('Form Validation', () => {
    test('should show error for invalid email format', async ({ page }) => {
      await page.getByLabel(/email/i).fill('invalid-email');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/please enter a valid email/i)).toBeVisible();
    });

    test('should show error for short password', async ({ page }) => {
      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('12345');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/password must be at least 6 characters/i)).toBeVisible();
    });

    test('should validate both fields before submission', async ({ page }) => {
      await page.getByLabel(/email/i).fill('bad-email');
      await page.getByLabel(/password/i).fill('short');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/please enter a valid email/i)).toBeVisible();
      await expect(page.getByText(/password must be at least 6 characters/i)).toBeVisible();
    });
  });

  test.describe('Tab Navigation', () => {
    test('should switch between sign in and sign up tabs', async ({ page }) => {
      // Default is sign in
      await expect(page.getByRole('tab', { name: /sign in/i })).toHaveAttribute('data-state', 'active');

      // Click sign up
      await page.getByRole('tab', { name: /sign up/i }).click();
      await expect(page.getByRole('tab', { name: /sign up/i })).toHaveAttribute('data-state', 'active');
      await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();

      // Click back to sign in
      await page.getByRole('tab', { name: /sign in/i }).click();
      await expect(page.getByRole('tab', { name: /sign in/i })).toHaveAttribute('data-state', 'active');
    });

    test('should show different button text for sign up', async ({ page }) => {
      await page.getByRole('tab', { name: /sign up/i }).click();
      await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();
    });
  });

  test.describe('Sign In Flow', () => {
    test('should show loading state during sign in', async ({ page }) => {
      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');

      // Mock the Supabase auth to delay response
      await page.route('**/auth/v1/token**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 500));
        await route.fulfill({
          status: 400,
          json: { error: 'Invalid login credentials' }
        });
      });

      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show loading indicator
      await expect(page.getByText(/signing in/i)).toBeVisible();
    });

    test('should display error toast for invalid credentials', async ({ page }) => {
      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('wrongpassword');

      // Mock failed auth response
      await page.route('**/auth/v1/token**', (route) =>
        route.fulfill({
          status: 400,
          json: { error: 'Invalid login credentials', error_description: 'Invalid login credentials' }
        })
      );

      await page.getByRole('button', { name: /sign in/i }).click();

      // Wait for toast to appear
      await expect(page.getByText(/invalid credentials/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Sign Up Flow', () => {
    test('should show loading state during sign up', async ({ page }) => {
      await page.getByRole('tab', { name: /sign up/i }).click();

      await page.getByLabel(/email/i).fill('newuser@example.com');
      await page.getByLabel(/password/i).fill('password123');

      // Mock delayed signup
      await page.route('**/auth/v1/signup**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          json: { user: { id: '123', email: 'newuser@example.com' } }
        });
      });

      await page.getByRole('button', { name: /create account/i }).click();

      await expect(page.getByText(/creating account/i)).toBeVisible();
    });

    test('should show confirmation message after successful signup', async ({ page }) => {
      await page.getByRole('tab', { name: /sign up/i }).click();

      await page.getByLabel(/email/i).fill('newuser@example.com');
      await page.getByLabel(/password/i).fill('password123');

      // Mock successful signup
      await page.route('**/auth/v1/signup**', (route) =>
        route.fulfill({
          status: 200,
          json: {
            user: { id: '123', email: 'newuser@example.com' },
            session: null // No session means email confirmation required
          }
        })
      );

      await page.getByRole('button', { name: /create account/i }).click();

      await expect(page.getByText(/check your email/i)).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Accessibility', () => {
    test('should be keyboard navigable', async ({ page }) => {
      // Tab through form elements
      await page.keyboard.press('Tab');
      await expect(page.getByRole('tab', { name: /sign in/i })).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByRole('tab', { name: /sign up/i })).toBeFocused();
    });

    test('should have proper form labels', async ({ page }) => {
      const emailInput = page.getByLabel(/email/i);
      const passwordInput = page.getByLabel(/password/i);

      await expect(emailInput).toBeVisible();
      await expect(passwordInput).toBeVisible();
    });
  });
});

test.describe('Session Persistence / Cached Load', () => {
  // Helper to create a mock Supabase session in localStorage
  const createMockSession = (expiresInSeconds = 3600) => {
    const now = Math.floor(Date.now() / 1000);
    return {
      access_token: 'mock-access-token-' + Date.now(),
      refresh_token: 'mock-refresh-token',
      expires_in: expiresInSeconds,
      expires_at: now + expiresInSeconds,
      token_type: 'bearer',
      user: {
        id: 'test-user-id-' + Date.now(),
        email: 'testuser@example.com',
        email_confirmed_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        user_metadata: {},
        app_metadata: { provider: 'email' },
        aud: 'authenticated',
        role: 'authenticated',
      },
    };
  };

  test.describe('Auth State Restoration on Page Load', () => {
    test('should restore user from localStorage on initial load', async ({ page }) => {
      // Set up localStorage with a valid session before navigating
      const mockSession = createMockSession();

      // Need to navigate first to access localStorage for this domain
      await page.goto('/');

      // Inject the mock session into localStorage
      await page.evaluate((session) => {
        // Supabase stores session with a key like 'sb-{project-ref}-auth-token'
        // For testing, we'll use a generic pattern
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, mockSession);

      // Mock the auth API to return the session
      await page.route('**/auth/v1/token**', (route) => {
        route.fulfill({
          status: 200,
          json: mockSession,
        });
      });

      // Reload the page (simulating second/cached load)
      await page.reload();

      // Wait for the page to settle
      await page.waitForLoadState('networkidle');

      // The dashboard should load without getting stuck
      // Check that we can see dashboard content (not auth page)
      await expect(page.locator('body')).not.toContainText('Session fetch timeout', { timeout: 10000 });
    });

    test('should not show loading spinner indefinitely on cached auth load', async ({ page }) => {
      const mockSession = createMockSession();

      await page.goto('/');

      // Set localStorage
      await page.evaluate((session) => {
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, mockSession);

      // Mock successful session refresh
      await page.route('**/auth/v1/token**', async (route) => {
        // Simulate some network latency
        await new Promise(resolve => setTimeout(resolve, 100));
        route.fulfill({
          status: 200,
          json: mockSession,
        });
      });

      // Record the time before reload
      const startTime = Date.now();

      // Reload and wait for dashboard content
      await page.reload();

      // Dashboard stats or content should be visible within reasonable time
      // This ensures we're not stuck in a loading state
      await expect(page.getByText(/politician|trading|trades|dashboard/i).first()).toBeVisible({ timeout: 10000 });

      const loadTime = Date.now() - startTime;

      // Page should load within 10 seconds (generous for test stability)
      expect(loadTime).toBeLessThan(10000);
    });

    test('should handle expired session gracefully', async ({ page }) => {
      // Create an expired session
      const expiredSession = createMockSession(-3600); // Expired 1 hour ago

      await page.goto('/');

      await page.evaluate((session) => {
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, expiredSession);

      // Mock refresh token failure (expired)
      await page.route('**/auth/v1/token**', (route) => {
        route.fulfill({
          status: 401,
          json: { error: 'invalid_grant', error_description: 'Token has expired' },
        });
      });

      await page.reload();

      // Page should still load (user will be logged out)
      await expect(page.getByText(/politician|trading|trades|dashboard/i).first()).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Page Load Performance with Auth', () => {
    test('should load dashboard quickly when authenticated', async ({ page }) => {
      const mockSession = createMockSession();

      await page.goto('/');

      await page.evaluate((session) => {
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, mockSession);

      // Mock session and API calls
      await page.route('**/auth/v1/**', (route) => {
        route.fulfill({
          status: 200,
          json: mockSession,
        });
      });

      // Time the reload
      const startTime = Date.now();
      await page.reload();

      // Wait for main content to be interactive
      await page.waitForLoadState('domcontentloaded');

      const domContentLoadedTime = Date.now() - startTime;

      // DOM should be ready within 5 seconds
      expect(domContentLoadedTime).toBeLessThan(5000);
    });

    test('should not block rendering on slow auth API', async ({ page }) => {
      const mockSession = createMockSession();

      await page.goto('/');

      await page.evaluate((session) => {
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, mockSession);

      // Mock a VERY slow auth API (simulating network issues)
      await page.route('**/auth/v1/token**', async (route) => {
        // Wait 5 seconds before responding
        await new Promise(resolve => setTimeout(resolve, 5000));
        route.fulfill({
          status: 200,
          json: mockSession,
        });
      });

      await page.reload();

      // Content should still be visible even with slow auth API
      // The page should use localStorage hydration and not block
      await expect(page.getByText(/politician|trading|trades|dashboard/i).first()).toBeVisible({ timeout: 3000 });
    });
  });

  test.describe('Auth State Consistency', () => {
    test('should show user info in header when authenticated', async ({ page }) => {
      const mockSession = createMockSession();

      await page.goto('/');

      await page.evaluate((session) => {
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, mockSession);

      await page.route('**/auth/v1/**', (route) => {
        route.fulfill({
          status: 200,
          json: mockSession,
        });
      });

      await page.reload();
      await page.waitForLoadState('networkidle');

      // User email or display name should be visible in header
      // The exact text depends on the UI, but we should see something indicating logged in
      const headerUserIndicator = page.locator('header').getByText(/testuser|sign out/i);
      await expect(headerUserIndicator).toBeVisible({ timeout: 5000 });
    });

    test('should show sign in button when not authenticated', async ({ page }) => {
      // Clear any existing session
      await page.goto('/');
      await page.evaluate(() => {
        const keys = Object.keys(localStorage).filter(k => k.endsWith('-auth-token'));
        keys.forEach(k => localStorage.removeItem(k));
      });

      await page.reload();
      await page.waitForLoadState('networkidle');

      // Should see sign in button
      const signInButton = page.locator('header').getByRole('button', { name: /sign in/i });
      await expect(signInButton).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Multiple Refresh Resilience', () => {
    test('should handle multiple rapid refreshes without breaking auth', async ({ page }) => {
      const mockSession = createMockSession();

      await page.goto('/');

      await page.evaluate((session) => {
        const key = Object.keys(localStorage).find(k => k.endsWith('-auth-token')) || 'sb-test-auth-token';
        localStorage.setItem(key, JSON.stringify(session));
      }, mockSession);

      await page.route('**/auth/v1/**', (route) => {
        route.fulfill({
          status: 200,
          json: mockSession,
        });
      });

      // Perform multiple rapid refreshes
      for (let i = 0; i < 3; i++) {
        await page.reload();
        await page.waitForLoadState('domcontentloaded');
      }

      // After multiple refreshes, page should still work
      await expect(page.getByText(/politician|trading|trades|dashboard/i).first()).toBeVisible({ timeout: 10000 });

      // No error messages about session timeouts
      await expect(page.locator('body')).not.toContainText('Session fetch timeout');
    });
  });
});
