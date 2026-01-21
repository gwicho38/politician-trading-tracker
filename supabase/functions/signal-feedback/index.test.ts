/**
 * Tests for signal-feedback Edge Function
 *
 * Tests:
 * - Outcome calculation logic
 * - Return percentage calculations
 * - Win/loss classification
 * - Feature correlation calculations
 * - Sharpe ratio calculations
 */

import { assertEquals, assertAlmostEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Extracted logic for testing
function calculateReturn(entryPrice: number, exitPrice: number): number {
  return ((exitPrice - entryPrice) / entryPrice) * 100;
}

function classifyOutcome(returnPct: number): 'win' | 'loss' | 'breakeven' {
  if (returnPct > 0.5) {
    return 'win';
  } else if (returnPct < -0.5) {
    return 'loss';
  } else {
    return 'breakeven';
  }
}

function calculateHoldingDays(entryDate: Date, exitDate: Date): number {
  return Math.ceil((exitDate.getTime() - entryDate.getTime()) / (1000 * 60 * 60 * 24));
}

function calculateWinRate(wins: number, total: number): number {
  return total > 0 ? (wins / total) * 100 : 0;
}

function calculateSharpeRatio(returns: number[]): number {
  if (returns.length === 0) return 0;

  const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const stdDev = Math.sqrt(
    returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length
  );

  return stdDev !== 0 ? avgReturn / stdDev : 0;
}

function calculatePearsonCorrelation(xValues: number[], yValues: number[]): number {
  if (xValues.length !== yValues.length || xValues.length === 0) return 0;

  const n = xValues.length;
  const sumX = xValues.reduce((sum, x) => sum + x, 0);
  const sumY = yValues.reduce((sum, y) => sum + y, 0);
  const sumXY = xValues.reduce((sum, x, i) => sum + x * yValues[i], 0);
  const sumX2 = xValues.reduce((sum, x) => sum + x * x, 0);
  const sumY2 = yValues.reduce((sum, y) => sum + y * y, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  return denominator !== 0 ? numerator / denominator : 0;
}

// Tests

Deno.test("calculateReturn() - positive return", () => {
  const result = calculateReturn(100, 110);
  assertEquals(result, 10);
});

Deno.test("calculateReturn() - negative return", () => {
  const result = calculateReturn(100, 90);
  assertEquals(result, -10);
});

Deno.test("calculateReturn() - zero return", () => {
  const result = calculateReturn(100, 100);
  assertEquals(result, 0);
});

Deno.test("calculateReturn() - handles decimal prices", () => {
  const result = calculateReturn(50.50, 55.55);
  assertAlmostEquals(result, 10, 0.01);
});

Deno.test("classifyOutcome() - win when return > 0.5%", () => {
  assertEquals(classifyOutcome(5), 'win');
  assertEquals(classifyOutcome(0.6), 'win');
  assertEquals(classifyOutcome(100), 'win');
});

Deno.test("classifyOutcome() - loss when return < -0.5%", () => {
  assertEquals(classifyOutcome(-5), 'loss');
  assertEquals(classifyOutcome(-0.6), 'loss');
  assertEquals(classifyOutcome(-100), 'loss');
});

Deno.test("classifyOutcome() - breakeven when return between -0.5% and 0.5%", () => {
  assertEquals(classifyOutcome(0), 'breakeven');
  assertEquals(classifyOutcome(0.3), 'breakeven');
  assertEquals(classifyOutcome(-0.3), 'breakeven');
  assertEquals(classifyOutcome(0.5), 'breakeven');
  assertEquals(classifyOutcome(-0.5), 'breakeven');
});

Deno.test("calculateHoldingDays() - same day", () => {
  const entry = new Date('2024-01-01');
  const exit = new Date('2024-01-01');
  assertEquals(calculateHoldingDays(entry, exit), 0);
});

Deno.test("calculateHoldingDays() - one day", () => {
  const entry = new Date('2024-01-01');
  const exit = new Date('2024-01-02');
  assertEquals(calculateHoldingDays(entry, exit), 1);
});

Deno.test("calculateHoldingDays() - multiple days", () => {
  const entry = new Date('2024-01-01');
  const exit = new Date('2024-01-10');
  assertEquals(calculateHoldingDays(entry, exit), 9);
});

Deno.test("calculateHoldingDays() - rounds up partial days", () => {
  const entry = new Date('2024-01-01T00:00:00');
  const exit = new Date('2024-01-02T12:00:00');
  assertEquals(calculateHoldingDays(entry, exit), 2);
});

Deno.test("calculateWinRate() - 100% win rate", () => {
  assertEquals(calculateWinRate(10, 10), 100);
});

Deno.test("calculateWinRate() - 0% win rate", () => {
  assertEquals(calculateWinRate(0, 10), 0);
});

Deno.test("calculateWinRate() - 50% win rate", () => {
  assertEquals(calculateWinRate(5, 10), 50);
});

Deno.test("calculateWinRate() - handles zero total", () => {
  assertEquals(calculateWinRate(0, 0), 0);
});

Deno.test("calculateSharpeRatio() - positive ratio", () => {
  const returns = [5, 6, 7, 8, 9];
  const ratio = calculateSharpeRatio(returns);
  // Average = 7, should have positive Sharpe
  assertEquals(ratio > 0, true);
});

Deno.test("calculateSharpeRatio() - zero when all same", () => {
  const returns = [5, 5, 5, 5, 5];
  const ratio = calculateSharpeRatio(returns);
  // No variance, Sharpe is undefined but we return 0
  assertEquals(ratio, 0);
});

Deno.test("calculateSharpeRatio() - handles empty array", () => {
  assertEquals(calculateSharpeRatio([]), 0);
});

Deno.test("calculateSharpeRatio() - mixed returns", () => {
  const returns = [10, -5, 8, -3, 12, -2, 7];
  const ratio = calculateSharpeRatio(returns);
  // Average is positive, so Sharpe should be positive
  assertEquals(ratio > 0, true);
});

Deno.test("calculatePearsonCorrelation() - perfect positive correlation", () => {
  const x = [1, 2, 3, 4, 5];
  const y = [2, 4, 6, 8, 10];
  const correlation = calculatePearsonCorrelation(x, y);
  assertAlmostEquals(correlation, 1, 0.001);
});

Deno.test("calculatePearsonCorrelation() - perfect negative correlation", () => {
  const x = [1, 2, 3, 4, 5];
  const y = [10, 8, 6, 4, 2];
  const correlation = calculatePearsonCorrelation(x, y);
  assertAlmostEquals(correlation, -1, 0.001);
});

Deno.test("calculatePearsonCorrelation() - no correlation", () => {
  const x = [1, 2, 3, 4, 5];
  const y = [5, 5, 5, 5, 5];
  const correlation = calculatePearsonCorrelation(x, y);
  assertEquals(correlation, 0);
});

Deno.test("calculatePearsonCorrelation() - empty arrays", () => {
  assertEquals(calculatePearsonCorrelation([], []), 0);
});

Deno.test("calculatePearsonCorrelation() - mismatched lengths", () => {
  const x = [1, 2, 3];
  const y = [1, 2];
  assertEquals(calculatePearsonCorrelation(x, y), 0);
});

// Test feature lift calculation
function calculateLift(avgReturnHigh: number, avgReturnLow: number): number {
  return avgReturnHigh - avgReturnLow;
}

Deno.test("calculateLift() - positive lift", () => {
  assertEquals(calculateLift(10, 5), 5);
});

Deno.test("calculateLift() - negative lift", () => {
  assertEquals(calculateLift(3, 8), -5);
});

Deno.test("calculateLift() - zero lift", () => {
  assertEquals(calculateLift(5, 5), 0);
});

// Test feature usefulness determination
function isFeatureUseful(correlation: number, liftPct: number): boolean {
  return Math.abs(correlation) > 0.1 || Math.abs(liftPct) > 1;
}

Deno.test("isFeatureUseful() - useful due to high correlation", () => {
  assertEquals(isFeatureUseful(0.5, 0.5), true);
});

Deno.test("isFeatureUseful() - useful due to high lift", () => {
  assertEquals(isFeatureUseful(0.05, 5), true);
});

Deno.test("isFeatureUseful() - not useful", () => {
  assertEquals(isFeatureUseful(0.05, 0.5), false);
});

// Test recommended weight calculation
function calculateRecommendedWeight(correlation: number): number {
  const baseWeight = 0.2;
  const recommendedWeight = baseWeight + (correlation * 0.3);
  return Math.max(0, Math.min(1, recommendedWeight));
}

Deno.test("calculateRecommendedWeight() - positive correlation", () => {
  const weight = calculateRecommendedWeight(0.5);
  assertEquals(weight, 0.35);
});

Deno.test("calculateRecommendedWeight() - negative correlation", () => {
  const weight = calculateRecommendedWeight(-0.5);
  assertEquals(weight, 0.05);
});

Deno.test("calculateRecommendedWeight() - clamps to 0", () => {
  const weight = calculateRecommendedWeight(-1);
  assertEquals(weight, 0);
});

Deno.test("calculateRecommendedWeight() - clamps to 1", () => {
  const weight = calculateRecommendedWeight(3);
  assertEquals(weight, 1);
});
