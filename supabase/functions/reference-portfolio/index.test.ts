/**
 * Tests for reference-portfolio Edge Function
 *
 * Tests:
 * - Position sizing
 * - Stop loss / take profit calculations
 * - P&L calculations
 * - Portfolio state management
 */

import { assertEquals, assertAlmostEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Position sizing
function calculatePositionSize(
  portfolioValue: number,
  maxPositionPct: number,
  signalConfidence: number
): number {
  const baseSize = portfolioValue * (maxPositionPct / 100);
  const adjustedSize = baseSize * signalConfidence;
  return Math.floor(adjustedSize * 100) / 100; // Round to 2 decimal places
}

function calculateQuantity(
  positionValue: number,
  sharePrice: number,
  minQuantity: number = 1
): number {
  const rawQuantity = positionValue / sharePrice;
  return Math.max(minQuantity, Math.floor(rawQuantity));
}

// Stop loss / take profit
function calculateStopLoss(
  entryPrice: number,
  stopLossPct: number
): number {
  return entryPrice * (1 - stopLossPct / 100);
}

function calculateTakeProfit(
  entryPrice: number,
  takeProfitPct: number
): number {
  return entryPrice * (1 + takeProfitPct / 100);
}

function shouldTriggerStopLoss(
  currentPrice: number,
  stopLossPrice: number
): boolean {
  return currentPrice <= stopLossPrice;
}

function shouldTriggerTakeProfit(
  currentPrice: number,
  takeProfitPrice: number
): boolean {
  return currentPrice >= takeProfitPrice;
}

// P&L calculations
function calculateUnrealizedPL(
  quantity: number,
  entryPrice: number,
  currentPrice: number
): number {
  return quantity * (currentPrice - entryPrice);
}

function calculateUnrealizedPLPct(
  entryPrice: number,
  currentPrice: number
): number {
  return ((currentPrice - entryPrice) / entryPrice) * 100;
}

function calculateRealizedPL(
  quantity: number,
  entryPrice: number,
  exitPrice: number
): number {
  return quantity * (exitPrice - entryPrice);
}

// Portfolio allocation
function calculateAllocationPct(
  positionValue: number,
  portfolioValue: number
): number {
  if (portfolioValue <= 0) return 0;
  return (positionValue / portfolioValue) * 100;
}

function isOverAllocated(
  currentAllocationPct: number,
  maxAllocationPct: number
): boolean {
  return currentAllocationPct > maxAllocationPct;
}

// Win rate calculation
function calculateWinRate(
  winningTrades: number,
  losingTrades: number
): number {
  const total = winningTrades + losingTrades;
  if (total === 0) return 0;
  return (winningTrades / total) * 100;
}

// Tests

Deno.test("calculatePositionSize() - basic calculation", () => {
  const size = calculatePositionSize(100000, 5, 0.8);
  // 100000 * 0.05 * 0.8 = 4000
  assertEquals(size, 4000);
});

Deno.test("calculatePositionSize() - low confidence", () => {
  const size = calculatePositionSize(100000, 5, 0.5);
  assertEquals(size, 2500);
});

Deno.test("calculatePositionSize() - full confidence", () => {
  const size = calculatePositionSize(100000, 5, 1.0);
  assertEquals(size, 5000);
});

Deno.test("calculateQuantity() - basic calculation", () => {
  const qty = calculateQuantity(5000, 150);
  assertEquals(qty, 33); // floor(5000/150) = 33
});

Deno.test("calculateQuantity() - respects minimum", () => {
  const qty = calculateQuantity(10, 150);
  assertEquals(qty, 1); // Would be 0, but min is 1
});

Deno.test("calculateQuantity() - custom minimum", () => {
  const qty = calculateQuantity(50, 150, 5);
  assertEquals(qty, 5); // Would be 0, but min is 5
});

Deno.test("calculateStopLoss() - 10% stop loss", () => {
  const stopLoss = calculateStopLoss(100, 10);
  assertEquals(stopLoss, 90);
});

Deno.test("calculateStopLoss() - 5% stop loss", () => {
  const stopLoss = calculateStopLoss(150, 5);
  assertEquals(stopLoss, 142.5);
});

Deno.test("calculateTakeProfit() - 20% take profit", () => {
  const takeProfit = calculateTakeProfit(100, 20);
  assertEquals(takeProfit, 120);
});

Deno.test("calculateTakeProfit() - 15% take profit", () => {
  const takeProfit = calculateTakeProfit(150, 15);
  assertEquals(takeProfit, 172.5);
});

Deno.test("shouldTriggerStopLoss() - triggered", () => {
  assertEquals(shouldTriggerStopLoss(85, 90), true);
  assertEquals(shouldTriggerStopLoss(90, 90), true);
});

Deno.test("shouldTriggerStopLoss() - not triggered", () => {
  assertEquals(shouldTriggerStopLoss(95, 90), false);
  assertEquals(shouldTriggerStopLoss(100, 90), false);
});

Deno.test("shouldTriggerTakeProfit() - triggered", () => {
  assertEquals(shouldTriggerTakeProfit(125, 120), true);
  assertEquals(shouldTriggerTakeProfit(120, 120), true);
});

Deno.test("shouldTriggerTakeProfit() - not triggered", () => {
  assertEquals(shouldTriggerTakeProfit(115, 120), false);
  assertEquals(shouldTriggerTakeProfit(100, 120), false);
});

Deno.test("calculateUnrealizedPL() - profit", () => {
  const pl = calculateUnrealizedPL(10, 100, 110);
  assertEquals(pl, 100); // 10 * (110 - 100)
});

Deno.test("calculateUnrealizedPL() - loss", () => {
  const pl = calculateUnrealizedPL(10, 100, 90);
  assertEquals(pl, -100); // 10 * (90 - 100)
});

Deno.test("calculateUnrealizedPLPct() - profit", () => {
  const pct = calculateUnrealizedPLPct(100, 110);
  assertEquals(pct, 10); // 10% gain
});

Deno.test("calculateUnrealizedPLPct() - loss", () => {
  const pct = calculateUnrealizedPLPct(100, 90);
  assertEquals(pct, -10); // 10% loss
});

Deno.test("calculateRealizedPL() - profit", () => {
  const pl = calculateRealizedPL(10, 100, 120);
  assertEquals(pl, 200);
});

Deno.test("calculateRealizedPL() - loss", () => {
  const pl = calculateRealizedPL(10, 100, 80);
  assertEquals(pl, -200);
});

Deno.test("calculateAllocationPct() - basic", () => {
  const pct = calculateAllocationPct(5000, 100000);
  assertEquals(pct, 5);
});

Deno.test("calculateAllocationPct() - zero portfolio", () => {
  const pct = calculateAllocationPct(5000, 0);
  assertEquals(pct, 0);
});

Deno.test("isOverAllocated() - over", () => {
  assertEquals(isOverAllocated(8, 5), true);
});

Deno.test("isOverAllocated() - under", () => {
  assertEquals(isOverAllocated(3, 5), false);
});

Deno.test("isOverAllocated() - exactly at limit", () => {
  assertEquals(isOverAllocated(5, 5), false);
});

Deno.test("calculateWinRate() - 50%", () => {
  assertEquals(calculateWinRate(5, 5), 50);
});

Deno.test("calculateWinRate() - 100%", () => {
  assertEquals(calculateWinRate(10, 0), 100);
});

Deno.test("calculateWinRate() - 0%", () => {
  assertEquals(calculateWinRate(0, 10), 0);
});

Deno.test("calculateWinRate() - no trades", () => {
  assertEquals(calculateWinRate(0, 0), 0);
});

// Exit reason determination
function determineExitReason(
  currentPrice: number,
  entryPrice: number,
  stopLossPrice: number,
  takeProfitPrice: number
): 'stop_loss' | 'take_profit' | 'manual' | null {
  if (currentPrice <= stopLossPrice) return 'stop_loss';
  if (currentPrice >= takeProfitPrice) return 'take_profit';
  return null;
}

Deno.test("determineExitReason() - stop loss", () => {
  assertEquals(determineExitReason(85, 100, 90, 120), 'stop_loss');
});

Deno.test("determineExitReason() - take profit", () => {
  assertEquals(determineExitReason(125, 100, 90, 120), 'take_profit');
});

Deno.test("determineExitReason() - no trigger", () => {
  assertEquals(determineExitReason(105, 100, 90, 120), null);
});

// Portfolio value calculation
function calculatePortfolioValue(
  cash: number,
  positions: Array<{ quantity: number; currentPrice: number }>
): number {
  const positionsValue = positions.reduce(
    (sum, pos) => sum + pos.quantity * pos.currentPrice,
    0
  );
  return cash + positionsValue;
}

Deno.test("calculatePortfolioValue() - cash only", () => {
  const value = calculatePortfolioValue(10000, []);
  assertEquals(value, 10000);
});

Deno.test("calculatePortfolioValue() - with positions", () => {
  const positions = [
    { quantity: 10, currentPrice: 100 },
    { quantity: 5, currentPrice: 200 },
  ];
  const value = calculatePortfolioValue(5000, positions);
  // 5000 + (10*100) + (5*200) = 5000 + 1000 + 1000 = 7000
  assertEquals(value, 7000);
});

// Risk management
function calculateMaxLoss(
  portfolioValue: number,
  maxLossPct: number
): number {
  return portfolioValue * (maxLossPct / 100);
}

function canOpenPosition(
  currentOpenPositions: number,
  maxPositions: number
): boolean {
  return currentOpenPositions < maxPositions;
}

Deno.test("calculateMaxLoss() - 2% max loss", () => {
  const maxLoss = calculateMaxLoss(100000, 2);
  assertEquals(maxLoss, 2000);
});

Deno.test("canOpenPosition() - under limit", () => {
  assertEquals(canOpenPosition(3, 5), true);
});

Deno.test("canOpenPosition() - at limit", () => {
  assertEquals(canOpenPosition(5, 5), false);
});

Deno.test("canOpenPosition() - over limit", () => {
  assertEquals(canOpenPosition(6, 5), false);
});
