# LLM Prompt Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 4 LLM-powered services to the ETL pipeline — validation gate, anomaly detection, lineage audit, and feedback loop — using the self-hosted Ollama instance.

**Architecture:** Modular service-per-prompt in `python-etl-service/app/services/llm/`, with a shared `LLMClient` wrapper around Ollama's `/api/generate` endpoint. Prompt templates stored as `.txt` files. FastAPI routes expose endpoints, Elixir scheduler triggers them on cron.

**Tech Stack:** Python 3.11, FastAPI, httpx (async), Supabase (PostgreSQL), Ollama (qwen3:8b, gemma3:12b-it-qat, deepseek-r1:7b), Elixir/Phoenix Quantum scheduler

**Design Doc:** `docs/plans/2026-02-20-llm-prompt-pipeline-design.md`

**Prompt Spec:** `prompts-etl-trading-system.md` (root of repo)

---

## Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/20260220100000_llm_prompt_pipeline.sql`

**Step 1: Write the migration**

```sql
-- LLM Prompt Pipeline Tables
-- Supports: validation gate, anomaly detection, lineage audit, feedback loop

-- 1. Audit trail for all LLM calls
CREATE TABLE IF NOT EXISTS llm_audit_trail (
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

CREATE INDEX IF NOT EXISTS idx_llm_audit_service ON llm_audit_trail(service_name);
CREATE INDEX IF NOT EXISTS idx_llm_audit_created ON llm_audit_trail(created_at);

-- 2. Anomaly signals from Prompt 2
CREATE TABLE IF NOT EXISTS llm_anomaly_signals (
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

CREATE INDEX IF NOT EXISTS idx_anomaly_signals_filer ON llm_anomaly_signals(filer);
CREATE INDEX IF NOT EXISTS idx_anomaly_signals_created ON llm_anomaly_signals(created_at);
CREATE INDEX IF NOT EXISTS idx_anomaly_signals_severity ON llm_anomaly_signals(severity);

-- 3. Prompt improvement recommendations from Prompt 4
CREATE TABLE IF NOT EXISTS llm_prompt_recommendations (
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

-- 4. Add LLM validation columns to trading_disclosures
ALTER TABLE trading_disclosures
  ADD COLUMN IF NOT EXISTS llm_validation_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS llm_validated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_disclosures_llm_status
  ON trading_disclosures(llm_validation_status);

-- 5. Enable RLS on new tables
ALTER TABLE llm_audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_anomaly_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_prompt_recommendations ENABLE ROW LEVEL SECURITY;

-- Service role full access policies
CREATE POLICY "Service role full access on llm_audit_trail"
  ON llm_audit_trail FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on llm_anomaly_signals"
  ON llm_anomaly_signals FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on llm_prompt_recommendations"
  ON llm_prompt_recommendations FOR ALL
  USING (auth.role() = 'service_role');

-- Anon read access for dashboard
CREATE POLICY "Anon read llm_anomaly_signals"
  ON llm_anomaly_signals FOR SELECT
  USING (true);

CREATE POLICY "Anon read llm_prompt_recommendations"
  ON llm_prompt_recommendations FOR SELECT
  USING (true);
```

**Step 2: Push migration to remote Supabase**

Run: `cd /Users/home/repos/politician-trading-tracker && npx supabase db push --linked`

Expected: Migration applied successfully.

**Step 3: Commit**

```bash
git add supabase/migrations/20260220100000_llm_prompt_pipeline.sql
git commit -m "feat: add LLM prompt pipeline database tables"
```

---

## Task 2: Shared Infrastructure — LLMClient and AuditLogger

**Files:**
- Create: `python-etl-service/app/services/llm/__init__.py`
- Create: `python-etl-service/app/services/llm/client.py`
- Create: `python-etl-service/app/services/llm/audit_logger.py`
- Test: `python-etl-service/tests/test_llm_client.py`

**Step 1: Write the failing tests**

Create `python-etl-service/tests/test_llm_client.py` with tests for:
- `LLMClient.generate()` sends correct request to Ollama `/api/generate`
- `LLMClient.generate()` retries on failure (3 attempts with backoff)
- `LLMClient.generate()` returns parsed JSON when `format="json"`
- `LLMClient.generate()` raises on non-200 after retries exhausted
- `LLMClient.test_connection()` returns True on 200
- `LLMAuditLogger.log()` inserts row into `llm_audit_trail` table
- `LLMAuditLogger.log()` computes prompt hash correctly

Mock `httpx.AsyncClient` and Supabase client. Follow the pattern from `tests/test_feature_pipeline.py` for mocking.

**Step 2: Run tests to verify they fail**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_llm_client.py -v`

Expected: FAIL (modules don't exist yet)

**Step 3: Create `__init__.py`**

Create `python-etl-service/app/services/llm/__init__.py`:
```python
"""LLM prompt pipeline services using self-hosted Ollama."""
```

**Step 4: Implement LLMClient**

Create `python-etl-service/app/services/llm/client.py`. Pattern from `error_report_processor.py`:
- Uses `httpx.AsyncClient` (not sync like ErrorReportProcessor — all new services are async)
- `OLLAMA_BASE_URL` and `OLLAMA_API_KEY` from env (same vars as existing services)
- `generate(prompt, model, system_prompt=None, temperature=0.1, max_tokens=4096)` method
- Retries 3 times with `[2, 4, 8]` second delays
- `format: "json"` for structured output
- `test_connection()` hits `/api/tags`
- Returns `LLMResponse` dataclass with `text`, `model`, `input_tokens`, `output_tokens`, `latency_ms`

**Step 5: Implement LLMAuditLogger**

Create `python-etl-service/app/services/llm/audit_logger.py`:
- `log(service_name, prompt_version, prompt_hash, model_used, response, request_context, parsed_output)` method
- Writes to `llm_audit_trail` table via Supabase client
- `compute_prompt_hash(template_text)` — SHA-256 of the template file contents
- Non-blocking (fire-and-forget logging, don't fail the main operation if logging fails)

**Step 6: Run tests to verify they pass**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_llm_client.py -v`

Expected: ALL PASS

**Step 7: Commit**

```bash
git add python-etl-service/app/services/llm/ python-etl-service/tests/test_llm_client.py
git commit -m "feat: add LLMClient and AuditLogger for Ollama integration"
```

---

## Task 3: Prompt Templates

**Files:**
- Create: `python-etl-service/app/prompts/validation_gate.txt`
- Create: `python-etl-service/app/prompts/anomaly_detection.txt`
- Create: `python-etl-service/app/prompts/lineage_audit.txt`
- Create: `python-etl-service/app/prompts/feedback_loop.txt`

**Step 1: Create the prompts directory and templates**

Copy the 4 prompts verbatim from `prompts-etl-trading-system.md` into separate `.txt` files. Each template uses `{{ variable_name }}` placeholder syntax (matching the spec doc). Add a version header comment to each:

```
# Version: 1.0.0
# Service: validation_gate
```

**Key template variables per prompt:**
- `validation_gate.txt`: `{{ batch_json }}`
- `anomaly_detection.txt`: `{{ start_date }}`, `{{ end_date }}`, `{{ filer_names_or_ALL }}`, `{{ calendar_events_json }}`, `{{ trading_records_json }}`, `{{ baseline_stats_json }}`
- `lineage_audit.txt`: `{{ record_json }}`, `{{ source_url }}`, `{{ source_hash }}`, `{{ method }}`, `{{ extraction_ts }}`, `{{ transform_chain_json }}`, `{{ current_hash }}`
- `feedback_loop.txt`: `{{ start_date }}`, `{{ end_date }}`, `{{ signals_with_outcomes_json }}`, `{{ validation_version }}`, `{{ anomaly_version }}`, `{{ thresholds_json }}`

**Step 2: Write template rendering tests**

Add to `tests/test_llm_client.py` (or a new `tests/test_prompt_templates.py`):
- Test that each template file exists and can be loaded
- Test that `{{ batch_json }}` substitution works correctly
- Test that the rendered prompt doesn't contain unresolved `{{ }}` placeholders

**Step 3: Run tests**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_prompt_templates.py -v`

Expected: ALL PASS

**Step 4: Commit**

```bash
git add python-etl-service/app/prompts/ python-etl-service/tests/test_prompt_templates.py
git commit -m "feat: add LLM prompt templates for 4 pipeline stages"
```

---

## Task 4: ValidationGateService (Prompt 1)

**Files:**
- Create: `python-etl-service/app/services/llm/validation_gate.py`
- Test: `python-etl-service/tests/test_validation_gate.py`

**Step 1: Write the failing tests**

Create `python-etl-service/tests/test_validation_gate.py`:

Test cases:
1. `test_fetch_pending_records` — queries `trading_disclosures` where `llm_validation_status='pending'`, limited to last 2 hours
2. `test_batch_records` — splits 60 records into 3 batches of 25, 25, 10
3. `test_render_prompt` — fills `{{ batch_json }}` with serialized records
4. `test_process_pass_result` — updates `llm_validation_status='pass'` and `llm_validated_at`
5. `test_process_flag_result` — writes to `data_quality_issues` with severity=warning, updates status='flag'
6. `test_process_reject_result` — writes to `data_quality_quarantine`, updates status='reject'
7. `test_parse_llm_response` — parses the structured JSON output format from spec
8. `test_invalid_llm_json` — handles malformed LLM responses gracefully (logs, skips batch)
9. `test_validate_batch_end_to_end` — full flow with mocked Ollama returning mixed pass/flag/reject

Mock: `LLMClient.generate()`, Supabase client. Use `unittest.mock.patch` and `AsyncMock`.

**Step 2: Run tests to verify they fail**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_validation_gate.py -v`

Expected: FAIL

**Step 3: Implement ValidationGateService**

Create `python-etl-service/app/services/llm/validation_gate.py`:

```python
class ValidationGateService:
    """Post-ingestion semantic validation of trading disclosure records."""

    MODEL = os.getenv("LLM_VALIDATION_MODEL", "qwen3:8b")
    BATCH_SIZE = 25
    LOOKBACK_HOURS = 2

    def __init__(self, llm_client: LLMClient, supabase: Client):
        ...

    async def validate_recent(self) -> dict:
        """Main entry point: fetch pending records, batch, validate, update."""
        ...

    async def _fetch_pending(self) -> list[dict]:
        """Query trading_disclosures where llm_validation_status='pending'."""
        ...

    def _batch_records(self, records: list[dict]) -> list[list[dict]]:
        """Split into batches of BATCH_SIZE."""
        ...

    async def _validate_batch(self, batch: list[dict], batch_index: int) -> dict:
        """Send one batch to Ollama, parse response, return structured result."""
        ...

    async def _apply_results(self, results: dict) -> dict:
        """Update DB: pass/flag/reject for each record."""
        ...
```

The prompt template is loaded from `app/prompts/validation_gate.txt` at import time (like `ErrorReportProcessor` builds prompts inline, but we load from file for versioning).

**Step 4: Run tests to verify they pass**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_validation_gate.py -v`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/llm/validation_gate.py python-etl-service/tests/test_validation_gate.py
git commit -m "feat: add ValidationGateService (Prompt 1) for LLM batch validation"
```

---

## Task 5: AnomalyDetectionService (Prompt 2)

**Files:**
- Create: `python-etl-service/app/services/llm/anomaly_detector.py`
- Test: `python-etl-service/tests/test_anomaly_detector.py`

**Step 1: Write the failing tests**

Test cases:
1. `test_fetch_trading_window` — queries 30-day and 90-day windows per filer
2. `test_compute_baseline_stats` — computes avg_trades_per_month, typical_sectors, avg_amount_range_index from prior 12 months
3. `test_render_prompt_with_context` — fills all template variables including calendar events
4. `test_parse_anomaly_signals` — parses the structured JSON output matching spec format
5. `test_store_anomaly_signals` — inserts into `llm_anomaly_signals` table
6. `test_high_confidence_to_trading_signals` — signals with confidence >= 7 also written to `trading_signals`
7. `test_no_anomalies_detected` — handles clean data gracefully (empty signals array)
8. `test_self_verification_filtering` — respects the self-verification step (signals removed in Phase 4)

**Step 2: Run tests to verify they fail**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_anomaly_detector.py -v`

Expected: FAIL

**Step 3: Implement AnomalyDetectionService**

Create `python-etl-service/app/services/llm/anomaly_detector.py`:

```python
class AnomalyDetectionService:
    """Detect anomalous trading patterns using rolling time windows."""

    MODEL = os.getenv("LLM_ANOMALY_MODEL", "gemma3:12b-it-qat")

    def __init__(self, llm_client: LLMClient, supabase: Client):
        ...

    async def detect(self, start_date: str, end_date: str, filer: str = "ALL") -> dict:
        """Main entry: fetch window, compute baselines, detect anomalies."""
        ...

    async def _fetch_trading_window(self, start: str, end: str, filer: str) -> list[dict]:
        ...

    async def _compute_baseline_stats(self, filer: str) -> dict:
        ...

    async def _fetch_calendar_events(self, start: str, end: str) -> list[dict]:
        ...

    async def _store_signals(self, signals: list[dict], audit_id: str) -> int:
        ...
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_anomaly_detector.py -v`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/llm/anomaly_detector.py python-etl-service/tests/test_anomaly_detector.py
git commit -m "feat: add AnomalyDetectionService (Prompt 2) for trading pattern analysis"
```

---

## Task 6: LineageAuditService (Prompt 3)

**Files:**
- Create: `python-etl-service/app/services/llm/lineage_auditor.py`
- Test: `python-etl-service/tests/test_lineage_auditor.py`

**Step 1: Write the failing tests**

Test cases:
1. `test_fetch_record_metadata` — fetches disclosure + source_url + extraction metadata
2. `test_compute_hash_chain` — SHA-256 chain from source to current state
3. `test_render_audit_prompt` — fills all template variables
4. `test_parse_provenance_report` — parses structured JSON with trust_score and chain_integrity
5. `test_verification_questions_generated` — response includes 3-5 verification questions
6. `test_chain_integrity_valid` — hash chain matches, temporal ordering valid
7. `test_chain_integrity_broken` — detects gaps in transform chain

**Step 2: Run tests to verify they fail**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_lineage_auditor.py -v`

Expected: FAIL

**Step 3: Implement LineageAuditService**

Create `python-etl-service/app/services/llm/lineage_auditor.py`:

```python
class LineageAuditService:
    """Full provenance chain verification for questioned records."""

    MODEL = os.getenv("LLM_AUDIT_MODEL", "deepseek-r1:7b")

    def __init__(self, llm_client: LLMClient, supabase: Client):
        ...

    async def audit(self, disclosure_id: str) -> dict:
        """Audit a single record's provenance chain."""
        ...

    async def _fetch_record_and_metadata(self, disclosure_id: str) -> dict:
        ...

    def _compute_hash_chain(self, record: dict) -> list[dict]:
        ...

    def _render_prompt(self, record: dict, metadata: dict) -> str:
        ...
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_lineage_auditor.py -v`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/llm/lineage_auditor.py python-etl-service/tests/test_lineage_auditor.py
git commit -m "feat: add LineageAuditService (Prompt 3) for data provenance verification"
```

---

## Task 7: FeedbackLoopService (Prompt 4)

**Files:**
- Create: `python-etl-service/app/services/llm/feedback_loop.py`
- Test: `python-etl-service/tests/test_feedback_loop.py`

**Step 1: Write the failing tests**

Test cases:
1. `test_fetch_signals_with_outcomes` — joins `trading_signals` with `positions` to get return data
2. `test_compute_scorecard` — calculates hit_rate, alpha_rate, false_positive_rate, avg_confidence
3. `test_render_feedback_prompt` — fills template with signals and current prompt versions
4. `test_parse_recommendations` — parses structured JSON with prompt_recommendations and threshold_adjustments
5. `test_store_recommendations` — inserts into `llm_prompt_recommendations` with status='pending'
6. `test_empty_signals_window` — handles periods with no signals gracefully
7. `test_no_outcomes_yet` — handles signals that don't have position outcomes yet

**Step 2: Run tests to verify they fail**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_feedback_loop.py -v`

Expected: FAIL

**Step 3: Implement FeedbackLoopService**

Create `python-etl-service/app/services/llm/feedback_loop.py`:

```python
class FeedbackLoopService:
    """Evaluate signal quality and recommend prompt/threshold improvements."""

    MODEL = os.getenv("LLM_FEEDBACK_MODEL", "gemma3:12b-it-qat")

    def __init__(self, llm_client: LLMClient, supabase: Client):
        ...

    async def analyze(self, start_date: str, end_date: str) -> dict:
        """Main entry: fetch outcomes, compute scorecard, get LLM recommendations."""
        ...

    async def _fetch_signals_with_outcomes(self, start: str, end: str) -> list[dict]:
        ...

    def _compute_scorecard(self, signals: list[dict]) -> dict:
        ...

    async def _store_recommendations(self, result: dict, audit_id: str) -> str:
        ...
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_feedback_loop.py -v`

Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/llm/feedback_loop.py python-etl-service/tests/test_feedback_loop.py
git commit -m "feat: add FeedbackLoopService (Prompt 4) for self-learning signal quality"
```

---

## Task 8: FastAPI Routes

**Files:**
- Create: `python-etl-service/app/routes/llm_pipeline.py`
- Modify: `python-etl-service/app/main.py` (add router registration)
- Test: `python-etl-service/tests/test_llm_routes.py`

**Step 1: Write the failing tests**

Test cases (using `fastapi.testclient.TestClient`):
1. `test_validate_batch_endpoint` — POST `/llm/validate-batch` returns 200 with summary
2. `test_detect_anomalies_endpoint` — POST `/llm/detect-anomalies` with date window
3. `test_audit_lineage_endpoint` — POST `/llm/audit-lineage` with disclosure_id
4. `test_run_feedback_endpoint` — POST `/llm/run-feedback` with date window
5. `test_audit_trail_endpoint` — GET `/llm/audit-trail` returns paginated results
6. `test_health_endpoint` — GET `/llm/health` returns Ollama connection status
7. `test_auth_required` — endpoints return 401 without API key

**Step 2: Run tests to verify they fail**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_llm_routes.py -v`

Expected: FAIL

**Step 3: Implement routes**

Create `python-etl-service/app/routes/llm_pipeline.py`:

Follow the exact pattern from `app/routes/error_reports.py`:
- Pydantic request/response models
- Router with `APIRouter()`
- Background task execution for long-running operations (validation, anomaly detection)
- Each endpoint creates the service instance, calls the method, returns result

Endpoints:
```python
router = APIRouter()

@router.post("/validate-batch")
async def validate_batch(request: ValidateBatchRequest, background_tasks: BackgroundTasks): ...

@router.post("/detect-anomalies")
async def detect_anomalies(request: DetectAnomaliesRequest, background_tasks: BackgroundTasks): ...

@router.post("/audit-lineage")
async def audit_lineage(request: AuditLineageRequest): ...

@router.post("/run-feedback")
async def run_feedback(request: RunFeedbackRequest, background_tasks: BackgroundTasks): ...

@router.get("/audit-trail")
async def get_audit_trail(service_name: Optional[str] = None, limit: int = 50): ...

@router.get("/health")
async def llm_health(): ...
```

**Step 4: Register router in main.py**

Add to `python-etl-service/app/main.py`:
```python
from app.routes import llm_pipeline
# In OPENAPI_TAGS list:
{"name": "llm", "description": "LLM prompt pipeline for validation, anomaly detection, lineage audit, and feedback."}
# In router registration:
app.include_router(llm_pipeline.router, prefix="/llm", tags=["llm"])
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_llm_routes.py -v`

Expected: ALL PASS

**Step 6: Commit**

```bash
git add python-etl-service/app/routes/llm_pipeline.py python-etl-service/app/main.py python-etl-service/tests/test_llm_routes.py
git commit -m "feat: add FastAPI routes for LLM prompt pipeline"
```

---

## Task 9: Elixir Scheduler Jobs

**Files:**
- Create: `server/lib/server/scheduler/jobs/llm_validation_job.ex`
- Create: `server/lib/server/scheduler/jobs/llm_anomaly_detection_job.ex`
- Create: `server/lib/server/scheduler/jobs/llm_feedback_job.ex`
- Modify: `server/lib/server/application.ex` (register new jobs)

**Step 1: Create LLMValidationJob**

Create `server/lib/server/scheduler/jobs/llm_validation_job.ex`. Follow the exact pattern from `error_reports_job.ex`:

```elixir
defmodule Server.Scheduler.Jobs.LLMValidationJob do
  @moduledoc """
  Hourly LLM validation of recently-ingested trading disclosures.
  Calls the Python ETL service POST /llm/validate-batch endpoint.
  """

  @behaviour Server.Scheduler.Job
  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "llm-validation"

  @impl true
  def job_name, do: "LLM Validation Gate"

  @impl true
  def schedule, do: "30 * * * *"

  @impl true
  def run do
    Logger.info("[LLMValidationJob] Starting LLM validation scan")

    url = "#{@etl_service_url}/llm/validate-batch"
    body = Jason.encode!(%{})

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ],
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 300_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"total_records" => total, "passed" => passed, "flagged" => flagged}} ->
            Logger.info("[LLMValidationJob] Validated #{total}: #{passed} passed, #{flagged} flagged")
            {:ok, total}

          {:ok, response} ->
            Logger.info("[LLMValidationJob] Response: #{inspect(response)}")
            {:ok, 0}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        Logger.error("[LLMValidationJob] HTTP #{status}: #{response_body}")
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @impl true
  def metadata do
    %{
      description: "LLM-powered semantic validation of trading disclosures",
      etl_service: @etl_service_url,
      model: "qwen3:8b"
    }
  end
end
```

**Step 2: Create LLMAnomalyDetectionJob**

Same pattern, but:
- `job_id: "llm-anomaly-detection"`
- `schedule: "0 1 * * *"` (daily 01:00 UTC)
- POST to `/llm/detect-anomalies` with `%{days_back: 30}`
- `receive_timeout: 600_000` (10 min, larger context)

**Step 3: Create LLMFeedbackJob**

Same pattern, but:
- `job_id: "llm-feedback"`
- `schedule: "0 2 * * 0"` (weekly Sunday 02:00 UTC)
- POST to `/llm/run-feedback` with `%{days_back: 7}`
- `receive_timeout: 600_000`

**Step 4: Register in application.ex**

Add to the `static_jobs` list in `server/lib/server/application.ex` (around line 132, after data quality jobs):

```elixir
# LLM prompt pipeline jobs
Server.Scheduler.Jobs.LLMValidationJob,
Server.Scheduler.Jobs.LLMAnomalyDetectionJob,
Server.Scheduler.Jobs.LLMFeedbackJob,
```

**Step 5: Commit**

```bash
git add server/lib/server/scheduler/jobs/llm_validation_job.ex \
        server/lib/server/scheduler/jobs/llm_anomaly_detection_job.ex \
        server/lib/server/scheduler/jobs/llm_feedback_job.ex \
        server/lib/server/application.ex
git commit -m "feat: add Elixir scheduler jobs for LLM pipeline (hourly/daily/weekly)"
```

---

## Task 10: Run Full Test Suite and Integration Verify

**Step 1: Run all Python tests**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest tests/test_llm_client.py tests/test_prompt_templates.py tests/test_validation_gate.py tests/test_anomaly_detector.py tests/test_lineage_auditor.py tests/test_feedback_loop.py tests/test_llm_routes.py -v`

Expected: ALL PASS

**Step 2: Run existing tests to verify no regressions**

Run: `cd /Users/home/repos/politician-trading-tracker/python-etl-service && uv run pytest --timeout=60 -x -q`

Expected: All existing tests still pass.

**Step 3: Verify Elixir compiles**

Run: `cd /Users/home/repos/politician-trading-tracker/server && mix compile --warnings-as-errors`

Expected: Compiles without errors.

**Step 4: Smoke test Ollama connection**

Run: `curl -s -H "Authorization: Bearer $OLLAMA_API_KEY" https://ollama.lefv.info/api/tags | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))"`

Expected: JSON listing available models.

**Step 5: Final commit and push**

```bash
git push origin HEAD
```

---

## Summary of Deliverables

| # | Component | Files Created | Tests |
|---|-----------|--------------|-------|
| 1 | Database migration | 1 SQL file | — |
| 2 | LLMClient + AuditLogger | 3 Python files | ~10 tests |
| 3 | Prompt templates | 4 .txt files | ~6 tests |
| 4 | ValidationGateService | 1 Python file | ~9 tests |
| 5 | AnomalyDetectionService | 1 Python file | ~8 tests |
| 6 | LineageAuditService | 1 Python file | ~7 tests |
| 7 | FeedbackLoopService | 1 Python file | ~7 tests |
| 8 | FastAPI routes + main.py | 2 Python files | ~7 tests |
| 9 | Elixir scheduler jobs | 3 .ex files + 1 modified | — |
| 10 | Integration verification | — | Full suite run |

**Total: ~15 new files, ~54 new tests, 1 migration**
