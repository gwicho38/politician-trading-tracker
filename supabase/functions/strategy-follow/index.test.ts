/**
 * Tests for strategy-follow Edge Function
 *
 * Tests:
 * - Strategy following logic
 * - Allocation calculations
 * - Sync operations
 * - Position mirroring
 */

import { assertEquals, assertAlmostEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Action determination
function determineAction(path: string, bodyAction?: string): string {
  const validActions = [
    'get-following',
    'follow',
    'unfollow',
    'sync-all-active',
    'sync-follower',
    'get-allocations',
  ];

  const action = bodyAction || path;

  if (validActions.includes(action)) return action;
  return 'unknown';
}

// Allocation calculation
function calculateTargetAllocation(
  followerBuyingPower: number,
  allocationPct: number
): number {
  return followerBuyingPower * (allocationPct / 100);
}

function calculateMirrorQuantity(
  sourceQuantity: number,
  sourceTotalValue: number,
  followerAllocation: number,
  sharePrice: number
): number {
  // Calculate the proportion of source position
  const sourcePct = (sourceQuantity * sharePrice) / sourceTotalValue;
  // Apply same proportion to follower allocation
  const targetValue = followerAllocation * sourcePct;
  // Convert to quantity
  return Math.floor(targetValue / sharePrice);
}

// Sync status
interface SyncResult {
  followerId: string;
  positionsSynced: number;
  ordersPlaced: number;
  errors: string[];
}

function isSyncSuccessful(result: SyncResult): boolean {
  return result.errors.length === 0;
}

function formatSyncSummary(results: SyncResult[]): {
  total: number;
  successful: number;
  failed: number;
  totalOrders: number;
} {
  return {
    total: results.length,
    successful: results.filter(r => r.errors.length === 0).length,
    failed: results.filter(r => r.errors.length > 0).length,
    totalOrders: results.reduce((sum, r) => sum + r.ordersPlaced, 0),
  };
}

// Following validation
function canFollow(
  followerId: string,
  targetId: string,
  maxFollowing: number,
  currentFollowing: number
): { allowed: boolean; reason?: string } {
  if (followerId === targetId) {
    return { allowed: false, reason: 'Cannot follow yourself' };
  }

  if (currentFollowing >= maxFollowing) {
    return { allowed: false, reason: `Maximum following limit (${maxFollowing}) reached` };
  }

  return { allowed: true };
}

// Position difference detection
interface PositionDiff {
  ticker: string;
  action: 'buy' | 'sell' | 'adjust';
  quantityDiff: number;
}

function calculatePositionDiffs(
  sourcePositions: Array<{ ticker: string; quantity: number }>,
  followerPositions: Array<{ ticker: string; quantity: number }>,
  scaleFactor: number
): PositionDiff[] {
  const diffs: PositionDiff[] = [];

  const sourceMap = new Map(sourcePositions.map(p => [p.ticker, p.quantity]));
  const followerMap = new Map(followerPositions.map(p => [p.ticker, p.quantity]));

  // Check source positions
  for (const [ticker, sourceQty] of sourceMap) {
    const targetQty = Math.floor(sourceQty * scaleFactor);
    const followerQty = followerMap.get(ticker) || 0;
    const diff = targetQty - followerQty;

    if (diff > 0) {
      diffs.push({ ticker, action: 'buy', quantityDiff: diff });
    } else if (diff < 0) {
      diffs.push({ ticker, action: 'sell', quantityDiff: Math.abs(diff) });
    }
  }

  // Check follower positions not in source (should be sold)
  for (const [ticker, followerQty] of followerMap) {
    if (!sourceMap.has(ticker) && followerQty > 0) {
      diffs.push({ ticker, action: 'sell', quantityDiff: followerQty });
    }
  }

  return diffs;
}

// Market hours check
function isMarketOpen(now: Date): boolean {
  const day = now.getUTCDay();

  // Weekend
  if (day === 0 || day === 6) return false;

  const hour = now.getUTCHours();
  const minute = now.getUTCMinutes();
  const timeInMinutes = hour * 60 + minute;

  // Market hours: 9:30 AM - 4:00 PM ET
  // In UTC: 14:30 - 21:00 (during EDT)
  const marketOpen = 14 * 60 + 30; // 14:30 UTC
  const marketClose = 21 * 60; // 21:00 UTC

  return timeInMinutes >= marketOpen && timeInMinutes < marketClose;
}

// Tests

Deno.test("determineAction() - valid actions", () => {
  assertEquals(determineAction('get-following'), 'get-following');
  assertEquals(determineAction('follow'), 'follow');
  assertEquals(determineAction('unfollow'), 'unfollow');
  assertEquals(determineAction('sync-all-active'), 'sync-all-active');
  assertEquals(determineAction('sync-follower'), 'sync-follower');
  assertEquals(determineAction('get-allocations'), 'get-allocations');
});

Deno.test("determineAction() - body action overrides path", () => {
  assertEquals(determineAction('invalid', 'follow'), 'follow');
});

Deno.test("determineAction() - unknown action", () => {
  assertEquals(determineAction('invalid'), 'unknown');
  assertEquals(determineAction(''), 'unknown');
});

Deno.test("calculateTargetAllocation() - 50% allocation", () => {
  const allocation = calculateTargetAllocation(100000, 50);
  assertEquals(allocation, 50000);
});

Deno.test("calculateTargetAllocation() - 100% allocation", () => {
  const allocation = calculateTargetAllocation(50000, 100);
  assertEquals(allocation, 50000);
});

Deno.test("calculateTargetAllocation() - 10% allocation", () => {
  const allocation = calculateTargetAllocation(100000, 10);
  assertEquals(allocation, 10000);
});

Deno.test("calculateMirrorQuantity() - proportional mirroring", () => {
  // Source has 10 shares at $100 = $1000 of $10000 total (10%)
  // Follower allocation is $5000
  // Should get $500 worth = 5 shares
  const qty = calculateMirrorQuantity(10, 10000, 5000, 100);
  assertEquals(qty, 5);
});

Deno.test("calculateMirrorQuantity() - rounds down", () => {
  // 7.5 shares should become 7
  const qty = calculateMirrorQuantity(10, 10000, 7500, 100);
  assertEquals(qty, 7);
});

Deno.test("isSyncSuccessful() - no errors", () => {
  const result: SyncResult = {
    followerId: 'user-1',
    positionsSynced: 5,
    ordersPlaced: 3,
    errors: [],
  };
  assertEquals(isSyncSuccessful(result), true);
});

Deno.test("isSyncSuccessful() - with errors", () => {
  const result: SyncResult = {
    followerId: 'user-1',
    positionsSynced: 3,
    ordersPlaced: 2,
    errors: ['Order failed'],
  };
  assertEquals(isSyncSuccessful(result), false);
});

Deno.test("formatSyncSummary() - all successful", () => {
  const results: SyncResult[] = [
    { followerId: 'user-1', positionsSynced: 5, ordersPlaced: 3, errors: [] },
    { followerId: 'user-2', positionsSynced: 3, ordersPlaced: 2, errors: [] },
  ];

  const summary = formatSyncSummary(results);

  assertEquals(summary.total, 2);
  assertEquals(summary.successful, 2);
  assertEquals(summary.failed, 0);
  assertEquals(summary.totalOrders, 5);
});

Deno.test("formatSyncSummary() - mixed results", () => {
  const results: SyncResult[] = [
    { followerId: 'user-1', positionsSynced: 5, ordersPlaced: 3, errors: [] },
    { followerId: 'user-2', positionsSynced: 0, ordersPlaced: 0, errors: ['Failed'] },
  ];

  const summary = formatSyncSummary(results);

  assertEquals(summary.total, 2);
  assertEquals(summary.successful, 1);
  assertEquals(summary.failed, 1);
  assertEquals(summary.totalOrders, 3);
});

Deno.test("canFollow() - allowed", () => {
  const result = canFollow('user-1', 'user-2', 5, 2);
  assertEquals(result.allowed, true);
});

Deno.test("canFollow() - cannot follow self", () => {
  const result = canFollow('user-1', 'user-1', 5, 0);
  assertEquals(result.allowed, false);
  assertEquals(result.reason, 'Cannot follow yourself');
});

Deno.test("canFollow() - at limit", () => {
  const result = canFollow('user-1', 'user-2', 5, 5);
  assertEquals(result.allowed, false);
  assertEquals(result.reason?.includes('limit'), true);
});

Deno.test("calculatePositionDiffs() - new position needed", () => {
  const source = [{ ticker: 'AAPL', quantity: 10 }];
  const follower: Array<{ ticker: string; quantity: number }> = [];

  const diffs = calculatePositionDiffs(source, follower, 0.5);

  assertEquals(diffs.length, 1);
  assertEquals(diffs[0].ticker, 'AAPL');
  assertEquals(diffs[0].action, 'buy');
  assertEquals(diffs[0].quantityDiff, 5);
});

Deno.test("calculatePositionDiffs() - position to close", () => {
  const source: Array<{ ticker: string; quantity: number }> = [];
  const follower = [{ ticker: 'TSLA', quantity: 5 }];

  const diffs = calculatePositionDiffs(source, follower, 1);

  assertEquals(diffs.length, 1);
  assertEquals(diffs[0].ticker, 'TSLA');
  assertEquals(diffs[0].action, 'sell');
  assertEquals(diffs[0].quantityDiff, 5);
});

Deno.test("calculatePositionDiffs() - position adjustment", () => {
  const source = [{ ticker: 'AAPL', quantity: 20 }];
  const follower = [{ ticker: 'AAPL', quantity: 5 }];

  const diffs = calculatePositionDiffs(source, follower, 0.5);

  assertEquals(diffs.length, 1);
  assertEquals(diffs[0].ticker, 'AAPL');
  assertEquals(diffs[0].action, 'buy');
  assertEquals(diffs[0].quantityDiff, 5); // Need 10, have 5
});

Deno.test("calculatePositionDiffs() - no changes needed", () => {
  const source = [{ ticker: 'AAPL', quantity: 10 }];
  const follower = [{ ticker: 'AAPL', quantity: 5 }];

  const diffs = calculatePositionDiffs(source, follower, 0.5);

  assertEquals(diffs.length, 0); // 10 * 0.5 = 5, already have 5
});

Deno.test("isMarketOpen() - weekday during hours", () => {
  // Wednesday 15:00 UTC (10:00 AM ET)
  const date = new Date('2024-01-17T15:00:00Z');
  assertEquals(isMarketOpen(date), true);
});

Deno.test("isMarketOpen() - weekend", () => {
  // Saturday
  const saturday = new Date('2024-01-20T15:00:00Z');
  assertEquals(isMarketOpen(saturday), false);

  // Sunday
  const sunday = new Date('2024-01-21T15:00:00Z');
  assertEquals(isMarketOpen(sunday), false);
});

Deno.test("isMarketOpen() - before hours", () => {
  // Wednesday 12:00 UTC (7:00 AM ET)
  const date = new Date('2024-01-17T12:00:00Z');
  assertEquals(isMarketOpen(date), false);
});

Deno.test("isMarketOpen() - after hours", () => {
  // Wednesday 22:00 UTC (5:00 PM ET)
  const date = new Date('2024-01-17T22:00:00Z');
  assertEquals(isMarketOpen(date), false);
});

// Subscription validation
function isSubscriptionActive(
  expiresAt: Date | null,
  now: Date = new Date()
): boolean {
  if (!expiresAt) return false;
  return expiresAt > now;
}

Deno.test("isSubscriptionActive() - active", () => {
  const future = new Date(Date.now() + 86400000); // Tomorrow
  assertEquals(isSubscriptionActive(future), true);
});

Deno.test("isSubscriptionActive() - expired", () => {
  const past = new Date(Date.now() - 86400000); // Yesterday
  assertEquals(isSubscriptionActive(past), false);
});

Deno.test("isSubscriptionActive() - null", () => {
  assertEquals(isSubscriptionActive(null), false);
});

// Rebalance threshold check
function needsRebalance(
  currentPct: number,
  targetPct: number,
  threshold: number
): boolean {
  return Math.abs(currentPct - targetPct) > threshold;
}

Deno.test("needsRebalance() - significant drift", () => {
  assertEquals(needsRebalance(15, 10, 3), true);
});

Deno.test("needsRebalance() - within threshold", () => {
  assertEquals(needsRebalance(11, 10, 3), false);
});

Deno.test("needsRebalance() - exactly at threshold", () => {
  assertEquals(needsRebalance(13, 10, 3), false); // Not greater than
});
