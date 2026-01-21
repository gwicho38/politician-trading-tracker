/**
 * Tests for sync-data Edge Function
 *
 * Tests:
 * - ETL endpoint routing
 * - Batch processing
 * - Party resolution
 * - Stats aggregation
 */

import { assertEquals, assertStringIncludes } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Endpoint routing
function determineEndpoint(path: string): string {
  const validEndpoints = [
    'sync-full',
    'sync-house',
    'sync-senate',
    'sync-quiver',
    'update-chart-data',
    'update-stats',
    'update-politician-parties',
  ];

  if (validEndpoints.includes(path)) return path;
  return 'unknown';
}

// Batch processing
function createBatches<T>(items: T[], batchSize: number): T[][] {
  const batches: T[][] = [];
  for (let i = 0; i < items.length; i += batchSize) {
    batches.push(items.slice(i, i + batchSize));
  }
  return batches;
}

// Party code normalization
function normalizePartyCode(party: string | null): 'D' | 'R' | 'I' | null {
  if (!party) return null;

  const normalized = party.toUpperCase().trim();

  if (normalized === 'D' || normalized === 'DEMOCRAT' || normalized === 'DEMOCRATIC') {
    return 'D';
  }
  if (normalized === 'R' || normalized === 'REPUBLICAN') {
    return 'R';
  }
  if (normalized === 'I' || normalized === 'INDEPENDENT' || normalized === 'IND') {
    return 'I';
  }

  return null;
}

// Chamber normalization
function normalizeChamber(chamber: string | null): 'House' | 'Senate' | null {
  if (!chamber) return null;

  const normalized = chamber.toLowerCase().trim();

  if (normalized.includes('house') || normalized.includes('rep')) {
    return 'House';
  }
  if (normalized.includes('senate') || normalized.includes('sen')) {
    return 'Senate';
  }

  return null;
}

// Stats calculation
interface TradeStats {
  totalTrades: number;
  totalVolume: number;
  uniqueTickers: number;
  buyCount: number;
  sellCount: number;
}

function calculateTradeStats(trades: Array<{
  ticker: string;
  type: 'purchase' | 'sale';
  volume?: number;
}>): TradeStats {
  const tickers = new Set<string>();
  let totalVolume = 0;
  let buyCount = 0;
  let sellCount = 0;

  for (const trade of trades) {
    tickers.add(trade.ticker.toUpperCase());
    totalVolume += trade.volume || 0;

    if (trade.type === 'purchase') {
      buyCount++;
    } else {
      sellCount++;
    }
  }

  return {
    totalTrades: trades.length,
    totalVolume,
    uniqueTickers: tickers.size,
    buyCount,
    sellCount,
  };
}

// Sync result formatting
interface SyncResult {
  endpoint: string;
  success: boolean;
  recordsProcessed: number;
  recordsInserted: number;
  recordsUpdated: number;
  errors: number;
  duration: number;
}

function formatSyncResult(result: SyncResult): string {
  if (!result.success) {
    return `${result.endpoint}: FAILED (${result.errors} errors) in ${result.duration}ms`;
  }
  return `${result.endpoint}: ${result.recordsProcessed} processed (${result.recordsInserted} new, ${result.recordsUpdated} updated) in ${result.duration}ms`;
}

// Tests

Deno.test("determineEndpoint() - valid endpoints", () => {
  assertEquals(determineEndpoint('sync-full'), 'sync-full');
  assertEquals(determineEndpoint('sync-house'), 'sync-house');
  assertEquals(determineEndpoint('sync-senate'), 'sync-senate');
  assertEquals(determineEndpoint('sync-quiver'), 'sync-quiver');
  assertEquals(determineEndpoint('update-chart-data'), 'update-chart-data');
  assertEquals(determineEndpoint('update-stats'), 'update-stats');
  assertEquals(determineEndpoint('update-politician-parties'), 'update-politician-parties');
});

Deno.test("determineEndpoint() - invalid endpoint", () => {
  assertEquals(determineEndpoint('invalid'), 'unknown');
  assertEquals(determineEndpoint(''), 'unknown');
});

Deno.test("createBatches() - exact divisions", () => {
  const items = [1, 2, 3, 4, 5, 6];
  const batches = createBatches(items, 2);

  assertEquals(batches.length, 3);
  assertEquals(batches[0], [1, 2]);
  assertEquals(batches[1], [3, 4]);
  assertEquals(batches[2], [5, 6]);
});

Deno.test("createBatches() - uneven divisions", () => {
  const items = [1, 2, 3, 4, 5];
  const batches = createBatches(items, 2);

  assertEquals(batches.length, 3);
  assertEquals(batches[2], [5]);
});

Deno.test("createBatches() - single batch", () => {
  const items = [1, 2, 3];
  const batches = createBatches(items, 10);

  assertEquals(batches.length, 1);
  assertEquals(batches[0], [1, 2, 3]);
});

Deno.test("createBatches() - empty array", () => {
  const batches = createBatches([], 5);
  assertEquals(batches.length, 0);
});

Deno.test("normalizePartyCode() - Democrat variations", () => {
  assertEquals(normalizePartyCode('D'), 'D');
  assertEquals(normalizePartyCode('Democrat'), 'D');
  assertEquals(normalizePartyCode('DEMOCRATIC'), 'D');
  assertEquals(normalizePartyCode('d'), 'D');
});

Deno.test("normalizePartyCode() - Republican variations", () => {
  assertEquals(normalizePartyCode('R'), 'R');
  assertEquals(normalizePartyCode('Republican'), 'R');
  assertEquals(normalizePartyCode('REPUBLICAN'), 'R');
  assertEquals(normalizePartyCode('r'), 'R');
});

Deno.test("normalizePartyCode() - Independent variations", () => {
  assertEquals(normalizePartyCode('I'), 'I');
  assertEquals(normalizePartyCode('Independent'), 'I');
  assertEquals(normalizePartyCode('IND'), 'I');
});

Deno.test("normalizePartyCode() - null/unknown", () => {
  assertEquals(normalizePartyCode(null), null);
  assertEquals(normalizePartyCode(''), null);
  assertEquals(normalizePartyCode('Libertarian'), null);
});

Deno.test("normalizeChamber() - House variations", () => {
  assertEquals(normalizeChamber('House'), 'House');
  assertEquals(normalizeChamber('HOUSE'), 'House');
  assertEquals(normalizeChamber('Representative'), 'House');
  assertEquals(normalizeChamber('rep'), 'House');
});

Deno.test("normalizeChamber() - Senate variations", () => {
  assertEquals(normalizeChamber('Senate'), 'Senate');
  assertEquals(normalizeChamber('SENATE'), 'Senate');
  assertEquals(normalizeChamber('Senator'), 'Senate');
  assertEquals(normalizeChamber('sen'), 'Senate');
});

Deno.test("normalizeChamber() - null/unknown", () => {
  assertEquals(normalizeChamber(null), null);
  assertEquals(normalizeChamber(''), null);
});

Deno.test("calculateTradeStats() - basic calculation", () => {
  const trades = [
    { ticker: 'AAPL', type: 'purchase' as const, volume: 10000 },
    { ticker: 'TSLA', type: 'sale' as const, volume: 5000 },
    { ticker: 'AAPL', type: 'purchase' as const, volume: 15000 },
  ];

  const stats = calculateTradeStats(trades);

  assertEquals(stats.totalTrades, 3);
  assertEquals(stats.totalVolume, 30000);
  assertEquals(stats.uniqueTickers, 2);
  assertEquals(stats.buyCount, 2);
  assertEquals(stats.sellCount, 1);
});

Deno.test("calculateTradeStats() - empty trades", () => {
  const stats = calculateTradeStats([]);

  assertEquals(stats.totalTrades, 0);
  assertEquals(stats.totalVolume, 0);
  assertEquals(stats.uniqueTickers, 0);
});

Deno.test("calculateTradeStats() - handles missing volume", () => {
  const trades = [
    { ticker: 'AAPL', type: 'purchase' as const },
    { ticker: 'TSLA', type: 'sale' as const, volume: 5000 },
  ];

  const stats = calculateTradeStats(trades);

  assertEquals(stats.totalVolume, 5000);
});

Deno.test("formatSyncResult() - success", () => {
  const result: SyncResult = {
    endpoint: 'sync-house',
    success: true,
    recordsProcessed: 100,
    recordsInserted: 80,
    recordsUpdated: 20,
    errors: 0,
    duration: 1500,
  };

  const formatted = formatSyncResult(result);

  assertStringIncludes(formatted, 'sync-house');
  assertStringIncludes(formatted, '100 processed');
  assertStringIncludes(formatted, '80 new');
  assertStringIncludes(formatted, '20 updated');
  assertStringIncludes(formatted, '1500ms');
});

Deno.test("formatSyncResult() - failure", () => {
  const result: SyncResult = {
    endpoint: 'sync-senate',
    success: false,
    recordsProcessed: 50,
    recordsInserted: 0,
    recordsUpdated: 0,
    errors: 5,
    duration: 500,
  };

  const formatted = formatSyncResult(result);

  assertStringIncludes(formatted, 'sync-senate');
  assertStringIncludes(formatted, 'FAILED');
  assertStringIncludes(formatted, '5 errors');
});

// Date range helpers
function isWithinDays(date: Date, days: number): boolean {
  const now = new Date();
  const threshold = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  return date >= threshold;
}

Deno.test("isWithinDays() - within range", () => {
  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
  assertEquals(isWithinDays(yesterday, 7), true);
});

Deno.test("isWithinDays() - outside range", () => {
  const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
  assertEquals(isWithinDays(twoWeeksAgo, 7), false);
});

Deno.test("isWithinDays() - boundary", () => {
  const exactlySevenDays = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  assertEquals(isWithinDays(exactlySevenDays, 7), true);
});

// Volume aggregation
function aggregateVolumeByTicker(trades: Array<{ ticker: string; volume: number }>): Map<string, number> {
  const volumeMap = new Map<string, number>();

  for (const trade of trades) {
    const currentVolume = volumeMap.get(trade.ticker) || 0;
    volumeMap.set(trade.ticker, currentVolume + trade.volume);
  }

  return volumeMap;
}

Deno.test("aggregateVolumeByTicker() - aggregates correctly", () => {
  const trades = [
    { ticker: 'AAPL', volume: 100 },
    { ticker: 'TSLA', volume: 200 },
    { ticker: 'AAPL', volume: 150 },
  ];

  const result = aggregateVolumeByTicker(trades);

  assertEquals(result.get('AAPL'), 250);
  assertEquals(result.get('TSLA'), 200);
});

Deno.test("aggregateVolumeByTicker() - empty trades", () => {
  const result = aggregateVolumeByTicker([]);
  assertEquals(result.size, 0);
});
