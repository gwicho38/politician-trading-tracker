import { test, expect } from '@playwright/test';

test.describe('Trading Signals Page', () => {
  const mockSignals = [
    {
      id: '1',
      ticker: 'NVDA',
      asset_name: 'NVIDIA Corporation',
      signal_type: 'strong_buy',
      signal_strength: 'high',
      confidence_score: 0.92,
      target_price: 150.00,
      stop_loss: 120.00,
      take_profit: 180.00,
      generated_at: new Date().toISOString(),
      politician_activity_count: 15,
      buy_sell_ratio: 3.5,
      is_active: true
    },
    {
      id: '2',
      ticker: 'AAPL',
      asset_name: 'Apple Inc.',
      signal_type: 'buy',
      signal_strength: 'medium',
      confidence_score: 0.78,
      target_price: 185.00,
      generated_at: new Date().toISOString(),
      politician_activity_count: 8,
      buy_sell_ratio: 2.1,
      is_active: true
    },
    {
      id: '3',
      ticker: 'TSLA',
      asset_name: 'Tesla Inc.',
      signal_type: 'sell',
      signal_strength: 'medium',
      confidence_score: 0.71,
      generated_at: new Date().toISOString(),
      politician_activity_count: 5,
      buy_sell_ratio: 0.4,
      is_active: true
    }
  ];

  test.beforeEach(async ({ page }) => {
    // Mock trading signals API
    await page.route('**/rest/v1/trading_signals**', (route) =>
      route.fulfill({
        status: 200,
        json: mockSignals
      })
    );

    await page.goto('/');
    await page.getByRole('button', { name: /trading signals/i }).click();
  });

  test.describe('Page Structure', () => {
    test('should display trading signals heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });

    test('should display AI-powered description', async ({ page }) => {
      await expect(page.getByText(/ai-powered/i)).toBeVisible();
    });
  });

  test.describe('Signal List', () => {
    test('should display signal cards with ticker symbols', async ({ page }) => {
      await expect(page.getByText(/nvda/i)).toBeVisible();
      await expect(page.getByText(/aapl/i)).toBeVisible();
      await expect(page.getByText(/tsla/i)).toBeVisible();
    });

    test('should display signal type badges', async ({ page }) => {
      await expect(page.getByText(/strong buy/i)).toBeVisible();
      await expect(page.getByText(/buy/i).first()).toBeVisible();
      await expect(page.getByText(/sell/i)).toBeVisible();
    });

    test('should display confidence scores', async ({ page }) => {
      await expect(page.getByText(/92%|0\.92/)).toBeVisible();
      await expect(page.getByText(/78%|0\.78/)).toBeVisible();
    });

    test('should display asset names', async ({ page }) => {
      await expect(page.getByText(/nvidia corporation/i)).toBeVisible();
      await expect(page.getByText(/apple inc/i)).toBeVisible();
    });
  });

  test.describe('Signal Generation', () => {
    test('should display generate signals button for authenticated users', async ({ page }) => {
      // Mock authenticated user
      await page.route('**/auth/v1/user**', (route) =>
        route.fulfill({
          status: 200,
          json: { id: 'test-user', email: 'test@example.com' }
        })
      );

      await page.reload();
      await page.getByRole('button', { name: /trading signals/i }).click();

      await expect(page.getByRole('button', { name: /generate/i })).toBeVisible();
    });

    test('should display signal generation parameters', async ({ page }) => {
      await expect(page.getByText(/lookback/i)).toBeVisible();
      await expect(page.getByText(/confidence/i)).toBeVisible();
    });
  });

  test.describe('Shopping Cart', () => {
    test('should display add to cart buttons', async ({ page }) => {
      await expect(page.getByRole('button', { name: /add to cart/i }).first()).toBeVisible();
    });

    test('should display cart icon', async ({ page }) => {
      await expect(page.locator('[data-testid="cart-icon"], .shopping-cart, svg').first()).toBeVisible();
    });
  });

  test.describe('Filtering', () => {
    test('should display signal type filter options', async ({ page }) => {
      await expect(page.getByText(/buy/i).first()).toBeVisible();
      await expect(page.getByText(/sell/i)).toBeVisible();
    });

    test('should display confidence filter slider', async ({ page }) => {
      await expect(page.getByRole('slider')).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should show empty state when no signals', async ({ page }) => {
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.reload();
      await page.getByRole('button', { name: /trading signals/i }).click();

      await expect(page.getByText(/no signals|no trading signals/i)).toBeVisible();
    });
  });

  test.describe('Target Prices', () => {
    test('should display target price when available', async ({ page }) => {
      await expect(page.getByText(/\$150/)).toBeVisible();
    });

    test('should display stop loss when available', async ({ page }) => {
      await expect(page.getByText(/stop loss/i)).toBeVisible();
    });

    test('should display take profit when available', async ({ page }) => {
      await expect(page.getByText(/take profit/i)).toBeVisible();
    });
  });
});
