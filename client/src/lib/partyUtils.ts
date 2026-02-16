import * as React from 'react';
import type { PartyRecord } from '@/hooks/useParties';

// Default fallback color for unknown parties (gray)
const FALLBACK_COLOR = '#94A3B8';

/**
 * Build a Map from party code -> PartyRecord for O(1) lookups.
 */
export function buildPartyMap(parties: PartyRecord[]): Map<string, PartyRecord> {
  return new Map(parties.map(p => [p.code, p]));
}

/**
 * Get hex color for a party code. Returns fallback gray if not found.
 */
export function getPartyColor(partyMap: Map<string, PartyRecord>, code: string | null | undefined): string {
  if (!code) return FALLBACK_COLOR;
  return partyMap.get(code)?.color || FALLBACK_COLOR;
}

/**
 * Get display label for a party (short_name or code).
 */
export function getPartyLabel(partyMap: Map<string, PartyRecord>, code: string | null | undefined): string {
  if (!code) return 'Unknown';
  const party = partyMap.get(code);
  return party?.short_name || party?.code || code;
}

/**
 * Get full name for a party.
 */
export function getPartyName(partyMap: Map<string, PartyRecord>, code: string | null | undefined): string {
  if (!code) return 'Unknown';
  const party = partyMap.get(code);
  return party?.name || code;
}

/**
 * Generate inline style for party text color.
 */
export function partyColorStyle(partyMap: Map<string, PartyRecord>, code: string | null | undefined): React.CSSProperties {
  return { color: getPartyColor(partyMap, code) };
}

/**
 * Generate inline style for party badge background + border.
 * Uses 20% opacity for bg and 30% for border.
 */
export function partyBadgeStyle(partyMap: Map<string, PartyRecord>, code: string | null | undefined): React.CSSProperties {
  const hex = getPartyColor(partyMap, code);
  return {
    backgroundColor: hex + '33',  // 20% opacity
    borderColor: hex + '4D',      // 30% opacity
    borderWidth: '1px',
    borderStyle: 'solid',
  };
}

/**
 * Build party filter options from DB records, grouped by jurisdiction.
 */
export function buildPartyFilterOptions(parties: PartyRecord[]): { value: string; label: string }[] {
  const usParties = parties.filter(p => p.jurisdiction === 'US');
  const euParties = parties.filter(p => p.jurisdiction === 'EU');
  const otherParties = parties.filter(p => p.jurisdiction !== 'US' && p.jurisdiction !== 'EU');

  return [
    { value: '', label: 'All Parties' },
    ...usParties.map(p => ({ value: p.code, label: p.short_name || p.code })),
    ...euParties.map(p => ({ value: p.code, label: p.short_name || p.code })),
    ...otherParties.map(p => ({ value: p.code, label: p.short_name || p.code })),
  ];
}
