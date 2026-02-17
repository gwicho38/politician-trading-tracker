# UK Parliament ETL Service Design

**Date:** 2026-02-17
**Status:** Approved
**Author:** Claude Code

## Overview

Add a UK Parliament ETL service that fetches MP financial interests from the official Register of Interests API (`interests-api.parliament.uk`) and loads them into `trading_disclosures` via the `BaseETLService` pattern with per-MP incremental upload.

## Data Source

- **Members API:** `https://members-api.parliament.uk/api/v1/Members/Search`
- **Interests API:** `https://interests-api.parliament.uk/api/v1/Interests`
- **Auth:** None required (public API)
- **Format:** JSON with pagination (`Skip`/`Take`, max Take=20)
- **Language:** English only

## Architecture: Members-First with Incremental Upload

```
members-api.parliament.uk
    |
    GET /api/v1/Members/Search?House=Commons&IsCurrentMember=true
        |
        For each MP (650+):
            |
            GET interests-api.parliament.uk/api/v1/Interests
                ?MemberId=X&ExpandChildInterests=true&Take=20&Skip=N
                |
                Parse all categories -> trading_disclosures rows
                Upload immediately (upsert per MP)
                Update progress: "MP 42/650: Keir Starmer (15 records)"
```

### Why Members-First

- Enables per-MP incremental upload (survives Fly.io restarts)
- Progress tracking per MP (real-time status endpoint updates)
- No memory pressure from buffering thousands of records
- Consistent with EU Parliament ETL pattern (proven in production)

## Implementation

### File: `app/services/uk_parliament_etl.py`

Subclasses `BaseETLService` with `@ETLRegistry.register`.

```python
source_id = "uk_parliament"
source_name = "UK Parliament"
```

### Key Methods

- `_fetch_mp_list()` — Paginate Members API, return `[{id, name, party, constituency}]`
- `_fetch_mp_interests(mp_id)` — Paginate Interests API for one MP, return raw interests
- `_parse_interest(interest, mp)` — Map one interest (+ children) to list of disclosure dicts
- `run()` — Override base class; iterate MPs, fetch+parse+upload per MP immediately

### Category to transaction_type Mapping

| UK Category (ID) | transaction_type |
|---|---|
| Employment and earnings (12) | `"income"` |
| Ad hoc payments (1) | `"income"` |
| Ongoing paid employment (2) | `"income"` |
| Shareholdings (8) | `"holding"` |
| Land and property (7) | `"holding"` |
| Donations and support (3) | `"gift"` |
| Gifts/hospitality UK (4) | `"gift"` |
| Gifts/benefits foreign (6) | `"gift"` |
| Overseas visits (5) | `"gift"` |
| Miscellaneous (9) | `"other"` |
| Family employed (10) | `"other"` |
| Family lobbying (11) | `"other"` |

### Field Mapping

| UK API Field | DB Field | Notes |
|---|---|---|
| `member.nameDisplayAs` | `full_name` | Split into first/last |
| `member.id` | `bioguide_id` | Stable MP identifier |
| `member.party` | `party` | Direct mapping |
| `member.memberFrom` | `district` | Constituency |
| `"United Kingdom"` | `state_or_country` | Constant |
| `summary` | `asset_name` | Max 200 chars |
| Category mapping | `transaction_type` | See table above |
| `fields[].Value` (Decimal) | `value_low` / `value_high` | GBP amounts from child interests |
| `registrationDate` | `transaction_date` | ISO date |
| `publishedDate` | `disclosure_date` | ISO date |
| Interest API URL | `source_url` | Self-link |
| Interest `id` | `doc_id` | Stored as string |
| `"uk_parliament"` | `raw_data.source` | Source identifier |

### Child Interest Handling

Parent interests (employment agreements, shareholdings) produce one row.
Each child interest (individual payment) produces a separate row:
- `asset_name` = parent's `summary` (employer/entity name)
- `value_low` / `value_high` = child's GBP `Value` field
- `transaction_date` = child's `ReceivedDate` (or parent's `registrationDate`)
- `raw_data` includes `parent_interest_id` for audit linkage

### Politician Integration

- `chamber = "uk_parliament"`
- Add `"uk_parliament": "Member of Parliament"` to `chamber_role_map` in `politician.py`
- Members API `id` stored as `bioguide_id` for reliable matching
- `state_or_country = "United Kingdom"`, `district` = constituency

## Estimated Scale

- ~650 current MPs
- ~10 categories with child interests
- Estimated 5,000-10,000+ total disclosure records
- ~1,300-3,300 API calls
- ~10-30 minutes runtime
- No rate limiting concerns

## Testing

- Mock Members API and Interests API responses with `httpx`/`respx`
- Test category mapping, child interest flattening, GBP amount extraction
- Test incremental upload flow (verify per-MP upload, not buffered)
- Test pagination handling for both APIs
- Test name splitting, field extraction edge cases
- Target: ~40-50 tests

## Integration Points

- **ETL trigger:** Automatic via `_run_registry_service()` — no route changes needed
- **Admin UI:** Will appear in source dropdown automatically via `ETLRegistry.get_all_info()`
- **Frontend:** `trading_disclosures` records with `raw_data.source = "uk_parliament"` display automatically
- **mcli:** Add `uk-trigger` command to `.mcli/workflows/etl.py`
