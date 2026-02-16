/**
 * Runtime type guards for validating data from external sources (API, database).
 *
 * These guards ensure type safety when dealing with data that TypeScript
 * cannot verify at compile time (e.g., API responses, URL params, localStorage).
 */

// =============================================================================
// Party Types
// =============================================================================

/**
 * Party codes are now dynamic (stored in `parties` table).
 * Any non-empty string is a valid party code.
 * Use partyUtils.ts for display name/color lookups.
 */
export type Party = string;

/**
 * Type guard: any non-empty string is a valid party code.
 * The parties table is the source of truth for known parties.
 */
export function isParty(value: unknown): value is Party {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Safely convert unknown to Party. Returns fallback for null/undefined/empty.
 */
export function toParty(value: unknown, fallback: string = 'Unknown'): string {
  return isParty(value) ? value : fallback;
}

// Legacy compat — these now delegate to partyUtils for DB-backed lookups.
// Components should migrate to using partyUtils directly.
export function getPartyFullName(party: string): string {
  const legacy: Record<string, string> = {
    D: 'Democratic', R: 'Republican', I: 'Independent',
  };
  return legacy[party] || party;
}

export function getPartyLabel(party: string): string {
  const legacy: Record<string, string> = {
    D: 'Democrat', R: 'Republican', I: 'Independent',
  };
  return legacy[party] || party;
}

// =============================================================================
// Transaction Types
// =============================================================================

/**
 * Valid transaction types from the database.
 * Note: 'purchase' and 'sale' are the primary types from ETL.
 */
export const VALID_TRANSACTION_TYPES = [
  'purchase',
  'sale',
  'exchange',
  'holding',
  'unknown',
] as const;
export type TransactionType = (typeof VALID_TRANSACTION_TYPES)[number];

/**
 * Display-friendly transaction types (used in UI).
 */
export const DISPLAY_TRANSACTION_TYPES = ['buy', 'sell', 'exchange', 'holding', 'unknown'] as const;
export type DisplayTransactionType = (typeof DISPLAY_TRANSACTION_TYPES)[number];

/**
 * Type guard to check if a value is a valid TransactionType.
 */
export function isTransactionType(value: unknown): value is TransactionType {
  return typeof value === 'string' && VALID_TRANSACTION_TYPES.includes(value as TransactionType);
}

/**
 * Type guard to check if a value is a valid DisplayTransactionType.
 */
export function isDisplayTransactionType(value: unknown): value is DisplayTransactionType {
  return (
    typeof value === 'string' && DISPLAY_TRANSACTION_TYPES.includes(value as DisplayTransactionType)
  );
}

/**
 * Safely convert an unknown value to a TransactionType, with fallback.
 */
export function toTransactionType(
  value: unknown,
  fallback: TransactionType = 'unknown'
): TransactionType {
  return isTransactionType(value) ? value : fallback;
}

/**
 * Convert database transaction type to display type.
 * 'purchase' -> 'buy', 'sale' -> 'sell', others pass through.
 */
export function toDisplayTransactionType(value: unknown): DisplayTransactionType {
  if (value === 'purchase') return 'buy';
  if (value === 'sale') return 'sell';
  if (isDisplayTransactionType(value)) return value;
  return 'unknown';
}

/**
 * Convert display transaction type back to database type.
 * 'buy' -> 'purchase', 'sell' -> 'sale', others pass through.
 */
export function toDatabaseTransactionType(value: unknown): TransactionType {
  if (value === 'buy') return 'purchase';
  if (value === 'sell') return 'sale';
  if (isTransactionType(value)) return value;
  return 'unknown';
}

// =============================================================================
// Signal Types
// =============================================================================

/**
 * Valid signal types for ML predictions.
 */
export const VALID_SIGNAL_TYPES = [
  'strong_buy',
  'buy',
  'hold',
  'sell',
  'strong_sell',
] as const;
export type SignalType = (typeof VALID_SIGNAL_TYPES)[number];

/**
 * Type guard to check if a value is a valid SignalType.
 */
export function isSignalType(value: unknown): value is SignalType {
  return typeof value === 'string' && VALID_SIGNAL_TYPES.includes(value as SignalType);
}

/**
 * Safely convert an unknown value to a SignalType, with fallback.
 */
export function toSignalType(value: unknown, fallback: SignalType = 'hold'): SignalType {
  return isSignalType(value) ? value : fallback;
}

// =============================================================================
// Chamber Types
// =============================================================================

/**
 * Valid chamber/role types.
 */
export const VALID_CHAMBERS = ['House', 'Senate', 'Commission', 'Other'] as const;
export type Chamber = (typeof VALID_CHAMBERS)[number];

/**
 * Type guard to check if a value is a valid Chamber.
 */
export function isChamber(value: unknown): value is Chamber {
  return typeof value === 'string' && VALID_CHAMBERS.includes(value as Chamber);
}

/**
 * Safely convert an unknown value to a Chamber, with fallback.
 */
export function toChamber(value: unknown, fallback: Chamber = 'Other'): Chamber {
  return isChamber(value) ? value : fallback;
}

// =============================================================================
// Generic Utility Guards
// =============================================================================

/**
 * Type guard to check if a value is a non-null object.
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Type guard to check if a value is a non-empty string.
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Type guard to check if a value is a positive number.
 */
export function isPositiveNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value) && value > 0;
}

/**
 * Type guard to check if a value is a valid date string.
 */
export function isValidDateString(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const date = new Date(value);
  return !isNaN(date.getTime());
}

/**
 * Safely parse a number from unknown input.
 *
 * @param value - The value to parse
 * @param fallback - Fallback if parsing fails (default: 0)
 * @returns A valid number
 */
export function toNumber(value: unknown, fallback: number = 0): number {
  if (typeof value === 'number' && !isNaN(value)) return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    if (!isNaN(parsed)) return parsed;
  }
  return fallback;
}

/**
 * Safely get a string from unknown input.
 *
 * @param value - The value to convert
 * @param fallback - Fallback if not a string (default: '')
 * @returns A string value
 */
export function toString(value: unknown, fallback: string = ''): string {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return fallback;
  return String(value);
}
