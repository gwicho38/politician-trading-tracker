import { describe, it, expect } from 'vitest';
import {
  // Party
  VALID_PARTIES,
  isParty,
  toParty,
  getPartyFullName,
  // Transaction types
  VALID_TRANSACTION_TYPES,
  DISPLAY_TRANSACTION_TYPES,
  isTransactionType,
  isDisplayTransactionType,
  toTransactionType,
  toDisplayTransactionType,
  toDatabaseTransactionType,
  // Signal types
  VALID_SIGNAL_TYPES,
  isSignalType,
  toSignalType,
  // Chamber
  VALID_CHAMBERS,
  isChamber,
  toChamber,
  // Generic utilities
  isObject,
  isNonEmptyString,
  isPositiveNumber,
  isValidDateString,
  toNumber,
  toString,
} from './typeGuards';

// =============================================================================
// Party Tests
// =============================================================================

describe('Party type guards', () => {
  describe('isParty', () => {
    it('returns true for valid parties', () => {
      expect(isParty('D')).toBe(true);
      expect(isParty('R')).toBe(true);
      expect(isParty('I')).toBe(true);
      expect(isParty('Other')).toBe(true);
    });

    it('returns false for invalid parties', () => {
      expect(isParty('Democrat')).toBe(false);
      expect(isParty('Republican')).toBe(false);
      expect(isParty('')).toBe(false);
      expect(isParty(null)).toBe(false);
      expect(isParty(undefined)).toBe(false);
      expect(isParty(123)).toBe(false);
      expect(isParty({})).toBe(false);
    });

    it('is case-sensitive', () => {
      expect(isParty('d')).toBe(false);
      expect(isParty('r')).toBe(false);
      expect(isParty('other')).toBe(false);
    });
  });

  describe('toParty', () => {
    it('returns the party if valid', () => {
      expect(toParty('D')).toBe('D');
      expect(toParty('R')).toBe('R');
      expect(toParty('I')).toBe('I');
      expect(toParty('Other')).toBe('Other');
    });

    it('returns fallback for invalid values', () => {
      expect(toParty('invalid')).toBe('Other');
      expect(toParty(null)).toBe('Other');
      expect(toParty(undefined)).toBe('Other');
    });

    it('respects custom fallback', () => {
      expect(toParty('invalid', 'D')).toBe('D');
      expect(toParty(null, 'R')).toBe('R');
    });
  });

  describe('getPartyFullName', () => {
    it('returns full names for all parties', () => {
      expect(getPartyFullName('D')).toBe('Democratic');
      expect(getPartyFullName('R')).toBe('Republican');
      expect(getPartyFullName('I')).toBe('Independent');
      expect(getPartyFullName('Other')).toBe('Other');
    });
  });

  describe('VALID_PARTIES constant', () => {
    it('contains all expected parties', () => {
      // US parties
      expect(VALID_PARTIES).toContain('D');
      expect(VALID_PARTIES).toContain('R');
      expect(VALID_PARTIES).toContain('I');
      expect(VALID_PARTIES).toContain('Other');
      // EU Parliament groups
      expect(VALID_PARTIES).toContain('EPP');
      expect(VALID_PARTIES).toContain('S&D');
      expect(VALID_PARTIES).toContain('Renew');
      expect(VALID_PARTIES).toContain('Greens/EFA');
      expect(VALID_PARTIES).toContain('ECR');
      expect(VALID_PARTIES).toContain('ID');
      expect(VALID_PARTIES).toContain('GUE/NGL');
      expect(VALID_PARTIES).toContain('NI');
      expect(VALID_PARTIES.length).toBe(12);
    });
  });
});

// =============================================================================
// Transaction Type Tests
// =============================================================================

describe('Transaction type guards', () => {
  describe('isTransactionType', () => {
    it('returns true for valid transaction types', () => {
      expect(isTransactionType('purchase')).toBe(true);
      expect(isTransactionType('sale')).toBe(true);
      expect(isTransactionType('exchange')).toBe(true);
      expect(isTransactionType('holding')).toBe(true);
      expect(isTransactionType('unknown')).toBe(true);
    });

    it('returns false for display types', () => {
      expect(isTransactionType('buy')).toBe(false);
      expect(isTransactionType('sell')).toBe(false);
    });

    it('returns false for invalid values', () => {
      expect(isTransactionType('')).toBe(false);
      expect(isTransactionType(null)).toBe(false);
      expect(isTransactionType(123)).toBe(false);
    });
  });

  describe('isDisplayTransactionType', () => {
    it('returns true for display transaction types', () => {
      expect(isDisplayTransactionType('buy')).toBe(true);
      expect(isDisplayTransactionType('sell')).toBe(true);
      expect(isDisplayTransactionType('exchange')).toBe(true);
      expect(isDisplayTransactionType('holding')).toBe(true);
      expect(isDisplayTransactionType('unknown')).toBe(true);
    });

    it('returns false for database types', () => {
      expect(isDisplayTransactionType('purchase')).toBe(false);
      expect(isDisplayTransactionType('sale')).toBe(false);
    });
  });

  describe('toTransactionType', () => {
    it('returns the type if valid', () => {
      expect(toTransactionType('purchase')).toBe('purchase');
      expect(toTransactionType('sale')).toBe('sale');
    });

    it('returns fallback for invalid values', () => {
      expect(toTransactionType('invalid')).toBe('unknown');
      expect(toTransactionType('buy')).toBe('unknown'); // display type, not db type
    });

    it('respects custom fallback', () => {
      expect(toTransactionType('invalid', 'purchase')).toBe('purchase');
    });
  });

  describe('toDisplayTransactionType', () => {
    it('converts purchase to buy', () => {
      expect(toDisplayTransactionType('purchase')).toBe('buy');
    });

    it('converts sale to sell', () => {
      expect(toDisplayTransactionType('sale')).toBe('sell');
    });

    it('passes through valid display types', () => {
      expect(toDisplayTransactionType('exchange')).toBe('exchange');
      expect(toDisplayTransactionType('holding')).toBe('holding');
      expect(toDisplayTransactionType('buy')).toBe('buy');
      expect(toDisplayTransactionType('sell')).toBe('sell');
    });

    it('returns unknown for invalid values', () => {
      expect(toDisplayTransactionType('invalid')).toBe('unknown');
      expect(toDisplayTransactionType(null)).toBe('unknown');
    });
  });

  describe('toDatabaseTransactionType', () => {
    it('converts buy to purchase', () => {
      expect(toDatabaseTransactionType('buy')).toBe('purchase');
    });

    it('converts sell to sale', () => {
      expect(toDatabaseTransactionType('sell')).toBe('sale');
    });

    it('passes through valid database types', () => {
      expect(toDatabaseTransactionType('purchase')).toBe('purchase');
      expect(toDatabaseTransactionType('sale')).toBe('sale');
      expect(toDatabaseTransactionType('exchange')).toBe('exchange');
    });

    it('returns unknown for invalid values', () => {
      expect(toDatabaseTransactionType('invalid')).toBe('unknown');
    });
  });

  describe('Constants', () => {
    it('VALID_TRANSACTION_TYPES has expected values', () => {
      expect(VALID_TRANSACTION_TYPES).toContain('purchase');
      expect(VALID_TRANSACTION_TYPES).toContain('sale');
      expect(VALID_TRANSACTION_TYPES).toContain('exchange');
      expect(VALID_TRANSACTION_TYPES).toContain('holding');
      expect(VALID_TRANSACTION_TYPES).toContain('unknown');
    });

    it('DISPLAY_TRANSACTION_TYPES has expected values', () => {
      expect(DISPLAY_TRANSACTION_TYPES).toContain('buy');
      expect(DISPLAY_TRANSACTION_TYPES).toContain('sell');
      expect(DISPLAY_TRANSACTION_TYPES).toContain('exchange');
    });
  });
});

// =============================================================================
// Signal Type Tests
// =============================================================================

describe('Signal type guards', () => {
  describe('isSignalType', () => {
    it('returns true for valid signal types', () => {
      expect(isSignalType('strong_buy')).toBe(true);
      expect(isSignalType('buy')).toBe(true);
      expect(isSignalType('hold')).toBe(true);
      expect(isSignalType('sell')).toBe(true);
      expect(isSignalType('strong_sell')).toBe(true);
    });

    it('returns false for invalid values', () => {
      expect(isSignalType('purchase')).toBe(false);
      expect(isSignalType('STRONG_BUY')).toBe(false);
      expect(isSignalType('')).toBe(false);
      expect(isSignalType(null)).toBe(false);
    });
  });

  describe('toSignalType', () => {
    it('returns the type if valid', () => {
      expect(toSignalType('strong_buy')).toBe('strong_buy');
      expect(toSignalType('sell')).toBe('sell');
    });

    it('returns hold as default fallback', () => {
      expect(toSignalType('invalid')).toBe('hold');
      expect(toSignalType(null)).toBe('hold');
    });

    it('respects custom fallback', () => {
      expect(toSignalType('invalid', 'buy')).toBe('buy');
    });
  });

  describe('VALID_SIGNAL_TYPES constant', () => {
    it('contains all signal types in order', () => {
      expect(VALID_SIGNAL_TYPES).toEqual(['strong_buy', 'buy', 'hold', 'sell', 'strong_sell']);
    });
  });
});

// =============================================================================
// Chamber Type Tests
// =============================================================================

describe('Chamber type guards', () => {
  describe('isChamber', () => {
    it('returns true for valid chambers', () => {
      expect(isChamber('House')).toBe(true);
      expect(isChamber('Senate')).toBe(true);
      expect(isChamber('Commission')).toBe(true);
      expect(isChamber('Other')).toBe(true);
    });

    it('returns false for invalid values', () => {
      expect(isChamber('house')).toBe(false); // case-sensitive
      expect(isChamber('SENATE')).toBe(false);
      expect(isChamber('')).toBe(false);
      expect(isChamber(null)).toBe(false);
    });
  });

  describe('toChamber', () => {
    it('returns the chamber if valid', () => {
      expect(toChamber('House')).toBe('House');
      expect(toChamber('Senate')).toBe('Senate');
    });

    it('returns Other as default fallback', () => {
      expect(toChamber('invalid')).toBe('Other');
      expect(toChamber(null)).toBe('Other');
    });

    it('respects custom fallback', () => {
      expect(toChamber('invalid', 'House')).toBe('House');
    });
  });

  describe('VALID_CHAMBERS constant', () => {
    it('contains expected chambers', () => {
      expect(VALID_CHAMBERS).toContain('House');
      expect(VALID_CHAMBERS).toContain('Senate');
      expect(VALID_CHAMBERS).toContain('Commission');
      expect(VALID_CHAMBERS).toContain('Other');
    });
  });
});

// =============================================================================
// Generic Utility Tests
// =============================================================================

describe('Generic utility guards', () => {
  describe('isObject', () => {
    it('returns true for plain objects', () => {
      expect(isObject({})).toBe(true);
      expect(isObject({ a: 1 })).toBe(true);
    });

    it('returns false for arrays', () => {
      expect(isObject([])).toBe(false);
      expect(isObject([1, 2, 3])).toBe(false);
    });

    it('returns false for primitives and null', () => {
      expect(isObject(null)).toBe(false);
      expect(isObject(undefined)).toBe(false);
      expect(isObject('string')).toBe(false);
      expect(isObject(123)).toBe(false);
      expect(isObject(true)).toBe(false);
    });
  });

  describe('isNonEmptyString', () => {
    it('returns true for non-empty strings', () => {
      expect(isNonEmptyString('hello')).toBe(true);
      expect(isNonEmptyString('a')).toBe(true);
      expect(isNonEmptyString(' a ')).toBe(true);
    });

    it('returns false for empty or whitespace-only strings', () => {
      expect(isNonEmptyString('')).toBe(false);
      expect(isNonEmptyString('   ')).toBe(false);
      expect(isNonEmptyString('\t\n')).toBe(false);
    });

    it('returns false for non-strings', () => {
      expect(isNonEmptyString(null)).toBe(false);
      expect(isNonEmptyString(undefined)).toBe(false);
      expect(isNonEmptyString(123)).toBe(false);
    });
  });

  describe('isPositiveNumber', () => {
    it('returns true for positive numbers', () => {
      expect(isPositiveNumber(1)).toBe(true);
      expect(isPositiveNumber(0.1)).toBe(true);
      expect(isPositiveNumber(1000000)).toBe(true);
    });

    it('returns false for zero and negative numbers', () => {
      expect(isPositiveNumber(0)).toBe(false);
      expect(isPositiveNumber(-1)).toBe(false);
      expect(isPositiveNumber(-0.1)).toBe(false);
    });

    it('returns false for NaN and non-numbers', () => {
      expect(isPositiveNumber(NaN)).toBe(false);
      expect(isPositiveNumber('1')).toBe(false);
      expect(isPositiveNumber(null)).toBe(false);
    });
  });

  describe('isValidDateString', () => {
    it('returns true for valid date strings', () => {
      expect(isValidDateString('2024-01-15')).toBe(true);
      expect(isValidDateString('2024-12-31T23:59:59Z')).toBe(true);
      expect(isValidDateString('January 1, 2024')).toBe(true);
    });

    it('returns false for invalid date strings', () => {
      expect(isValidDateString('not-a-date')).toBe(false);
      expect(isValidDateString('')).toBe(false);
    });

    it('returns false for non-strings', () => {
      expect(isValidDateString(null)).toBe(false);
      expect(isValidDateString(undefined)).toBe(false);
      expect(isValidDateString(12345)).toBe(false);
    });
  });

  describe('toNumber', () => {
    it('returns numbers as-is', () => {
      expect(toNumber(42)).toBe(42);
      expect(toNumber(3.14)).toBe(3.14);
      expect(toNumber(-10)).toBe(-10);
    });

    it('parses numeric strings', () => {
      expect(toNumber('42')).toBe(42);
      expect(toNumber('3.14')).toBe(3.14);
      expect(toNumber('-10')).toBe(-10);
    });

    it('returns fallback for invalid values', () => {
      expect(toNumber('not a number')).toBe(0);
      expect(toNumber(null)).toBe(0);
      expect(toNumber(undefined)).toBe(0);
      expect(toNumber(NaN)).toBe(0);
    });

    it('respects custom fallback', () => {
      expect(toNumber('invalid', 100)).toBe(100);
      expect(toNumber(null, -1)).toBe(-1);
    });
  });

  describe('toString', () => {
    it('returns strings as-is', () => {
      expect(toString('hello')).toBe('hello');
      expect(toString('')).toBe('');
    });

    it('converts numbers to strings', () => {
      expect(toString(42)).toBe('42');
      expect(toString(3.14)).toBe('3.14');
    });

    it('returns fallback for null/undefined', () => {
      expect(toString(null)).toBe('');
      expect(toString(undefined)).toBe('');
    });

    it('respects custom fallback', () => {
      expect(toString(null, 'N/A')).toBe('N/A');
      expect(toString(undefined, 'default')).toBe('default');
    });

    it('converts other types to string', () => {
      expect(toString(true)).toBe('true');
      expect(toString(false)).toBe('false');
    });
  });
});
