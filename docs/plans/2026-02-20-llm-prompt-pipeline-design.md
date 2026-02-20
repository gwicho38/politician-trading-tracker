# LLM Prompt Pipeline for Government Trading Data

## Date: 2026-02-20
## Status: Approved

---

## Overview

Integrate a 4-prompt LLM system into the ETL pipeline for data validation, anomaly detection, lineage auditing, and self-learning feedback. All prompts run on the self-hosted Ollama instance (`ollama.lefv.info`) using the existing `httpx` integration pattern established by `ErrorReportProcessor`.

**Architecture**: Modular service-per-prompt with shared infrastructure in the Python ETL service. Post-ingestion batch scanning (not inline blocking). Elixir scheduler triggers via HTTP.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | Self-hosted Ollama | No API costs, existing infrastructure and auth pattern |
| Orchestration Layer | Python ETL service | Consolidates all LLM logic, follows existing patterns |
| Validation Mode | Post-ingestion batch scan | Non-blocking, works for all 6 ETL sources including House/Senate |
| Architecture | Modular service-per-prompt | Clean separation, independently testable, versionable prompts |

---

## Available Models (on `ollama.lefv.info`)

| Model | Size | Assignment |
|-------|------|------------|
| `qwen3:8b` | 8.2B | Prompt 1 (Validation Gate) — fast, good JSON output |
| `gemma3:12b-it-qat` | 12.2B | Prompt 2 (Anomaly Detection) — strongest reasoning |
| `deepseek-r1:7b` | 7.6B | Prompt 3 (Lineage Audit) — native chain-of-thought |
| `gemma3:12b-it-qat` | 12.2B | Prompt 4 (Feedback Loop) — analytical reasoning |

All models configurable via env vars. Defaults chosen to balance speed vs reasoning quality.

---

## File Structure

```
python-etl-service/app/
├── services/llm/
│   ├── __init__.py
│   ├── client.py              # LLMClient wrapper (Ollama httpx, retries, audit)
│   ├── audit_logger.py        # LLMAuditLogger (writes to llm_audit_trail table)
│   ├── validation_gate.py     # Prompt 1: ValidationGateService
│   ├── anomaly_detector.py    # Prompt 2: AnomalyDetectionService
│   ├── lineage_auditor.py     # Prompt 3: LineageAuditService
│   └── feedback_loop.py       # Prompt 4: FeedbackLoopService
├── prompts/
│   ├── validation_gate.txt    # Prompt 1 template
│   ├── anomaly_detection.txt  # Prompt 2 template
│   ├── lineage_audit.txt      # Prompt 3 template
│   └── feedback_loop.txt      # Prompt 4 template
├── routes/
│   └── llm_pipeline.py        # New FastAPI router for all endpoints
```

---

## Shared Infrastructure

### LLMClient (`services/llm/client.py`)

Thin wrapper around `httpx.AsyncClient` calling Ollama's `/api/generate` endpoint. Follows the exact pattern from `ErrorReportProcessor` and `BiographyGenerator`.

- **Model selection per call**: configurable via env vars per service
- **Retry logic**: 3 attempts with exponential backoff
- **Structured output**: `format: "json"` parameter for all calls
- **Auto-logging**: every call logged via `LLMAuditLogger`
- **Connection test**: health check method

Environment variables:
```
OLLAMA_BASE_URL=https://ollama.lefv.info     # existing
OLLAMA_API_KEY=...                            # existing
LLM_VALIDATION_MODEL=qwen3:8b
LLM_ANOMALY_MODEL=gemma3:12b-it-qat
LLM_AUDIT_MODEL=deepseek-r1:7b
LLM_FEEDBACK_MODEL=gemma3:12b-it-qat
```

### LLMAuditLogger (`services/llm/audit_logger.py`)

Writes every LLM call to `llm_audit_trail` table:
- `prompt_version_hash` (SHA-256 of the template file)
- `resolved_prompt` (template with variables filled in)
- `raw_response` (full LLM output)
- `parsed_output` (validated JSON)
- `model_used`, `latency_ms`, `input_tokens`, `output_tokens`

---

## Database Changes

### New Table: `llm_audit_trail`

```sql
CREATE TABLE llm_audit_trail (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  service_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  model_used TEXT NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  request_context JSONB,
  raw_response TEXT,
  parsed_output JSONB,
  parse_success BOOLEAN DEFAULT true,
  error_message TEXT
);

CREATE INDEX idx_llm_audit_service ON llm_audit_trail(service_name);
CREATE INDEX idx_llm_audit_created ON llm_audit_trail(created_at);
```

### New Table: `llm_anomaly_signals`

```sql
CREATE TABLE llm_anomaly_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  signal_id TEXT UNIQUE NOT NULL,
  filer TEXT NOT NULL,
  classification TEXT NOT NULL,
  severity TEXT NOT NULL,
  confidence INTEGER NOT NULL,
  trades_involved JSONB NOT NULL,
  legislative_context JSONB,
  statistical_evidence JSONB,
  reasoning TEXT,
  trading_signal JSONB,
  self_verification_notes TEXT,
  analysis_window_start DATE,
  analysis_window_end DATE,
  audit_trail_id UUID REFERENCES llm_audit_trail(id)
);

CREATE INDEX idx_anomaly_signals_filer ON llm_anomaly_signals(filer);
CREATE INDEX idx_anomaly_signals_created ON llm_anomaly_signals(created_at);
CREATE INDEX idx_anomaly_signals_severity ON llm_anomaly_signals(severity);
```

### New Table: `llm_prompt_recommendations`

```sql
CREATE TABLE llm_prompt_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  feedback_id TEXT UNIQUE NOT NULL,
  analysis_period_start DATE,
  analysis_period_end DATE,
  scorecard JSONB NOT NULL,
  failure_patterns JSONB,
  prompt_recommendations JSONB,
  threshold_adjustments JSONB,
  data_quality_feedback JSONB,
  meta_confidence INTEGER,
  status TEXT DEFAULT 'pending',
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  audit_trail_id UUID REFERENCES llm_audit_trail(id)
);
```

### Column Addition: `trading_disclosures`

```sql
ALTER TABLE trading_disclosures
  ADD COLUMN IF NOT EXISTS llm_validation_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS llm_validated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_disclosures_llm_status
  ON trading_disclosures(llm_validation_status);
```

### Reused Tables (no changes needed)

- `data_quality_issues` — LLM validation flags written with `source = 'llm_validation'`
- `data_quality_quarantine` — records flagged for human review
- `data_quality_corrections` — correction audit trail

---

## Service Details

### Prompt 1 — ValidationGateService

**Purpose**: Post-ingestion semantic validation of trading disclosure records.
**Trigger**: Elixir `LLMValidationJob` (hourly at :30)
**Model**: `qwen3:8b`

**Flow**:
1. Query `trading_disclosures` where `llm_validation_status = 'pending'` (last 2 hours)
2. Batch records (25 per batch)
3. Render `validation_gate.txt` template with batch JSON
4. Send to Ollama
5. Parse structured JSON response
6. `pass` records: set `llm_validation_status = 'pass'`, `llm_validated_at = now()`
7. `flag` records: write to `data_quality_issues` (severity=warning), set status='flag'
8. `reject` records: write to `data_quality_quarantine`, set status='reject'

### Prompt 2 — AnomalyDetectionService

**Purpose**: Detect anomalous trading patterns using rolling time windows.
**Trigger**: Elixir `LLMAnomalyDetectionJob` (daily at 01:00 UTC)
**Model**: `gemma3:12b-it-qat`

**Flow**:
1. Pull 30-day and 90-day windows of `trading_disclosures` per filer
2. Compute baseline statistics from prior 12 months per filer
3. Gather legislative calendar context (from existing committee data)
4. Render `anomaly_detection.txt` template
5. Send to Ollama
6. Parse anomaly signals
7. Write to `llm_anomaly_signals` table
8. High-confidence signals (confidence >= 7) also written to `trading_signals`

### Prompt 3 — LineageAuditService

**Purpose**: Full provenance chain verification for questioned records.
**Trigger**: On-demand via API endpoint
**Model**: `deepseek-r1:7b`

**Flow**:
1. Accept a `trading_disclosure_id`
2. Gather pipeline metadata: source URL, extraction method, transform chain
3. Compute hash chain from source to current state
4. Render `lineage_audit.txt` template
5. Send to Ollama
6. Return provenance report with trust score

### Prompt 4 — FeedbackLoopService

**Purpose**: Evaluate signal quality and recommend prompt/threshold improvements.
**Trigger**: Elixir `LLMFeedbackJob` (weekly, Sunday 02:00 UTC)
**Model**: `gemma3:12b-it-qat`

**Flow**:
1. Query `trading_signals` with position outcomes from `positions` table
2. Compute signal scorecard (hit rate, alpha rate, false positive rate)
3. Identify failure patterns
4. Render `feedback_loop.txt` template
5. Send to Ollama
6. Write recommendations to `llm_prompt_recommendations` (status='pending')
7. Human review required before prompt changes are applied

---

## API Endpoints

New router at `/llm/`:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/llm/validate-batch` | Trigger Prompt 1 on recent records |
| POST | `/llm/detect-anomalies` | Trigger Prompt 2 on a date window |
| POST | `/llm/audit-lineage` | Trigger Prompt 3 for a specific record |
| POST | `/llm/run-feedback` | Trigger Prompt 4 for a date window |
| GET | `/llm/audit-trail` | Query the LLM audit trail |

All endpoints authenticated via existing API key middleware.

---

## Scheduling (Elixir)

Three new Quantum jobs in `server/lib/server/scheduler/jobs/`:

| Job | Cron | Target |
|-----|------|--------|
| `LLMValidationJob` | `30 * * * *` | POST `{ETL_URL}/llm/validate-batch` |
| `LLMAnomalyDetectionJob` | `0 1 * * *` | POST `{ETL_URL}/llm/detect-anomalies` |
| `LLMFeedbackJob` | `0 2 * * 0` | POST `{ETL_URL}/llm/run-feedback` |

---

## Testing Strategy

- Unit tests for each service with mocked Ollama responses
- Integration test for `LLMClient` with Ollama connection
- Prompt template rendering tests (variable substitution)
- JSON parsing tests for each prompt's expected output schema
- Follow existing patterns: `uv run pytest`

---

## Sources

Based on `prompts-etl-trading-system.md`, synthesized from DocETL (UC Berkeley), AWS Bedrock ETL patterns, and academic research on prompt engineering for financial market integrity.
