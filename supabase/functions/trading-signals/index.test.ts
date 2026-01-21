/**
 * Tests for trading-signals Edge Function
 *
 * Tests:
 * - Signal eligibility filtering for reference portfolio
 * - Confidence score calculations
 * - Signal type classification
 * - Request routing
 */

import { assertEquals, assertArrayIncludes } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Configuration constants
const REFERENCE_PORTFOLIO_MIN_CONFIDENCE = 0.70;
const REFERENCE_PORTFOLIO_SIGNAL_TYPES = ['buy', 'strong_buy', 'sell', 'strong_sell'];

// Signal eligibility filtering
interface Signal {
  id: string;
  ticker: string;
  signal_type: string;
  confidence_score: number;
}

function filterEligibleSignals(signals: Signal[]): Signal[] {
  return signals.filter(signal =>
    signal.confidence_score >= REFERENCE_PORTFOLIO_MIN_CONFIDENCE &&
    REFERENCE_PORTFOLIO_SIGNAL_TYPES.includes(signal.signal_type)
  );
}

// Signal type classification
function classifySignalType(
  buyRatio: number,
  thresholds: { strongBuy: number; buy: number; sell: number; strongSell: number }
): 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell' {
  if (buyRatio >= thresholds.strongBuy) return 'strong_buy';
  if (buyRatio >= thresholds.buy) return 'buy';
  if (buyRatio <= thresholds.strongSell) return 'strong_sell';
  if (buyRatio <= thresholds.sell) return 'sell';
  return 'hold';
}

// Confidence score calculation components
function calculateBaseConfidence(baseValue: number): number {
  return Math.max(0, Math.min(1, baseValue));
}

function calculatePoliticianCountBonus(count: number): number {
  if (count >= 5) return 0.15;
  if (count >= 3) return 0.10;
  if (count >= 2) return 0.05;
  return 0;
}

function calculateRecentActivityBonus(recentCount: number): number {
  if (recentCount >= 5) return 0.15;
  if (recentCount >= 2) return 0.10;
  return 0;
}

function calculateBipartisanBonus(hasBipartisan: boolean): number {
  return hasBipartisan ? 0.10 : 0;
}

function calculateVolumeBonus(volumeUsd: number): number {
  if (volumeUsd >= 1000000) return 0.15;
  if (volumeUsd >= 100000) return 0.10;
  return 0;
}

function calculateSignalStrengthBonus(signalType: string): number {
  if (signalType === 'strong_buy' || signalType === 'strong_sell') return 0.15;
  if (signalType === 'buy' || signalType === 'sell') return 0.10;
  return 0;
}

// Full confidence calculation
function calculateConfidenceScore(
  base: number,
  politicianCount: number,
  recentActivity: number,
  isBipartisan: boolean,
  volumeUsd: number,
  signalType: string
): number {
  let score = calculateBaseConfidence(base);
  score += calculatePoliticianCountBonus(politicianCount);
  score += calculateRecentActivityBonus(recentActivity);
  score += calculateBipartisanBonus(isBipartisan);
  score += calculateVolumeBonus(volumeUsd);
  score += calculateSignalStrengthBonus(signalType);
  return Math.min(1, score);
}

// Buy ratio calculation
function calculateBuyRatio(buyCount: number, sellCount: number): number {
  const total = buyCount + sellCount;
  if (total === 0) return 0.5; // Neutral if no trades
  return buyCount / total;
}

// Route determination
function determineRoute(path: string): string {
  const routes = ['get-signals', 'generate-signals', 'regenerate-signals', 'get-signal-stats', 'update-target-prices', 'preview-signals', 'test'];
  if (routes.includes(path)) return path;
  return 'unknown';
}

// Tests

Deno.test("filterEligibleSignals() - filters by confidence", () => {
  const signals: Signal[] = [
    { id: '1', ticker: 'AAPL', signal_type: 'buy', confidence_score: 0.80 },
    { id: '2', ticker: 'TSLA', signal_type: 'buy', confidence_score: 0.60 },
    { id: '3', ticker: 'MSFT', signal_type: 'strong_buy', confidence_score: 0.75 },
  ];

  const result = filterEligibleSignals(signals);

  assertEquals(result.length, 2);
  assertEquals(result.map(s => s.ticker), ['AAPL', 'MSFT']);
});

Deno.test("filterEligibleSignals() - filters by signal type", () => {
  const signals: Signal[] = [
    { id: '1', ticker: 'AAPL', signal_type: 'buy', confidence_score: 0.80 },
    { id: '2', ticker: 'TSLA', signal_type: 'hold', confidence_score: 0.85 },
    { id: '3', ticker: 'MSFT', signal_type: 'sell', confidence_score: 0.75 },
  ];

  const result = filterEligibleSignals(signals);

  assertEquals(result.length, 2);
  assertEquals(result.map(s => s.ticker), ['AAPL', 'MSFT']);
});

Deno.test("filterEligibleSignals() - allows strong signals", () => {
  const signals: Signal[] = [
    { id: '1', ticker: 'AAPL', signal_type: 'strong_buy', confidence_score: 0.90 },
    { id: '2', ticker: 'TSLA', signal_type: 'strong_sell', confidence_score: 0.85 },
  ];

  const result = filterEligibleSignals(signals);

  assertEquals(result.length, 2);
});

Deno.test("filterEligibleSignals() - empty when none eligible", () => {
  const signals: Signal[] = [
    { id: '1', ticker: 'AAPL', signal_type: 'hold', confidence_score: 0.80 },
    { id: '2', ticker: 'TSLA', signal_type: 'buy', confidence_score: 0.50 },
  ];

  const result = filterEligibleSignals(signals);

  assertEquals(result.length, 0);
});

Deno.test("filterEligibleSignals() - boundary case at 70%", () => {
  const signals: Signal[] = [
    { id: '1', ticker: 'AAPL', signal_type: 'buy', confidence_score: 0.70 },
    { id: '2', ticker: 'TSLA', signal_type: 'buy', confidence_score: 0.69 },
  ];

  const result = filterEligibleSignals(signals);

  assertEquals(result.length, 1);
  assertEquals(result[0].ticker, 'AAPL');
});

Deno.test("classifySignalType() - strong buy", () => {
  const thresholds = { strongBuy: 3.0, buy: 2.0, sell: 0.5, strongSell: 0.33 };
  assertEquals(classifySignalType(3.5, thresholds), 'strong_buy');
  assertEquals(classifySignalType(3.0, thresholds), 'strong_buy');
});

Deno.test("classifySignalType() - buy", () => {
  const thresholds = { strongBuy: 3.0, buy: 2.0, sell: 0.5, strongSell: 0.33 };
  assertEquals(classifySignalType(2.5, thresholds), 'buy');
  assertEquals(classifySignalType(2.0, thresholds), 'buy');
});

Deno.test("classifySignalType() - hold", () => {
  const thresholds = { strongBuy: 3.0, buy: 2.0, sell: 0.5, strongSell: 0.33 };
  assertEquals(classifySignalType(1.5, thresholds), 'hold');
  assertEquals(classifySignalType(1.0, thresholds), 'hold');
  assertEquals(classifySignalType(0.6, thresholds), 'hold');
});

Deno.test("classifySignalType() - sell", () => {
  const thresholds = { strongBuy: 3.0, buy: 2.0, sell: 0.5, strongSell: 0.33 };
  assertEquals(classifySignalType(0.5, thresholds), 'sell');
  assertEquals(classifySignalType(0.4, thresholds), 'sell');
});

Deno.test("classifySignalType() - strong sell", () => {
  const thresholds = { strongBuy: 3.0, buy: 2.0, sell: 0.5, strongSell: 0.33 };
  assertEquals(classifySignalType(0.33, thresholds), 'strong_sell');
  assertEquals(classifySignalType(0.1, thresholds), 'strong_sell');
});

Deno.test("calculateBaseConfidence() - clamps to 0-1", () => {
  assertEquals(calculateBaseConfidence(0.5), 0.5);
  assertEquals(calculateBaseConfidence(-0.1), 0);
  assertEquals(calculateBaseConfidence(1.5), 1);
});

Deno.test("calculatePoliticianCountBonus() - 5+ politicians", () => {
  assertEquals(calculatePoliticianCountBonus(5), 0.15);
  assertEquals(calculatePoliticianCountBonus(10), 0.15);
});

Deno.test("calculatePoliticianCountBonus() - 3-4 politicians", () => {
  assertEquals(calculatePoliticianCountBonus(3), 0.10);
  assertEquals(calculatePoliticianCountBonus(4), 0.10);
});

Deno.test("calculatePoliticianCountBonus() - 2 politicians", () => {
  assertEquals(calculatePoliticianCountBonus(2), 0.05);
});

Deno.test("calculatePoliticianCountBonus() - 1 or fewer", () => {
  assertEquals(calculatePoliticianCountBonus(1), 0);
  assertEquals(calculatePoliticianCountBonus(0), 0);
});

Deno.test("calculateRecentActivityBonus() - 5+ recent", () => {
  assertEquals(calculateRecentActivityBonus(5), 0.15);
  assertEquals(calculateRecentActivityBonus(10), 0.15);
});

Deno.test("calculateRecentActivityBonus() - 2-4 recent", () => {
  assertEquals(calculateRecentActivityBonus(2), 0.10);
  assertEquals(calculateRecentActivityBonus(4), 0.10);
});

Deno.test("calculateRecentActivityBonus() - 0-1 recent", () => {
  assertEquals(calculateRecentActivityBonus(0), 0);
  assertEquals(calculateRecentActivityBonus(1), 0);
});

Deno.test("calculateBipartisanBonus() - bipartisan", () => {
  assertEquals(calculateBipartisanBonus(true), 0.10);
});

Deno.test("calculateBipartisanBonus() - not bipartisan", () => {
  assertEquals(calculateBipartisanBonus(false), 0);
});

Deno.test("calculateVolumeBonus() - 1M+ volume", () => {
  assertEquals(calculateVolumeBonus(1000000), 0.15);
  assertEquals(calculateVolumeBonus(5000000), 0.15);
});

Deno.test("calculateVolumeBonus() - 100K-1M volume", () => {
  assertEquals(calculateVolumeBonus(100000), 0.10);
  assertEquals(calculateVolumeBonus(500000), 0.10);
});

Deno.test("calculateVolumeBonus() - under 100K volume", () => {
  assertEquals(calculateVolumeBonus(50000), 0);
  assertEquals(calculateVolumeBonus(0), 0);
});

Deno.test("calculateSignalStrengthBonus() - strong signals", () => {
  assertEquals(calculateSignalStrengthBonus('strong_buy'), 0.15);
  assertEquals(calculateSignalStrengthBonus('strong_sell'), 0.15);
});

Deno.test("calculateSignalStrengthBonus() - regular signals", () => {
  assertEquals(calculateSignalStrengthBonus('buy'), 0.10);
  assertEquals(calculateSignalStrengthBonus('sell'), 0.10);
});

Deno.test("calculateSignalStrengthBonus() - hold", () => {
  assertEquals(calculateSignalStrengthBonus('hold'), 0);
});

Deno.test("calculateConfidenceScore() - combines all bonuses", () => {
  const score = calculateConfidenceScore(
    0.5,  // base
    5,    // 5+ politicians: +0.15
    5,    // 5+ recent: +0.15
    true, // bipartisan: +0.10
    1000000, // 1M+ volume: +0.15
    'strong_buy' // strong signal: +0.15
  );

  // 0.5 + 0.15 + 0.15 + 0.10 + 0.15 + 0.15 = 1.2 -> capped at 1.0
  assertEquals(score, 1);
});

Deno.test("calculateConfidenceScore() - minimal bonuses", () => {
  const score = calculateConfidenceScore(
    0.5,    // base
    1,      // 1 politician: +0
    1,      // 1 recent: +0
    false,  // not bipartisan: +0
    10000,  // low volume: +0
    'hold'  // hold signal: +0
  );

  assertEquals(score, 0.5);
});

Deno.test("calculateBuyRatio() - all buys", () => {
  assertEquals(calculateBuyRatio(10, 0), 1);
});

Deno.test("calculateBuyRatio() - all sells", () => {
  assertEquals(calculateBuyRatio(0, 10), 0);
});

Deno.test("calculateBuyRatio() - equal", () => {
  assertEquals(calculateBuyRatio(5, 5), 0.5);
});

Deno.test("calculateBuyRatio() - no trades", () => {
  assertEquals(calculateBuyRatio(0, 0), 0.5); // Neutral
});

Deno.test("calculateBuyRatio() - 3:1 ratio", () => {
  assertEquals(calculateBuyRatio(3, 1), 0.75);
});

Deno.test("determineRoute() - valid routes", () => {
  assertEquals(determineRoute('get-signals'), 'get-signals');
  assertEquals(determineRoute('generate-signals'), 'generate-signals');
  assertEquals(determineRoute('regenerate-signals'), 'regenerate-signals');
  assertEquals(determineRoute('get-signal-stats'), 'get-signal-stats');
  assertEquals(determineRoute('update-target-prices'), 'update-target-prices');
  assertEquals(determineRoute('preview-signals'), 'preview-signals');
  assertEquals(determineRoute('test'), 'test');
});

Deno.test("determineRoute() - unknown route", () => {
  assertEquals(determineRoute('invalid'), 'unknown');
  assertEquals(determineRoute(''), 'unknown');
});

// Queue entry building
interface QueueEntry {
  signal_id: string;
  status: string;
}

function buildQueueEntries(signals: Signal[]): QueueEntry[] {
  return signals.map(signal => ({
    signal_id: signal.id,
    status: 'pending',
  }));
}

Deno.test("buildQueueEntries() - creates pending entries", () => {
  const signals: Signal[] = [
    { id: 'sig-1', ticker: 'AAPL', signal_type: 'buy', confidence_score: 0.8 },
    { id: 'sig-2', ticker: 'TSLA', signal_type: 'sell', confidence_score: 0.75 },
  ];

  const result = buildQueueEntries(signals);

  assertEquals(result.length, 2);
  assertEquals(result[0].signal_id, 'sig-1');
  assertEquals(result[0].status, 'pending');
  assertEquals(result[1].signal_id, 'sig-2');
  assertEquals(result[1].status, 'pending');
});

// Signal features extraction
interface SignalFeatures {
  politician_count: number;
  buy_sell_ratio: number;
  bipartisan: boolean;
  recent_activity_30d: number;
  net_volume: number;
}

function extractSignalFeatures(
  politicianCount: number,
  buyCount: number,
  sellCount: number,
  parties: string[],
  recentCount: number,
  buyVolume: number,
  sellVolume: number
): SignalFeatures {
  const uniqueParties = new Set(parties);
  const hasBoth = uniqueParties.has('D') && uniqueParties.has('R');

  return {
    politician_count: politicianCount,
    buy_sell_ratio: calculateBuyRatio(buyCount, sellCount),
    bipartisan: hasBoth,
    recent_activity_30d: recentCount,
    net_volume: buyVolume - sellVolume,
  };
}

Deno.test("extractSignalFeatures() - bipartisan detection", () => {
  const result = extractSignalFeatures(
    5, 3, 2, ['D', 'R', 'D'], 4, 100000, 50000
  );

  assertEquals(result.bipartisan, true);
  assertEquals(result.politician_count, 5);
  assertEquals(result.buy_sell_ratio, 0.6);
  assertEquals(result.recent_activity_30d, 4);
  assertEquals(result.net_volume, 50000);
});

Deno.test("extractSignalFeatures() - single party", () => {
  const result = extractSignalFeatures(
    3, 3, 0, ['D', 'D', 'D'], 2, 75000, 0
  );

  assertEquals(result.bipartisan, false);
});
