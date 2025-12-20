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
