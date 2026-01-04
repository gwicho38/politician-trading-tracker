import { test, expect } from '@playwright/test';

test.describe('NotFound (404) Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/this-page-does-not-exist');
  });

  test.describe('Page Structure', () => {
    test('should display 404 heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
    });

    test('should display page not found message', async ({ page }) => {
      await expect(page.getByText(/page not found/i)).toBeVisible();
    });

    test('should display return to home link', async ({ page }) => {
      await expect(page.getByRole('link', { name: /return to home/i })).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should navigate back to home when clicking return link', async ({ page }) => {
      await page.getByRole('link', { name: /return to home/i }).click();
      await expect(page).toHaveURL('/');
    });
  });

  test.describe('Styling', () => {
    test('should be centered on page', async ({ page }) => {
      const container = page.locator('.flex.min-h-screen.items-center.justify-center');
      await expect(container).toBeVisible();
    });

    test('should have muted background', async ({ page }) => {
      const background = page.locator('.bg-muted');
      await expect(background).toBeVisible();
    });
  });

  test.describe('Various Invalid Routes', () => {
    const invalidRoutes = [
      '/random-path',
      '/admin/something',
      '/api/v1/users',
      '/dashboard/invalid',
    ];

    for (const route of invalidRoutes) {
      test(`should show 404 for ${route}`, async ({ page }) => {
        await page.goto(route);
        await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
      });
    }
  });
});
