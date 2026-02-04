# QuiverQuant Validation System Design

**Date**: 2026-02-04
**Status**: Approved
**Goal**: Create a 1:1 validation cycle against QuiverQuant to ensure data accuracy and credibility

---

## Overview

A two-phase validation system that compares every trade in our database against QuiverQuant's data:

1. **Phase 1: Historical Audit** - One-time deep comparison of all trades
2. **Phase 2: Rolling Validation** - Ongoing validation of recent trades on each sync

When discrepancies are found:
- Generate detailed report
- Flag records in database with validation status
- Diagnose root cause of the mismatch

---

## Database Schema

### New Table: `trade_validation_results`

```sql
CREATE TABLE trade_validation_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trading_disclosure_id UUID REFERENCES trading_disclosures(id),
  quiver_record JSONB,                    -- Raw QuiverQuant data
  validation_status TEXT NOT NULL,        -- 'match' | 'mismatch' | 'app_only' | 'quiver_only'
  field_mismatches JSONB,                 -- {field: {app: x, quiver: y, severity: 'critical'|'warning'}}
  root_cause TEXT,                        -- Diagnosed reason for mismatch
  validated_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  resolution_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_validation_status ON trade_validation_results(validation_status);
CREATE INDEX idx_validation_root_cause ON trade_validation_results(root_cause);
CREATE INDEX idx_validation_disclosure ON trade_validation_results(trading_disclosure_id);
```

### Alter Table: `trading_disclosures`

```sql
ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS quiver_validation_status TEXT DEFAULT 'pending';

CREATE INDEX idx_quiver_validation ON trading_disclosures(quiver_validation_status);
```

---

## Field Mapping & Matching Logic

### Trade Matching Key

To find the same trade in both systems, match on:
```
(politician_bioguide_id OR normalized_name) + ticker + transaction_date + transaction_type
```

### Field-by-Field Validation

| Field | App Column | QuiverQuant Field | Match Logic | Severity |
|-------|-----------|-------------------|-------------|----------|
| Politician | `politicians.full_name` | `Representative` | Fuzzy match (90% similarity) | Critical |
| BioGuide ID | `politicians.bioguide_id` | `BioGuideID` | Exact match | Critical |
| Ticker | `asset_ticker` | `Ticker` | Exact (uppercase) | Critical |
| Transaction Date | `transaction_date` | `TransactionDate` | Exact date | Critical |
| Transaction Type | `transaction_type` | `Transaction` | Map: Purchase→buy, Sale*→sell | Critical |
| Disclosure Date | `disclosure_date` | `ReportDate` | Exact date | Warning |
| Amount Min | `amount_range_min` | Parse from `Range` | ±$1 tolerance | Warning |
| Amount Max | `amount_range_max` | Parse from `Range` | ±$1 tolerance | Warning |
| Party | `politicians.party` | `Party` | D/R/I mapping | Warning |
| Chamber | `politicians.chamber` | `House` | Representatives→house | Warning |

### Root Cause Categories

| Root Cause | Description |
|------------|-------------|
| `name_normalization` | "Hon. John Smith" vs "John Smith" |
| `date_parse_error` | Date format differences |
| `amount_parse_error` | Range string parsing issue |
| `transaction_type_mapping` | "Sale (Partial)" not mapped correctly |
| `missing_in_source` | Trade exists in one system only |
| `data_lag` | Our scraper hasn't picked up the trade yet |
| `source_correction` | QuiverQuant updated their data after we scraped |
| `ticker_mismatch` | Different ticker symbols for same asset |
| `unknown` | Could not diagnose root cause |

---

## CLI Commands

### Phase 1: Historical Audit

```bash
# Full historical audit
mcli run etl quiver audit --full

# Audit from specific date
mcli run etl quiver audit --from 2025-01-01

# Show audit progress
mcli run etl quiver audit --status
```

### Phase 2: Rolling Validation

```bash
# Validate last 500 trades (default)
mcli run etl quiver validate --recent

# Validate specific ticker
mcli run etl quiver validate --ticker NVDA

# Validate specific politician
mcli run etl quiver validate --politician "Nancy Pelosi"
```

### Reporting & Analysis

```bash
# Summary of all mismatches
mcli run etl quiver report

# Only critical mismatches
mcli run etl quiver report --critical

# Group by root cause
mcli run etl quiver report --root-cause

# Export for review
mcli run etl quiver report --export csv
```

### Resolution

```bash
# Mark specific issue as resolved
mcli run etl quiver resolve <id> --notes "Fixed name normalization"

# Batch fix known issues
mcli run etl quiver fix --root-cause name_normalization
```

---

## Output Format

```
┌─────────────────────────────────────────────────────────────┐
│ QuiverQuant Validation Report - 2026-02-04                  │
├─────────────────────────────────────────────────────────────┤
│ Total trades compared: 1,247                                │
│ ✓ Matched: 1,198 (96.1%)                                    │
│ ⚠ Mismatched: 34 (2.7%)                                     │
│ ✗ App only: 8 (0.6%)                                        │
│ ✗ Quiver only: 7 (0.6%)                                     │
├─────────────────────────────────────────────────────────────┤
│ Root Cause Breakdown:                                       │
│   name_normalization: 18                                    │
│   date_parse_error: 9                                       │
│   data_lag: 7                                               │
│   amount_parse_error: 5                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Automated Integration

- After each ETL sync, automatically run `quiver validate --recent`
- If critical mismatches > 5%, send alert
- Weekly full audit report generated automatically

---

## Implementation Steps

### Step 1: Database Migration
- Create `trade_validation_results` table
- Add `quiver_validation_status` column to `trading_disclosures`
- Create indexes for efficient querying

### Step 2: Core Validation Engine
Add to `.mcli/workflows/etl.py`:
- `_match_trade()` - Find matching trade using composite key
- `_compare_fields()` - Field-by-field comparison with severity
- `_diagnose_root_cause()` - Analyze why mismatch occurred
- `_store_validation_result()` - Write to database

### Step 3: Commands
- `quiver audit` - Historical audit with progress tracking
- `quiver validate` - Rolling validation
- `quiver report` - Reporting with filters
- `quiver resolve` - Mark issues as resolved

### Step 4: Integration
- Hook into existing ETL sync to run validation automatically

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `supabase/migrations/20260204_quiver_validation.sql` | New migration |
| `.mcli/workflows/etl.py` | Add validation commands |
| `docs/quiverquant-validation.md` | Update existing docs |

---

## Success Criteria

- Match rate > 95% for trades in overlapping date ranges
- All critical field mismatches diagnosed with root cause
- Validation runs automatically after each sync
- Clear reporting for manual review when needed
