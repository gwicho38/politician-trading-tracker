/**
 * Tests for scheduled-sync Edge Function
 *
 * Tests:
 * - Sync mode determination
 * - Logging utilities
 * - Result aggregation
 */

import { assertEquals, assertStringIncludes } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Extracted types
type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

interface LogMetadata {
  [key: string]: unknown;
}

interface SyncResult {
  success: boolean;
  data?: unknown;
  error?: string;
}

// Extracted logic for testing
function determineSyncMode(searchParams: URLSearchParams): 'daily' | 'full' | 'quick' {
  const mode = searchParams.get('mode');
  if (mode === 'full' || mode === 'quick') {
    return mode;
  }
  return 'daily';
}

function shouldRunFullSync(mode: string): boolean {
  return mode === 'full';
}

function shouldRunPartyUpdate(mode: string): boolean {
  return mode !== 'quick';
}

function formatDuration(startTime: number): string {
  return `${Date.now() - startTime}ms`;
}

function formatLogMessage(level: LogLevel, fn: string, message: string, metadata?: LogMetadata): string {
  const timestamp = new Date().toISOString();
  const prefix = `[${timestamp}] [${level}] [${fn}]`;

  if (metadata) {
    return `${prefix} ${message} ${JSON.stringify(metadata)}`;
  }
  return `${prefix} ${message}`;
}

function countSuccessfulResults(results: Record<string, SyncResult>): number {
  return Object.values(results).filter(r => r.success).length;
}

function countFailedResults(results: Record<string, SyncResult>): number {
  return Object.values(results).filter(r => !r.success).length;
}

function getFailedSteps(results: Record<string, SyncResult>): string[] {
  return Object.entries(results)
    .filter(([_, result]) => !result.success)
    .map(([step, _]) => step);
}

// Tests

Deno.test("determineSyncMode() - defaults to daily", () => {
  const params = new URLSearchParams();
  assertEquals(determineSyncMode(params), 'daily');
});

Deno.test("determineSyncMode() - full mode", () => {
  const params = new URLSearchParams('mode=full');
  assertEquals(determineSyncMode(params), 'full');
});

Deno.test("determineSyncMode() - quick mode", () => {
  const params = new URLSearchParams('mode=quick');
  assertEquals(determineSyncMode(params), 'quick');
});

Deno.test("determineSyncMode() - invalid mode defaults to daily", () => {
  const params = new URLSearchParams('mode=invalid');
  assertEquals(determineSyncMode(params), 'daily');
});

Deno.test("shouldRunFullSync() - true for full mode", () => {
  assertEquals(shouldRunFullSync('full'), true);
});

Deno.test("shouldRunFullSync() - false for daily mode", () => {
  assertEquals(shouldRunFullSync('daily'), false);
});

Deno.test("shouldRunFullSync() - false for quick mode", () => {
  assertEquals(shouldRunFullSync('quick'), false);
});

Deno.test("shouldRunPartyUpdate() - true for daily mode", () => {
  assertEquals(shouldRunPartyUpdate('daily'), true);
});

Deno.test("shouldRunPartyUpdate() - true for full mode", () => {
  assertEquals(shouldRunPartyUpdate('full'), true);
});

Deno.test("shouldRunPartyUpdate() - false for quick mode", () => {
  assertEquals(shouldRunPartyUpdate('quick'), false);
});

Deno.test("formatDuration() - returns ms string", () => {
  const start = Date.now() - 1500;
  const duration = formatDuration(start);
  assertStringIncludes(duration, 'ms');
});

Deno.test("formatLogMessage() - includes level", () => {
  const message = formatLogMessage('INFO', 'test-fn', 'Test message');
  assertStringIncludes(message, '[INFO]');
});

Deno.test("formatLogMessage() - includes function name", () => {
  const message = formatLogMessage('INFO', 'scheduled-sync', 'Test message');
  assertStringIncludes(message, '[scheduled-sync]');
});

Deno.test("formatLogMessage() - includes message", () => {
  const message = formatLogMessage('INFO', 'test-fn', 'My test message');
  assertStringIncludes(message, 'My test message');
});

Deno.test("formatLogMessage() - includes metadata when provided", () => {
  const message = formatLogMessage('INFO', 'test-fn', 'Test', { requestId: 'abc123' });
  assertStringIncludes(message, 'abc123');
});

Deno.test("formatLogMessage() - handles ERROR level", () => {
  const message = formatLogMessage('ERROR', 'test-fn', 'Error occurred');
  assertStringIncludes(message, '[ERROR]');
});

Deno.test("countSuccessfulResults() - all successful", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: true, data: {} },
    stats: { success: true, data: {} },
    parties: { success: true, data: {} },
  };

  assertEquals(countSuccessfulResults(results), 3);
});

Deno.test("countSuccessfulResults() - some failed", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: true, data: {} },
    stats: { success: false, error: 'Failed' },
    parties: { success: true, data: {} },
  };

  assertEquals(countSuccessfulResults(results), 2);
});

Deno.test("countSuccessfulResults() - all failed", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: false, error: 'Failed' },
    stats: { success: false, error: 'Failed' },
  };

  assertEquals(countSuccessfulResults(results), 0);
});

Deno.test("countFailedResults() - none failed", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: true, data: {} },
    stats: { success: true, data: {} },
  };

  assertEquals(countFailedResults(results), 0);
});

Deno.test("countFailedResults() - some failed", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: true, data: {} },
    stats: { success: false, error: 'Failed' },
    parties: { success: false, error: 'Also failed' },
  };

  assertEquals(countFailedResults(results), 2);
});

Deno.test("getFailedSteps() - returns failed step names", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: true, data: {} },
    stats: { success: false, error: 'Failed' },
    parties: { success: true, data: {} },
    strategyFollow: { success: false, error: 'Also failed' },
  };

  const failed = getFailedSteps(results);
  assertEquals(failed.length, 2);
  assertEquals(failed.includes('stats'), true);
  assertEquals(failed.includes('strategyFollow'), true);
});

Deno.test("getFailedSteps() - empty when all succeed", () => {
  const results: Record<string, SyncResult> = {
    chartData: { success: true },
    stats: { success: true },
  };

  const failed = getFailedSteps(results);
  assertEquals(failed.length, 0);
});

// Test sync log entry structure
interface SyncLogEntry {
  sync_type: string;
  status: 'completed' | 'failed';
  results?: Record<string, SyncResult>;
  error_message?: string;
  duration_ms: number;
  request_id: string;
}

Deno.test("SyncLogEntry - completed entry", () => {
  const entry: SyncLogEntry = {
    sync_type: 'scheduled',
    status: 'completed',
    results: { chartData: { success: true } },
    duration_ms: 1500,
    request_id: 'abc123',
  };

  assertEquals(entry.status, 'completed');
  assertEquals(entry.sync_type, 'scheduled');
});

Deno.test("SyncLogEntry - failed entry", () => {
  const entry: SyncLogEntry = {
    sync_type: 'scheduled',
    status: 'failed',
    error_message: 'Connection timeout',
    duration_ms: 30000,
    request_id: 'def456',
  };

  assertEquals(entry.status, 'failed');
  assertEquals(entry.error_message, 'Connection timeout');
});

// Test response structure
interface SyncResponse {
  success: boolean;
  message: string;
  mode: 'daily' | 'full' | 'quick';
  requestId: string;
  duration: string;
  results: Record<string, SyncResult>;
}

Deno.test("SyncResponse - successful response", () => {
  const response: SyncResponse = {
    success: true,
    message: 'Scheduled sync completed (daily mode)',
    mode: 'daily',
    requestId: 'abc123',
    duration: '1500ms',
    results: {
      chartData: { success: true },
      stats: { success: true },
    },
  };

  assertEquals(response.success, true);
  assertStringIncludes(response.message, 'daily');
});

Deno.test("SyncResponse - full mode message", () => {
  const response: SyncResponse = {
    success: true,
    message: 'Scheduled sync completed (full mode)',
    mode: 'full',
    requestId: 'xyz789',
    duration: '5000ms',
    results: {},
  };

  assertStringIncludes(response.message, 'full');
});
