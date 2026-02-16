# Dynamic Parties Table — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded party enums with a database-backed `parties` table that auto-registers new parties and provides colors, names, and labels for the frontend.

**Architecture:** A `parties` table stores code, name, jurisdiction, and hex color. The ETL auto-creates unknown parties via `party_registry.py` (Ollama color generation with hash fallback). The frontend preloads parties into a React context on app init, replacing all hardcoded switch statements and enum arrays.

**Tech Stack:** Supabase (PostgreSQL), FastAPI (Python ETL), React + TanStack Query (frontend), Ollama (optional color generation)

**Design doc:** `docs/plans/2026-02-16-dynamic-parties-table-design.md`

---

## Task 1: Database Migration — Create `parties` Table

**Files:**
- Create: `supabase/migrations/20260216100000_create_parties_table.sql`

**Step 1: Write the migration**

```sql
-- Create parties lookup table
CREATE TABLE IF NOT EXISTS parties (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code       VARCHAR(20) NOT NULL UNIQUE,
  name       VARCHAR(100) NOT NULL,
  short_name VARCHAR(30),
  jurisdiction VARCHAR(10) NOT NULL DEFAULT 'US',
  color      VARCHAR(7) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE parties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anon read access" ON parties FOR SELECT USING (true);
CREATE POLICY "Allow service role full access" ON parties FOR ALL
  USING (auth.role() = 'service_role');

-- Seed known parties
INSERT INTO parties (code, name, short_name, jurisdiction, color) VALUES
  ('D',          'Democratic Party',                                   'Democrat',    'US', '#3B82F6'),
  ('R',          'Republican Party',                                   'Republican',  'US', '#EF4444'),
  ('I',          'Independent',                                        'Independent', 'US', '#EAB308'),
  ('EPP',        'European People''s Party',                           'EPP',         'EU', '#38BDF8'),
  ('S&D',        'Progressive Alliance of Socialists and Democrats',   'S&D',         'EU', '#3B82F6'),
  ('Renew',      'Renew Europe',                                       'Renew',       'EU', '#EAB308'),
  ('Greens/EFA', 'Greens/European Free Alliance',                      'Greens/EFA',  'EU', '#22C55E'),
  ('ECR',        'European Conservatives and Reformists',              'ECR',         'EU', '#EF4444'),
  ('ID',         'Identity and Democracy',                             'ID',          'EU', '#6366F1'),
  ('GUE/NGL',    'The Left in the European Parliament',               'GUE/NGL',     'EU', '#F43F5E'),
  ('NI',         'Non-Inscrits',                                       'Non-Inscrit', 'EU', '#94A3B8'),
  ('PfE',        'Patriots for Europe',                                'Patriots',    'EU', '#0E7490')
ON CONFLICT (code) DO NOTHING;

-- Index for fast lookups by jurisdiction
CREATE INDEX IF NOT EXISTS idx_parties_jurisdiction ON parties(jurisdiction);
```

**Step 2: Verify migration syntax**

Run: `cat supabase/migrations/20260216100000_create_parties_table.sql | head -5`
Expected: Clean SQL with no syntax errors.

**Step 3: Commit**

```bash
git add supabase/migrations/20260216100000_create_parties_table.sql
git commit -m "feat: create parties table with seed data"
```

---

## Task 2: ETL — Party Registry Module

**Files:**
- Create: `python-etl-service/app/lib/party_registry.py`
- Create: `python-etl-service/tests/test_party_registry.py`

**Step 1: Write failing tests**

```python
# tests/test_party_registry.py
"""Tests for party_registry module."""
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.lib.party_registry import (
    ensure_party_exists,
    generate_party_color,
    abbreviate_group_name,
)


class TestGeneratePartyColor:
    """Test hex color generation."""

    def test_returns_7_char_hex(self):
        color = generate_party_color("Test Party")
        assert len(color) == 7
        assert color.startswith("#")

    def test_deterministic_for_same_input(self):
        c1 = generate_party_color("Democrats")
        c2 = generate_party_color("Democrats")
        assert c1 == c2

    def test_different_for_different_input(self):
        c1 = generate_party_color("Democrats")
        c2 = generate_party_color("Republicans")
        assert c1 != c2

    def test_valid_hex_chars(self):
        color = generate_party_color("Any Party Name")
        assert all(c in "0123456789abcdefABCDEF#" for c in color)


class TestAbbreviateGroupName:
    """Test EU group name abbreviation."""

    def test_known_group_epp(self):
        assert abbreviate_group_name("Group of the European People's Party (Christian Democrats)") == "EPP"

    def test_known_group_sd(self):
        assert abbreviate_group_name("Group of the Progressive Alliance of Socialists and Democrats") == "S&D"

    def test_known_group_renew(self):
        assert abbreviate_group_name("Renew Europe Group") == "Renew"

    def test_known_group_greens(self):
        assert abbreviate_group_name("Group of the Greens/European Free Alliance") == "Greens/EFA"

    def test_known_group_ecr(self):
        assert abbreviate_group_name("European Conservatives and Reformists Group") == "ECR"

    def test_known_group_id(self):
        assert abbreviate_group_name("Identity and Democracy Group") == "ID"

    def test_known_group_left(self):
        assert abbreviate_group_name("The Left group in the European Parliament - GUE/NGL") == "GUE/NGL"

    def test_known_group_ni(self):
        assert abbreviate_group_name("Non-attached Members") == "NI"

    def test_patriots_for_europe(self):
        assert abbreviate_group_name("Patriots for Europe Group") == "PfE"

    def test_unknown_group_generates_initials(self):
        result = abbreviate_group_name("Some New Political Movement")
        # Should generate initials from significant words
        assert isinstance(result, str)
        assert len(result) <= 20

    def test_empty_string(self):
        assert abbreviate_group_name("") == ""

    def test_none_input(self):
        assert abbreviate_group_name(None) == ""


class TestEnsurePartyExists:
    """Test party registration with Supabase."""

    def test_returns_code_when_party_exists(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"code": "D"}
        ]
        result = ensure_party_exists(mock_sb, "D", "Democratic Party", "US")
        assert result == "D"

    def test_creates_party_when_not_exists(self):
        mock_sb = MagicMock()
        # First call: select returns empty (not found)
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        # Second call: insert succeeds
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"code": "NEW"}]

        result = ensure_party_exists(mock_sb, "NEW", "New Party", "EU")
        assert result == "NEW"
        # Verify insert was called
        mock_sb.table.return_value.insert.assert_called_once()
        insert_arg = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_arg["code"] == "NEW"
        assert insert_arg["name"] == "New Party"
        assert insert_arg["jurisdiction"] == "EU"
        assert insert_arg["color"].startswith("#")

    def test_uses_code_as_name_when_name_not_provided(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"code": "X"}]

        ensure_party_exists(mock_sb, "X")
        insert_arg = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_arg["name"] == "X"

    def test_handles_insert_error_gracefully(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        # Should not raise, should return code anyway
        result = ensure_party_exists(mock_sb, "ERR", "Error Party")
        assert result == "ERR"

    def test_caches_known_parties(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"code": "D"}
        ]

        # Call twice with same code
        ensure_party_exists(mock_sb, "D")
        ensure_party_exists(mock_sb, "D")

        # Should only query DB once (second call hits cache)
        assert mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.call_count == 1
```

**Step 2: Run tests to verify they fail**

Run: `cd python-etl-service && uv run pytest tests/test_party_registry.py -v`
Expected: FAIL — module not found.

**Step 3: Write implementation**

```python
# python-etl-service/app/lib/party_registry.py
"""
Party Registry — auto-creates parties in the `parties` table.

When the ETL encounters a party code not yet in the database,
this module creates it with a generated hex color (Ollama or hash fallback).
"""

import hashlib
import logging
import os
import re
from typing import Dict, Optional, Set

import httpx
from supabase import Client

logger = logging.getLogger(__name__)

# In-memory cache to avoid repeated DB lookups within the same ETL run
_known_parties: Set[str] = set()

# Ollama config (optional — falls back to hash-based color)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

# Known EU group abbreviations (moved from eu_parliament_client.py)
_EU_GROUP_ABBREVIATIONS = {
    "european people's party": "EPP",
    "progressive alliance": "S&D",
    "renew europe": "Renew",
    "greens": "Greens/EFA",
    "european free alliance": "Greens/EFA",
    "conservatives and reformists": "ECR",
    "identity and democracy": "ID",
    "the left group": "GUE/NGL",
    "gue/ngl": "GUE/NGL",
    "non-attached": "NI",
    "patriots for europe": "PfE",
    "europe of sovereign nations": "ESN",
}


def abbreviate_group_name(full_name: Optional[str]) -> str:
    """Convert an EU Parliament group name to its standard abbreviation.

    Checks known patterns first, then generates initials from significant words.
    """
    if not full_name:
        return ""

    lower = full_name.lower().strip()

    # Check known abbreviations
    for pattern, abbrev in _EU_GROUP_ABBREVIATIONS.items():
        if pattern in lower:
            return abbrev

    # Generate initials from significant words (skip articles/prepositions)
    skip_words = {"of", "the", "and", "in", "for", "group", "a", "an"}
    words = re.findall(r"[A-Z][a-z]*|[A-Z]+", full_name)
    if not words:
        words = [w for w in full_name.split() if w.lower() not in skip_words]
    initials = "".join(w[0].upper() for w in words if w.lower() not in skip_words)
    return initials[:20] if initials else full_name[:20]


def generate_party_color(party_name: str) -> str:
    """Generate a hex color for a political party.

    Uses a deterministic hash to produce a visually distinct, saturated color.
    Avoids very dark or very light colors for readability on dark backgrounds.
    """
    h = hashlib.md5(party_name.encode()).hexdigest()
    # Use first 6 hex chars but ensure saturation by mixing channels
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)

    # Boost saturation: push channels apart from the mean
    mean = (r + g + b) // 3
    r = min(255, max(60, r + (r - mean) // 2))
    g = min(255, max(60, g + (g - mean) // 2))
    b = min(255, max(60, b + (b - mean) // 2))

    return f"#{r:02X}{g:02X}{b:02X}"


def ensure_party_exists(
    supabase: Client,
    code: str,
    full_name: Optional[str] = None,
    jurisdiction: str = "US",
) -> str:
    """Ensure a party exists in the parties table. Auto-creates if missing.

    Args:
        supabase: Supabase client
        code: Short party code (e.g., 'D', 'EPP', 'PfE')
        full_name: Full party name (used when creating)
        jurisdiction: 'US' or 'EU'

    Returns:
        The party code (always returns the input code).
    """
    global _known_parties

    if not code:
        return code

    # Check in-memory cache first
    if code in _known_parties:
        return code

    try:
        existing = (
            supabase.table("parties")
            .select("code")
            .eq("code", code)
            .limit(1)
            .execute()
        )
        if existing.data:
            _known_parties.add(code)
            return code
    except Exception as e:
        logger.debug(f"Error checking party {code}: {e}")
        return code

    # Party not found — create it
    name = full_name or code
    short_name = code if len(code) <= 20 else code[:20]
    color = generate_party_color(name)

    try:
        supabase.table("parties").insert({
            "code": code,
            "name": name,
            "short_name": short_name,
            "jurisdiction": jurisdiction,
            "color": color,
        }).execute()
        _known_parties.add(code)
        logger.info(f"Auto-registered party: {code} ({name}) color={color}")
    except Exception as e:
        # Likely a unique constraint race condition — safe to ignore
        logger.debug(f"Error creating party {code}: {e}")
        _known_parties.add(code)

    return code


def reset_cache():
    """Clear the in-memory party cache (useful for testing)."""
    global _known_parties
    _known_parties = set()
```

**Step 4: Run tests to verify they pass**

Run: `cd python-etl-service && uv run pytest tests/test_party_registry.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add python-etl-service/app/lib/party_registry.py python-etl-service/tests/test_party_registry.py
git commit -m "feat: add party_registry module with auto-create and color generation"
```

---

## Task 3: ETL Integration — Wire Party Registry Into ETLs

**Files:**
- Modify: `python-etl-service/app/services/eu_parliament_client.py:336-351` — replace `_abbreviate_group`
- Modify: `python-etl-service/app/lib/politician.py:165-175` — call `ensure_party_exists` before insert
- Modify: `python-etl-service/app/services/biography_generator.py:41-68` — look up party name from DB + fix chamber display

**Step 1: Replace `_abbreviate_group` in `eu_parliament_client.py`**

Replace the `_abbreviate_group` function (lines 336-351) with:

```python
from app.lib.party_registry import abbreviate_group_name

# Delete the old _abbreviate_group function entirely.
# All callers now use abbreviate_group_name from party_registry.
```

Then update all references from `_abbreviate_group(...)` to `abbreviate_group_name(...)` in the same file.

**Step 2: Wire `ensure_party_exists` into `find_or_create_politician`**

In `python-etl-service/app/lib/politician.py`, add at the top:

```python
from app.lib.party_registry import ensure_party_exists
```

Before the `politician_data = { ... }` block (line ~165), add:

```python
        # Register party in parties table (auto-creates if unknown)
        if party:
            jurisdiction = "EU" if chamber == "eu_parliament" else "US"
            ensure_party_exists(supabase, party, jurisdiction=jurisdiction)
```

**Step 3: Fix biography generator**

In `python-etl-service/app/services/biography_generator.py`, replace the `party_full` dict (lines 41-45) with:

```python
    # Look up party display name from parties table
    party_full = party or "Unknown party"
    try:
        from app.lib.database import get_supabase
        sb = get_supabase()
        party_row = sb.table("parties").select("name").eq("code", party).limit(1).execute()
        if party_row.data:
            party_full = party_row.data[0]["name"]
    except Exception:
        # Fallback to simple D/R/I map if DB unavailable
        party_full = {"D": "Democratic", "R": "Republican", "I": "Independent"}.get(
            party or "", party or "Unknown party"
        )
```

Also fix the chamber display (after line 54). Replace the chamber_full block:

```python
    chamber_map = {
        "representative": "Representative",
        "senator": "Senator",
        "mep": "Member of the European Parliament",
    }
    chamber_full = "Member of Congress"
    for key, value in chamber_map.items():
        if key in (role or "").lower():
            chamber_full = value
            break
```

**Step 4: Run affected tests**

Run: `cd python-etl-service && uv run pytest tests/test_politician.py tests/test_house_etl_service.py tests/test_senate_etl_service.py -x -q`
Expected: All PASS (existing tests should still work since `ensure_party_exists` gracefully handles errors).

**Step 5: Commit**

```bash
git add python-etl-service/app/services/eu_parliament_client.py python-etl-service/app/lib/politician.py python-etl-service/app/services/biography_generator.py
git commit -m "feat: wire party_registry into ETL pipeline and fix biography generator"
```

---

## Task 4: Frontend — `useParties` Hook + Party Utilities

**Files:**
- Create: `client/src/hooks/useParties.ts`
- Create: `client/src/lib/partyUtils.ts`

**Step 1: Create the hook and utility functions**

```typescript
// client/src/hooks/useParties.ts
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface PartyRecord {
  id: string;
  code: string;
  name: string;
  short_name: string | null;
  jurisdiction: string;
  color: string;
}

export const useParties = () => {
  return useQuery<PartyRecord[]>({
    queryKey: ['parties'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('parties')
        .select('*')
        .order('jurisdiction')
        .order('name');
      if (error) throw error;
      return data || [];
    },
    staleTime: 30 * 60 * 1000, // 30 min cache
  });
};
```

```typescript
// client/src/lib/partyUtils.ts
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
```

**Step 2: Commit**

```bash
git add client/src/hooks/useParties.ts client/src/lib/partyUtils.ts
git commit -m "feat: add useParties hook and party utility functions"
```

---

## Task 5: Frontend — Replace `typeGuards.ts` Party Section + `mockData.ts` Color Maps

**Files:**
- Modify: `client/src/lib/typeGuards.ts:10-101` — remove hardcoded party enum, simplify functions
- Modify: `client/src/lib/mockData.ts:245-295` — replace `getPartyColor`/`getPartyBg` switch statements

**Step 1: Simplify typeGuards.ts**

Replace lines 10-101 (the entire Party Types section) with:

```typescript
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
  // Kept as lightweight fallback; components should use partyUtils.getPartyName
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
```

**Step 2: Replace mockData.ts color functions**

Replace `getPartyColor` and `getPartyBg` (lines 245-295) with thin wrappers that still work without the party context (for backwards compat during migration):

```typescript
/**
 * @deprecated Use partyUtils.getPartyColor with useParties() instead.
 * Kept during migration — returns a Tailwind class for legacy callers.
 */
export const getPartyColor = (party: string): string => {
  // Legacy fallback — components should migrate to partyUtils
  const map: Record<string, string> = {
    D: 'text-blue-400', 'S&D': 'text-blue-400',
    R: 'text-red-400', ECR: 'text-red-400',
    I: 'text-yellow-400', Renew: 'text-yellow-400',
    EPP: 'text-sky-400', 'Greens/EFA': 'text-green-400',
    ID: 'text-indigo-400', 'GUE/NGL': 'text-rose-400',
    NI: 'text-slate-400',
  };
  return map[party] || 'text-muted-foreground';
};

/**
 * @deprecated Use partyUtils.partyBadgeStyle with useParties() instead.
 */
export const getPartyBg = (party: string): string => {
  const map: Record<string, string> = {
    D: 'bg-blue-500/20 border-blue-500/30', 'S&D': 'bg-blue-500/20 border-blue-500/30',
    R: 'bg-red-500/20 border-red-500/30', ECR: 'bg-red-500/20 border-red-500/30',
    I: 'bg-yellow-500/20 border-yellow-500/30', Renew: 'bg-yellow-500/20 border-yellow-500/30',
    EPP: 'bg-sky-500/20 border-sky-500/30', 'Greens/EFA': 'bg-green-500/20 border-green-500/30',
    ID: 'bg-indigo-500/20 border-indigo-500/30', 'GUE/NGL': 'bg-rose-500/20 border-rose-500/30',
    NI: 'bg-slate-500/20 border-slate-500/30',
  };
  return map[party] || 'bg-muted border-border';
};
```

**Step 3: Run frontend tests**

Run: `cd client && npx vitest run`
Expected: All 800 tests PASS (typeGuards tests may need updating if they test VALID_PARTIES).

**Step 4: Fix any failing typeGuards tests**

Update `client/src/lib/typeGuards.test.ts` to reflect that `isParty` now accepts any non-empty string and `toParty` returns the input string directly.

**Step 5: Commit**

```bash
git add client/src/lib/typeGuards.ts client/src/lib/typeGuards.test.ts client/src/lib/mockData.ts
git commit -m "refactor: simplify party type system for dynamic parties"
```

---

## Task 6: Frontend — Migrate Components to `useParties` + `partyUtils`

This is the bulk migration. Each component follows the same pattern:

1. Add `import { useParties } from '@/hooks/useParties';`
2. Add `import { buildPartyMap, getPartyColor, getPartyLabel, partyColorStyle, partyBadgeStyle } from '@/lib/partyUtils';`
3. Inside the component, add: `const { data: parties = [] } = useParties();` and `const partyMap = useMemo(() => buildPartyMap(parties), [parties]);`
4. Replace `getPartyColor(party)` (Tailwind class on className) with `style={partyColorStyle(partyMap, party)}`
5. Replace `getPartyBg(party)` (Tailwind class on className) with `style={partyBadgeStyle(partyMap, party)}`
6. Replace `getPartyLabel(toParty(party))` with `getPartyLabel(partyMap, party)`
7. Remove now-unused imports of `toParty`, `getPartyLabel` from typeGuards, `getPartyColor`/`getPartyBg` from mockData

**Files to migrate (in order):**

| # | File | Party usage pattern |
|---|------|-------------------|
| 1 | `client/src/components/LandingTradesTable.tsx` | Badge + filter dropdown + text color |
| 2 | `client/src/components/PoliticiansView.tsx` | Badge + filter dropdown + text color |
| 3 | `client/src/components/TopTraders.tsx` | Badge |
| 4 | `client/src/components/TradeCard.tsx` | Badge |
| 5 | `client/src/components/GlobalSearch.tsx` | Badge |
| 6 | `client/src/components/RecentTrades.tsx` | Badge |
| 7 | `client/src/components/TradesView.tsx` | Badge |
| 8 | `client/src/components/detail-modals/PoliticianDetailModal.tsx` | Badge |
| 9 | `client/src/components/detail-modals/PoliticianProfileModal.tsx` | Badge + bio generation |
| 10 | `client/src/components/detail-modals/TickerDetailModal.tsx` | Badge |
| 11 | `client/src/components/detail-modals/MonthDetailModal.tsx` | Badge |
| 12 | `client/src/components/admin/AdminAnalytics.tsx` | Recharts hex colors |
| 13 | `client/src/components/admin/AdminContentManagement.tsx` | Badge variant |

**For the filter dropdown components (LandingTradesTable + PoliticiansView):**

Replace the hardcoded `PARTY_OPTIONS` / `PARTY_FILTER_OPTIONS` arrays with:

```typescript
const { data: parties = [] } = useParties();
const partyFilterOptions = useMemo(() => buildPartyFilterOptions(parties), [parties]);
```

Then use `partyFilterOptions` in the `<Select>` dropdown.

**For PoliticianProfileModal (bio fix):**

Replace the `generateClientFallbackBio` function's party handling:

```typescript
const partyMap = useMemo(() => buildPartyMap(parties), [parties]);

const generateClientFallbackBio = (pol: Politician, det: typeof detail): string => {
  const partyFull = getPartyName(partyMap, pol.party) || 'Independent';
  const chamberFull = pol.chamber?.toLowerCase().includes('rep') ? 'Representative' :
                      pol.chamber?.toLowerCase().includes('sen') ? 'Senator' :
                      pol.role?.toLowerCase() === 'mep' ? 'Member of the European Parliament' :
                      'Member of Congress';
  // ... rest stays the same
};
```

**For AdminAnalytics (Recharts):**

Replace the local `PARTY_COLORS` map and `getPartyColor` function:

```typescript
const { data: parties = [] } = useParties();
const partyMap = useMemo(() => buildPartyMap(parties), [parties]);

// In the chart Cell component:
<Cell fill={getPartyColor(partyMap, entry.name)} />
```

**Commit after each batch of 3-4 files:**

```bash
git commit -m "refactor: migrate LandingTradesTable, PoliticiansView, TopTraders to dynamic parties"
git commit -m "refactor: migrate TradeCard, GlobalSearch, RecentTrades, TradesView to dynamic parties"
git commit -m "refactor: migrate detail modals to dynamic parties"
git commit -m "refactor: migrate admin components to dynamic parties"
```

---

## Task 7: Edge Function — Fix Biography Party Lookup

**Files:**
- Modify: `supabase/functions/politician-profile/index.ts:114-145`

**Step 1: Update `buildPrompt` and `generateFallbackBio`**

In `buildPrompt` (line 119), replace the raw `politician.party` with a looked-up name:

```typescript
// Before buildPrompt, fetch party name
const { data: partyData } = await supabaseClient
  .from('parties')
  .select('name')
  .eq('code', politician.party)
  .single();
const partyName = partyData?.name || politician.party || 'Independent';
```

In `generateFallbackBio` (lines 132-145), replace the ternary chain:

```typescript
function generateFallbackBio(politician: PoliticianData, partyName: string): string {
  const chamberFull = politician.chamber?.toLowerCase().includes("rep") ? "Representative" :
                      politician.chamber?.toLowerCase().includes("sen") ? "Senator" :
                      politician.role?.toLowerCase() === "mep" ? "Member of the European Parliament" :
                      "Member of Congress";
  // ... use partyName instead of raw politician.party
}
```

**Step 2: Commit**

```bash
git add supabase/functions/politician-profile/index.ts
git commit -m "fix: look up party name from parties table in edge function bio"
```

---

## Task 8: Update Existing Party Values + Clean Up

**Files:**
- Create: `supabase/migrations/20260216100001_update_existing_party_values.sql`

**Step 1: Write migration to update "Patriots for Europe Group" and similar raw values**

```sql
-- Fix raw EU party values that weren't abbreviated
UPDATE politicians
SET party = 'PfE'
WHERE party ILIKE '%patriots for europe%';

UPDATE politicians
SET party = 'ESN'
WHERE party ILIKE '%europe of sovereign%';

-- Fix any other truncated raw group names
UPDATE politicians
SET party = 'EPP'
WHERE party ILIKE '%european people%' AND party != 'EPP';

UPDATE politicians
SET party = 'S&D'
WHERE party ILIKE '%progressive alliance%' AND party != 'S&D';

UPDATE politicians
SET party = 'Renew'
WHERE party ILIKE '%renew europe%' AND party != 'Renew';

UPDATE politicians
SET party = 'Greens/EFA'
WHERE (party ILIKE '%greens%' OR party ILIKE '%free alliance%')
  AND party != 'Greens/EFA';

UPDATE politicians
SET party = 'ECR'
WHERE party ILIKE '%conservatives and reformists%' AND party != 'ECR';

UPDATE politicians
SET party = 'ID'
WHERE party ILIKE '%identity and democracy%' AND party != 'ID';

UPDATE politicians
SET party = 'GUE/NGL'
WHERE party ILIKE '%the left group%' AND party != 'GUE/NGL';

UPDATE politicians
SET party = 'NI'
WHERE party ILIKE '%non-attached%' AND party != 'NI';
```

**Step 2: Commit**

```bash
git add supabase/migrations/20260216100001_update_existing_party_values.sql
git commit -m "fix: normalize existing raw party values to abbreviated codes"
```

---

## Task 9: Run Full Test Suite + Final Verification

**Step 1: Run all ETL tests**

Run: `cd python-etl-service && uv run pytest tests/ -x -q`
Expected: All ~1940 tests PASS.

**Step 2: Run all frontend tests**

Run: `cd client && npx vitest run`
Expected: All ~800 tests PASS (some may need updating for new party type).

**Step 3: Build frontend**

Run: `cd client && npm run build`
Expected: Clean build, no TypeScript errors.

**Step 4: Final commit + PR**

```bash
git push -u origin HEAD
gh pr create --title "feat: dynamic parties table with auto-registration" --body "..."
gh run watch
gh pr merge --squash --delete-branch
```

---

## Execution Order Summary

| Task | Description | Dependencies |
|------|-------------|-------------|
| 1 | DB migration (create parties table) | None |
| 2 | party_registry.py + tests | None |
| 3 | Wire registry into ETL + fix bio generator | 1, 2 |
| 4 | useParties hook + partyUtils | None |
| 5 | Simplify typeGuards + mockData | 4 |
| 6 | Migrate all components | 4, 5 |
| 7 | Fix edge function bio | 1 |
| 8 | Normalize existing party values | 1 |
| 9 | Full test suite + PR | All |

Tasks 1, 2, and 4 can be done in parallel (no dependencies). Tasks 3, 5, 7, 8 depend on their prerequisites. Task 6 is the largest (13 component files) and should be done after 4+5. Task 9 is the final verification.
