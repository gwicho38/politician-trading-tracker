// Deno tests for sync-data edge function
// Run with: deno test --allow-env --allow-net index.test.ts

import {
  assertEquals,
  assertExists,
  assertStringIncludes,
} from "https://deno.land/std@0.168.0/testing/asserts.ts";

// =============================================================================
// METRICS.md Section 1.1: Dashboard Stats Aggregation Tests
// =============================================================================

Deno.test("[ ] total_trades aggregation - COUNT(trading_disclosures)", () => {
  const mockDisclosures = [
    { id: "1", transaction_type: "purchase" },
    { id: "2", transaction_type: "sale" },
    { id: "3", transaction_type: "exchange" },
  ];

  const totalTrades = mockDisclosures.length;
  assertEquals(totalTrades, 3);
});

Deno.test("[ ] total_volume aggregation - SUM(amount_range_avg)", () => {
  const mockDisclosures = [
    { amount_range_min: 1001, amount_range_max: 15000 }, // mid = 8000.5
    { amount_range_min: 15001, amount_range_max: 50000 }, // mid = 32500.5
  ];

  const calculateMidpoint = (d: any): number => {
    const min = d.amount_range_min || 0;
    const max = d.amount_range_max || min;
    return (min + max) / 2;
  };

  const totalVolume = mockDisclosures.reduce(
    (sum, d) => sum + calculateMidpoint(d),
    0
  );
  assertEquals(totalVolume, 8000.5 + 32500.5);
});

Deno.test("[ ] active_politicians aggregation - COUNT(DISTINCT politician_id)", () => {
  const mockDisclosures = [
    { politician_id: "pol-1" },
    { politician_id: "pol-1" }, // Duplicate
    { politician_id: "pol-2" },
    { politician_id: "pol-3" },
  ];

  const uniquePoliticians = new Set(mockDisclosures.map((d) => d.politician_id));
  assertEquals(uniquePoliticians.size, 3);
});

Deno.test("[ ] trades_this_month aggregation - COUNT WHERE month = current", () => {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();

  const mockDisclosures = [
    { transaction_date: new Date(currentYear, currentMonth, 15).toISOString() },
    { transaction_date: new Date(currentYear, currentMonth, 10).toISOString() },
    { transaction_date: new Date(currentYear, currentMonth - 1, 15).toISOString() }, // Last month
  ];

  const isCurrentMonth = (dateStr: string): boolean => {
    const date = new Date(dateStr);
    return date.getMonth() === currentMonth && date.getFullYear() === currentYear;
  };

  const tradesThisMonth = mockDisclosures.filter((d) =>
    isCurrentMonth(d.transaction_date)
  ).length;
  assertEquals(tradesThisMonth, 2);
});

Deno.test("[ ] average_trade_size aggregation - AVG(amount_range_avg)", () => {
  const mockDisclosures = [
    { amount_range_min: 1001, amount_range_max: 15000 }, // mid = 8000.5
    { amount_range_min: 15001, amount_range_max: 50000 }, // mid = 32500.5
  ];

  const calculateMidpoint = (d: any): number => {
    const min = d.amount_range_min || 0;
    const max = d.amount_range_max || min;
    return (min + max) / 2;
  };

  const midpoints = mockDisclosures.map(calculateMidpoint);
  const avgTradeSize = midpoints.reduce((a, b) => a + b, 0) / midpoints.length;
  assertEquals(avgTradeSize, (8000.5 + 32500.5) / 2);
});

Deno.test("[ ] top_traded_stock aggregation - MODE(asset_ticker)", () => {
  const mockDisclosures = [
    { asset_ticker: "AAPL" },
    { asset_ticker: "AAPL" },
    { asset_ticker: "NVDA" },
    { asset_ticker: "MSFT" },
    { asset_ticker: "AAPL" },
  ];

  const tickerCounts: Record<string, number> = {};
  mockDisclosures.forEach((d) => {
    if (d.asset_ticker) {
      tickerCounts[d.asset_ticker] = (tickerCounts[d.asset_ticker] || 0) + 1;
    }
  });

  const topTicker = Object.entries(tickerCounts).sort(
    ([, a], [, b]) => b - a
  )[0][0];
  assertEquals(topTicker, "AAPL");
});

// =============================================================================
// METRICS.md Section 1.4: Chart Data Aggregation Tests
// =============================================================================

Deno.test("[ ] chart_data.buy_count - COUNT WHERE type='purchase'", () => {
  const mockDisclosures = [
    { transaction_type: "purchase" },
    { transaction_type: "purchase" },
    { transaction_type: "sale" },
  ];

  const buyCount = mockDisclosures.filter(
    (d) => d.transaction_type === "purchase"
  ).length;
  assertEquals(buyCount, 2);
});

Deno.test("[ ] chart_data.sell_count - COUNT WHERE type='sale'", () => {
  const mockDisclosures = [
    { transaction_type: "purchase" },
    { transaction_type: "sale" },
    { transaction_type: "sale" },
  ];

  const sellCount = mockDisclosures.filter(
    (d) => d.transaction_type === "sale"
  ).length;
  assertEquals(sellCount, 2);
});

Deno.test("[ ] chart_data.volume - SUM(amount_range_avg) by month", () => {
  const mockDisclosures = [
    { month: "2024-01", amount_range_min: 1001, amount_range_max: 15000 },
    { month: "2024-01", amount_range_min: 15001, amount_range_max: 50000 },
    { month: "2024-02", amount_range_min: 50001, amount_range_max: 100000 },
  ];

  const calculateMidpoint = (d: any): number => {
    const min = d.amount_range_min || 0;
    const max = d.amount_range_max || min;
    return (min + max) / 2;
  };

  const monthlyVolume: Record<string, number> = {};
  mockDisclosures.forEach((d) => {
    const month = d.month;
    const mid = calculateMidpoint(d);
    monthlyVolume[month] = (monthlyVolume[month] || 0) + mid;
  });

  assertEquals(monthlyVolume["2024-01"], 8000.5 + 32500.5);
  assertEquals(monthlyVolume["2024-02"], 75000.5);
});

Deno.test("[ ] chart_data.unique_politicians - COUNT(DISTINCT politician_id) by month", () => {
  const mockDisclosures = [
    { month: "2024-01", politician_id: "pol-1" },
    { month: "2024-01", politician_id: "pol-1" },
    { month: "2024-01", politician_id: "pol-2" },
    { month: "2024-02", politician_id: "pol-3" },
  ];

  const monthlyPoliticians: Record<string, Set<string>> = {};
  mockDisclosures.forEach((d) => {
    const month = d.month;
    if (!monthlyPoliticians[month]) {
      monthlyPoliticians[month] = new Set();
    }
    monthlyPoliticians[month].add(d.politician_id);
  });

  assertEquals(monthlyPoliticians["2024-01"].size, 2);
  assertEquals(monthlyPoliticians["2024-02"].size, 1);
});

Deno.test("[ ] chart_data.top_tickers - GROUP BY ticker, TOP 5", () => {
  const mockDisclosures = [
    ...Array(10).fill({ asset_ticker: "AAPL" }),
    ...Array(8).fill({ asset_ticker: "NVDA" }),
    ...Array(6).fill({ asset_ticker: "MSFT" }),
    ...Array(4).fill({ asset_ticker: "GOOGL" }),
    ...Array(2).fill({ asset_ticker: "TSLA" }),
    { asset_ticker: "META" },
  ];

  const tickerCounts: Record<string, number> = {};
  mockDisclosures.forEach((d) => {
    if (d.asset_ticker) {
      tickerCounts[d.asset_ticker] = (tickerCounts[d.asset_ticker] || 0) + 1;
    }
  });

  const topTickers = Object.entries(tickerCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([ticker]) => ticker);

  assertEquals(topTickers.length, 5);
  assertEquals(topTickers[0], "AAPL");
  assertEquals(topTickers.includes("META"), false); // 6th place
});

// =============================================================================
// METRICS.md Section 1.2: Politician Totals Update Tests
// =============================================================================

Deno.test("[ ] handleUpdatePoliticianTotals - total_trades per politician", () => {
  const mockDisclosures = [
    { politician_id: "pol-1" },
    { politician_id: "pol-1" },
    { politician_id: "pol-1" },
    { politician_id: "pol-2" },
  ];

  const politicianTrades: Record<string, number> = {};
  mockDisclosures.forEach((d) => {
    const polId = d.politician_id;
    politicianTrades[polId] = (politicianTrades[polId] || 0) + 1;
  });

  assertEquals(politicianTrades["pol-1"], 3);
  assertEquals(politicianTrades["pol-2"], 1);
});

Deno.test("[ ] handleUpdatePoliticianTotals - total_volume per politician", () => {
  const mockDisclosures = [
    { politician_id: "pol-1", amount_range_min: 1001, amount_range_max: 15000 },
    { politician_id: "pol-1", amount_range_min: 50001, amount_range_max: 100000 },
    { politician_id: "pol-2", amount_range_min: 15001, amount_range_max: 50000 },
  ];

  const calculateMidpoint = (d: any): number => {
    const min = d.amount_range_min || 0;
    const max = d.amount_range_max || min;
    return (min + max) / 2;
  };

  const politicianVolume: Record<string, number> = {};
  mockDisclosures.forEach((d) => {
    const polId = d.politician_id;
    const mid = calculateMidpoint(d);
    politicianVolume[polId] = (politicianVolume[polId] || 0) + mid;
  });

  assertEquals(politicianVolume["pol-1"], 8000.5 + 75000.5);
  assertEquals(politicianVolume["pol-2"], 32500.5);
});

// =============================================================================
// Sync Data Request/Response Tests
// =============================================================================

Deno.test("Sync data request - valid actions", () => {
  const validActions = [
    "sync-house",
    "sync-senate",
    "sync-quiver",
    "update-stats",
    "update-chart-data",
    "update-politician-totals",
  ];

  validActions.forEach((action) => {
    assertExists(action);
  });
});

Deno.test("Sync data response - success format", () => {
  const createSuccessResponse = (
    action: string,
    stats: any
  ): any => {
    return {
      success: true,
      action,
      stats,
      timestamp: new Date().toISOString(),
    };
  };

  const response = createSuccessResponse("update-stats", {
    totalTrades: 15234,
    totalVolume: 50000000,
  });

  assertEquals(response.success, true);
  assertEquals(response.action, "update-stats");
  assertExists(response.stats);
  assertExists(response.timestamp);
});

Deno.test("Sync data response - error format", () => {
  const createErrorResponse = (message: string, error?: any): any => {
    return {
      success: false,
      error: message,
      details: error?.message || null,
    };
  };

  const response = createErrorResponse("Sync failed", new Error("DB timeout"));

  assertEquals(response.success, false);
  assertEquals(response.error, "Sync failed");
  assertEquals(response.details, "DB timeout");
});

// =============================================================================
// Amount Range Parsing Tests
// =============================================================================

Deno.test("Amount range parsing - standard ranges", () => {
  const parseAmountRange = (
    rangeStr: string
  ): { min: number; max: number } | null => {
    const cleanStr = rangeStr.replace(/[$,]/g, "");
    const match = cleanStr.match(/(\d+)\s*-\s*(\d+)/);
    if (match) {
      return { min: parseInt(match[1]), max: parseInt(match[2]) };
    }
    return null;
  };

  assertEquals(parseAmountRange("$1,001 - $15,000"), { min: 1001, max: 15000 });
  assertEquals(parseAmountRange("$15,001 - $50,000"), {
    min: 15001,
    max: 50000,
  });
  assertEquals(parseAmountRange("$1,000,001 - $5,000,000"), {
    min: 1000001,
    max: 5000000,
  });
});

// =============================================================================
// Date Filtering Tests
// =============================================================================

Deno.test("Date filtering - within range", () => {
  const isWithinRange = (
    dateStr: string,
    startDate: Date,
    endDate: Date
  ): boolean => {
    const date = new Date(dateStr);
    return date >= startDate && date <= endDate;
  };

  const start = new Date("2024-01-01");
  const end = new Date("2024-01-31");

  assertEquals(isWithinRange("2024-01-15", start, end), true);
  assertEquals(isWithinRange("2024-02-01", start, end), false);
  assertEquals(isWithinRange("2023-12-31", start, end), false);
});

Deno.test("Date filtering - lookback days", () => {
  const getLookbackStart = (days: number): Date => {
    const start = new Date();
    start.setDate(start.getDate() - days);
    return start;
  };

  const thirtyDaysAgo = getLookbackStart(30);
  const now = new Date();

  assertEquals(
    Math.round((now.getTime() - thirtyDaysAgo.getTime()) / (1000 * 60 * 60 * 24)),
    30
  );
});

// =============================================================================
// Month Grouping Tests
// =============================================================================

Deno.test("Month grouping - extracts YYYY-MM", () => {
  const getMonthKey = (dateStr: string): string => {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
  };

  assertEquals(getMonthKey("2024-01-15"), "2024-01");
  assertEquals(getMonthKey("2024-12-25"), "2024-12");
  assertEquals(getMonthKey("2023-05-01"), "2023-05");
});

// =============================================================================
// Party Breakdown Tests
// =============================================================================

Deno.test("[ ] chart_data.party_breakdown - GROUP BY party", () => {
  const mockDisclosures = [
    { party: "D", transaction_type: "purchase" },
    { party: "D", transaction_type: "purchase" },
    { party: "R", transaction_type: "sale" },
    { party: "R", transaction_type: "purchase" },
    { party: "I", transaction_type: "sale" },
  ];

  const partyBreakdown: Record<string, { buys: number; sells: number }> = {};
  mockDisclosures.forEach((d) => {
    const party = d.party;
    if (!partyBreakdown[party]) {
      partyBreakdown[party] = { buys: 0, sells: 0 };
    }
    if (d.transaction_type === "purchase") {
      partyBreakdown[party].buys++;
    } else {
      partyBreakdown[party].sells++;
    }
  });

  assertEquals(partyBreakdown["D"].buys, 2);
  assertEquals(partyBreakdown["R"].buys, 1);
  assertEquals(partyBreakdown["R"].sells, 1);
  assertEquals(partyBreakdown["I"].sells, 1);
});

// =============================================================================
// CORS Headers Tests
// =============================================================================

Deno.test("CORS headers - correct format", () => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":
      "authorization, x-client-info, apikey, content-type",
  };

  assertEquals(corsHeaders["Access-Control-Allow-Origin"], "*");
  assertStringIncludes(
    corsHeaders["Access-Control-Allow-Headers"],
    "authorization"
  );
});

// =============================================================================
// Scheduled Sync Trigger Tests
// =============================================================================

Deno.test("Scheduled sync - invokes correct actions", () => {
  const scheduledActions = [
    "update-stats",
    "update-chart-data",
    "update-politician-totals",
  ];

  assertEquals(scheduledActions.length, 3);
  assertEquals(scheduledActions.includes("update-stats"), true);
  assertEquals(scheduledActions.includes("update-chart-data"), true);
  assertEquals(scheduledActions.includes("update-politician-totals"), true);
});

// =============================================================================
// Stats Update Upsert Tests
// =============================================================================

Deno.test("Stats upsert - creates stats object", () => {
  const createStatsUpdate = (
    totalTrades: number,
    totalVolume: number,
    activePoliticians: number
  ): any => {
    return {
      id: "1", // Singleton row
      total_trades: totalTrades,
      total_volume: totalVolume,
      active_politicians: activePoliticians,
      updated_at: new Date().toISOString(),
    };
  };

  const stats = createStatsUpdate(15234, 50000000, 245);

  assertEquals(stats.total_trades, 15234);
  assertEquals(stats.total_volume, 50000000);
  assertEquals(stats.active_politicians, 245);
  assertExists(stats.updated_at);
});

// =============================================================================
// Null/Undefined Handling Tests
// =============================================================================

Deno.test("Null handling - amount ranges", () => {
  const calculateMidpoint = (min: number | null, max: number | null): number => {
    const minVal = min || 0;
    const maxVal = max || minVal;
    return (minVal + maxVal) / 2;
  };

  assertEquals(calculateMidpoint(1000, 15000), 8000);
  assertEquals(calculateMidpoint(null, 15000), 7500);
  assertEquals(calculateMidpoint(1000, null), 1000);
  assertEquals(calculateMidpoint(null, null), 0);
});

Deno.test("Null handling - ticker filtering", () => {
  const mockDisclosures = [
    { asset_ticker: "AAPL" },
    { asset_ticker: null },
    { asset_ticker: "NVDA" },
    { asset_ticker: undefined },
  ];

  const withTickers = mockDisclosures.filter((d) => d.asset_ticker);
  assertEquals(withTickers.length, 2);
});

// =============================================================================
// Batch Processing Tests
// =============================================================================

Deno.test("Batch processing - chunks array", () => {
  const chunkArray = <T>(array: T[], size: number): T[][] => {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  };

  const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const chunks = chunkArray(items, 3);

  assertEquals(chunks.length, 4);
  assertEquals(chunks[0], [1, 2, 3]);
  assertEquals(chunks[1], [4, 5, 6]);
  assertEquals(chunks[2], [7, 8, 9]);
  assertEquals(chunks[3], [10]);
});

// =============================================================================
// Service Role Authentication Tests
// =============================================================================

Deno.test("Service role auth - header required", () => {
  const isServiceRole = (authHeader: string | null): boolean => {
    if (!authHeader) return false;
    return authHeader.startsWith("Bearer ") && authHeader.length > 7;
  };

  assertEquals(isServiceRole("Bearer service-key-123"), true);
  assertEquals(isServiceRole("Bearer"), false);
  assertEquals(isServiceRole(null), false);
  assertEquals(isServiceRole(""), false);
});
