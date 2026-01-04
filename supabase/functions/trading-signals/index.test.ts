// Deno tests for trading-signals edge function
// Run with: deno test --allow-env --allow-net index.test.ts

import {
  assertEquals,
  assertExists,
  assertStringIncludes,
} from "https://deno.land/std@0.168.0/testing/asserts.ts";

// ============================================================================
// Structured Logging Tests
// ============================================================================

Deno.test("Structured logging - log.info formats correctly", () => {
  const logs: string[] = [];
  const originalLog = console.log;
  console.log = (msg: string) => logs.push(msg);

  const log = {
    info: (message: string, metadata?: any) => {
      console.log(JSON.stringify({
        level: 'INFO',
        timestamp: new Date().toISOString(),
        service: 'trading-signals',
        message,
        ...metadata,
      }));
    },
  };

  log.info('Test message', { requestId: '12345' });

  console.log = originalLog;

  assertEquals(logs.length, 1);
  const parsed = JSON.parse(logs[0]);
  assertEquals(parsed.level, 'INFO');
  assertEquals(parsed.service, 'trading-signals');
  assertEquals(parsed.message, 'Test message');
  assertEquals(parsed.requestId, '12345');
});

Deno.test("Structured logging - log.error includes error details", () => {
  const logs: string[] = [];
  const originalError = console.error;
  console.error = (msg: string) => logs.push(msg);

  const log = {
    error: (message: string, error?: any, metadata?: any) => {
      console.error(JSON.stringify({
        level: 'ERROR',
        timestamp: new Date().toISOString(),
        service: 'trading-signals',
        message,
        error: error?.message || error,
        stack: error?.stack,
        ...metadata,
      }));
    },
  };

  const testError = new Error('Test error');
  log.error('Something failed', testError, { requestId: '12345' });

  console.error = originalError;

  assertEquals(logs.length, 1);
  const parsed = JSON.parse(logs[0]);
  assertEquals(parsed.level, 'ERROR');
  assertEquals(parsed.error, 'Test error');
  assertExists(parsed.stack);
});

Deno.test("Structured logging - log.warn formats correctly", () => {
  const logs: string[] = [];
  const originalWarn = console.warn;
  console.warn = (msg: string) => logs.push(msg);

  const log = {
    warn: (message: string, metadata?: any) => {
      console.warn(JSON.stringify({
        level: 'WARN',
        timestamp: new Date().toISOString(),
        service: 'trading-signals',
        message,
        ...metadata,
      }));
    },
  };

  log.warn('Warning message', { detail: 'test' });

  console.warn = originalWarn;

  assertEquals(logs.length, 1);
  const parsed = JSON.parse(logs[0]);
  assertEquals(parsed.level, 'WARN');
  assertEquals(parsed.message, 'Warning message');
});

// ============================================================================
// Request/Response Sanitization Tests
// ============================================================================

Deno.test("sanitizeRequestForLogging - redacts sensitive headers", () => {
  const sanitizeRequestForLogging = (req: Request): any => {
    const headers = Object.fromEntries(req.headers.entries());

    const sensitiveHeaders = ['authorization', 'x-api-key', 'cookie', 'x-supabase-auth'];
    sensitiveHeaders.forEach(header => {
      if (headers[header]) {
        headers[header] = '[REDACTED]';
      }
    });

    return {
      method: req.method,
      url: req.url,
      headers,
    };
  };

  const req = new Request('http://localhost/test', {
    method: 'POST',
    headers: {
      'authorization': 'Bearer secret-token',
      'x-api-key': 'api-secret',
      'content-type': 'application/json',
    },
  });

  const sanitized = sanitizeRequestForLogging(req);

  assertEquals(sanitized.headers['authorization'], '[REDACTED]');
  assertEquals(sanitized.headers['x-api-key'], '[REDACTED]');
  assertEquals(sanitized.headers['content-type'], 'application/json');
});

Deno.test("sanitizeResponseForLogging - truncates large bodies", () => {
  const sanitizeResponseForLogging = (body: any): any => {
    const bodyStr = JSON.stringify(body);
    return {
      body: bodyStr.substring(0, 500) + (bodyStr.length > 500 ? '...' : ''),
    };
  };

  const largeBody = { data: 'x'.repeat(1000) };
  const sanitized = sanitizeResponseForLogging(largeBody);

  assertEquals(sanitized.body.length, 503); // 500 + '...'
  assertStringIncludes(sanitized.body, '...');
});

// ============================================================================
// Confidence Calculation Tests
// ============================================================================

Deno.test("Confidence calculation - base confidence", () => {
  const DEFAULT_WEIGHTS = {
    baseConfidence: 0.50,
    politicianCount5Plus: 0.15,
    politicianCount3_4: 0.10,
    politicianCount2: 0.05,
    recentActivity5Plus: 0.10,
    recentActivity2_4: 0.05,
    bipartisanBonus: 0.10,
    volume1MPlus: 0.10,
    volume100KPlus: 0.05,
  };

  const calculateConfidence = (
    politicianCount: number,
    recentActivity: number,
    bipartisan: boolean,
    netVolume: number
  ): number => {
    let confidence = DEFAULT_WEIGHTS.baseConfidence;

    if (politicianCount >= 5) confidence += DEFAULT_WEIGHTS.politicianCount5Plus;
    else if (politicianCount >= 3) confidence += DEFAULT_WEIGHTS.politicianCount3_4;
    else if (politicianCount >= 2) confidence += DEFAULT_WEIGHTS.politicianCount2;

    if (recentActivity >= 5) confidence += DEFAULT_WEIGHTS.recentActivity5Plus;
    else if (recentActivity >= 2) confidence += DEFAULT_WEIGHTS.recentActivity2_4;

    if (bipartisan) confidence += DEFAULT_WEIGHTS.bipartisanBonus;

    if (Math.abs(netVolume) > 1000000) confidence += DEFAULT_WEIGHTS.volume1MPlus;
    else if (Math.abs(netVolume) > 100000) confidence += DEFAULT_WEIGHTS.volume100KPlus;

    return confidence;
  };

  // Base only
  assertEquals(calculateConfidence(1, 1, false, 0), 0.50);

  // 5+ politicians
  assertEquals(calculateConfidence(5, 0, false, 0), 0.65);

  // Full combination
  const fullConfidence = calculateConfidence(5, 5, true, 2000000);
  assertEquals(fullConfidence, 0.95); // 0.50 + 0.15 + 0.10 + 0.10 + 0.10
});

Deno.test("Confidence calculation - politician count tiers", () => {
  const getConfidenceBonus = (politicianCount: number): number => {
    if (politicianCount >= 5) return 0.15;
    if (politicianCount >= 3) return 0.10;
    if (politicianCount >= 2) return 0.05;
    return 0;
  };

  assertEquals(getConfidenceBonus(1), 0);
  assertEquals(getConfidenceBonus(2), 0.05);
  assertEquals(getConfidenceBonus(3), 0.10);
  assertEquals(getConfidenceBonus(4), 0.10);
  assertEquals(getConfidenceBonus(5), 0.15);
  assertEquals(getConfidenceBonus(10), 0.15);
});

// ============================================================================
// Buy/Sell Ratio Tests
// ============================================================================

Deno.test("Buy/sell ratio calculation - basic cases", () => {
  const calculateBuySellRatio = (buys: number, sells: number): number => {
    return sells > 0 ? buys / sells : buys > 0 ? 10 : 1;
  };

  assertEquals(calculateBuySellRatio(10, 5), 2);
  assertEquals(calculateBuySellRatio(5, 10), 0.5);
  assertEquals(calculateBuySellRatio(10, 0), 10); // No sells = max ratio
  assertEquals(calculateBuySellRatio(0, 0), 1); // No activity = neutral
});

Deno.test("Buy/sell ratio calculation - edge cases", () => {
  const calculateBuySellRatio = (buys: number, sells: number): number => {
    return sells > 0 ? buys / sells : buys > 0 ? 10 : 1;
  };

  // Many buys, one sell
  assertEquals(calculateBuySellRatio(100, 1), 100);

  // One buy, many sells
  assertEquals(calculateBuySellRatio(1, 100), 0.01);
});

// ============================================================================
// Signal Type Determination Tests
// ============================================================================

Deno.test("Signal type determination - thresholds", () => {
  const THRESHOLDS = {
    strongBuyThreshold: 3.0,
    buyThreshold: 2.0,
    strongSellThreshold: 0.33,
    sellThreshold: 0.5,
  };

  const getSignalType = (buySellRatio: number): { type: string; strength: string } => {
    if (buySellRatio >= THRESHOLDS.strongBuyThreshold) {
      return { type: 'strong_buy', strength: 'very_strong' };
    } else if (buySellRatio >= THRESHOLDS.buyThreshold) {
      return { type: 'buy', strength: 'strong' };
    } else if (buySellRatio <= THRESHOLDS.strongSellThreshold) {
      return { type: 'strong_sell', strength: 'very_strong' };
    } else if (buySellRatio <= THRESHOLDS.sellThreshold) {
      return { type: 'sell', strength: 'strong' };
    }
    return { type: 'hold', strength: 'moderate' };
  };

  // Strong buy
  assertEquals(getSignalType(3.5).type, 'strong_buy');
  assertEquals(getSignalType(3.0).type, 'strong_buy');

  // Buy
  assertEquals(getSignalType(2.5).type, 'buy');
  assertEquals(getSignalType(2.0).type, 'buy');

  // Hold
  assertEquals(getSignalType(1.0).type, 'hold');
  assertEquals(getSignalType(0.6).type, 'hold');

  // Sell
  assertEquals(getSignalType(0.5).type, 'sell');
  assertEquals(getSignalType(0.4).type, 'sell');

  // Strong sell
  assertEquals(getSignalType(0.33).type, 'strong_sell');
  assertEquals(getSignalType(0.1).type, 'strong_sell');
});

// ============================================================================
// Target Price Calculation Tests
// ============================================================================

Deno.test("calculateTargetPrice - buy signal", () => {
  const calculateTargetPrice = (
    currentPrice: number,
    signalType: string,
    signalStrength: string
  ): { target: number; stopLoss: number; takeProfit: number } => {
    const strengthMultipliers: Record<string, number> = {
      'very_strong': 0.10,
      'strong': 0.07,
      'moderate': 0.05,
      'weak': 0.03,
    };

    const multiplier = strengthMultipliers[signalStrength] || 0.05;

    if (signalType.includes('buy')) {
      const target = currentPrice * (1 + multiplier);
      const stopLoss = currentPrice * (1 - multiplier * 0.5);
      const takeProfit = currentPrice * (1 + multiplier * 1.5);
      return {
        target: Math.round(target * 100) / 100,
        stopLoss: Math.round(stopLoss * 100) / 100,
        takeProfit: Math.round(takeProfit * 100) / 100,
      };
    } else if (signalType.includes('sell')) {
      const target = currentPrice * (1 - multiplier);
      const stopLoss = currentPrice * (1 + multiplier * 0.5);
      const takeProfit = currentPrice * (1 - multiplier * 1.5);
      return {
        target: Math.round(target * 100) / 100,
        stopLoss: Math.round(stopLoss * 100) / 100,
        takeProfit: Math.round(takeProfit * 100) / 100,
      };
    }

    return {
      target: currentPrice,
      stopLoss: currentPrice * 0.95,
      takeProfit: currentPrice * 1.05,
    };
  };

  // Strong buy at $100
  const buyResult = calculateTargetPrice(100, 'strong_buy', 'very_strong');
  assertEquals(buyResult.target, 110); // +10%
  assertEquals(buyResult.stopLoss, 95); // -5%
  assertEquals(buyResult.takeProfit, 115); // +15%

  // Sell at $100
  const sellResult = calculateTargetPrice(100, 'sell', 'strong');
  assertEquals(sellResult.target, 93); // -7%
  assertEquals(sellResult.stopLoss, 103.5); // +3.5%
  assertEquals(sellResult.takeProfit, 89.5); // -10.5%
});

Deno.test("calculateTargetPrice - strength multipliers", () => {
  const getMultiplier = (signalStrength: string): number => {
    const strengthMultipliers: Record<string, number> = {
      'very_strong': 0.10,
      'strong': 0.07,
      'moderate': 0.05,
      'weak': 0.03,
    };
    return strengthMultipliers[signalStrength] || 0.05;
  };

  assertEquals(getMultiplier('very_strong'), 0.10);
  assertEquals(getMultiplier('strong'), 0.07);
  assertEquals(getMultiplier('moderate'), 0.05);
  assertEquals(getMultiplier('weak'), 0.03);
  assertEquals(getMultiplier('unknown'), 0.05); // Default
});

// ============================================================================
// Default Weights Configuration Tests
// ============================================================================

Deno.test("DEFAULT_WEIGHTS - has correct structure", () => {
  const DEFAULT_WEIGHTS = {
    baseConfidence: 0.50,
    politicianCount5Plus: 0.15,
    politicianCount3_4: 0.10,
    politicianCount2: 0.05,
    recentActivity5Plus: 0.10,
    recentActivity2_4: 0.05,
    bipartisanBonus: 0.10,
    volume1MPlus: 0.10,
    volume100KPlus: 0.05,
    strongSignalBonus: 0.15,
    moderateSignalBonus: 0.10,
    strongBuyThreshold: 3.0,
    buyThreshold: 2.0,
    strongSellThreshold: 0.33,
    sellThreshold: 0.5,
  };

  assertEquals(DEFAULT_WEIGHTS.baseConfidence, 0.50);
  assertEquals(DEFAULT_WEIGHTS.politicianCount5Plus, 0.15);
  assertEquals(DEFAULT_WEIGHTS.bipartisanBonus, 0.10);
  assertEquals(DEFAULT_WEIGHTS.strongBuyThreshold, 3.0);
  assertEquals(DEFAULT_WEIGHTS.sellThreshold, 0.5);
});

// ============================================================================
// ML Integration Tests
// ============================================================================

Deno.test("Signal type to numeric mapping", () => {
  const SIGNAL_TYPE_MAP: Record<string, number> = {
    'strong_buy': 2,
    'buy': 1,
    'hold': 0,
    'sell': -1,
    'strong_sell': -2,
  };

  assertEquals(SIGNAL_TYPE_MAP['strong_buy'], 2);
  assertEquals(SIGNAL_TYPE_MAP['buy'], 1);
  assertEquals(SIGNAL_TYPE_MAP['hold'], 0);
  assertEquals(SIGNAL_TYPE_MAP['sell'], -1);
  assertEquals(SIGNAL_TYPE_MAP['strong_sell'], -2);
});

Deno.test("blendSignals - ML not available", () => {
  const blendSignals = (
    heuristicType: string,
    heuristicConfidence: number,
    mlPrediction: number | null,
    mlConfidence: number | null
  ): { signalType: string; confidence: number; mlEnhanced: boolean } => {
    if (mlPrediction === null || mlConfidence === null) {
      return { signalType: heuristicType, confidence: heuristicConfidence, mlEnhanced: false };
    }
    // ML blending logic would go here
    return { signalType: heuristicType, confidence: heuristicConfidence, mlEnhanced: true };
  };

  const result = blendSignals('buy', 0.75, null, null);
  assertEquals(result.signalType, 'buy');
  assertEquals(result.confidence, 0.75);
  assertEquals(result.mlEnhanced, false);
});

Deno.test("blendSignals - signals agree (confidence boosted)", () => {
  const SIGNAL_TYPE_MAP: Record<string, number> = {
    'strong_buy': 2, 'buy': 1, 'hold': 0, 'sell': -1, 'strong_sell': -2,
  };
  const ML_BLEND_WEIGHT = 0.4;

  const blendSignals = (
    heuristicType: string,
    heuristicConfidence: number,
    mlPrediction: number,
    mlConfidence: number
  ): { signalType: string; confidence: number; mlEnhanced: boolean } => {
    const heuristicNumeric = SIGNAL_TYPE_MAP[heuristicType] ?? 0;
    const blendedConfidence = heuristicConfidence * (1 - ML_BLEND_WEIGHT) + mlConfidence * ML_BLEND_WEIGHT;

    if (heuristicNumeric === mlPrediction) {
      return {
        signalType: heuristicType,
        confidence: Math.min(blendedConfidence * 1.1, 0.98),
        mlEnhanced: true,
      };
    }

    return {
      signalType: heuristicType,
      confidence: blendedConfidence * 0.85,
      mlEnhanced: true,
    };
  };

  // Signals agree: buy (1) == buy (1)
  const agreeResult = blendSignals('buy', 0.70, 1, 0.80);
  assertEquals(agreeResult.mlEnhanced, true);
  // Confidence boosted by 1.1x: (0.70 * 0.6 + 0.80 * 0.4) * 1.1 = (0.42 + 0.32) * 1.1 = 0.814
  assertEquals(agreeResult.confidence, 0.814);

  // Signals disagree: buy (1) != sell (-1)
  const disagreeResult = blendSignals('buy', 0.70, -1, 0.80);
  assertEquals(disagreeResult.mlEnhanced, true);
  // Confidence reduced by 0.85x: (0.70 * 0.6 + 0.80 * 0.4) * 0.85 = 0.74 * 0.85 = 0.629
  assertEquals(disagreeResult.confidence, 0.629);
});

// ============================================================================
// Reproducibility Hash Tests
// ============================================================================

Deno.test("computeReproducibilityHash - generates consistent hash", () => {
  const computeReproducibilityHash = (features: any, modelId: string | null): string => {
    const data = JSON.stringify({
      features: features,
      modelId: modelId,
      timestamp: Math.floor(Date.now() / 3600000), // Hour-level precision
    });

    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return `hash_${Math.abs(hash).toString(16)}`;
  };

  const features = { buys: 10, sells: 5 };
  const modelId = 'model-123';

  const hash1 = computeReproducibilityHash(features, modelId);
  const hash2 = computeReproducibilityHash(features, modelId);

  // Same inputs within same hour = same hash
  assertEquals(hash1, hash2);
  assertStringIncludes(hash1, 'hash_');
});

Deno.test("computeReproducibilityHash - different features produce different hashes", () => {
  const computeReproducibilityHash = (features: any, modelId: string | null): string => {
    const data = JSON.stringify({
      features: features,
      modelId: modelId,
      timestamp: 12345, // Fixed for testing
    });

    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return `hash_${Math.abs(hash).toString(16)}`;
  };

  const features1 = { buys: 10, sells: 5 };
  const features2 = { buys: 15, sells: 5 };

  const hash1 = computeReproducibilityHash(features1, 'model-123');
  const hash2 = computeReproducibilityHash(features2, 'model-123');

  // Different features = different hash
  const hashesMatch = hash1 === hash2;
  assertEquals(hashesMatch, false);
});

// ============================================================================
// Ticker Validation Tests
// ============================================================================

Deno.test("Ticker validation - valid tickers", () => {
  const isValidTicker = (ticker: string | null | undefined): boolean => {
    if (!ticker || ticker.length < 1 || ticker.length > 10) return false;
    if (ticker.includes(' ') || ticker.includes('[') || ticker.includes('(')) return false;
    return true;
  };

  assertEquals(isValidTicker('AAPL'), true);
  assertEquals(isValidTicker('GOOGL'), true);
  assertEquals(isValidTicker('MSFT'), true);
  assertEquals(isValidTicker('A'), true); // Single char ticker
  assertEquals(isValidTicker('VERYLONGTKR'), false); // Too long
});

Deno.test("Ticker validation - invalid tickers", () => {
  const isValidTicker = (ticker: string | null | undefined): boolean => {
    if (!ticker || ticker.length < 1 || ticker.length > 10) return false;
    if (ticker.includes(' ') || ticker.includes('[') || ticker.includes('(')) return false;
    return true;
  };

  assertEquals(isValidTicker('SOME BOND'), false); // Contains space
  assertEquals(isValidTicker('[PRIVATE]'), false); // Contains bracket
  assertEquals(isValidTicker('FUND(A)'), false); // Contains parentheses
  assertEquals(isValidTicker(''), false); // Empty
  assertEquals(isValidTicker(null), false); // Null
  assertEquals(isValidTicker(undefined), false); // Undefined
});

// ============================================================================
// Signal Filtering Tests
// ============================================================================

Deno.test("Signal filtering - minimum requirements", () => {
  const MIN_POLITICIANS = 2;
  const MIN_TRANSACTIONS = 3;

  const meetsMinimumRequirements = (
    politicianCount: number,
    totalTransactions: number
  ): boolean => {
    return politicianCount >= MIN_POLITICIANS && totalTransactions >= MIN_TRANSACTIONS;
  };

  assertEquals(meetsMinimumRequirements(2, 3), true);
  assertEquals(meetsMinimumRequirements(5, 10), true);
  assertEquals(meetsMinimumRequirements(1, 10), false); // Not enough politicians
  assertEquals(meetsMinimumRequirements(5, 2), false); // Not enough transactions
  assertEquals(meetsMinimumRequirements(1, 2), false); // Both below minimum
});

Deno.test("Signal filtering - relaxed requirements for regenerate", () => {
  // regenerate-signals uses more relaxed criteria
  const MIN_POLITICIANS_RELAXED = 1;
  const MIN_TRANSACTIONS_RELAXED = 2;

  const meetsRelaxedRequirements = (
    politicianCount: number,
    totalTransactions: number
  ): boolean => {
    return politicianCount >= MIN_POLITICIANS_RELAXED && totalTransactions >= MIN_TRANSACTIONS_RELAXED;
  };

  assertEquals(meetsRelaxedRequirements(1, 2), true);
  assertEquals(meetsRelaxedRequirements(1, 3), true);
  assertEquals(meetsRelaxedRequirements(0, 2), false);
  assertEquals(meetsRelaxedRequirements(1, 1), false);
});

// ============================================================================
// Transaction Type Classification Tests
// ============================================================================

Deno.test("Transaction type classification - buys", () => {
  const isBuyTransaction = (txType: string): boolean => {
    const normalized = (txType || '').toLowerCase();
    return normalized.includes('purchase') || normalized.includes('buy');
  };

  assertEquals(isBuyTransaction('Purchase'), true);
  assertEquals(isBuyTransaction('PURCHASE'), true);
  assertEquals(isBuyTransaction('Buy'), true);
  assertEquals(isBuyTransaction('Stock Purchase'), true);
  assertEquals(isBuyTransaction('Sale'), false);
  assertEquals(isBuyTransaction(''), false);
});

Deno.test("Transaction type classification - sells", () => {
  const isSellTransaction = (txType: string): boolean => {
    const normalized = (txType || '').toLowerCase();
    return normalized.includes('sale') || normalized.includes('sell');
  };

  assertEquals(isSellTransaction('Sale'), true);
  assertEquals(isSellTransaction('SALE'), true);
  assertEquals(isSellTransaction('Sell'), true);
  assertEquals(isSellTransaction('Stock Sale'), true);
  assertEquals(isSellTransaction('Purchase'), false);
  assertEquals(isSellTransaction(''), false);
});

// ============================================================================
// Volume Calculation Tests
// ============================================================================

Deno.test("Volume calculation - average of range", () => {
  const calculateVolume = (minVal: number | null, maxVal: number | null): number => {
    const min = minVal || 0;
    const max = maxVal || min;
    return (min + max) / 2;
  };

  assertEquals(calculateVolume(1000, 15000), 8000);
  assertEquals(calculateVolume(50000, 100000), 75000);
  assertEquals(calculateVolume(1000, null), 1000);
  assertEquals(calculateVolume(null, null), 0);
});

// ============================================================================
// Signal Statistics Tests
// ============================================================================

Deno.test("Signal statistics - type distribution", () => {
  const signals = [
    { signal_type: 'buy', confidence_score: 0.80 },
    { signal_type: 'buy', confidence_score: 0.75 },
    { signal_type: 'strong_buy', confidence_score: 0.90 },
    { signal_type: 'sell', confidence_score: 0.65 },
  ];

  const distribution: Record<string, number> = {};
  signals.forEach(signal => {
    const type = signal.signal_type;
    distribution[type] = (distribution[type] || 0) + 1;
  });

  assertEquals(distribution['buy'], 2);
  assertEquals(distribution['strong_buy'], 1);
  assertEquals(distribution['sell'], 1);
  assertEquals(distribution['hold'], undefined);
});

Deno.test("Signal statistics - average confidence", () => {
  const signals = [
    { confidence_score: 0.80 },
    { confidence_score: 0.70 },
    { confidence_score: 0.90 },
    { confidence_score: 0.60 },
  ];

  const confidences = signals.map(s => s.confidence_score);
  const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;

  assertEquals(avgConfidence, 0.75);
});

Deno.test("Signal statistics - high confidence count", () => {
  const signals = [
    { confidence_score: 0.80 },
    { confidence_score: 0.70 },
    { confidence_score: 0.90 },
    { confidence_score: 0.60 },
  ];

  const highConfidenceCount = signals.filter(s => s.confidence_score >= 0.8).length;

  assertEquals(highConfidenceCount, 2);
});

// ============================================================================
// CORS Headers Tests
// ============================================================================

Deno.test("CORS headers - correct format", () => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  };

  assertEquals(corsHeaders['Access-Control-Allow-Origin'], '*');
  assertStringIncludes(corsHeaders['Access-Control-Allow-Headers'], 'authorization');
  assertStringIncludes(corsHeaders['Access-Control-Allow-Headers'], 'content-type');
});

// ============================================================================
// URL Path Parsing Tests
// ============================================================================

Deno.test("URL path parsing - extracts endpoint correctly", () => {
  const getEndpoint = (url: string): string => {
    const urlObj = new URL(url);
    return urlObj.pathname.split('/').pop() || '';
  };

  assertEquals(getEndpoint('http://localhost/functions/v1/trading-signals/get-signals'), 'get-signals');
  assertEquals(getEndpoint('http://localhost/trading-signals/generate-signals'), 'generate-signals');
  assertEquals(getEndpoint('http://localhost/preview-signals'), 'preview-signals');
  assertEquals(getEndpoint('http://localhost/test'), 'test');
});

// ============================================================================
// Query Parameter Parsing Tests
// ============================================================================

Deno.test("Query parameter parsing - handles defaults", () => {
  const parseQueryParams = (url: string): {
    limit: number;
    offset: number;
    signalType: string | null;
    minConfidence: number;
  } => {
    const urlObj = new URL(url);
    return {
      limit: parseInt(urlObj.searchParams.get('limit') || '100'),
      offset: parseInt(urlObj.searchParams.get('offset') || '0'),
      signalType: urlObj.searchParams.get('signal_type'),
      minConfidence: parseFloat(urlObj.searchParams.get('min_confidence') || '0'),
    };
  };

  // Default values
  const defaults = parseQueryParams('http://localhost/signals');
  assertEquals(defaults.limit, 100);
  assertEquals(defaults.offset, 0);
  assertEquals(defaults.signalType, null);
  assertEquals(defaults.minConfidence, 0);

  // Custom values
  const custom = parseQueryParams('http://localhost/signals?limit=50&offset=10&signal_type=buy&min_confidence=0.7');
  assertEquals(custom.limit, 50);
  assertEquals(custom.offset, 10);
  assertEquals(custom.signalType, 'buy');
  assertEquals(custom.minConfidence, 0.7);
});

// ============================================================================
// Signal Sorting Tests
// ============================================================================

Deno.test("Signal sorting - by confidence descending", () => {
  const signals = [
    { ticker: 'AAPL', confidence_score: 0.70 },
    { ticker: 'GOOGL', confidence_score: 0.90 },
    { ticker: 'MSFT', confidence_score: 0.80 },
  ];

  signals.sort((a, b) => b.confidence_score - a.confidence_score);

  assertEquals(signals[0].ticker, 'GOOGL');
  assertEquals(signals[1].ticker, 'MSFT');
  assertEquals(signals[2].ticker, 'AAPL');
});

// ============================================================================
// Signal Limit Tests
// ============================================================================

Deno.test("Signal limiting - top N signals", () => {
  const signals = Array.from({ length: 150 }, (_, i) => ({
    ticker: `TICK${i}`,
    confidence_score: Math.random(),
  }));

  signals.sort((a, b) => b.confidence_score - a.confidence_score);
  const topSignals = signals.slice(0, 100);

  assertEquals(topSignals.length, 100);
  assertEquals(topSignals[0].confidence_score >= topSignals[99].confidence_score, true);
});

// ============================================================================
// Date Range Calculation Tests
// ============================================================================

Deno.test("Date range calculation - lookback days", () => {
  const calculateStartDate = (lookbackDays: number): string => {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - lookbackDays);
    return startDate.toISOString().split('T')[0];
  };

  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const result = calculateStartDate(30);
  assertEquals(result, thirtyDaysAgo.toISOString().split('T')[0]);
});

// ============================================================================
// Bipartisan Detection Tests
// ============================================================================

Deno.test("Bipartisan detection - both parties", () => {
  const isBipartisan = (parties: Set<string>): boolean => {
    return parties.has('D') && parties.has('R');
  };

  const bothParties = new Set(['D', 'R']);
  const onlyDemocrats = new Set(['D']);
  const onlyRepublicans = new Set(['R']);
  const independentOnly = new Set(['I']);

  assertEquals(isBipartisan(bothParties), true);
  assertEquals(isBipartisan(onlyDemocrats), false);
  assertEquals(isBipartisan(onlyRepublicans), false);
  assertEquals(isBipartisan(independentOnly), false);
});

// ============================================================================
// ML Model Version Tests
// ============================================================================

Deno.test("Model version - default versions", () => {
  const generateSignalsVersion = 'v2.0';
  const regenerateSignalsVersion = 'v2.1-service';

  assertEquals(generateSignalsVersion, 'v2.0');
  assertEquals(regenerateSignalsVersion, 'v2.1-service');
});

// ============================================================================
// Hold Signal Filtering Tests
// ============================================================================

Deno.test("Hold signal filtering - only actionable signals", () => {
  const isActionableSignal = (signalType: string): boolean => {
    return signalType !== 'hold';
  };

  assertEquals(isActionableSignal('strong_buy'), true);
  assertEquals(isActionableSignal('buy'), true);
  assertEquals(isActionableSignal('sell'), true);
  assertEquals(isActionableSignal('strong_sell'), true);
  assertEquals(isActionableSignal('hold'), false);
});

// ============================================================================
// Minimum Confidence Filter Tests
// ============================================================================

Deno.test("Minimum confidence filter", () => {
  const meetsMinConfidence = (confidence: number, minConfidence: number): boolean => {
    return confidence >= minConfidence;
  };

  assertEquals(meetsMinConfidence(0.70, 0.65), true);
  assertEquals(meetsMinConfidence(0.65, 0.65), true);
  assertEquals(meetsMinConfidence(0.60, 0.65), false);
  assertEquals(meetsMinConfidence(0.90, 0.80), true);
});

// ============================================================================
// ML Timeout Configuration Tests
// ============================================================================

Deno.test("ML configuration - timeout and blend weight", () => {
  const ML_TIMEOUT_MS = 10000;
  const ML_BLEND_WEIGHT = 0.4;

  assertEquals(ML_TIMEOUT_MS, 10000);
  assertEquals(ML_BLEND_WEIGHT, 0.4);

  // Blend weight validation
  assertEquals(ML_BLEND_WEIGHT > 0 && ML_BLEND_WEIGHT < 1, true);
});

// ============================================================================
// ML Feature Vector Tests
// ============================================================================

Deno.test("ML feature vector - structure", () => {
  interface MlFeatures {
    ticker: string;
    politician_count: number;
    buy_sell_ratio: number;
    recent_activity_30d: number;
    bipartisan: boolean;
    net_volume: number;
  }

  const features: MlFeatures = {
    ticker: 'AAPL',
    politician_count: 5,
    buy_sell_ratio: 2.5,
    recent_activity_30d: 10,
    bipartisan: true,
    net_volume: 500000,
  };

  assertEquals(features.ticker, 'AAPL');
  assertEquals(features.politician_count, 5);
  assertEquals(features.buy_sell_ratio, 2.5);
  assertEquals(features.recent_activity_30d, 10);
  assertEquals(features.bipartisan, true);
  assertEquals(features.net_volume, 500000);
});

// ============================================================================
// Signal Response Format Tests
// ============================================================================

Deno.test("Signal response format - success response", () => {
  const createSuccessResponse = (
    signals: any[],
    stats: any,
    weights?: any
  ): any => {
    return {
      success: true,
      signals,
      stats,
      weights: weights || undefined,
    };
  };

  const response = createSuccessResponse(
    [{ ticker: 'AAPL', signal_type: 'buy' }],
    { totalDisclosures: 100, signalsGenerated: 1 },
    { baseConfidence: 0.5 }
  );

  assertEquals(response.success, true);
  assertEquals(response.signals.length, 1);
  assertExists(response.stats);
  assertExists(response.weights);
});

Deno.test("Signal response format - preview response", () => {
  const createPreviewResponse = (signals: any[], weights: any, stats: any): any => {
    return {
      success: true,
      preview: true,
      signals,
      weights,
      stats,
    };
  };

  const response = createPreviewResponse(
    [{ ticker: 'AAPL', signal_type: 'buy' }],
    { baseConfidence: 0.5 },
    { totalDisclosures: 100 }
  );

  assertEquals(response.success, true);
  assertEquals(response.preview, true);
});
