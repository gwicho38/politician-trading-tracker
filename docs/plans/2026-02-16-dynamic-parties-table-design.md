# Dynamic Parties Table Design

**Date:** 2026-02-16
**Status:** Approved
**Problem:** Political parties are hardcoded as enums across 11+ frontend components, 3 ETL services, and 3 biography generators. When the EU Parliament ETL encounters a party not in the hardcoded map (e.g., "Patriots for Europe Group"), it stores the raw string, which the frontend can't display — falling back to "Other" with no color. Biography generators produce broken text like "Alexandre VARAUT is a Patriots for Europe Group eu_parliament from France."

## Decisions

- **Approach A: Soft FK + auto-create** — `parties` table with auto-registration of unknown parties. `politicians.party` stays `VARCHAR` referencing `parties.code`. No hard FK constraint.
- **Data flow:** Frontend preloads all parties on app init via `useQuery` with 30-min cache.
- **Color format:** Hex colors (`#3B82F6`) stored in DB. Works for both Tailwind inline styles and Recharts fills.
- **Uniqueness:** One row per party code globally. `jurisdiction` column for context (US/EU).

## Database Schema

```sql
CREATE TABLE parties (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code       VARCHAR(20) NOT NULL UNIQUE,
  name       VARCHAR(100) NOT NULL,
  short_name VARCHAR(30),
  jurisdiction VARCHAR(10) NOT NULL DEFAULT 'US',
  color      VARCHAR(7) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: anon read access
ALTER TABLE parties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anon read access" ON parties FOR SELECT USING (true);
```

### Seed Data

| code | name | short_name | jurisdiction | color |
|------|------|------------|-------------|-------|
| D | Democratic Party | Democrat | US | #3B82F6 |
| R | Republican Party | Republican | US | #EF4444 |
| I | Independent | Independent | US | #EAB308 |
| EPP | European People's Party | EPP | EU | #38BDF8 |
| S&D | Progressive Alliance of Socialists and Democrats | S&D | EU | #3B82F6 |
| Renew | Renew Europe | Renew | EU | #EAB308 |
| Greens/EFA | Greens/European Free Alliance | Greens/EFA | EU | #22C55E |
| ECR | European Conservatives and Reformists | ECR | EU | #EF4444 |
| ID | Identity and Democracy | ID | EU | #6366F1 |
| GUE/NGL | The Left in the European Parliament | GUE/NGL | EU | #F43F5E |
| NI | Non-Inscrits | Non-Inscrit | EU | #94A3B8 |
| PfE | Patriots for Europe | Patriots | EU | #0E7490 |

## ETL Party Registry

New utility: `python-etl-service/app/lib/party_registry.py`

```python
def ensure_party_exists(supabase, code, full_name=None, jurisdiction='US'):
    """Look up party by code. If not found, auto-create with generated color."""
    existing = supabase.table("parties").select("code").eq("code", code).limit(1).execute()
    if existing.data:
        return code

    color = generate_party_color(full_name or code)  # Ollama or random fallback

    supabase.table("parties").insert({
        "code": code,
        "name": full_name or code,
        "short_name": code[:20],
        "jurisdiction": jurisdiction,
        "color": color,
    }).execute()
    return code


def generate_party_color(party_name):
    """Generate a hex color for a political party.
    1. Try Ollama: 'What hex color best represents {party_name}?'
    2. Fallback: deterministic hash-based color from party name
    """
    ...
```

### Integration Points

- `eu_parliament_client.py._abbreviate_group()`: Replace hardcoded map. Look up `parties` table by full name pattern. If not found, generate a new code from initials (e.g., "Patriots for Europe Group" -> "PfE") and call `ensure_party_exists()`.
- `house_etl.py`: After resolving party from @unitedstates dataset, call `ensure_party_exists('D', 'Democratic Party', 'US')`.
- `senate_etl.py`: Same pattern for Senate party values.
- `find_or_create_politician()`: Before inserting/updating, call `ensure_party_exists()` if party is non-null.

## Frontend Changes

### New Hook: `useParties()`

```typescript
export const useParties = () => useQuery({
  queryKey: ['parties'],
  queryFn: async () => {
    const { data } = await supabase.from('parties').select('*');
    return data || [];
  },
  staleTime: 30 * 60 * 1000,
});
```

### PartyContext Provider

Wrap the app in a `PartyProvider` that exposes:
- `parties: Party[]` — full list
- `getPartyColor(code: string): string` — hex color lookup
- `getPartyName(code: string): string` — display name lookup
- `getPartyLabel(code: string): string` — short name lookup

### Component Migration

Replace in all 11 component files:
- `getPartyColor(party)` (Tailwind class) -> `getPartyColor(party)` (hex from context) applied via `style={{ color }}`
- `getPartyBg(party)` (Tailwind class) -> hex color with opacity applied via `style={{ backgroundColor: color + '33', borderColor: color + '4D' }}`
- `getPartyLabel(toParty(party))` -> `getPartyLabel(party)` from context
- `toParty(party)` calls removed — any string is valid

### Filter Dropdowns

`LandingTradesTable.tsx` and `PoliticiansView.tsx`:
- Replace hardcoded `PARTY_OPTIONS` / `PARTY_FILTER_OPTIONS` with parties from `useParties()`
- Group by jurisdiction (US parties first, then EU)

### Admin Analytics

`AdminAnalytics.tsx`:
- Replace local `PARTY_COLORS` hex map with parties context lookup

## Biography Fix

All 3 biography generators updated:

### Python (`biography_generator.py`)
```python
# Before: hardcoded D/R/I dict
# After: query parties table
party_row = supabase.table("parties").select("name").eq("code", party).limit(1).execute()
party_full = party_row.data[0]["name"] if party_row.data else party or "Unknown"
```

### Edge Function (`politician-profile/index.ts`)
```typescript
// Fetch party name from parties table
const { data: partyData } = await supabase.from('parties').select('name').eq('code', politician.party).single();
const partyFull = partyData?.name || politician.party || 'Independent';
```

### Client Fallback (`PoliticianProfileModal.tsx`)
```typescript
// Use parties context
const partyName = getPartyName(politician.party);
```

### Chamber Display Fix
Map raw `chamber` values to display names in all bio generators:
- `"eu_parliament"` -> `"EU Parliament"`
- `"house"` -> `"US House of Representatives"`
- `"senate"` -> `"US Senate"`

## Files Changed

| File | Change |
|------|--------|
| `supabase/migrations/2026XXXX_create_parties_table.sql` | New: create + seed |
| `python-etl-service/app/lib/party_registry.py` | New: ensure_party_exists + color gen |
| `python-etl-service/app/services/eu_parliament_client.py` | Replace `_abbreviate_group` hardcoded map |
| `python-etl-service/app/services/house_etl.py` | Call ensure_party_exists |
| `python-etl-service/app/services/senate_etl.py` | Call ensure_party_exists |
| `python-etl-service/app/lib/politician.py` | Call ensure_party_exists before insert |
| `python-etl-service/app/services/biography_generator.py` | Look up party name from DB |
| `python-etl-service/app/services/party_enrichment.py` | Register D/R/I via party_registry |
| `supabase/functions/politician-profile/index.ts` | Fetch party name from DB |
| `client/src/lib/typeGuards.ts` | Remove VALID_PARTIES, simplify toParty |
| `client/src/lib/mockData.ts` | Replace switch-based color maps with DB lookup |
| `client/src/hooks/useParties.ts` | New: useParties hook |
| `client/src/contexts/PartyContext.tsx` | New: PartyProvider + helpers |
| `client/src/components/LandingTradesTable.tsx` | Dynamic filter options + inline styles |
| `client/src/components/PoliticiansView.tsx` | Dynamic filter options + inline styles |
| `client/src/components/TopTraders.tsx` | Use party context |
| `client/src/components/TradeCard.tsx` | Use party context |
| `client/src/components/GlobalSearch.tsx` | Use party context |
| `client/src/components/RecentTrades.tsx` | Use party context |
| `client/src/components/TradesView.tsx` | Use party context |
| `client/src/components/detail-modals/*.tsx` | Use party context (4 files) |
| `client/src/components/admin/AdminAnalytics.tsx` | Use party context |
| `client/src/components/admin/AdminContentManagement.tsx` | Use party context |
| `client/src/components/detail-modals/PoliticianProfileModal.tsx` | Bio fix + party context |
