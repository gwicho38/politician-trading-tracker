/**
 * Tests for politician-trading-collect Edge Function
 *
 * Tests:
 * - Name parsing logic
 * - Source validation
 * - Cache key generation
 * - Disclosure record building
 * - URL construction
 * - Results summary formatting
 */

import { assertEquals, assertStringIncludes } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Configuration type
interface ScrapingConfig {
  userAgent: string;
  timeout: number;
  maxRetries: number;
  requestDelay: number;
}

// Default configuration
function getDefaultConfig(): ScrapingConfig {
  return {
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    timeout: 30000,
    maxRetries: 1,
    requestDelay: 1000,
  };
}

// Name parsing
function parseName(name: string): { firstName: string; lastName: string } {
  const parts = name.trim().split(' ');
  const firstName = parts[0] || 'Unknown';
  const lastName = parts.slice(1).join(' ') || 'Unknown';
  return { firstName, lastName };
}

// Cache key generation
function generateCacheKey(name: string, role: string): string {
  return `${name}:${role}`;
}

// Source validation
const validSources = ['house', 'senate', 'quiver', 'eu', 'california'];

function isValidSource(source: string): boolean {
  return validSources.includes(source.toLowerCase());
}

function normalizeSource(source: string): string {
  return source.toLowerCase().trim();
}

// URL construction helpers
function constructFullUrl(baseUrl: string, relativePath: string): string {
  if (relativePath.startsWith('http')) {
    return relativePath;
  }
  return `${baseUrl}${relativePath}`;
}

// Source URLs
const sourceUrls: Record<string, string> = {
  house: 'https://disclosures-clerk.house.gov/FinancialDisclosure',
  senate: 'https://efdsearch.senate.gov/search/',
  quiver: 'https://www.quiverquant.com/congresstrading/',
  eu: 'https://www.europarl.europa.eu/meps/en/full-list/all',
  california_sf: 'https://public.netfile.com/pub2/?AID=SFO',
  california_la: 'https://public.netfile.com/pub2/?AID=LAC',
};

function getSourceUrl(source: string): string | null {
  return sourceUrls[source] || null;
}

// Disclosure record building
interface DisclosureRecord {
  source_url: string;
  politician_id: string;
  transaction_date: string;
  disclosure_date: string;
  asset_name: string;
  transaction_type: string;
  amount_range_min: number;
  amount_range_max: number;
  status: string;
  raw_data: Record<string, unknown>;
}

function buildDisclosureRecord(
  sourceUrl: string,
  politicianId: string,
  source: string,
  assetName: string = 'Unknown Asset',
  transactionType: string = 'purchase',
  amountMin: number = 1000,
  amountMax: number = 15000
): DisclosureRecord {
  const now = new Date().toISOString();
  return {
    source_url: sourceUrl,
    politician_id: politicianId,
    transaction_date: now,
    disclosure_date: now,
    asset_name: assetName,
    transaction_type: transactionType,
    amount_range_min: amountMin,
    amount_range_max: amountMax,
    status: 'pending',
    raw_data: {
      source: source,
      url: sourceUrl,
    },
  };
}

// Results summary
interface CollectionSummary {
  total_new_disclosures: number;
  total_updated_disclosures: number;
  errors: string[];
}

function createEmptySummary(): CollectionSummary {
  return {
    total_new_disclosures: 0,
    total_updated_disclosures: 0,
    errors: [],
  };
}

function updateSummary(
  summary: CollectionSummary,
  newDisclosures: number,
  error?: string
): CollectionSummary {
  const updated = { ...summary };
  updated.total_new_disclosures += newDisclosures;
  if (error) {
    updated.errors.push(error);
  }
  return updated;
}

// Job result formatting
interface JobResult {
  source: string;
  disclosures_found: number;
  disclosures: DisclosureRecord[];
}

function createEmptyJobResult(source: string): JobResult {
  return {
    source: source,
    disclosures_found: 0,
    disclosures: [],
  };
}

function isJobSuccessful(result: JobResult): boolean {
  return result.disclosures_found > 0;
}

// Link extraction helpers
function extractDisclosureLinks(html: string, pattern: RegExp): string[] {
  const matches = html.match(pattern) || [];
  return matches.map(match => {
    const href = match.match(/href="([^"]*)"/);
    return href ? href[1] : '';
  }).filter(Boolean);
}

function limitResults<T>(items: T[], limit: number): T[] {
  return items.slice(0, limit);
}

// Placeholder politician names
const placeholderNames: Record<string, { name: string; role: string }> = {
  house: { name: 'House Member (Placeholder)', role: 'Representative' },
  senate: { name: 'Senate Member (Placeholder)', role: 'Senate' },
  quiver: { name: 'Congress Member (QuiverQuant)', role: 'Congress' },
  eu: { name: 'EU MEP (Placeholder)', role: 'MEP' },
  california: { name: 'California Official (Placeholder)', role: 'State Official' },
};

function getPlaceholderName(source: string): { name: string; role: string } | null {
  return placeholderNames[source] || null;
}

// Response formatting
function formatSuccessResponse(source: string, disclosuresFound: number): string {
  return `${source} collection completed. Found ${disclosuresFound} disclosures.`;
}

function formatFullCollectionResponse(status: string, totalDisclosures: number): string {
  return `Collection ${status}. Found ${totalDisclosures} disclosures.`;
}

// Tests

Deno.test("getDefaultConfig() - returns expected defaults", () => {
  const config = getDefaultConfig();

  assertEquals(config.timeout, 30000);
  assertEquals(config.maxRetries, 1);
  assertEquals(config.requestDelay, 1000);
  assertStringIncludes(config.userAgent, 'Mozilla');
});

Deno.test("parseName() - single name", () => {
  const result = parseName('Nancy');

  assertEquals(result.firstName, 'Nancy');
  assertEquals(result.lastName, 'Unknown');
});

Deno.test("parseName() - two parts", () => {
  const result = parseName('Nancy Pelosi');

  assertEquals(result.firstName, 'Nancy');
  assertEquals(result.lastName, 'Pelosi');
});

Deno.test("parseName() - multiple parts", () => {
  const result = parseName('Alexandria Ocasio-Cortez');

  assertEquals(result.firstName, 'Alexandria');
  assertEquals(result.lastName, 'Ocasio-Cortez');
});

Deno.test("parseName() - three parts", () => {
  const result = parseName('John Quincy Adams');

  assertEquals(result.firstName, 'John');
  assertEquals(result.lastName, 'Quincy Adams');
});

Deno.test("parseName() - empty string", () => {
  const result = parseName('');

  assertEquals(result.firstName, 'Unknown');
  assertEquals(result.lastName, 'Unknown');
});

Deno.test("parseName() - whitespace only", () => {
  const result = parseName('   ');

  assertEquals(result.firstName, 'Unknown');
  assertEquals(result.lastName, 'Unknown');
});

Deno.test("parseName() - with extra whitespace", () => {
  const result = parseName('  Nancy   Pelosi  ');

  assertEquals(result.firstName, 'Nancy');
  assertStringIncludes(result.lastName, 'Pelosi');
});

Deno.test("generateCacheKey() - basic key", () => {
  const key = generateCacheKey('Nancy Pelosi', 'Representative');

  assertEquals(key, 'Nancy Pelosi:Representative');
});

Deno.test("generateCacheKey() - same name different roles", () => {
  const key1 = generateCacheKey('John Smith', 'Representative');
  const key2 = generateCacheKey('John Smith', 'Senator');

  assertEquals(key1 !== key2, true);
});

Deno.test("isValidSource() - valid sources", () => {
  assertEquals(isValidSource('house'), true);
  assertEquals(isValidSource('senate'), true);
  assertEquals(isValidSource('quiver'), true);
  assertEquals(isValidSource('eu'), true);
  assertEquals(isValidSource('california'), true);
});

Deno.test("isValidSource() - case insensitive", () => {
  assertEquals(isValidSource('HOUSE'), true);
  assertEquals(isValidSource('Senate'), true);
  assertEquals(isValidSource('QuIvEr'), true);
});

Deno.test("isValidSource() - invalid sources", () => {
  assertEquals(isValidSource('unknown'), false);
  assertEquals(isValidSource('congress'), false);
  assertEquals(isValidSource(''), false);
});

Deno.test("normalizeSource() - lowercases and trims", () => {
  assertEquals(normalizeSource('HOUSE'), 'house');
  assertEquals(normalizeSource('  Senate  '), 'senate');
  assertEquals(normalizeSource('QuIvEr'), 'quiver');
});

Deno.test("constructFullUrl() - absolute URL unchanged", () => {
  const url = constructFullUrl('https://base.com', 'https://other.com/path');

  assertEquals(url, 'https://other.com/path');
});

Deno.test("constructFullUrl() - relative URL combined", () => {
  const url = constructFullUrl('https://base.com', '/path/to/resource');

  assertEquals(url, 'https://base.com/path/to/resource');
});

Deno.test("constructFullUrl() - http URL unchanged", () => {
  const url = constructFullUrl('https://base.com', 'http://insecure.com/path');

  assertEquals(url, 'http://insecure.com/path');
});

Deno.test("getSourceUrl() - valid sources", () => {
  assertEquals(getSourceUrl('house'), 'https://disclosures-clerk.house.gov/FinancialDisclosure');
  assertEquals(getSourceUrl('senate'), 'https://efdsearch.senate.gov/search/');
  assertEquals(getSourceUrl('quiver'), 'https://www.quiverquant.com/congresstrading/');
});

Deno.test("getSourceUrl() - invalid source", () => {
  assertEquals(getSourceUrl('unknown'), null);
  assertEquals(getSourceUrl('congress'), null);
});

Deno.test("buildDisclosureRecord() - creates valid record", () => {
  const record = buildDisclosureRecord(
    'https://example.com/disclosure',
    'politician-uuid-123',
    'us_house'
  );

  assertEquals(record.source_url, 'https://example.com/disclosure');
  assertEquals(record.politician_id, 'politician-uuid-123');
  assertEquals(record.asset_name, 'Unknown Asset');
  assertEquals(record.transaction_type, 'purchase');
  assertEquals(record.amount_range_min, 1000);
  assertEquals(record.amount_range_max, 15000);
  assertEquals(record.status, 'pending');
  assertEquals(record.raw_data.source, 'us_house');
});

Deno.test("buildDisclosureRecord() - custom values", () => {
  const record = buildDisclosureRecord(
    'https://example.com',
    'pol-id',
    'senate',
    'AAPL Stock',
    'sale',
    50000,
    100000
  );

  assertEquals(record.asset_name, 'AAPL Stock');
  assertEquals(record.transaction_type, 'sale');
  assertEquals(record.amount_range_min, 50000);
  assertEquals(record.amount_range_max, 100000);
});

Deno.test("createEmptySummary() - initializes correctly", () => {
  const summary = createEmptySummary();

  assertEquals(summary.total_new_disclosures, 0);
  assertEquals(summary.total_updated_disclosures, 0);
  assertEquals(summary.errors.length, 0);
});

Deno.test("updateSummary() - adds disclosures", () => {
  let summary = createEmptySummary();
  summary = updateSummary(summary, 10);
  summary = updateSummary(summary, 5);

  assertEquals(summary.total_new_disclosures, 15);
  assertEquals(summary.errors.length, 0);
});

Deno.test("updateSummary() - adds error", () => {
  let summary = createEmptySummary();
  summary = updateSummary(summary, 5, 'Connection failed');

  assertEquals(summary.total_new_disclosures, 5);
  assertEquals(summary.errors.length, 1);
  assertEquals(summary.errors[0], 'Connection failed');
});

Deno.test("updateSummary() - multiple errors", () => {
  let summary = createEmptySummary();
  summary = updateSummary(summary, 0, 'Error 1');
  summary = updateSummary(summary, 0, 'Error 2');

  assertEquals(summary.errors.length, 2);
});

Deno.test("createEmptyJobResult() - initializes correctly", () => {
  const result = createEmptyJobResult('us_house');

  assertEquals(result.source, 'us_house');
  assertEquals(result.disclosures_found, 0);
  assertEquals(result.disclosures.length, 0);
});

Deno.test("isJobSuccessful() - successful with disclosures", () => {
  const result: JobResult = {
    source: 'house',
    disclosures_found: 5,
    disclosures: [],
  };

  assertEquals(isJobSuccessful(result), true);
});

Deno.test("isJobSuccessful() - unsuccessful with no disclosures", () => {
  const result: JobResult = {
    source: 'house',
    disclosures_found: 0,
    disclosures: [],
  };

  assertEquals(isJobSuccessful(result), false);
});

Deno.test("extractDisclosureLinks() - finds href links", () => {
  const html = `
    <a href="/disclosure/123">Link 1</a>
    <a href="/disclosure/456">Link 2</a>
    <a href="/other/789">Other</a>
  `;

  const links = extractDisclosureLinks(html, /href="([^"]*disclosure[^"]*)"/gi);

  assertEquals(links.length, 2);
  assertEquals(links[0], '/disclosure/123');
  assertEquals(links[1], '/disclosure/456');
});

Deno.test("extractDisclosureLinks() - no matches", () => {
  const html = '<p>No links here</p>';

  const links = extractDisclosureLinks(html, /href="([^"]*disclosure[^"]*)"/gi);

  assertEquals(links.length, 0);
});

Deno.test("limitResults() - limits correctly", () => {
  const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const limited = limitResults(items, 5);

  assertEquals(limited.length, 5);
  assertEquals(limited, [1, 2, 3, 4, 5]);
});

Deno.test("limitResults() - returns all if under limit", () => {
  const items = [1, 2, 3];
  const limited = limitResults(items, 5);

  assertEquals(limited.length, 3);
  assertEquals(limited, [1, 2, 3]);
});

Deno.test("limitResults() - empty array", () => {
  const limited = limitResults([], 5);

  assertEquals(limited.length, 0);
});

Deno.test("getPlaceholderName() - house", () => {
  const placeholder = getPlaceholderName('house');

  assertEquals(placeholder?.name, 'House Member (Placeholder)');
  assertEquals(placeholder?.role, 'Representative');
});

Deno.test("getPlaceholderName() - senate", () => {
  const placeholder = getPlaceholderName('senate');

  assertEquals(placeholder?.name, 'Senate Member (Placeholder)');
  assertEquals(placeholder?.role, 'Senate');
});

Deno.test("getPlaceholderName() - quiver", () => {
  const placeholder = getPlaceholderName('quiver');

  assertEquals(placeholder?.name, 'Congress Member (QuiverQuant)');
  assertEquals(placeholder?.role, 'Congress');
});

Deno.test("getPlaceholderName() - eu", () => {
  const placeholder = getPlaceholderName('eu');

  assertEquals(placeholder?.name, 'EU MEP (Placeholder)');
  assertEquals(placeholder?.role, 'MEP');
});

Deno.test("getPlaceholderName() - california", () => {
  const placeholder = getPlaceholderName('california');

  assertEquals(placeholder?.name, 'California Official (Placeholder)');
  assertEquals(placeholder?.role, 'State Official');
});

Deno.test("getPlaceholderName() - invalid source", () => {
  const placeholder = getPlaceholderName('unknown');

  assertEquals(placeholder, null);
});

Deno.test("formatSuccessResponse() - formats correctly", () => {
  const message = formatSuccessResponse('house', 15);

  assertEquals(message, 'house collection completed. Found 15 disclosures.');
});

Deno.test("formatSuccessResponse() - zero disclosures", () => {
  const message = formatSuccessResponse('senate', 0);

  assertEquals(message, 'senate collection completed. Found 0 disclosures.');
});

Deno.test("formatFullCollectionResponse() - completed", () => {
  const message = formatFullCollectionResponse('completed', 25);

  assertEquals(message, 'Collection completed. Found 25 disclosures.');
});

Deno.test("formatFullCollectionResponse() - failed", () => {
  const message = formatFullCollectionResponse('failed', 0);

  assertEquals(message, 'Collection failed. Found 0 disclosures.');
});

// California portal configuration
interface CaliforniaPortal {
  url: string;
  jurisdiction: string;
}

const californiaPortals: CaliforniaPortal[] = [
  { url: 'https://public.netfile.com/pub2/?AID=SFO', jurisdiction: 'San Francisco' },
  { url: 'https://public.netfile.com/pub2/?AID=LAC', jurisdiction: 'Los Angeles' },
];

function getCaliforniaPortals(): CaliforniaPortal[] {
  return californiaPortals;
}

Deno.test("getCaliforniaPortals() - returns both portals", () => {
  const portals = getCaliforniaPortals();

  assertEquals(portals.length, 2);
  assertEquals(portals[0].jurisdiction, 'San Francisco');
  assertEquals(portals[1].jurisdiction, 'Los Angeles');
});

// Amount range validation
function isValidAmountRange(min: number, max: number): boolean {
  return min >= 0 && max >= min;
}

Deno.test("isValidAmountRange() - valid range", () => {
  assertEquals(isValidAmountRange(1000, 15000), true);
  assertEquals(isValidAmountRange(0, 100), true);
  assertEquals(isValidAmountRange(5000, 5000), true);
});

Deno.test("isValidAmountRange() - invalid range", () => {
  assertEquals(isValidAmountRange(15000, 1000), false);
  assertEquals(isValidAmountRange(-100, 100), false);
});

// Transaction type validation
const validTransactionTypes = ['purchase', 'sale', 'disclosure', 'exchange'];

function isValidTransactionType(type: string): boolean {
  return validTransactionTypes.includes(type.toLowerCase());
}

Deno.test("isValidTransactionType() - valid types", () => {
  assertEquals(isValidTransactionType('purchase'), true);
  assertEquals(isValidTransactionType('sale'), true);
  assertEquals(isValidTransactionType('disclosure'), true);
  assertEquals(isValidTransactionType('exchange'), true);
});

Deno.test("isValidTransactionType() - invalid type", () => {
  assertEquals(isValidTransactionType('unknown'), false);
  assertEquals(isValidTransactionType('buy'), false);
});

// Job status determination
type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

function determineJobStatus(
  hasStarted: boolean,
  hasCompleted: boolean,
  hasError: boolean
): JobStatus {
  if (hasError) return 'failed';
  if (hasCompleted) return 'completed';
  if (hasStarted) return 'running';
  return 'pending';
}

Deno.test("determineJobStatus() - pending", () => {
  assertEquals(determineJobStatus(false, false, false), 'pending');
});

Deno.test("determineJobStatus() - running", () => {
  assertEquals(determineJobStatus(true, false, false), 'running');
});

Deno.test("determineJobStatus() - completed", () => {
  assertEquals(determineJobStatus(true, true, false), 'completed');
});

Deno.test("determineJobStatus() - failed", () => {
  assertEquals(determineJobStatus(true, false, true), 'failed');
  assertEquals(determineJobStatus(true, true, true), 'failed'); // Error takes precedence
});

// HTML link pattern matching
function createLinkPattern(keyword: string): RegExp {
  return new RegExp(`href="([^"]*${keyword}[^"]*)"`, 'gi');
}

Deno.test("createLinkPattern() - disclosure pattern", () => {
  const pattern = createLinkPattern('disclosure');
  const html = '<a href="/disclosure/123">Link</a>';

  const matches = html.match(pattern);
  assertEquals(matches?.length, 1);
});

Deno.test("createLinkPattern() - report pattern", () => {
  const pattern = createLinkPattern('report');
  const html = '<a href="/report/456">Link</a>';

  const matches = html.match(pattern);
  assertEquals(matches?.length, 1);
});

Deno.test("createLinkPattern() - mep pattern", () => {
  const pattern = createLinkPattern('mep');
  const html = '<a href="/meps/en/12345">MEP Link</a>';

  const matches = html.match(pattern);
  assertEquals(matches?.length, 1);
});

// Retry delay calculation
function calculateRetryDelay(attempt: number, baseDelay: number): number {
  return baseDelay * (attempt + 1);
}

Deno.test("calculateRetryDelay() - first attempt", () => {
  assertEquals(calculateRetryDelay(0, 1000), 1000);
});

Deno.test("calculateRetryDelay() - second attempt", () => {
  assertEquals(calculateRetryDelay(1, 1000), 2000);
});

Deno.test("calculateRetryDelay() - third attempt", () => {
  assertEquals(calculateRetryDelay(2, 1000), 3000);
});

// Rate limit detection
function isRateLimited(statusCode: number): boolean {
  return statusCode === 429;
}

Deno.test("isRateLimited() - 429 status", () => {
  assertEquals(isRateLimited(429), true);
});

Deno.test("isRateLimited() - other statuses", () => {
  assertEquals(isRateLimited(200), false);
  assertEquals(isRateLimited(404), false);
  assertEquals(isRateLimited(500), false);
});

// Collection results aggregation
interface FullCollectionResults {
  started_at: string;
  completed_at?: string;
  status?: string;
  jobs: Record<string, {
    status: string;
    new_disclosures: number;
    updated_disclosures: number;
    errors: string[];
  }>;
  summary: CollectionSummary;
}

function aggregateResults(results: FullCollectionResults): {
  totalSources: number;
  successfulSources: number;
  failedSources: number;
  totalDisclosures: number;
} {
  const jobs = Object.values(results.jobs);
  return {
    totalSources: jobs.length,
    successfulSources: jobs.filter(j => j.status === 'completed').length,
    failedSources: jobs.filter(j => j.status === 'failed').length,
    totalDisclosures: results.summary.total_new_disclosures,
  };
}

Deno.test("aggregateResults() - all successful", () => {
  const results: FullCollectionResults = {
    started_at: new Date().toISOString(),
    jobs: {
      house: { status: 'completed', new_disclosures: 5, updated_disclosures: 0, errors: [] },
      senate: { status: 'completed', new_disclosures: 3, updated_disclosures: 0, errors: [] },
    },
    summary: { total_new_disclosures: 8, total_updated_disclosures: 0, errors: [] },
  };

  const aggregated = aggregateResults(results);

  assertEquals(aggregated.totalSources, 2);
  assertEquals(aggregated.successfulSources, 2);
  assertEquals(aggregated.failedSources, 0);
  assertEquals(aggregated.totalDisclosures, 8);
});

Deno.test("aggregateResults() - mixed results", () => {
  const results: FullCollectionResults = {
    started_at: new Date().toISOString(),
    jobs: {
      house: { status: 'completed', new_disclosures: 5, updated_disclosures: 0, errors: [] },
      senate: { status: 'failed', new_disclosures: 0, updated_disclosures: 0, errors: ['Timeout'] },
      quiver: { status: 'completed', new_disclosures: 10, updated_disclosures: 0, errors: [] },
    },
    summary: { total_new_disclosures: 15, total_updated_disclosures: 0, errors: ['Timeout'] },
  };

  const aggregated = aggregateResults(results);

  assertEquals(aggregated.totalSources, 3);
  assertEquals(aggregated.successfulSources, 2);
  assertEquals(aggregated.failedSources, 1);
  assertEquals(aggregated.totalDisclosures, 15);
});

// Source URL query parameter parsing
function parseSourceFromUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    return parsed.searchParams.get('source');
  } catch {
    return null;
  }
}

Deno.test("parseSourceFromUrl() - with source param", () => {
  const source = parseSourceFromUrl('https://example.com/collect?source=house');

  assertEquals(source, 'house');
});

Deno.test("parseSourceFromUrl() - without source param", () => {
  const source = parseSourceFromUrl('https://example.com/collect');

  assertEquals(source, null);
});

Deno.test("parseSourceFromUrl() - multiple params", () => {
  const source = parseSourceFromUrl('https://example.com/collect?source=senate&year=2024');

  assertEquals(source, 'senate');
});

Deno.test("parseSourceFromUrl() - invalid URL", () => {
  const source = parseSourceFromUrl('not-a-url');

  assertEquals(source, null);
});
