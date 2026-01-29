/**
 * Tests for lib/formatters.ts
 */

import { describe, it, expect } from 'vitest';
import {
  formatCurrencyCompact,
  formatCurrencyFull,
  formatCurrencyWhole,
  formatAmountRange,
  formatDate,
  formatTime,
  formatDateTime,
  formatDateForChart,
  toISODateString,
  formatNumber,
  formatPercent,
  formatCurrency,
  DATE_FORMATS,
} from './formatters';

describe('Currency Formatting', () => {
  describe('formatCurrencyCompact', () => {
    it('formats billions with B suffix', () => {
      expect(formatCurrencyCompact(1_000_000_000)).toBe('$1.0B');
      expect(formatCurrencyCompact(2_500_000_000)).toBe('$2.5B');
      expect(formatCurrencyCompact(10_000_000_000)).toBe('$10.0B');
    });

    it('formats millions with M suffix', () => {
      expect(formatCurrencyCompact(1_000_000)).toBe('$1.0M');
      expect(formatCurrencyCompact(2_500_000)).toBe('$2.5M');
      expect(formatCurrencyCompact(999_000_000)).toBe('$999.0M');
    });

    it('formats thousands with K suffix', () => {
      expect(formatCurrencyCompact(1_000)).toBe('$1.0K');
      expect(formatCurrencyCompact(2_500)).toBe('$2.5K');
      expect(formatCurrencyCompact(999_000)).toBe('$999.0K');
    });

    it('formats small values without suffix', () => {
      expect(formatCurrencyCompact(500)).toBe('$500');
      expect(formatCurrencyCompact(0)).toBe('$0');
      expect(formatCurrencyCompact(999)).toBe('$999');
    });

    it('handles decimal precision correctly', () => {
      expect(formatCurrencyCompact(1_234_567)).toBe('$1.2M');
      expect(formatCurrencyCompact(1_567_890)).toBe('$1.6M');
    });
  });

  describe('formatCurrencyFull', () => {
    it('formats values with full decimal precision', () => {
      expect(formatCurrencyFull(1500000)).toBe('$1,500,000.00');
      expect(formatCurrencyFull(2500.5)).toBe('$2,500.50');
      expect(formatCurrencyFull(100)).toBe('$100.00');
    });

    it('handles null and undefined', () => {
      expect(formatCurrencyFull(null)).toBe('$0.00');
      expect(formatCurrencyFull(undefined)).toBe('$0.00');
    });

    it('handles zero', () => {
      expect(formatCurrencyFull(0)).toBe('$0.00');
    });

    it('handles negative values', () => {
      expect(formatCurrencyFull(-1500)).toBe('-$1,500.00');
    });
  });

  describe('formatCurrencyWhole', () => {
    it('formats values without decimal places', () => {
      expect(formatCurrencyWhole(1500000)).toBe('$1,500,000');
      expect(formatCurrencyWhole(2500.99)).toBe('$2,501');
      expect(formatCurrencyWhole(100)).toBe('$100');
    });

    it('handles null and undefined', () => {
      expect(formatCurrencyWhole(null)).toBe('$0');
      expect(formatCurrencyWhole(undefined)).toBe('$0');
    });
  });

  describe('formatAmountRange', () => {
    it('formats full range', () => {
      expect(formatAmountRange(1000, 15000)).toBe('$1,000 - $15,000');
    });

    it('formats upper bound only', () => {
      expect(formatAmountRange(null, 15000)).toBe('Up to $15,000');
    });

    it('formats lower bound only', () => {
      expect(formatAmountRange(1000, null)).toBe('$1,000+');
    });

    it('formats equal bounds as single value', () => {
      expect(formatAmountRange(5000, 5000)).toBe('$5,000');
    });

    it('handles both null', () => {
      expect(formatAmountRange(null, null)).toBe('Unknown');
    });
  });

  describe('formatCurrency (backwards compatibility)', () => {
    it('is an alias for formatCurrencyCompact', () => {
      expect(formatCurrency).toBe(formatCurrencyCompact);
      expect(formatCurrency(1_500_000)).toBe('$1.5M');
    });
  });
});

describe('Date Formatting', () => {
  // Use a fixed date for consistent testing
  const testDate = new Date('2026-01-15T14:30:00Z');
  const testDateStr = '2026-01-15T14:30:00Z';

  describe('formatDate', () => {
    it('formats date with short format by default', () => {
      const result = formatDate(testDateStr);
      expect(result).toContain('Jan');
      expect(result).toContain('15');
      expect(result).toContain('2026');
    });

    it('formats Date object', () => {
      const result = formatDate(testDate);
      expect(result).toContain('Jan');
      expect(result).toContain('15');
    });

    it('formats with long format', () => {
      const result = formatDate(testDateStr, 'long');
      expect(result).toContain('January');
      expect(result).toContain('15');
      expect(result).toContain('2026');
    });

    it('formats with monthYear format', () => {
      const result = formatDate(testDateStr, 'monthYear');
      expect(result).toContain('January');
      expect(result).toContain('2026');
      expect(result).not.toContain('15');
    });

    it('returns empty string for null', () => {
      expect(formatDate(null)).toBe('');
    });

    it('returns empty string for undefined', () => {
      expect(formatDate(undefined)).toBe('');
    });

    it('returns empty string for invalid date', () => {
      expect(formatDate('invalid-date')).toBe('');
    });
  });

  describe('formatTime', () => {
    it('formats time', () => {
      const result = formatTime(testDateStr);
      // Time will vary by timezone, but should contain AM or PM
      expect(result).toMatch(/\d{1,2}:\d{2}\s*(AM|PM)/);
    });

    it('returns empty string for null', () => {
      expect(formatTime(null)).toBe('');
    });

    it('returns empty string for invalid date', () => {
      expect(formatTime('invalid')).toBe('');
    });
  });

  describe('formatDateTime', () => {
    it('formats date and time', () => {
      const result = formatDateTime(testDateStr);
      expect(result).toContain('Jan');
      expect(result).toContain('15');
      expect(result).toContain('2026');
      expect(result).toMatch(/(AM|PM)/);
    });

    it('returns empty string for null', () => {
      expect(formatDateTime(null)).toBe('');
    });
  });

  describe('formatDateForChart', () => {
    it('formats date for chart display', () => {
      const result = formatDateForChart(testDateStr);
      expect(result).toContain('Jan');
      expect(result).toContain('15');
      expect(result).not.toContain('2026');
    });

    it('returns empty string for null', () => {
      expect(formatDateForChart(null)).toBe('');
    });
  });

  describe('toISODateString', () => {
    it('converts Date to ISO date string', () => {
      expect(toISODateString(testDate)).toBe('2026-01-15');
    });

    it('returns empty string for null', () => {
      expect(toISODateString(null)).toBe('');
    });

    it('returns empty string for undefined', () => {
      expect(toISODateString(undefined)).toBe('');
    });
  });

  describe('DATE_FORMATS', () => {
    it('exports predefined date formats', () => {
      expect(DATE_FORMATS).toHaveProperty('short');
      expect(DATE_FORMATS).toHaveProperty('long');
      expect(DATE_FORMATS).toHaveProperty('withWeekday');
      expect(DATE_FORMATS).toHaveProperty('monthYear');
      expect(DATE_FORMATS).toHaveProperty('time');
      expect(DATE_FORMATS).toHaveProperty('datetime');
      expect(DATE_FORMATS).toHaveProperty('iso');
    });
  });
});

describe('Number Formatting', () => {
  describe('formatNumber', () => {
    it('formats numbers with thousands separators', () => {
      expect(formatNumber(1234567)).toBe('1,234,567');
      expect(formatNumber(1000)).toBe('1,000');
      expect(formatNumber(100)).toBe('100');
    });

    it('handles null and undefined', () => {
      expect(formatNumber(null)).toBe('0');
      expect(formatNumber(undefined)).toBe('0');
    });

    it('handles zero', () => {
      expect(formatNumber(0)).toBe('0');
    });

    it('handles decimal numbers', () => {
      expect(formatNumber(1234.567)).toBe('1,234.567');
    });
  });

  describe('formatPercent', () => {
    it('formats percentage with default 2 decimal places', () => {
      expect(formatPercent(0.1234)).toBe('12.34%');
      expect(formatPercent(0.5)).toBe('50.00%');
      expect(formatPercent(1)).toBe('100.00%');
    });

    it('formats percentage with custom decimal places', () => {
      expect(formatPercent(0.1234, 0)).toBe('12%');
      expect(formatPercent(0.1234, 1)).toBe('12.3%');
      expect(formatPercent(0.1234, 3)).toBe('12.340%');
    });

    it('handles null and undefined', () => {
      expect(formatPercent(null)).toBe('0%');
      expect(formatPercent(undefined)).toBe('0%');
    });

    it('handles zero', () => {
      expect(formatPercent(0)).toBe('0.00%');
    });

    it('handles negative values', () => {
      expect(formatPercent(-0.05)).toBe('-5.00%');
    });
  });
});
