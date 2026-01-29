/**
 * Centralized formatting utilities for the application.
 *
 * This module consolidates all formatting logic (currency, dates, amounts)
 * to ensure consistent formatting across the application and reduce code duplication.
 */

// ============================================================================
// Currency Formatting
// ============================================================================

/**
 * Format a number as a compact currency string with suffix (K, M, B).
 * Used for displaying large values in a human-readable way.
 *
 * @example
 * formatCurrencyCompact(1500000) // "$1.5M"
 * formatCurrencyCompact(2500) // "$2.5K"
 * formatCurrencyCompact(500) // "$500"
 */
export function formatCurrencyCompact(value: number): string {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
}

/**
 * Format a number as a full currency string with thousands separators.
 * Used for displaying precise monetary values.
 *
 * @example
 * formatCurrencyFull(1500000) // "$1,500,000.00"
 * formatCurrencyFull(2500.5) // "$2,500.50"
 */
export function formatCurrencyFull(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '$0.00';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number as currency without decimal places.
 * Used for integer currency amounts.
 *
 * @example
 * formatCurrencyWhole(1500) // "$1,500"
 */
export function formatCurrencyWhole(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '$0';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a disclosure amount range (min/max values).
 * Handles various edge cases like null values and equal min/max.
 *
 * @example
 * formatAmountRange(1000, 15000) // "$1,000 - $15,000"
 * formatAmountRange(null, 15000) // "Up to $15,000"
 * formatAmountRange(1000, null) // "$1,000+"
 * formatAmountRange(5000, 5000) // "$5,000"
 */
export function formatAmountRange(min: number | null, max: number | null): string {
  if (min === null && max === null) {
    return 'Unknown';
  }
  if (min === null) {
    return `Up to $${max?.toLocaleString()}`;
  }
  if (max === null) {
    return `$${min.toLocaleString()}+`;
  }
  if (min === max) {
    return `$${min.toLocaleString()}`;
  }
  return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
}

// ============================================================================
// Date Formatting
// ============================================================================

/**
 * Date format options for consistent styling across the app.
 */
export const DATE_FORMATS = {
  /** Short date: "Jan 15, 2026" */
  short: { month: 'short', day: 'numeric', year: 'numeric' } as const,
  /** Long date: "January 15, 2026" */
  long: { month: 'long', day: 'numeric', year: 'numeric' } as const,
  /** Date with weekday: "Mon, Jan 15, 2026" */
  withWeekday: { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' } as const,
  /** Month and year only: "January 2026" */
  monthYear: { month: 'long', year: 'numeric' } as const,
  /** Time only: "2:30 PM" */
  time: { hour: 'numeric', minute: '2-digit', hour12: true } as const,
  /** Full datetime: "Jan 15, 2026, 2:30 PM" */
  datetime: { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true } as const,
  /** ISO date: "2026-01-15" */
  iso: { year: 'numeric', month: '2-digit', day: '2-digit' } as const,
};

/**
 * Format a date string or Date object to a localized date string.
 * Uses the "short" format by default: "Jan 15, 2026"
 *
 * @example
 * formatDate("2026-01-15") // "Jan 15, 2026"
 * formatDate(new Date()) // "Jan 29, 2026"
 */
export function formatDate(
  date: string | Date | null | undefined,
  format: keyof typeof DATE_FORMATS = 'short'
): string {
  if (!date) return '';

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';

    return dateObj.toLocaleDateString('en-US', DATE_FORMATS[format]);
  } catch {
    return '';
  }
}

/**
 * Format a date string or Date object to a localized time string.
 * Output: "2:30 PM"
 */
export function formatTime(
  date: string | Date | null | undefined
): string {
  if (!date) return '';

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';

    return dateObj.toLocaleTimeString('en-US', DATE_FORMATS.time);
  } catch {
    return '';
  }
}

/**
 * Format a date string or Date object to a full datetime string.
 * Output: "Jan 15, 2026, 2:30 PM"
 */
export function formatDateTime(
  date: string | Date | null | undefined
): string {
  if (!date) return '';

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';

    return dateObj.toLocaleString('en-US', DATE_FORMATS.datetime);
  } catch {
    return '';
  }
}

/**
 * Format a date for chart display (short month and day).
 * Output: "Jan 15"
 */
export function formatDateForChart(date: string | Date | null | undefined): string {
  if (!date) return '';

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';

    return dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

/**
 * Get an ISO date string (YYYY-MM-DD) from a Date object.
 * Useful for form inputs and API calls.
 */
export function toISODateString(date: Date | null | undefined): string {
  if (!date) return '';
  return date.toISOString().split('T')[0];
}

// ============================================================================
// Number Formatting
// ============================================================================

/**
 * Format a number with thousands separators.
 *
 * @example
 * formatNumber(1234567) // "1,234,567"
 */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '0';
  }
  return value.toLocaleString('en-US');
}

/**
 * Format a percentage with specified decimal places.
 *
 * @example
 * formatPercent(0.1234) // "12.34%"
 * formatPercent(0.1234, 0) // "12%"
 */
export function formatPercent(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined) {
    return '0%';
  }
  return `${(value * 100).toFixed(decimals)}%`;
}

// ============================================================================
// Backwards Compatibility
// ============================================================================

/**
 * @deprecated Use formatCurrencyCompact instead.
 * This alias exists for backwards compatibility with existing code.
 */
export const formatCurrency = formatCurrencyCompact;
