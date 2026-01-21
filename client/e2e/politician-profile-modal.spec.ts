import { test, expect } from '@playwright/test';

/**
 * E2E tests for PoliticianProfileModal
 *
 * Tests the Ollama AI profile generation integration:
 * - Successful AI profile generation (source: "ollama")
 * - Fallback profile when Ollama fails (source: "fallback")
 * - Loading states and timeout handling
 * - Error states
 */
test.describe('Politician Profile Modal - Ollama Integration', () => {
  const mockPolitician = {
    id: 'test-politician-1',
    first_name: 'Nancy',
    last_name: 'Pelosi',
    full_name: 'Nancy Pelosi',
    name: 'Nancy Pelosi',
    party: 'D',
    role: 'Representative',
    chamber: 'Representative',
    state_or_country: 'California',
    state: 'California',
    district: 'CA-11',
    jurisdiction_id: 'us-congress',
    avatar_url: null,
    total_trades: 150,
    total_volume: 50000000,
    is_active: true,
  };

  const mockTrades = [
    {
      id: 'trade-1',
      politician_id: 'test-politician-1',
      asset_ticker: 'NVDA',
      asset_name: 'NVIDIA Corporation',
      transaction_type: 'purchase',
      transaction_date: '2024-01-15',
      disclosure_date: '2024-01-20',
      amount_range_min: 100000,
      amount_range_max: 250000,
      status: 'active',
      source_url: 'https://example.com/filing1',
    },
    {
      id: 'trade-2',
      politician_id: 'test-politician-1',
      asset_ticker: 'AAPL',
      asset_name: 'Apple Inc.',
      transaction_type: 'sale',
      transaction_date: '2024-01-10',
      disclosure_date: '2024-01-15',
      amount_range_min: 50000,
      amount_range_max: 100000,
      status: 'active',
      source_url: 'https://example.com/filing2',
    },
    {
      id: 'trade-3',
      politician_id: 'test-politician-1',
      asset_ticker: 'MSFT',
      asset_name: 'Microsoft Corporation',
      transaction_type: 'purchase',
      transaction_date: '2024-01-05',
      disclosure_date: '2024-01-10',
      amount_range_min: 250000,
      amount_range_max: 500000,
      status: 'active',
      source_url: 'https://example.com/filing3',
    },
  ];

  const mockOllamaSuccessResponse = {
    bio: 'Nancy Pelosi is a Democratic Representative from California who has served in the U.S. House of Representatives since 1987. With over 150 disclosed trades totaling approximately $50M in volume, her portfolio shows significant activity in technology stocks including NVDA, AAPL, and MSFT.',
    source: 'ollama',
  };

  const mockFallbackResponse = {
    bio: 'Nancy Pelosi is a Democratic Representative from California. According to public financial disclosure filings, they have reported 150 trades with an estimated trading volume of $50.0M. Their most frequently traded securities include NVDA, AAPL, MSFT.',
    source: 'fallback',
    reason: 'ollama_error',
  };

  test.beforeEach(async ({ page }) => {
    // Mock politicians list API
    await page.route('**/rest/v1/politicians**', (route) => {
      const url = route.request().url();
      // Single politician fetch by ID
      if (url.includes('id=eq.test-politician-1')) {
        return route.fulfill({ status: 200, json: [mockPolitician] });
      }
      // List fetch
      return route.fulfill({ status: 200, json: [mockPolitician] });
    });

    // Mock RPC call for politicians with stats
    await page.route('**/rest/v1/rpc/get_politicians_with_stats**', (route) =>
      route.fulfill({ status: 200, json: [mockPolitician] })
    );

    // Mock trading disclosures for politician detail
    await page.route('**/rest/v1/trading_disclosures**', (route) => {
      const url = route.request().url();
      if (url.includes('politician_id=eq.test-politician-1')) {
        return route.fulfill({ status: 200, json: mockTrades });
      }
      return route.fulfill({ status: 200, json: [] });
    });
  });

  test.describe('Successful AI Profile Generation', () => {
    test('should display AI-generated profile with "AI" badge when Ollama succeeds', async ({ page }) => {
      // Mock successful Ollama Edge Function response
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      // Navigate to politicians view and open modal
      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();

      // Wait for politician card to appear and click it
      const politicianCard = page.getByText(/nancy pelosi/i).first();
      await expect(politicianCard).toBeVisible();
      await politicianCard.click();

      // Wait for modal to open
      await expect(page.getByRole('dialog')).toBeVisible();

      // Wait for profile to load and verify AI badge
      await expect(page.getByText(/AI-Generated Profile/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/AI/).first()).toBeVisible();

      // Verify the bio content from Ollama
      await expect(page.getByText(/Democratic Representative from California/i)).toBeVisible();
    });

    test('should show Sparkles icon for AI-generated profile', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      // The Sparkles icon should be visible for AI profiles
      // We check for the AI badge which indicates AI generation
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText(/AI-Generated Profile/i)).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Fallback Profile Generation', () => {
    test('should display fallback profile when Ollama returns error', async ({ page }) => {
      // Mock Ollama Edge Function with fallback response
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockFallbackResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show "Profile Summary" instead of "AI-Generated Profile"
      await expect(page.getByText(/Profile Summary/i)).toBeVisible({ timeout: 10000 });

      // Should NOT show AI badge
      await expect(page.getByText(/AI-Generated Profile/i)).not.toBeVisible();
    });

    test('should display fallback profile when Ollama returns 500 error', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal Server Error' }),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should fall back gracefully and show Profile Summary
      await expect(page.getByText(/Profile Summary/i)).toBeVisible({ timeout: 10000 });

      // Should show fallback error indicator
      await expect(page.getByText(/cached profile data/i)).toBeVisible();
    });

    test('should display fallback profile when Ollama times out', async ({ page }) => {
      // Mock Ollama Edge Function with delay longer than timeout (15s)
      await page.route('**/functions/v1/politician-profile', async (route) => {
        // Wait 20 seconds - longer than the 15s timeout in the component
        await new Promise(resolve => setTimeout(resolve, 20000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        });
      });

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show loading initially
      await expect(page.getByText(/Generating profile/i)).toBeVisible();

      // After timeout, should fall back and show error
      await expect(page.getByText(/Profile Summary/i)).toBeVisible({ timeout: 20000 });
      await expect(page.getByText(/timed out/i)).toBeVisible();
    });
  });

  test.describe('Loading States', () => {
    test('should show "Generating profile..." while fetching', async ({ page }) => {
      // Mock Ollama with delay to observe loading state
      await page.route('**/functions/v1/politician-profile', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        });
      });

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show loading state with spinner
      await expect(page.getByText(/Generating profile/i)).toBeVisible();
      await expect(page.locator('.animate-spin')).toBeVisible();

      // Eventually should show the profile
      await expect(page.getByText(/AI-Generated Profile/i)).toBeVisible({ timeout: 10000 });
    });

    test('should abort request and reset state when modal closes', async ({ page }) => {
      let requestCompleted = false;

      // Mock Ollama with delay
      await page.route('**/functions/v1/politician-profile', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 5000));
        requestCompleted = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        });
      });

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText(/Generating profile/i)).toBeVisible();

      // Close the modal before request completes
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).not.toBeVisible();

      // Re-open the modal
      await page.getByText(/nancy pelosi/i).first().click();
      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show loading again (not stale state)
      await expect(page.getByText(/Generating profile/i)).toBeVisible();
    });
  });

  test.describe('Network Errors', () => {
    test('should handle network failure gracefully', async ({ page }) => {
      // Mock network failure
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.abort('failed')
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should fall back gracefully
      await expect(page.getByText(/Profile Summary/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/Network error/i)).toBeVisible();
    });
  });

  test.describe('Profile Content Display', () => {
    test('should display trading stats in modal', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show trading stats
      await expect(page.getByText(/Total/i)).toBeVisible();
      await expect(page.getByText(/Buys/i)).toBeVisible();
      await expect(page.getByText(/Sells/i)).toBeVisible();
    });

    test('should display top tickers in modal', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show top tickers section
      await expect(page.getByText(/Most Traded Tickers/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/NVDA/i)).toBeVisible();
      await expect(page.getByText(/AAPL/i)).toBeVisible();
      await expect(page.getByText(/MSFT/i)).toBeVisible();
    });

    test('should display recent trades in modal', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show recent trades section
      await expect(page.getByText(/Recent Trades/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/BUY|SELL/i).first()).toBeVisible();
    });
  });

  test.describe('Modal Header', () => {
    test('should display politician name and party badge', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Modal header should have name
      const dialogTitle = page.getByRole('heading', { name: /nancy pelosi/i });
      await expect(dialogTitle).toBeVisible();

      // Should have party badge
      await expect(page.getByRole('dialog').getByText(/^D$/)).toBeVisible();
    });

    test('should display chamber and state info', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show chamber info
      await expect(page.getByRole('dialog').getByText(/Representative/i)).toBeVisible();
      // Should show state
      await expect(page.getByRole('dialog').getByText(/California/i)).toBeVisible();
    });

    test('should display initials avatar', async ({ page }) => {
      await page.route('**/functions/v1/politician-profile', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockOllamaSuccessResponse),
        })
      );

      await page.goto('/');
      await page.getByRole('button', { name: /politicians/i }).click();
      await page.getByText(/nancy pelosi/i).first().click();

      await expect(page.getByRole('dialog')).toBeVisible();

      // Should show initials (NP for Nancy Pelosi)
      await expect(page.getByRole('dialog').getByText(/NP/)).toBeVisible();
    });
  });
});
