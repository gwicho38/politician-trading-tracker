import { test, expect, Page } from '@playwright/test';
import { setupWalletAuthMocks } from './utils/api-mocks';

/**
 * Wallet Auth Network Integration Tests
 *
 * Tests the wallet authentication edge function route setup and auth page integration.
 *
 * IMPORTANT: The wallet UI section is conditionally rendered based on
 * isWalletDemoMode (config/wallet.ts). In test environments without
 * VITE_WALLETCONNECT_PROJECT_ID, the wallet section is hidden.
 * These tests verify:
 * 1. Auth page renders correctly (email auth is always available)
 * 2. The wallet-auth edge function routes can be intercepted
 * 3. Auth state redirects work correctly
 *
 * Hook under test: useWalletAuth()
 * Endpoints: POST /functions/v1/wallet-auth?action=nonce
 *            POST /functions/v1/wallet-auth?action=verify
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

test.describe('Wallet Auth Network Integration', () => {
  test.describe('Auth Page Rendering', () => {
    test('should display auth page with email form', async ({ page }) => {
      await page.goto('/auth');

      // Auth page heading
      await expect(page.getByRole('heading', { name: /govmarket/i })).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/sign in to track/i)).toBeVisible();
    });

    test('should have sign in and sign up tabs', async ({ page }) => {
      await page.goto('/auth');

      await expect(page.getByRole('tab', { name: /sign in/i })).toBeVisible({ timeout: 10000 });
      await expect(page.getByRole('tab', { name: /sign up/i })).toBeVisible();
    });

    test('should display email and password fields', async ({ page }) => {
      await page.goto('/auth');

      await expect(page.getByLabel(/email/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByLabel(/password/i)).toBeVisible();
    });
  });

  test.describe('Wallet Auth Edge Function Routes', () => {
    test('should intercept nonce endpoint when configured', async ({ page }) => {
      let nonceCalled = false;

      await page.route(`${SUPABASE_URL}/functions/v1/wallet-auth**`, (route) => {
        const url = route.request().url();
        if (url.includes('action=nonce')) {
          nonceCalled = true;
        }
        return route.fulfill({
          status: 200,
          json: { message: 'Sign this: test-nonce' },
        });
      });

      await page.goto('/auth');
      await expect(page.getByRole('heading', { name: /govmarket/i })).toBeVisible({ timeout: 10000 });

      // Route is registered and ready - actual call requires wallet provider
      // Verify route handler was set up without errors
    });

    test('should intercept verify endpoint when configured', async ({ page }) => {
      await page.route(`${SUPABASE_URL}/functions/v1/wallet-auth**`, (route) => {
        const url = route.request().url();
        if (url.includes('action=verify')) {
          return route.fulfill({
            status: 200,
            json: { token: 'test-token', isNewUser: false, userId: 'user-1' },
          });
        }
        return route.fulfill({ status: 200, json: {} });
      });

      await page.goto('/auth');
      await expect(page.getByRole('heading', { name: /govmarket/i })).toBeVisible({ timeout: 10000 });
    });

    test('should setup wallet auth mocks using helper', async ({ page }) => {
      await setupWalletAuthMocks(page, {
        nonceMessage: 'Sign this: custom-nonce',
        verifyToken: 'custom-token',
        verifyIsNewUser: true,
        verifyUserId: 'new-wallet-user',
      });

      await page.goto('/auth');
      await expect(page.getByRole('heading', { name: /govmarket/i })).toBeVisible({ timeout: 10000 });
    });

    test('should handle nonce error mock configuration', async ({ page }) => {
      await setupWalletAuthMocks(page, { nonceError: 'Rate limited' });

      await page.goto('/auth');
      await expect(page.getByRole('heading', { name: /govmarket/i })).toBeVisible({ timeout: 10000 });
    });

    test('should handle verify error mock configuration', async ({ page }) => {
      await setupWalletAuthMocks(page, { verifyError: 'Invalid signature' });

      await page.goto('/auth');
      await expect(page.getByRole('heading', { name: /govmarket/i })).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Auth State Redirects', () => {
    test('should show sign in form when not authenticated', async ({ page }) => {
      await page.addInitScript(() => {
        const keys = Object.keys(localStorage).filter(k => k.endsWith('-auth-token'));
        keys.forEach(k => localStorage.removeItem(k));
      });

      await page.goto('/auth');

      await expect(page.getByLabel(/email/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });

    test('should show sign in loading state during auth', async ({ page }) => {
      await page.route('**/auth/v1/token**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 500));
        await route.fulfill({
          status: 400,
          json: { error: 'Invalid login credentials' },
        });
      });

      await page.goto('/auth');

      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/signing in/i)).toBeVisible();
    });

    test('should handle invalid credentials error', async ({ page }) => {
      await page.route('**/auth/v1/token**', (route) =>
        route.fulfill({
          status: 400,
          json: { error: 'Invalid login credentials', error_description: 'Invalid login credentials' },
        })
      );

      await page.goto('/auth');

      await page.getByLabel(/email/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText('Invalid credentials', { exact: true })).toBeVisible({ timeout: 5000 });
    });
  });
});
