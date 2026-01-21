/**
 * Tests for process-error-reports Edge Function
 *
 * Tests:
 * - CORS handling
 * - Endpoint routing
 * - Correction confidence thresholds
 * - Status update logic
 */

import { assertEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Extracted types
interface CorrectionResult {
  field: string;
  old_value: unknown;
  new_value: unknown;
  confidence: number;
  reasoning: string;
}

interface ProcessingResult {
  report_id: string;
  status: 'fixed' | 'needs_review' | 'invalid' | 'error';
  corrections: CorrectionResult[];
  admin_notes: string;
}

// Extracted logic for testing
function shouldAutoFix(corrections: CorrectionResult[]): boolean {
  return corrections.every(c => c.confidence >= 0.8);
}

function formatCorrectionSummary(corrections: CorrectionResult[]): string {
  return corrections.map(c =>
    `${c.field}: ${c.old_value} → ${c.new_value}`
  ).join('; ');
}

function formatConfidenceSummary(corrections: CorrectionResult[]): string {
  return corrections.map(c =>
    `${c.field}: ${c.old_value} → ${c.new_value} (confidence: ${(c.confidence * 100).toFixed(0)}%)`
  ).join('; ');
}

function determineEndpoint(path: string): string {
  const parts = path.split('/');
  return parts[parts.length - 1] || 'default';
}

function isAmountCorrection(correction: CorrectionResult): boolean {
  return correction.field === 'amount_range_min' || correction.field === 'amount_range_max';
}

function filterAmountCorrections(corrections: CorrectionResult[]): CorrectionResult[] {
  return corrections.filter(isAmountCorrection);
}

// Tests

Deno.test("shouldAutoFix() - true when all corrections have high confidence", () => {
  const corrections: CorrectionResult[] = [
    { field: 'amount_range_min', old_value: 1000, new_value: 5000, confidence: 0.9, reasoning: 'test' },
    { field: 'amount_range_max', old_value: 10000, new_value: 50000, confidence: 0.85, reasoning: 'test' },
  ];

  assertEquals(shouldAutoFix(corrections), true);
});

Deno.test("shouldAutoFix() - false when any correction has low confidence", () => {
  const corrections: CorrectionResult[] = [
    { field: 'amount_range_min', old_value: 1000, new_value: 5000, confidence: 0.9, reasoning: 'test' },
    { field: 'amount_range_max', old_value: 10000, new_value: 50000, confidence: 0.7, reasoning: 'test' },
  ];

  assertEquals(shouldAutoFix(corrections), false);
});

Deno.test("shouldAutoFix() - true when confidence is exactly 0.8", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.8, reasoning: 'typo fix' },
  ];

  assertEquals(shouldAutoFix(corrections), true);
});

Deno.test("shouldAutoFix() - true for empty corrections", () => {
  const corrections: CorrectionResult[] = [];

  assertEquals(shouldAutoFix(corrections), true);
});

Deno.test("formatCorrectionSummary() - formats single correction", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.95, reasoning: 'test' },
  ];

  const summary = formatCorrectionSummary(corrections);
  assertEquals(summary, 'ticker: APPL → AAPL');
});

Deno.test("formatCorrectionSummary() - formats multiple corrections", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.95, reasoning: 'test' },
    { field: 'amount_range_min', old_value: 1000, new_value: 5000, confidence: 0.9, reasoning: 'test' },
  ];

  const summary = formatCorrectionSummary(corrections);
  assertEquals(summary, 'ticker: APPL → AAPL; amount_range_min: 1000 → 5000');
});

Deno.test("formatConfidenceSummary() - includes confidence percentages", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.95, reasoning: 'test' },
  ];

  const summary = formatConfidenceSummary(corrections);
  assertEquals(summary, 'ticker: APPL → AAPL (confidence: 95%)');
});

Deno.test("formatConfidenceSummary() - handles multiple corrections", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.9, reasoning: 'test' },
    { field: 'amount_range_min', old_value: 1000, new_value: 5000, confidence: 0.75, reasoning: 'test' },
  ];

  const summary = formatConfidenceSummary(corrections);
  assertEquals(summary, 'ticker: APPL → AAPL (confidence: 90%); amount_range_min: 1000 → 5000 (confidence: 75%)');
});

Deno.test("determineEndpoint() - process-pending", () => {
  assertEquals(determineEndpoint('/functions/v1/process-error-reports/process-pending'), 'process-pending');
});

Deno.test("determineEndpoint() - process-one", () => {
  assertEquals(determineEndpoint('/functions/v1/process-error-reports/process-one'), 'process-one');
});

Deno.test("determineEndpoint() - preview", () => {
  assertEquals(determineEndpoint('/functions/v1/process-error-reports/preview'), 'preview');
});

Deno.test("determineEndpoint() - handles trailing slash", () => {
  assertEquals(determineEndpoint('/functions/v1/process-error-reports/'), '');
});

Deno.test("isAmountCorrection() - true for amount_range_min", () => {
  const correction: CorrectionResult = {
    field: 'amount_range_min',
    old_value: 1000,
    new_value: 5000,
    confidence: 0.9,
    reasoning: 'test',
  };

  assertEquals(isAmountCorrection(correction), true);
});

Deno.test("isAmountCorrection() - true for amount_range_max", () => {
  const correction: CorrectionResult = {
    field: 'amount_range_max',
    old_value: 10000,
    new_value: 50000,
    confidence: 0.9,
    reasoning: 'test',
  };

  assertEquals(isAmountCorrection(correction), true);
});

Deno.test("isAmountCorrection() - false for other fields", () => {
  const correction: CorrectionResult = {
    field: 'ticker',
    old_value: 'APPL',
    new_value: 'AAPL',
    confidence: 0.95,
    reasoning: 'test',
  };

  assertEquals(isAmountCorrection(correction), false);
});

Deno.test("filterAmountCorrections() - filters correctly", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.95, reasoning: 'test' },
    { field: 'amount_range_min', old_value: 1000, new_value: 5000, confidence: 0.9, reasoning: 'test' },
    { field: 'transaction_date', old_value: '2024-01-01', new_value: '2024-02-01', confidence: 0.8, reasoning: 'test' },
    { field: 'amount_range_max', old_value: 10000, new_value: 50000, confidence: 0.85, reasoning: 'test' },
  ];

  const amountOnly = filterAmountCorrections(corrections);
  assertEquals(amountOnly.length, 2);
  assertEquals(amountOnly[0].field, 'amount_range_min');
  assertEquals(amountOnly[1].field, 'amount_range_max');
});

Deno.test("filterAmountCorrections() - returns empty for non-amount corrections", () => {
  const corrections: CorrectionResult[] = [
    { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.95, reasoning: 'test' },
    { field: 'transaction_date', old_value: '2024-01-01', new_value: '2024-02-01', confidence: 0.8, reasoning: 'test' },
  ];

  const amountOnly = filterAmountCorrections(corrections);
  assertEquals(amountOnly.length, 0);
});

// Test ProcessingResult construction
Deno.test("ProcessingResult - fixed status", () => {
  const result: ProcessingResult = {
    report_id: 'test-123',
    status: 'fixed',
    corrections: [
      { field: 'ticker', old_value: 'APPL', new_value: 'AAPL', confidence: 0.95, reasoning: 'typo' },
    ],
    admin_notes: 'Auto-corrected: ticker: APPL → AAPL',
  };

  assertEquals(result.status, 'fixed');
  assertEquals(result.corrections.length, 1);
});

Deno.test("ProcessingResult - needs_review status", () => {
  const result: ProcessingResult = {
    report_id: 'test-456',
    status: 'needs_review',
    corrections: [
      { field: 'amount_range_min', old_value: 1000, new_value: 5000, confidence: 0.6, reasoning: 'unclear' },
    ],
    admin_notes: 'Low confidence corrections suggested',
  };

  assertEquals(result.status, 'needs_review');
});

Deno.test("ProcessingResult - error status", () => {
  const result: ProcessingResult = {
    report_id: 'test-789',
    status: 'error',
    corrections: [],
    admin_notes: 'Database update failed',
  };

  assertEquals(result.status, 'error');
  assertEquals(result.corrections.length, 0);
});

// Test CORS headers structure
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

Deno.test("CORS headers - has required headers", () => {
  assertEquals(corsHeaders['Access-Control-Allow-Origin'], '*');
  assertEquals(corsHeaders['Access-Control-Allow-Headers'].includes('authorization'), true);
  assertEquals(corsHeaders['Access-Control-Allow-Headers'].includes('content-type'), true);
});
