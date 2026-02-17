import { Page, Route } from '@playwright/test';

// ============================================================================
// Type Definitions
// ============================================================================

export interface AlpacaAccount {
  id: string;
  account_number: string;
  status: string;
  currency: string;
  buying_power: string;
  cash: string;
  portfolio_value: string;
  equity: string;
  last_equity: string;
  long_market_value: string;
  short_market_value: string;
  trading_blocked: boolean;
  transfers_blocked: boolean;
  account_blocked: boolean;
  pattern_day_trader: boolean;
  daytrade_count: number;
}

export interface AlpacaPosition {
  asset_id: string;
  symbol: string;
  exchange: string;
  asset_class: string;
  qty: string;
  avg_entry_price: string;
  side: string;
  market_value: string;
  cost_basis: string;
  unrealized_pl: string;
  unrealized_plpc: string;
  current_price: string;
  lastday_price: string;
  change_today: string;
}

export interface Order {
  id: string;
  alpaca_order_id: string;
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit' | 'stop' | 'stop_limit';
  limit_price?: number;
  status: 'pending' | 'filled' | 'canceled' | 'rejected';
  filled_qty?: number;
  filled_avg_price?: number;
  trading_mode: 'paper' | 'live';
  created_at: string;
  updated_at: string;
}

export interface Signal {
  ticker: string;
  signal_type: 'buy' | 'sell' | 'hold';
  strength: number;
  confidence: number;
  ml_enhanced: boolean;
  politician_count: number;
  buy_sell_ratio: number;
  reasons: string[];
}

export interface Politician {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  name: string;
  party: string;
  role: string;
  chamber: string;
  state_or_country: string | null;
  state: string | null;
  district: string | null;
  jurisdiction_id: string;
  avatar_url: string | null;
  total_trades: number;
  total_volume: number;
  is_active: boolean;
}

export interface TradingDisclosure {
  id: string;
  politician_id: string;
  asset_ticker: string;
  asset_name: string;
  transaction_type: string;
  transaction_date: string;
  disclosure_date: string;
  amount_range_min: number;
  amount_range_max: number;
  status: string;
  source_url: string | null;
}

export interface DashboardStats {
  id: string;
  total_trades: number;
  total_volume: number;
  active_politicians: number;
  average_trade_size: number;
  updated_at: string;
}

// ============================================================================
// Mock Data Factories
// ============================================================================

export function mockAlpacaAccount(overrides?: Partial<AlpacaAccount>): AlpacaAccount {
  return {
    id: 'test-account-id',
    account_number: '123456789',
    status: 'ACTIVE',
    currency: 'USD',
    buying_power: '50000.00',
    cash: '25000.00',
    portfolio_value: '75000.00',
    equity: '75000.00',
    last_equity: '74500.00',
    long_market_value: '50000.00',
    short_market_value: '0.00',
    trading_blocked: false,
    transfers_blocked: false,
    account_blocked: false,
    pattern_day_trader: false,
    daytrade_count: 0,
    ...overrides,
  };
}

export function mockPosition(ticker: string, overrides?: Partial<AlpacaPosition>): AlpacaPosition {
  return {
    asset_id: `asset-${ticker.toLowerCase()}`,
    symbol: ticker,
    exchange: 'NASDAQ',
    asset_class: 'us_equity',
    qty: '10',
    avg_entry_price: '150.00',
    side: 'long',
    market_value: '1550.00',
    cost_basis: '1500.00',
    unrealized_pl: '50.00',
    unrealized_plpc: '0.0333',
    current_price: '155.00',
    lastday_price: '152.00',
    change_today: '0.0197',
    ...overrides,
  };
}

export function mockOrder(overrides?: Partial<Order>): Order {
  return {
    id: `order-${Date.now()}`,
    alpaca_order_id: `alpaca-${Date.now()}`,
    ticker: 'AAPL',
    side: 'buy',
    quantity: 10,
    order_type: 'market',
    status: 'filled',
    filled_qty: 10,
    filled_avg_price: 150.0,
    trading_mode: 'paper',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

export function mockSignal(ticker: string, overrides?: Partial<Signal>): Signal {
  return {
    ticker,
    signal_type: 'buy',
    strength: 0.75,
    confidence: 0.85,
    ml_enhanced: true,
    politician_count: 5,
    buy_sell_ratio: 3.5,
    reasons: ['High bipartisan activity', 'ML confidence boost'],
    ...overrides,
  };
}

export function mockPolitician(overrides?: Partial<Politician>): Politician {
  const firstName = overrides?.first_name || 'John';
  const lastName = overrides?.last_name || 'Doe';
  return {
    id: `pol-${Date.now()}`,
    first_name: firstName,
    last_name: lastName,
    full_name: `${firstName} ${lastName}`,
    name: `${firstName} ${lastName}`,
    party: 'D',
    role: 'Representative',
    chamber: 'Representative',
    state_or_country: 'California',
    state: 'California',
    district: 'CA-01',
    jurisdiction_id: 'us-congress',
    avatar_url: null,
    total_trades: 50,
    total_volume: 5000000,
    is_active: true,
    ...overrides,
  };
}

export function mockTrade(overrides?: Partial<TradingDisclosure>): TradingDisclosure {
  return {
    id: `trade-${Date.now()}`,
    politician_id: 'pol-1',
    asset_ticker: 'NVDA',
    asset_name: 'NVIDIA Corporation',
    transaction_type: 'purchase',
    transaction_date: new Date().toISOString().split('T')[0],
    disclosure_date: new Date().toISOString().split('T')[0],
    amount_range_min: 15001,
    amount_range_max: 50000,
    status: 'active',
    source_url: 'https://example.com/filing',
    ...overrides,
  };
}

export function mockDashboardStats(overrides?: Partial<DashboardStats>): DashboardStats {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    total_trades: 15420,
    total_volume: 2500000000,
    active_politicians: 535,
    average_trade_size: 162000,
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

// ============================================================================
// Route Setup Helpers
// ============================================================================

export interface AlpacaMockOptions {
  account?: AlpacaAccount | null;
  positions?: AlpacaPosition[];
  connectionStatus?: 'healthy' | 'degraded' | 'error';
  accountError?: string;
}

/**
 * Setup Alpaca edge function mocks
 */
export async function setupAlpacaMocks(page: Page, options: AlpacaMockOptions = {}) {
  const {
    account = mockAlpacaAccount(),
    positions = [mockPosition('AAPL'), mockPosition('NVDA')],
    connectionStatus = 'healthy',
    accountError,
  } = options;

  await page.route('**/functions/v1/alpaca-account**', async (route) => {
    const url = route.request().url();
    const body = await route.request().postData();
    const action = body ? JSON.parse(body).action : null;

    if (action === 'get-account' || url.includes('action=get-account')) {
      if (accountError) {
        return route.fulfill({
          status: 400,
          json: { success: false, error: accountError },
        });
      }
      return route.fulfill({
        status: 200,
        json: { success: true, account, tradingMode: 'paper' },
      });
    }

    if (action === 'get-positions' || url.includes('action=get-positions')) {
      return route.fulfill({
        status: 200,
        json: { success: true, positions },
      });
    }

    if (action === 'test-connection' || url.includes('action=test-connection')) {
      return route.fulfill({
        status: 200,
        json: { success: true, account },
      });
    }

    if (action === 'connection-status' || url.includes('action=connection-status')) {
      return route.fulfill({
        status: 200,
        json: { status: connectionStatus },
      });
    }

    return route.fulfill({ status: 200, json: {} });
  });
}

export interface OrdersMockOptions {
  orders?: Order[];
  placeOrderResult?: { success: boolean; order?: Order; error?: string };
}

/**
 * Setup Orders edge function mocks
 */
export async function setupOrdersMocks(page: Page, options: OrdersMockOptions = {}) {
  const {
    orders = [mockOrder(), mockOrder({ ticker: 'NVDA', side: 'sell' })],
    placeOrderResult = { success: true, order: mockOrder() },
  } = options;

  await page.route('**/functions/v1/orders**', async (route) => {
    const body = await route.request().postData();
    const action = body ? JSON.parse(body).action : null;

    if (action === 'get-orders') {
      return route.fulfill({
        status: 200,
        json: { success: true, orders, total: orders.length, limit: 50, offset: 0 },
      });
    }

    if (action === 'place-order') {
      return route.fulfill({
        status: 200,
        json: placeOrderResult,
      });
    }

    if (action === 'sync-orders') {
      return route.fulfill({
        status: 200,
        json: { success: true, message: 'Synced', summary: { total: 10, synced: 2, updated: 1, errors: 0 } },
      });
    }

    return route.fulfill({ status: 200, json: {} });
  });
}

export interface SignalsMockOptions {
  signals?: Signal[];
  lambdaError?: string;
}

/**
 * Setup Trading Signals edge function mocks
 */
export async function setupSignalsMocks(page: Page, options: SignalsMockOptions = {}) {
  const {
    signals = [mockSignal('NVDA'), mockSignal('AAPL'), mockSignal('MSFT', { signal_type: 'sell', strength: -0.6 })],
    lambdaError,
  } = options;

  await page.route('**/functions/v1/trading-signals/preview-signals**', (route) => {
    if (lambdaError) {
      return route.fulfill({
        status: 200,
        json: { signals: [], lambdaError, lambdaApplied: false },
      });
    }
    return route.fulfill({
      status: 200,
      json: { signals, stats: { mlEnhancedCount: signals.filter(s => s.ml_enhanced).length }, lambdaApplied: false },
    });
  });
}

/**
 * Setup Dashboard data mocks (Supabase REST)
 */
export async function setupDashboardMocks(page: Page, options: {
  stats?: DashboardStats;
  politicians?: Politician[];
  trades?: TradingDisclosure[];
} = {}) {
  const {
    stats = mockDashboardStats(),
    politicians = [
      mockPolitician({ id: '1', first_name: 'Nancy', last_name: 'Pelosi', party: 'D' }),
      mockPolitician({ id: '2', first_name: 'Dan', last_name: 'Crenshaw', party: 'R' }),
    ],
    trades = [mockTrade(), mockTrade({ asset_ticker: 'AAPL', transaction_type: 'sale' })],
  } = options;

  // Dashboard stats
  await page.route('**/rest/v1/dashboard_stats**', (route) =>
    route.fulfill({ status: 200, json: stats })
  );

  // Politicians list
  await page.route('**/rest/v1/politicians**', (route) =>
    route.fulfill({ status: 200, json: politicians })
  );

  // Politicians RPC
  await page.route('**/rest/v1/rpc/get_politicians_with_stats**', (route) =>
    route.fulfill({ status: 200, json: politicians })
  );

  // Trading disclosures
  await page.route('**/rest/v1/trading_disclosures**', (route) =>
    route.fulfill({ status: 200, json: trades })
  );

  // Top tickers
  await page.route('**/rest/v1/top_tickers**', (route) =>
    route.fulfill({
      status: 200,
      json: [
        { ticker: 'NVDA', name: 'NVIDIA Corporation', trade_count: 150, total_volume: 50000000 },
        { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 120, total_volume: 45000000 },
      ],
    })
  );

  // Chart data
  await page.route('**/rest/v1/chart_data**', (route) =>
    route.fulfill({
      status: 200,
      json: [
        { month: 1, year: 2024, buys: 150, sells: 80, volume: 25000000 },
        { month: 2, year: 2024, buys: 180, sells: 90, volume: 30000000 },
      ],
    })
  );
}

/**
 * Setup Ollama profile generation mock
 */
export async function setupProfileMock(page: Page, options: {
  bio?: string;
  source?: 'ollama' | 'fallback';
  delay?: number;
  error?: boolean;
} = {}) {
  const { bio, source = 'ollama', delay = 0, error = false } = options;

  await page.route('**/functions/v1/politician-profile**', async (route) => {
    if (delay > 0) {
      await new Promise(resolve => setTimeout(resolve, delay));
    }

    if (error) {
      return route.fulfill({
        status: 500,
        json: { error: 'Internal Server Error' },
      });
    }

    const body = await route.request().postData();
    const { politician } = JSON.parse(body || '{}');

    return route.fulfill({
      status: 200,
      json: {
        bio: bio || `${politician?.name || 'This politician'} is a ${politician?.party === 'D' ? 'Democratic' : 'Republican'} ${politician?.chamber || 'Member of Congress'}.`,
        source,
      },
    });
  });
}

// ============================================================================
// Authentication Helpers
// ============================================================================

export interface MockUser {
  id: string;
  email: string;
  isAdmin?: boolean;
}

/**
 * Mock authenticated session
 */
export async function mockAuthSession(page: Page, user: MockUser) {
  // Set localStorage for Supabase auth
  await page.addInitScript((userData) => {
    const session = {
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      expires_at: Date.now() + 3600000,
      user: {
        id: userData.id,
        email: userData.email,
        user_metadata: { is_admin: userData.isAdmin || false },
      },
    };
    localStorage.setItem('sb-uljsqvwkomdrlnofmlad-auth-token', JSON.stringify(session));
  }, user);

  // Mock admin role check if needed
  if (user.isAdmin) {
    await page.route('**/rest/v1/rpc/has_role**', (route) =>
      route.fulfill({ status: 200, json: true })
    );
  }
}

/**
 * Setup mocks for unauthenticated state
 */
export async function mockUnauthenticatedState(page: Page) {
  await page.addInitScript(() => {
    localStorage.removeItem('sb-uljsqvwkomdrlnofmlad-auth-token');
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Wait for API call and verify it was made with expected parameters
 */
export async function waitForApiCall(
  page: Page,
  urlPattern: string | RegExp,
  options: { timeout?: number; method?: string } = {}
): Promise<{ url: string; body: unknown }> {
  const { timeout = 5000, method } = options;

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`API call to ${urlPattern} not made within ${timeout}ms`)), timeout);

    page.on('request', (request) => {
      const url = request.url();
      const matches = typeof urlPattern === 'string' ? url.includes(urlPattern) : urlPattern.test(url);

      if (matches && (!method || request.method() === method)) {
        clearTimeout(timer);
        resolve({
          url,
          body: request.postData() ? JSON.parse(request.postData()!) : null,
        });
      }
    });
  });
}

/**
 * Create a delayed response mock for testing loading states
 */
export function withDelay<T>(response: T, delayMs: number): (route: Route) => Promise<void> {
  return async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.fulfill({ status: 200, json: response as unknown as Record<string, unknown> });
  };
}

/**
 * Create an error response mock
 */
export function withError(statusCode: number, message: string): (route: Route) => Promise<void> {
  return async (route: Route) => {
    await route.fulfill({
      status: statusCode,
      json: { error: message },
    });
  };
}

// ============================================================================
// Party Mock Data & Helpers
// ============================================================================

export interface Party {
  id: string;
  code: string;
  name: string;
  short_name: string | null;
  jurisdiction: string;
  color: string;
}

export function mockParty(overrides?: Partial<Party>): Party {
  return {
    id: `party-${Date.now()}`,
    code: 'D',
    name: 'Democratic Party',
    short_name: 'D',
    jurisdiction: 'us',
    color: '#0000FF',
    ...overrides,
  };
}

/**
 * Setup parties REST API mock
 */
export async function setupPartiesMock(page: Page, parties?: Party[]) {
  const data = parties ?? [
    mockParty({ id: 'p-1', code: 'D', name: 'Democratic Party', short_name: 'D', jurisdiction: 'us', color: '#0000FF' }),
    mockParty({ id: 'p-2', code: 'R', name: 'Republican Party', short_name: 'R', jurisdiction: 'us', color: '#FF0000' }),
    mockParty({ id: 'p-3', code: 'I', name: 'Independent', short_name: 'I', jurisdiction: 'us', color: '#808080' }),
  ];

  await page.route('**/rest/v1/parties**', (route) =>
    route.fulfill({ status: 200, json: data })
  );
}

// ============================================================================
// Showcase / Strategy Mock Data & Helpers
// ============================================================================

export interface ShowcaseStrategy {
  id: string;
  name: string;
  description: string;
  user_id: string | null;
  is_public: boolean;
  likes_count: number;
  user_has_liked: boolean;
  weights: Record<string, number>;
  created_at: string;
  profiles: { display_name: string } | null;
}

export function mockShowcaseStrategy(overrides?: Partial<ShowcaseStrategy>): ShowcaseStrategy {
  return {
    id: `strat-${Date.now()}`,
    name: 'Test Strategy',
    description: 'A test strategy',
    user_id: 'user-1',
    is_public: true,
    likes_count: 10,
    user_has_liked: false,
    weights: { baseConfidence: 0.7, bipartisanBonus: 0.3 },
    created_at: new Date().toISOString(),
    profiles: { display_name: 'TestUser' },
    ...overrides,
  };
}

/**
 * Setup showcase RPC mock (get_public_strategies)
 */
export async function setupShowcaseMocks(page: Page, strategies?: ShowcaseStrategy[]) {
  const data = strategies ?? [
    mockShowcaseStrategy({ id: 's-1', name: 'Conservative Growth', likes_count: 42 }),
    mockShowcaseStrategy({ id: 's-2', name: 'Momentum Chaser', likes_count: 28, user_has_liked: true }),
  ];

  await page.route('**/rest/v1/rpc/get_public_strategies**', (route) =>
    route.fulfill({ status: 200, json: data })
  );

  // Mock strategy_likes for like/unlike mutations
  await page.route('**/rest/v1/strategy_likes**', (route) =>
    route.fulfill({ status: 200, json: {} })
  );
}

// ============================================================================
// Admin Role RPC Helper
// ============================================================================

/**
 * Setup admin role check via has_role RPC (the actual endpoint useAdmin calls)
 */
export async function setupAdminRoleMock(page: Page, isAdmin: boolean) {
  await page.route('**/rest/v1/rpc/has_role**', (route) =>
    route.fulfill({ status: 200, json: isAdmin })
  );
}

// ============================================================================
// Wallet Auth Edge Function Helpers
// ============================================================================

export interface WalletAuthMockOptions {
  nonceMessage?: string;
  nonceError?: string;
  verifyToken?: string;
  verifyIsNewUser?: boolean;
  verifyUserId?: string;
  verifyError?: string;
}

/**
 * Setup wallet-auth edge function mocks (nonce + verify)
 */
export async function setupWalletAuthMocks(page: Page, options: WalletAuthMockOptions = {}) {
  const {
    nonceMessage = 'Sign this message to authenticate: nonce-abc123',
    nonceError,
    verifyToken = 'magic-link-token-xyz',
    verifyIsNewUser = false,
    verifyUserId = 'wallet-user-1',
    verifyError,
  } = options;

  await page.route('**/functions/v1/wallet-auth**', async (route) => {
    const url = route.request().url();

    if (url.includes('action=nonce')) {
      if (nonceError) {
        return route.fulfill({
          status: 400,
          json: { error: nonceError },
        });
      }
      return route.fulfill({
        status: 200,
        json: { message: nonceMessage },
      });
    }

    if (url.includes('action=verify')) {
      if (verifyError) {
        return route.fulfill({
          status: 400,
          json: { error: verifyError },
        });
      }
      return route.fulfill({
        status: 200,
        json: {
          token: verifyToken,
          isNewUser: verifyIsNewUser,
          userId: verifyUserId,
        },
      });
    }

    return route.fulfill({ status: 200, json: {} });
  });
}
