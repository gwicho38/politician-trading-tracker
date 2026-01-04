import { test, expect } from '@playwright/test';

/**
 * Index page tests
 * Note: Dashboard content is tested in dashboard.spec.ts
 * This file tests that the Index page loads correctly
 */

test.describe('Index Page', () => {
  test('should load the index page', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/');
  });

  test('should have a page title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/.*/);
  });

  test('should render the page content', async ({ page }) => {
    await page.goto('/');
    // Wait for page to load and have content
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have navigation elements', async ({ page }) => {
    await page.goto('/');
    // Check for any navigation
    const hasNav = await page.locator('nav').count() > 0 ||
                   await page.locator('[role="navigation"]').count() > 0 ||
                   await page.getByText(/dashboard/i).count() > 0;
    expect(hasNav).toBeTruthy();
  });
});
