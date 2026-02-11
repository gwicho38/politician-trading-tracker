import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format database labels into human-readable strings.
 * Converts snake_case, lowercase, and abbreviated values to proper display format.
 *
 * Examples:
 * - "house" → "House"
 * - "us_senate" → "US Senate"
 * - "Representative" → "Representative" (unchanged)
 */
export function formatLabel(value: string | null | undefined): string {
  if (!value) return 'Unknown';

  // Handle specific known values
  const labelMap: Record<string, string> = {
    'us_house': 'US House',
    'us_senate': 'US Senate',
    'us_senate_senator': 'US Senate Senator',
    'house': 'House',
    'senate': 'Senate',
    'unknown': 'Unknown',
    'mep': 'MEP',
  };

  const lowerValue = value.toLowerCase();
  if (labelMap[lowerValue]) {
    return labelMap[lowerValue];
  }

  // If already properly formatted (starts with uppercase, no underscores), return as-is
  if (/^[A-Z][a-zA-Z\s]*$/.test(value) && !value.includes('_')) {
    return value;
  }

  // Convert snake_case to Title Case
  return value
    .split('_')
    .map(word => {
      // Keep abbreviations uppercase (us, uk, eu, etc.)
      if (word.length <= 2 && /^[a-z]+$/.test(word)) {
        return word.toUpperCase();
      }
      // Capitalize first letter
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

/**
 * Format a politician's role for display.
 */
export function formatRole(role: string | null | undefined): string {
  return formatLabel(role);
}

/**
 * Format a politician's chamber for display.
 */
export function formatChamber(chamber: string | null | undefined): string {
  return formatLabel(chamber);
}
