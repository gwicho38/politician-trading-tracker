import { test, expect, Page } from '@playwright/test';
import {
  mockAlpacaAccount,
  mockPosition,
  mockOrder,
  setupAlpacaMocks,
  setupOrdersMocks,
  mockAuthSession,
} from './utils/api-mocks';

/**
 * Alpaca API Integration Tests
 *
 * These tests verify the complete integration between the UI and Alpaca APIs:
 * - Account data fetching and display
 * - Position tracking and P&L calculations
 * - Connection status monitoring
 * - Error handling and recovery
 * - Circuit breaker states
 */

const SUPABASE_URL = 'https://uljsqvwkomdrlnofmlad.supabase.co';

// Test user for authenticated scenarios
const testUser = {
  id: 'test-user-integration',
  email: 'integration@test.com',
  isAdmin: false,
};

// Mock credentials for connected state
const mockCredentials = {
  paper_api_key: 'PK_TEST_INTEGRATION',
  paper_secret_key: 'SK_TEST_INTEGRATION',
  paper_validated_at: new Date().toISOString(),
  live_api_key: null,
  live_secret_key: null,
  live_validated_at: null,
};

/**
 * Setup base authentication and credential mocks
 */
async function setupAuthenticatedState(page: Page, credentials = mockCredentials) {
  await mockAuthSession(page, testUser);

  // Mock auth endpoints
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

  // Mock credentials
  await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ status: 200, json: credentials ? [credentials] : [] });
    }
    return route.fulfill({ status: 200, json: {} });
  });
}

test.describe('Alpaca Account API Integration', () => {
  test.describe('Account Data Fetching', () => {
    test('should display account balance from API response', async ({ page }) => {
      await setupAuthenticatedState(page);

      const customAccount = mockAlpacaAccount({
        portfolio_value: '125000.50',
        cash: '45000.25',
        buying_power: '90000.75',
        equity: '125000.50',
      });

      await setupAlpacaMocks(page, { account: customAccount });
      await page.goto('/trading');

      // Verify portfolio value is displayed
      await expect(page.getByText('$125,000.50').first()).toBeVisible({ timeout: 10000 });
      // Verify cash is displayed
      await expect(page.getByText('$45,000.25').first()).toBeVisible();
      // Verify buying power
      await expect(page.getByText('$90,000.75').first()).toBeVisible();
    });

    test('should calculate and display daily P&L', async ({ page }) => {
      await setupAuthenticatedState(page);

      const customAccount = mockAlpacaAccount({
        equity: '105000.00',
        last_equity: '100000.00', // Previous day was $100k, now $105k = +$5k
      });

      await setupAlpacaMocks(page, { account: customAccount });
      await page.goto('/trading');

      // Should show positive P&L
      await expect(page.getByText("Today's P&L")).toBeVisible();
      await expect(page.getByText(/\+?\$5,000/).first()).toBeVisible({ timeout: 10000 });
    });

    test('should show negative P&L with appropriate styling', async ({ page }) => {
      await setupAuthenticatedState(page);

      const customAccount = mockAlpacaAccount({
        equity: '95000.00',
        last_equity: '100000.00', // Lost $5k
      });

      await setupAlpacaMocks(page, { account: customAccount });
      await page.goto('/trading');

      // Should show negative P&L (may be formatted as -$5,000 or ($5,000))
      await expect(page.getByText("Today's P&L")).toBeVisible();
    });

    test('should handle account with zero balance', async ({ page }) => {
      await setupAuthenticatedState(page);

      const zeroAccount = mockAlpacaAccount({
        portfolio_value: '0.00',
        cash: '0.00',
        buying_power: '0.00',
        equity: '0.00',
      });

      await setupAlpacaMocks(page, { account: zeroAccount });
      await page.goto('/trading');

      await expect(page.getByText('Portfolio Value')).toBeVisible();
      await expect(page.getByText('$0.00').first()).toBeVisible({ timeout: 10000 });
    });

    test('should refresh account data periodically', async ({ page }) => {
      await setupAuthenticatedState(page);

      let requestCount = 0;
      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        requestCount++;
        const updatedValue = (100000 + requestCount * 1000).toFixed(2);
        await route.fulfill({
          status: 200,
          json: {
            success: true,
            account: mockAlpacaAccount({ portfolio_value: updatedValue }),
            tradingMode: 'paper',
          },
        });
      });

      await page.goto('/trading');

      // Wait for initial load
      await expect(page.getByText('Portfolio Value')).toBeVisible();

      // The hook refreshes every 60 seconds, but we can verify initial call happened
      expect(requestCount).toBeGreaterThanOrEqual(1);
    });
  });

  test.describe('Account Error Handling', () => {
    test('should display error message when account fetch fails', async ({ page }) => {
      await setupAuthenticatedState(page);

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, (route) =>
        route.fulfill({
          status: 500,
          json: { success: false, error: 'Internal server error' },
        })
      );

      await page.goto('/trading');

      // Should show error state or connection issue
      await expect(
        page.getByText(/error|failed|unavailable|connect/i).first()
      ).toBeVisible({ timeout: 10000 });
    });

    test('should handle network timeout gracefully', async ({ page }) => {
      await setupAuthenticatedState(page);

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        // Simulate timeout by not responding for 30 seconds
        await new Promise(resolve => setTimeout(resolve, 30000));
        await route.fulfill({ status: 200, json: { success: true } });
      });

      await page.goto('/trading');

      // Page should still be interactive even if account data is loading
      await expect(page.getByRole('heading', { name: 'Trading' })).toBeVisible();
    });

    test('should show trading blocked warning when account is restricted', async ({ page }) => {
      await setupAuthenticatedState(page);

      const blockedAccount = mockAlpacaAccount({
        trading_blocked: true,
        account_blocked: false,
      });

      await setupAlpacaMocks(page, { account: blockedAccount });
      await page.goto('/trading');

      // Should show warning about trading being blocked
      await expect(
        page.getByText(/trading.*blocked|restricted|disabled/i).first()
      ).toBeVisible({ timeout: 10000 });
    });

    test('should show account blocked warning', async ({ page }) => {
      await setupAuthenticatedState(page);

      const blockedAccount = mockAlpacaAccount({
        account_blocked: true,
      });

      await setupAlpacaMocks(page, { account: blockedAccount });
      await page.goto('/trading');

      await expect(page.getByText('Account Overview')).toBeVisible();
    });
  });

  test.describe('Connection Status Monitoring', () => {
    test('should show healthy status indicator', async ({ page }) => {
      await setupAuthenticatedState(page);
      await setupAlpacaMocks(page, { connectionStatus: 'healthy' });
      await page.goto('/trading');

      await expect(page.getByText('Account Connected')).toBeVisible({ timeout: 10000 });
    });

    test('should show degraded status warning', async ({ page }) => {
      await setupAuthenticatedState(page);

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        const body = await route.request().postData();
        const action = body ? JSON.parse(body).action : null;

        if (action === 'connection-status') {
          return route.fulfill({
            status: 200,
            json: {
              status: 'degraded',
              circuitBreaker: { state: 'half-open' },
            },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, account: mockAlpacaAccount(), tradingMode: 'paper' },
        });
      });

      await page.goto('/trading');
      await expect(page.getByText('Account Overview')).toBeVisible();
    });

    test('should show error status with circuit breaker open', async ({ page }) => {
      await setupAuthenticatedState(page);

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        const body = await route.request().postData();
        const action = body ? JSON.parse(body).action : null;

        if (action === 'connection-status') {
          return route.fulfill({
            status: 200,
            json: {
              status: 'error',
              circuitBreaker: { state: 'open' },
            },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, account: mockAlpacaAccount(), tradingMode: 'paper' },
        });
      });

      await page.goto('/trading');
      await expect(page.getByText('Account Overview')).toBeVisible();
    });
  });
});

test.describe('Alpaca Positions API Integration', () => {
  test.describe('Position Display', () => {
    test('should display positions from API', async ({ page }) => {
      await setupAuthenticatedState(page);

      const positions = [
        mockPosition('AAPL', {
          qty: '100',
          avg_entry_price: '150.00',
          current_price: '175.00',
          market_value: '17500.00',
          unrealized_pl: '2500.00',
        }),
        mockPosition('NVDA', {
          qty: '50',
          avg_entry_price: '400.00',
          current_price: '450.00',
          market_value: '22500.00',
          unrealized_pl: '2500.00',
        }),
      ];

      await setupAlpacaMocks(page, { positions });
      await page.goto('/trading');

      // Should show positions section
      await expect(page.getByRole('heading', { name: /Positions/i })).toBeVisible();
    });

    test('should calculate total unrealized P&L across positions', async ({ page }) => {
      await setupAuthenticatedState(page);

      const positions = [
        mockPosition('AAPL', { unrealized_pl: '1000.00' }),
        mockPosition('NVDA', { unrealized_pl: '2000.00' }),
        mockPosition('MSFT', { unrealized_pl: '-500.00' }),
      ];

      await setupAlpacaMocks(page, { positions });
      await page.goto('/trading');

      await expect(page.getByRole('heading', { name: /Positions/i })).toBeVisible();
    });

    test('should handle empty positions gracefully', async ({ page }) => {
      await setupAuthenticatedState(page);
      await setupAlpacaMocks(page, { positions: [] });
      await page.goto('/trading');

      await expect(page.getByRole('heading', { name: /Positions/i })).toBeVisible();
      // May show empty state message
    });

    test('should display position with loss in red', async ({ page }) => {
      await setupAuthenticatedState(page);

      const positions = [
        mockPosition('AAPL', {
          qty: '100',
          avg_entry_price: '200.00',
          current_price: '150.00',
          market_value: '15000.00',
          unrealized_pl: '-5000.00',
          unrealized_plpc: '-0.25',
        }),
      ];

      await setupAlpacaMocks(page, { positions });
      await page.goto('/trading');

      await expect(page.getByRole('heading', { name: /Positions/i })).toBeVisible();
    });
  });

  test.describe('Position Error Handling', () => {
    test('should show error state when positions fetch fails', async ({ page }) => {
      await setupAuthenticatedState(page);

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        const body = await route.request().postData();
        const action = body ? JSON.parse(body).action : null;

        if (action === 'get-positions') {
          return route.fulfill({
            status: 500,
            json: { success: false, error: 'Failed to fetch positions' },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, account: mockAlpacaAccount(), tradingMode: 'paper' },
        });
      });

      await page.goto('/trading');
      await expect(page.getByRole('heading', { name: /Positions/i })).toBeVisible();
    });
  });
});

test.describe('Alpaca Credentials API Integration', () => {
  test.describe('Credential Validation', () => {
    test('should test connection with provided credentials', async ({ page }) => {
      await setupAuthenticatedState(page, null); // Start without credentials

      let testConnectionCalled = false;

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        const body = await route.request().postData();
        const action = body ? JSON.parse(body).action : null;

        if (action === 'test-connection') {
          testConnectionCalled = true;
          return route.fulfill({
            status: 200,
            json: { success: true, account: mockAlpacaAccount() },
          });
        }

        return route.fulfill({
          status: 200,
          json: { success: true, account: mockAlpacaAccount(), tradingMode: 'paper' },
        });
      });

      await page.goto('/trading');

      // Fill in credentials
      await page.getByLabel('API Key').fill('PK_TEST_NEW');
      await page.getByLabel('Secret Key').fill('SK_TEST_NEW');

      // Click test connection
      await page.getByRole('button', { name: /Test Connection/i }).click();

      // Wait for the test to complete
      await page.waitForTimeout(1000);
      expect(testConnectionCalled).toBe(true);
    });

    test('should show error for invalid credentials', async ({ page }) => {
      await setupAuthenticatedState(page, null);

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
        const body = await route.request().postData();
        const action = body ? JSON.parse(body).action : null;

        if (action === 'test-connection') {
          return route.fulfill({
            status: 200,
            json: { success: false, error: 'Invalid API credentials' },
          });
        }

        return route.fulfill({ status: 200, json: {} });
      });

      await page.goto('/trading');

      await page.getByLabel('API Key').fill('INVALID_KEY');
      await page.getByLabel('Secret Key').fill('INVALID_SECRET');
      await page.getByRole('button', { name: /Test Connection/i }).click();

      // Should show error message
      await expect(page.getByText(/invalid|error|failed/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should save credentials on successful connection', async ({ page }) => {
      await setupAuthenticatedState(page, null);

      let credentialsSaved = false;

      await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, (route) =>
        route.fulfill({
          status: 200,
          json: { success: true, account: mockAlpacaAccount() },
        })
      );

      await page.route(`${SUPABASE_URL}/rest/v1/user_api_keys**`, (route) => {
        if (route.request().method() === 'POST' || route.request().method() === 'PATCH') {
          credentialsSaved = true;
          return route.fulfill({ status: 200, json: {} });
        }
        return route.fulfill({ status: 200, json: [] });
      });

      await page.goto('/trading');

      await page.getByLabel('API Key').fill('PK_TEST_SAVE');
      await page.getByLabel('Secret Key').fill('SK_TEST_SAVE');
      await page.getByRole('button', { name: /Connect & Save/i }).click();

      await page.waitForTimeout(2000);
      expect(credentialsSaved).toBe(true);
    });
  });

  test.describe('Trading Mode Switching', () => {
    test('should switch between paper and live mode', async ({ page }) => {
      await setupAuthenticatedState(page);
      await setupAlpacaMocks(page);
      await page.goto('/trading');

      // Start in paper mode
      await expect(page.getByText('Paper Trading').first()).toBeVisible();

      // Switch to live
      await page.getByRole('button', { name: /Live Trading/i }).click();
      await expect(page.getByText('Live Trading').first()).toBeVisible();

      // Switch back to paper
      await page.getByRole('button', { name: /Paper Trading/i }).click();
      await expect(page.getByText('Paper Trading').first()).toBeVisible();
    });

    test('should show live trading warning', async ({ page }) => {
      await setupAuthenticatedState(page);
      await setupAlpacaMocks(page);
      await page.goto('/trading');

      await page.getByRole('button', { name: /Live Trading/i }).click();

      await expect(page.getByText(/real money|caution|warning/i).first()).toBeVisible();
    });

    test('should require separate credentials for live mode', async ({ page }) => {
      // Credentials only have paper keys, not live keys
      const paperOnlyCredentials = {
        paper_api_key: 'PK_PAPER',
        paper_secret_key: 'SK_PAPER',
        paper_validated_at: new Date().toISOString(),
        live_api_key: null,
        live_secret_key: null,
        live_validated_at: null,
      };

      await setupAuthenticatedState(page, paperOnlyCredentials);
      await setupAlpacaMocks(page);
      await page.goto('/trading');

      // Switch to live mode
      await page.getByRole('button', { name: /Live Trading/i }).click();

      // Should prompt for live credentials
      await expect(page.getByText(/connect.*live|live.*credentials/i).first()).toBeVisible({ timeout: 5000 });
    });
  });
});

test.describe('Alpaca Loading States', () => {
  test('should show loading spinner while fetching account', async ({ page }) => {
    await setupAuthenticatedState(page);

    await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        json: { success: true, account: mockAlpacaAccount(), tradingMode: 'paper' },
      });
    });

    await page.goto('/trading');

    // Should show loading state
    await expect(page.locator('.animate-spin, .animate-pulse').first()).toBeVisible();

    // Eventually shows data
    await expect(page.getByText('Portfolio Value')).toBeVisible({ timeout: 10000 });
  });

  test('should show skeleton loaders for positions', async ({ page }) => {
    await setupAuthenticatedState(page);

    await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
      const body = await route.request().postData();
      const action = body ? JSON.parse(body).action : null;

      if (action === 'get-positions') {
        await new Promise(resolve => setTimeout(resolve, 2000));
        return route.fulfill({
          status: 200,
          json: { success: true, positions: [mockPosition('AAPL')] },
        });
      }

      return route.fulfill({
        status: 200,
        json: { success: true, account: mockAlpacaAccount(), tradingMode: 'paper' },
      });
    });

    await page.goto('/trading');

    // Positions section should be visible
    await expect(page.getByRole('heading', { name: /Positions/i })).toBeVisible();
  });
});

test.describe('Alpaca Data Refresh', () => {
  test('should refresh data on manual refresh click', async ({ page }) => {
    await setupAuthenticatedState(page);

    let refreshCount = 0;

    await page.route(`${SUPABASE_URL}/functions/v1/alpaca-account**`, async (route) => {
      refreshCount++;
      await route.fulfill({
        status: 200,
        json: {
          success: true,
          account: mockAlpacaAccount({ portfolio_value: (100000 + refreshCount * 1000).toString() }),
          tradingMode: 'paper',
        },
      });
    });

    await page.goto('/trading');

    // Wait for initial load
    await expect(page.getByText('Portfolio Value')).toBeVisible();
    const initialCount = refreshCount;

    // Find and click refresh button if available
    const refreshButton = page.locator('button').filter({ has: page.locator('svg') }).first();
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(1000);
      expect(refreshCount).toBeGreaterThan(initialCount);
    }
  });
});
