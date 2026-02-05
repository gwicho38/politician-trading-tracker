# Admin Validation Dashboard Design

**Date**: 2026-02-05
**Status**: Approved
**Goal**: Create an admin dashboard to review, diagnose, and fix QuiverQuant validation discrepancies

---

## Overview

A web-based admin dashboard at `/admin` in the ETL service that allows administrators to:
- View validation audit results (matches, mismatches, app-only, quiver-only)
- Diagnose why parsing failed with side-by-side comparisons
- Fix data discrepancies directly in the database
- Track all fixes with an audit trail
- Create GitHub issues for systematic fixes needed in ETL code

---

## Architecture

### Tech Stack
- **Backend**: FastAPI routes under `/admin`
- **Templates**: Jinja2 for server-side HTML rendering
- **Interactivity**: HTMX for SPA-like updates without full page reloads
- **Styling**: Tailwind CSS via CDN
- **Auth**: API key verification via middleware

### File Structure
```
python-etl-service/app/
├── routes/
│   └── admin.py                    # Admin API routes
├── services/
│   └── validation_fixer.py         # Fix application logic
├── templates/
│   └── admin/
│       ├── base.html               # Layout with nav, auth check
│       ├── dashboard.html          # Main validation dashboard
│       ├── detail.html             # Single mismatch detail view
│       └── partials/
│           ├── results_table.html  # HTMX partial for results list
│           ├── summary_stats.html  # HTMX partial for stats cards
│           ├── field_row.html      # Single field comparison row
│           └── audit_form.html     # Run audit form
└── middleware/
    └── admin_auth.py               # API key verification
```

### URL Structure
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/admin` | Dashboard with validation results |
| GET | `/admin/detail/{id}` | Single mismatch detail view |
| GET | `/admin/api/results` | JSON/HTML partial of results (filterable) |
| GET | `/admin/api/stats` | Summary statistics |
| POST | `/admin/api/audit` | Trigger new audit |
| POST | `/admin/api/fix/{id}` | Apply a fix to a field |
| POST | `/admin/api/fix/{id}/accept-all` | Accept all QuiverQuant values |
| POST | `/admin/api/resolve/{id}` | Mark issue as resolved |
| POST | `/admin/api/import/{id}` | Import quiver_only trade |
| DELETE | `/admin/api/trade/{id}` | Soft delete app_only trade |

---

## Authentication

Simple API key authentication:
- Key stored in `ADMIN_API_KEY` environment variable
- Passed via query param: `/admin?key=<key>` (sets session cookie)
- Or via header: `X-Admin-Key: <key>` (for API calls)
- Invalid key returns 401 Unauthorized

---

## Dashboard UI

### Main Dashboard View
```
┌─────────────────────────────────────────────────────────────────────────┐
│ QuiverQuant Validation Admin                          [Run Audit ▼]    │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│ │  1,247   │ │  1,198   │ │    34    │ │     8    │ │     7    │      │
│ │  Total   │ │ Matches  │ │Mismatch  │ │ App Only │ │QQ Only   │      │
│ │          │ │  96.1%   │ │  2.7%    │ │   0.6%   │ │  0.6%    │      │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├─────────────────────────────────────────────────────────────────────────┤
│ Filters: [Status ▼] [Severity ▼] [Root Cause ▼] [Politician ▼] [Search]│
├─────────────────────────────────────────────────────────────────────────┤
│ Status    │ Politician      │ Ticker │ Date       │ Root Cause  │ Act  │
├───────────┼─────────────────┼────────┼────────────┼─────────────┼──────┤
│ ⚠ mismatch│ Nancy Pelosi    │ NVDA   │ 2026-01-15 │ name_norm   │ [→]  │
│ ⚠ mismatch│ Dan Crenshaw    │ AAPL   │ 2026-01-12 │ amount_err  │ [→]  │
│ ✗ app_only│ Josh Gottheimer │ MSFT   │ 2026-01-10 │ missing     │ [→]  │
│ ✗ qq_only │ Tommy Tuberville│ TSLA   │ 2026-01-08 │ data_lag    │ [→]  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detail View (Single Mismatch)
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← Back to Dashboard                                                     │
│                                                                         │
│ MISMATCH: Nancy Pelosi - NVDA - 2026-01-15                sale         │
├─────────────────────────────────────────────────────────────────────────┤
│ Field          │ App Value          │ QuiverQuant       │ Action       │
├────────────────┼────────────────────┼───────────────────┼──────────────┤
│ politician     │ "Pelosi, Nancy"    │ "Nancy Pelosi"    │ [Use QQ] [✎] │
│ amount_min     │ $1,000,000         │ $1,000,001        │ [Use QQ] [✎] │
│ amount_max     │ $5,000,000         │ $5,000,000        │ ✓ Match      │
│ tx_type        │ "sale"             │ "Sale (Full)"     │ [Use QQ] [✎] │
│ tx_date        │ 2026-01-15         │ 2026-01-15        │ ✓ Match      │
│ disclosure_date│ 2026-01-20         │ 2026-01-20        │ ✓ Match      │
├─────────────────────────────────────────────────────────────────────────┤
│ ROOT CAUSE: name_normalization                          Severity: warning│
│                                                                         │
│ 💡 SUGGESTED FIX:                                                       │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ The name "Pelosi, Nancy" uses "Last, First" format while           │ │
│ │ QuiverQuant uses "First Last".                                      │ │
│ │                                                                     │ │
│ │ → File: python-etl-service/app/lib/politician.py                   │ │
│ │ → Function: normalize_name()                                        │ │
│ │ → Add case for "Last, First" → "First Last" conversion             │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ 📋 RAW SOURCE DATA:                                                     │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ App source record:                                                  │ │
│ │ {                                                                   │ │
│ │   "filer_name": "HON. PELOSI, NANCY",                              │ │
│ │   "asset_ticker": "NVDA",                                          │ │
│ │   "transaction_date": "2026-01-15",                                │ │
│ │   ...                                                              │ │
│ │ }                                                                   │ │
│ ├─────────────────────────────────────────────────────────────────────┤ │
│ │ QuiverQuant record:                                                 │ │
│ │ {                                                                   │ │
│ │   "Representative": "Nancy Pelosi",                                │ │
│ │   "Ticker": "NVDA",                                                │ │
│ │   "TransactionDate": "2026-01-15",                                 │ │
│ │   ...                                                              │ │
│ │ }                                                                   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ [Accept All QQ Values] [Mark Resolved] [Create GitHub Issue]           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Fix Actions

| Action | Description | Database Operation |
|--------|-------------|-------------------|
| **[Use QQ]** | Copy QuiverQuant value to app field | `UPDATE trading_disclosures SET field = ? WHERE id = ?` |
| **[Accept All QQ Values]** | Overwrite all mismatched fields | Bulk update + mark resolved |
| **[✎] Manual Edit** | Inline editor for custom value | Update with user-provided value |
| **[Import Trade]** | Create new disclosure from quiver_only | `INSERT INTO trading_disclosures` |
| **[Delete Trade]** | Soft delete app_only trade | `UPDATE trading_disclosures SET deleted_at = now()` |
| **[Mark Resolved]** | Acknowledge without fixing data | `UPDATE trade_validation_results SET resolved_at = now()` |
| **[Create GitHub Issue]** | Opens GitHub with pre-filled template | No DB change |

---

## Root Cause → Suggested Fix Mapping

| Root Cause | Suggested Fix Location | Description |
|------------|----------------------|-------------|
| `name_normalization` | `app/lib/politician.py:normalize_name()` | Name format differences (Last, First vs First Last) |
| `date_parse_error` | `app/lib/parser.py:parse_date()` | Date format parsing issues |
| `amount_parse_error` | `app/lib/parser.py:parse_amount_range()` | Amount range string parsing |
| `transaction_type_mapping` | `app/services/*/etl.py` | Transaction type normalization |
| `ticker_mismatch` | `app/lib/parser.py:normalize_ticker()` | Ticker symbol differences |
| `missing_in_source` | N/A - data issue | Trade exists in one system only |
| `data_lag` | N/A - timing issue | Our scraper hasn't caught up yet |
| `source_correction` | N/A - data issue | QuiverQuant updated after we scraped |

---

## Database Schema

### New Table: validation_fix_log
```sql
CREATE TABLE validation_fix_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_result_id UUID REFERENCES trade_validation_results(id),
    trading_disclosure_id UUID REFERENCES trading_disclosures(id),
    action_type TEXT NOT NULL CHECK (action_type IN (
        'field_update', 'accept_all_qq', 'manual_edit',
        'import_trade', 'delete_trade', 'mark_resolved'
    )),
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    performed_by TEXT DEFAULT 'admin',
    performed_at TIMESTAMPTZ DEFAULT now(),
    notes TEXT
);

CREATE INDEX idx_fix_log_validation ON validation_fix_log(validation_result_id);
CREATE INDEX idx_fix_log_disclosure ON validation_fix_log(trading_disclosure_id);
CREATE INDEX idx_fix_log_date ON validation_fix_log(performed_at DESC);
```

### Alter: trading_disclosures
```sql
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_disclosure_deleted
ON trading_disclosures(deleted_at)
WHERE deleted_at IS NOT NULL;
```

---

## Re-validation Flow

After any fix action:
1. Log the fix to `validation_fix_log`
2. Re-fetch the QuiverQuant record for comparison
3. Re-run field comparison
4. Update `trade_validation_results` with new status
5. If all fields match → status = `match`
6. If still mismatched → status = `mismatch` (with updated field_mismatches)

---

## Dependencies

**Python packages to add:**
```
jinja2>=3.1.0
python-multipart>=0.0.6
```

**CDN (no install):**
- HTMX: `https://unpkg.com/htmx.org@1.9.10`
- Tailwind CSS: `https://cdn.tailwindcss.com`

---

## Environment Variables

```bash
ADMIN_API_KEY=<generate-secure-random-key>
```

Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

## Files to Create/Modify

| File | Action | Lines (est) |
|------|--------|-------------|
| `app/routes/admin.py` | Create | ~200 |
| `app/services/validation_fixer.py` | Create | ~150 |
| `app/middleware/admin_auth.py` | Create | ~30 |
| `app/templates/admin/base.html` | Create | ~60 |
| `app/templates/admin/dashboard.html` | Create | ~100 |
| `app/templates/admin/detail.html` | Create | ~150 |
| `app/templates/admin/partials/*.html` | Create | ~100 |
| `app/main.py` | Modify | +10 |
| `supabase/migrations/20260205_validation_fix_log.sql` | Create | ~40 |
| `pyproject.toml` | Modify | +2 |

**Total: ~850 lines of code**

---

## Access

**Local development:**
```
http://localhost:8000/admin?key=<ADMIN_API_KEY>
```

**Production:**
```
https://politician-etl.fly.dev/admin?key=<ADMIN_API_KEY>
```

---

## Success Criteria

1. Can view all validation results with filtering
2. Can see side-by-side field comparison for any mismatch
3. Can apply fixes (use QQ value, manual edit, import, delete)
4. All fixes logged to audit trail
5. Re-validation runs automatically after fixes
6. Can create GitHub issues with diagnostic context
7. Dashboard loads in <2 seconds

---

## Implementation Order

1. Database migration for `validation_fix_log`
2. Admin auth middleware
3. Basic dashboard route + template
4. Results list with HTMX filtering
5. Detail view with field comparison
6. Fix actions (one at a time)
7. Re-validation after fix
8. GitHub issue creation
9. Run audit from dashboard

---

*Design approved: 2026-02-05*
