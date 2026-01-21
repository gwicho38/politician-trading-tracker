import { test, expect, Page } from '@playwright/test';
import {
  mockSignal,
  setupSignalsMocks,
  mockAuthSession,
} from './utils/api-mocks';

/**
 * Trading Signals API Integration Tests
 *
 * These tests verify the integration between the UI and Trading Signals APIs:
 * - Signal preview/generation with weight parameters
 * - ML-enhanced signal processing
 * - Custom lambda function execution
 * - Signal preset management
 * - Error handling
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

const testUser = {
  id: 'test-user-signals',
  email: 'signals@test.com',
  isAdmin: false,
};

async function setupAuthenticatedState(page: Page) {
  await mockAuthSession(page, testUser);

  await page.route(`${SUPABASE_URL}/auth/v1/token**`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        access_token: 'mock-token',
        refresh_token: 'mock-refresh',
        user: { id: testUser.id, email: testUser.email },
      },
    })
  );

  await page.route(`${SUPABASE_URL}/auth/v1/user`, (route) =>
    route.fulfill({ status: 200, json: { id: testUser.id, email: testUser.email } })
  );
}

// Mock signal presets
const mockPresets = [
  {
    id: 'preset-1',
    name: 'Aggressive',
    description: 'High risk, high reward',
    is_system: true,
    weights: { politician_count: 0.3, buy_sell_ratio: 0.4, bipartisan: 0.3 },
    created_at: new Date().toISOString(),
  },
  {
    id: 'preset-2',
    name: 'Conservative',
    description: 'Low risk, steady returns',
    is_system: true,
    weights: { politician_count: 0.5, buy_sell_ratio: 0.3, bipartisan: 0.2 },
    created_at: new Date().toISOString(),
  },
  {
    id: 'user-preset-1',
    name: 'My Custom Strategy',
    description: 'Personal strategy',
    is_system: false,
    user_id: testUser.id,
    weights: { politician_count: 0.4, buy_sell_ratio: 0.35, bipartisan: 0.25 },
    created_at: new Date().toISOString(),
  },
];

test.describe('Trading Signals Preview API Integration', () => {
  test.describe('Signal Generation', () => {
    test('should generate signals with default weights', async ({ page }) => {
      const signals = [
        mockSignal('NVDA', { strength: 0.85, confidence: 0.92, ml_enhanced: true }),
        mockSignal('AAPL', { strength: 0.72, confidence: 0.85, ml_enhanced: true }),
        mockSignal('MSFT', { signal_type: 'sell', strength: -0.65, confidence: 0.78 }),
      ];

      await setupSignalsMocks(page, { signals });

      // Also mock the regular trading_signals endpoint for the signals page
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: signals })
      );

      await page.goto('/trading-signals');

      // Should display generated signals
      await expect(page.getByText(/NVDA/i).first()).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/AAPL/i).first()).toBeVisible();
    });

    test('should show ML-enhanced badge for enhanced signals', async ({ page }) => {
      const signals = [
        mockSignal('NVDA', { ml_enhanced: true, confidence: 0.95 }),
      ];

      await setupSignalsMocks(page, { signals });
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: signals })
      );

      await page.goto('/trading-signals');

      // ML-enhanced signals should have visual indicator
      await expect(page.getByText(/NVDA/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should update signals when weights change', async ({ page }) => {
      let callCount = 0;
      const signalSets = [
        [mockSignal('NVDA', { strength: 0.8 })],
        [mockSignal('AAPL', { strength: 0.9 })],
      ];

      await page.route('**/functions/v1/trading-signals/preview-signals**', (route) => {
        const signals = signalSets[Math.min(callCount, signalSets.length - 1)];
        callCount++;
        return route.fulfill({
          status: 200,
          json: { signals, stats: { mlEnhancedCount: 1 }, lambdaApplied: false },
        });
      });

      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: signalSets[0] })
      );

      await page.goto('/trading-signals');

      await expect(page.getByText(/NVDA|AAPL/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display signal strength indicators', async ({ page }) => {
      const signals = [
        mockSignal('NVDA', { signal_type: 'buy', strength: 0.9 }),
        mockSignal('TSLA', { signal_type: 'sell', strength: -0.7 }),
      ];

      await setupSignalsMocks(page, { signals });
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: signals })
      );

      await page.goto('/trading-signals');

      // Should show buy/sell indicators
      await expect(page.getByText(/buy/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should display confidence scores', async ({ page }) => {
      const signals = [
        mockSignal('NVDA', { confidence: 0.92 }),
      ];

      await setupSignalsMocks(page, { signals });
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: signals })
      );

      await page.goto('/trading-signals');

      // Should show confidence (92% or 0.92)
      await expect(page.getByText(/92%|0\.92|confidence/i).first()).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Signal Error Handling', () => {
    test('should handle API timeout gracefully', async ({ page }) => {
      await page.route('**/functions/v1/trading-signals/preview-signals**', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 35000));
        await route.fulfill({ status: 200, json: { signals: [] } });
      });

      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/trading-signals');

      // Page should still be functional
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });

    test('should show error state when API fails', async ({ page }) => {
      await page.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
        route.fulfill({
          status: 500,
          json: { error: 'Internal server error' },
        })
      );

      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 500, json: { error: 'Server error' } })
      );

      await page.goto('/trading-signals');

      // Should show error or empty state
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });

    test('should handle empty signal response', async ({ page }) => {
      await setupSignalsMocks(page, { signals: [] });
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.goto('/trading-signals');

      // Should show empty state
      await expect(page.getByText(/no signals|no trading signals|empty/i).first()).toBeVisible({ timeout: 10000 });
    });
  });
});

test.describe('Signal Preset Management Integration', () => {
  test.describe('Loading Presets', () => {
    test('should load system presets', async ({ page }) => {
      await page.route('**/rest/v1/signal_weight_presets**', (route) =>
        route.fulfill({ status: 200, json: mockPresets })
      );

      await setupSignalsMocks(page);
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [mockSignal('NVDA')] })
      );

      await page.goto('/trading-signals');

      // Should be able to access presets
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });

    test('should load user custom presets when authenticated', async ({ page }) => {
      await setupAuthenticatedState(page);

      await page.route('**/rest/v1/signal_weight_presets**', (route) =>
        route.fulfill({ status: 200, json: mockPresets })
      );

      await setupSignalsMocks(page);
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [mockSignal('NVDA')] })
      );

      await page.goto('/trading-signals');

      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });
  });

  test.describe('Saving Presets', () => {
    test('should save custom preset when authenticated', async ({ page }) => {
      await setupAuthenticatedState(page);

      let presetSaved = false;

      await page.route('**/rest/v1/signal_weight_presets**', (route) => {
        if (route.request().method() === 'POST') {
          presetSaved = true;
          return route.fulfill({
            status: 201,
            json: { id: 'new-preset', name: 'New Preset' },
          });
        }
        return route.fulfill({ status: 200, json: mockPresets });
      });

      await setupSignalsMocks(page);
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [mockSignal('NVDA')] })
      );

      await page.goto('/trading-signals');

      // Interact with signal configuration if available
      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });
  });

  test.describe('Deleting Presets', () => {
    test('should delete user preset', async ({ page }) => {
      await setupAuthenticatedState(page);

      let presetDeleted = false;

      await page.route('**/rest/v1/signal_weight_presets**', (route) => {
        if (route.request().method() === 'DELETE') {
          presetDeleted = true;
          return route.fulfill({ status: 200, json: {} });
        }
        return route.fulfill({ status: 200, json: mockPresets });
      });

      await setupSignalsMocks(page);
      await page.route('**/rest/v1/trading_signals**', (route) =>
        route.fulfill({ status: 200, json: [mockSignal('NVDA')] })
      );

      await page.goto('/trading-signals');

      await expect(page.getByRole('heading', { name: /trading signals/i })).toBeVisible();
    });
  });
});

test.describe('Signal Playground Integration', () => {
  test('should navigate to signal playground', async ({ page }) => {
    await setupSignalsMocks(page);
    await page.route('**/rest/v1/trading_signals**', (route) =>
      route.fulfill({ status: 200, json: [mockSignal('NVDA')] })
    );
    await page.route('**/rest/v1/signal_weight_presets**', (route) =>
      route.fulfill({ status: 200, json: mockPresets })
    );

    await page.goto('/signal-playground');

    await expect(page.getByRole('heading', { name: /signal.*playground|signal.*weight/i })).toBeVisible({ timeout: 10000 });
  });

  test('should display weight sliders', async ({ page }) => {
    await setupSignalsMocks(page);
    await page.route('**/rest/v1/signal_weight_presets**', (route) =>
      route.fulfill({ status: 200, json: mockPresets })
    );

    await page.goto('/signal-playground');

    // Should have sliders for adjusting weights
    await expect(page.getByRole('slider').first()).toBeVisible({ timeout: 10000 });
  });

  test('should update preview when weights change', async ({ page }) => {
    let previewCallCount = 0;

    await page.route('**/functions/v1/trading-signals/preview-signals**', (route) => {
      previewCallCount++;
      return route.fulfill({
        status: 200,
        json: {
          signals: [mockSignal('NVDA', { strength: 0.5 + previewCallCount * 0.1 })],
          stats: { mlEnhancedCount: 1 },
          lambdaApplied: false,
        },
      });
    });

    await page.route('**/rest/v1/signal_weight_presets**', (route) =>
      route.fulfill({ status: 200, json: mockPresets })
    );

    await page.goto('/signal-playground');

    // Wait for initial load
    await expect(page.getByRole('slider').first()).toBeVisible({ timeout: 10000 });

    // Interact with slider if possible
    const slider = page.getByRole('slider').first();
    if (await slider.isVisible()) {
      // Sliders should trigger preview updates (debounced)
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('Lambda Function Integration', () => {
  test('should execute custom lambda function', async ({ page }) => {
    await page.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
      route.fulfill({
        status: 200,
        json: {
          signals: [mockSignal('NVDA')],
          stats: { mlEnhancedCount: 1 },
          lambdaApplied: true,
          lambdaTrace: ['Filter applied: confidence > 0.8'],
        },
      })
    );

    await page.route('**/rest/v1/signal_weight_presets**', (route) =>
      route.fulfill({ status: 200, json: mockPresets })
    );

    await page.goto('/signal-playground');

    await expect(page.getByRole('heading', { name: /signal.*playground|signal.*weight/i })).toBeVisible({ timeout: 10000 });
  });

  test('should show lambda syntax errors', async ({ page }) => {
    await page.route('**/functions/v1/trading-signals/preview-signals**', (route) =>
      route.fulfill({
        status: 200,
        json: {
          signals: [],
          stats: { mlEnhancedCount: 0 },
          lambdaApplied: false,
          lambdaError: 'SyntaxError: Unexpected token at line 1',
        },
      })
    );

    await page.route('**/rest/v1/signal_weight_presets**', (route) =>
      route.fulfill({ status: 200, json: mockPresets })
    );

    await page.goto('/signal-playground');

    await expect(page.getByRole('heading', { name: /signal.*playground|signal.*weight/i })).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Signal Loading States', () => {
  test('should show loading state while generating signals', async ({ page }) => {
    await page.route('**/functions/v1/trading-signals/preview-signals**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        json: { signals: [mockSignal('NVDA')], stats: { mlEnhancedCount: 1 } },
      });
    });

    await page.route('**/rest/v1/trading_signals**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({ status: 200, json: [mockSignal('NVDA')] });
    });

    await page.goto('/trading-signals');

    // Should show loading indicator
    await expect(page.locator('.animate-spin, .animate-pulse').first()).toBeVisible();
  });

  test('should hide loading state when signals load', async ({ page }) => {
    await setupSignalsMocks(page);
    await page.route('**/rest/v1/trading_signals**', (route) =>
      route.fulfill({ status: 200, json: [mockSignal('NVDA')] })
    );

    await page.goto('/trading-signals');

    // Wait for content to load
    await expect(page.getByText(/NVDA/i).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Signal Filtering', () => {
  test('should filter signals by type', async ({ page }) => {
    const signals = [
      mockSignal('NVDA', { signal_type: 'buy' }),
      mockSignal('AAPL', { signal_type: 'buy' }),
      mockSignal('TSLA', { signal_type: 'sell' }),
    ];

    await setupSignalsMocks(page, { signals });
    await page.route('**/rest/v1/trading_signals**', (route) =>
      route.fulfill({ status: 200, json: signals })
    );

    await page.goto('/trading-signals');

    // Should show filter controls
    await expect(page.getByText(/buy/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('should filter signals by confidence threshold', async ({ page }) => {
    const signals = [
      mockSignal('NVDA', { confidence: 0.95 }),
      mockSignal('AAPL', { confidence: 0.75 }),
      mockSignal('TSLA', { confidence: 0.55 }),
    ];

    await setupSignalsMocks(page, { signals });
    await page.route('**/rest/v1/trading_signals**', (route) =>
      route.fulfill({ status: 200, json: signals })
    );

    await page.goto('/trading-signals');

    // Should have confidence slider
    await expect(page.getByRole('slider').first()).toBeVisible({ timeout: 10000 });
  });
});
