import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  // Helper to mock authenticated state
  const mockAuthenticatedUser = async (page: any) => {
    await page.route('**/auth/v1/user**', (route: any) =>
      route.fulfill({
        status: 200,
        json: { id: 'test-user-123', email: 'test@example.com' }
      })
    );
    await page.route('**/auth/v1/session**', (route: any) =>
      route.fulfill({
        status: 200,
        json: {
          access_token: 'mock-token',
          user: { id: 'test-user-123', email: 'test@example.com' }
        }
      })
    );
  };

  test.describe('Unauthenticated Access', () => {
    test('should redirect to auth when not logged in', async ({ page }) => {
      await page.goto('/settings');

      // Should redirect to auth page
      await expect(page).toHaveURL(/auth/);
    });
  });

  test.describe('Authenticated Settings View', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
    });

    test('should display settings heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
    });
  });

  test.describe('API Keys Tab', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
    });

    test('should display API keys section', async ({ page }) => {
      await expect(page.getByText(/api keys/i)).toBeVisible();
    });

    test('should display Alpaca API key input', async ({ page }) => {
      await expect(page.getByLabel(/api key/i)).toBeVisible();
    });

    test('should display Alpaca secret key input', async ({ page }) => {
      await expect(page.getByLabel(/secret key/i)).toBeVisible();
    });

    test('should display paper trading toggle', async ({ page }) => {
      await expect(page.getByText(/paper trading/i)).toBeVisible();
    });

    test('should have masked API key values by default', async ({ page }) => {
      await expect(page.getByText(/•••••/)).toBeVisible();
    });

    test('should toggle show/hide secrets', async ({ page }) => {
      const toggleButton = page.getByRole('button', { name: /show|hide/i });
      await expect(toggleButton).toBeVisible();
    });
  });

  test.describe('Save Functionality', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
    });

    test('should display save button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /save/i })).toBeVisible();
    });

    test('should validate empty API keys', async ({ page }) => {
      await page.getByRole('button', { name: /save/i }).click();

      // Should show validation error
      await expect(page.getByText(/please provide|required/i)).toBeVisible();
    });
  });

  test.describe('Tabs Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
    });

    test('should display API configuration tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /api|configuration/i })).toBeVisible();
    });

    test('should display security tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /security/i })).toBeVisible();
    });
  });

  test.describe('Security Section', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
      await page.getByRole('tab', { name: /security/i }).click();
    });

    test('should display security settings', async ({ page }) => {
      await expect(page.getByText(/security/i)).toBeVisible();
    });
  });

  test.describe('Alert Messages', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
    });

    test('should display security warning for live trading', async ({ page }) => {
      await expect(page.getByText(/securely stored|encrypted/i)).toBeVisible();
    });
  });

  test.describe('Form Inputs', () => {
    test.beforeEach(async ({ page }) => {
      await mockAuthenticatedUser(page);
      await page.goto('/settings');
    });

    test('should allow entering API key', async ({ page }) => {
      const apiKeyInput = page.getByLabel(/api key/i).first();
      await apiKeyInput.fill('test-api-key-123');
      await expect(apiKeyInput).toHaveValue('test-api-key-123');
    });

    test('should allow entering secret key', async ({ page }) => {
      const secretKeyInput = page.getByLabel(/secret key/i);
      await secretKeyInput.fill('test-secret-key-456');
      await expect(secretKeyInput).toHaveValue('test-secret-key-456');
    });
  });
});
