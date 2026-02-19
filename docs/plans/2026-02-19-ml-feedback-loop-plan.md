# ML Feedback Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the existing ML infrastructure into a working feedback loop: trade outcomes feed back into model retraining, with champion/challenger evaluation, dynamic blend weight, tighter thresholds, and paper/live toggle.

**Architecture:** The system already has signal outcome tracking (`signal_outcomes` table), model evaluation (`signal-feedback` edge function), and three retraining triggers (weekly, threshold, monthly). The gap is that training never reads outcomes, the monthly retrain calls a non-existent edge function, and the ML blend weight is hardcoded at 20%. This plan wires those pieces together.

**Tech Stack:** Python/FastAPI (ETL service), TypeScript/Deno (Supabase edge functions), Elixir/Phoenix (scheduler), Supabase/PostgreSQL (state), XGBoost (model)

---

### Task 1: Add `use_outcomes` and `outcome_weight` to TrainingConfig

**Files:**
- Modify: `python-etl-service/app/models/training_config.py:34-52` (TrainingConfig class fields)
- Modify: `python-etl-service/app/models/training_config.py:92-104` (to_hyperparameters_dict)
- Modify: `python-etl-service/app/models/training_config.py:106-119` (from_hyperparameters_dict)
- Test: `python-etl-service/tests/test_training_config.py`

**Step 1: Write the failing test**

```python
# In test_training_config.py — add to the existing test class

class TestOutcomeConfig:
    def test_use_outcomes_default_false(self):
        config = TrainingConfig()
        assert config.use_outcomes is False

    def test_outcome_weight_default_2(self):
        config = TrainingConfig()
        assert config.outcome_weight == 2.0

    def test_outcome_weight_validation(self):
        with pytest.raises(ValueError):
            TrainingConfig(outcome_weight=0.0)
        with pytest.raises(ValueError):
            TrainingConfig(outcome_weight=11.0)

    def test_use_outcomes_roundtrip_serialization(self):
        config = TrainingConfig(use_outcomes=True, outcome_weight=3.0)
        d = config.to_hyperparameters_dict()
        assert d["use_outcomes"] is True
        assert d["outcome_weight"] == 3.0
        restored = TrainingConfig.from_hyperparameters_dict(d)
        assert restored.use_outcomes is True
        assert restored.outcome_weight == 3.0

    def test_from_hyperparameters_dict_missing_outcome_fields(self):
        """Old models without outcome fields should default gracefully."""
        config = TrainingConfig.from_hyperparameters_dict({})
        assert config.use_outcomes is False
        assert config.outcome_weight == 2.0
```

**Step 2: Run test to verify it fails**

Run: `cd python-etl-service && uv run pytest tests/test_training_config.py::TestOutcomeConfig -v`
Expected: FAIL with `AttributeError` — `use_outcomes` doesn't exist yet.

**Step 3: Write minimal implementation**

In `training_config.py`, add two fields after line 52 (`triggered_by`):

```python
    use_outcomes: bool = Field(default=False, description="Use signal_outcomes for training labels")
    outcome_weight: float = Field(default=2.0, ge=0.1, le=10.0, description="Weight multiplier for outcome-labeled data vs yfinance-labeled data")
```

In `to_hyperparameters_dict()`, add after `"feature_names"` line (line 103):

```python
            "use_outcomes": self.use_outcomes,
            "outcome_weight": self.outcome_weight,
```

In `from_hyperparameters_dict()`, add to the `cls(...)` call (inside lines 110-119):

```python
            use_outcomes=data.get("use_outcomes", False),
            outcome_weight=data.get("outcome_weight", 2.0),
```

**Step 4: Run test to verify it passes**

Run: `cd python-etl-service && uv run pytest tests/test_training_config.py -v`
Expected: ALL PASS (existing + new tests)

**Step 5: Commit**

```bash
git add python-etl-service/app/models/training_config.py python-etl-service/tests/test_training_config.py
git commit -m "feat: add use_outcomes and outcome_weight to TrainingConfig"
```

---

### Task 2: Add `use_outcomes` to TrainRequest API model

**Files:**
- Modify: `python-etl-service/app/routes/ml.py:91-103` (TrainRequest)
- Modify: `python-etl-service/app/routes/ml.py:318-329` (TrainingConfig construction in /ml/train)
- Test: `python-etl-service/tests/test_ml_routes.py` (or the existing route test file)

**Step 1: Write the failing test**

```python
# In the existing ML routes test file, add:

class TestTrainRequestOutcome:
    def test_train_request_defaults(self):
        from app.routes.ml import TrainRequest
        req = TrainRequest()
        assert req.use_outcomes is False
        assert req.outcome_weight == 2.0

    def test_train_request_with_outcomes(self):
        from app.routes.ml import TrainRequest
        req = TrainRequest(use_outcomes=True, outcome_weight=3.5)
        assert req.use_outcomes is True
        assert req.outcome_weight == 3.5
```

**Step 2: Run test to verify it fails**

Run: `cd python-etl-service && uv run pytest tests/ -k "TestTrainRequestOutcome" -v`
Expected: FAIL — `use_outcomes` field not on `TrainRequest`.

**Step 3: Write minimal implementation**

In `ml.py`, add to `TrainRequest` class (after line 103):

```python
    use_outcomes: bool = Field(default=False, description="Use signal_outcomes for training labels")
    outcome_weight: float = Field(default=2.0, ge=0.1, le=10.0, description="Weight multiplier for outcome-labeled data")
```

In the `/ml/train` endpoint, find the `TrainingConfig(...)` construction (lines 318-329) and add:

```python
            use_outcomes=request.use_outcomes,
            outcome_weight=request.outcome_weight,
```

**Step 4: Run test to verify it passes**

Run: `cd python-etl-service && uv run pytest tests/ -k "TrainRequest" -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/routes/ml.py python-etl-service/tests/
git commit -m "feat: wire use_outcomes through TrainRequest API"
```

---

### Task 3: Implement `_fetch_outcome_data()` in FeaturePipeline

**Files:**
- Modify: `python-etl-service/app/services/feature_pipeline.py` — add method after `_fetch_disclosures()` (line ~211)
- Test: `python-etl-service/tests/test_feature_pipeline.py`

**Step 1: Write the failing test**

```python
class TestFetchOutcomeData:
    """Tests for _fetch_outcome_data() — reads signal_outcomes for training labels."""

    @pytest.fixture
    def pipeline(self):
        with patch("app.services.feature_pipeline.get_supabase") as mock_sb:
            mock_client = MagicMock()
            mock_sb.return_value = mock_client
            p = FeaturePipeline()
            p.supabase = mock_client
            yield p, mock_client

    @pytest.mark.asyncio
    async def test_fetch_outcome_data_returns_list(self, pipeline):
        p, mock_client = pipeline
        # Mock chain: .from_().select().in_().gte().execute()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "ticker": "AAPL",
                "signal_type": "buy",
                "signal_confidence": 0.85,
                "outcome": "win",
                "return_pct": 5.2,
                "entry_price": 150.0,
                "exit_price": 157.8,
                "holding_days": 14,
                "features": {
                    "politician_count": 5,
                    "buy_sell_ratio": 2.5,
                    "recent_activity_30d": 8,
                    "bipartisan": 1.0,
                    "net_volume": 500000,
                    "volume_magnitude": 5.7,
                    "party_alignment": 0.7,
                    "disclosure_delay": 30,
                    "market_momentum": 0.02,
                },
                "signal_date": "2026-01-15",
            }
        ]
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        outcomes = await p._fetch_outcome_data(window_days=90)
        assert len(outcomes) == 1
        assert outcomes[0]["ticker"] == "AAPL"
        assert outcomes[0]["outcome"] == "win"

    @pytest.mark.asyncio
    async def test_fetch_outcome_data_filters_open(self, pipeline):
        """Only closed outcomes (win/loss/breakeven) are fetched, not 'open'."""
        p, mock_client = pipeline
        mock_result = MagicMock()
        mock_result.data = []
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        await p._fetch_outcome_data(window_days=90)
        # Verify in_ filter excludes 'open'
        mock_table.in_.assert_called_once_with("outcome", ["win", "loss", "breakeven"])
```

**Step 2: Run test to verify it fails**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py::TestFetchOutcomeData -v`
Expected: FAIL — `_fetch_outcome_data` not defined.

**Step 3: Write minimal implementation**

Add to `FeaturePipeline` class, after `_fetch_disclosures()`:

```python
    async def _fetch_outcome_data(self, window_days: int = 90) -> list:
        """Fetch closed trade outcomes from signal_outcomes for training labels.

        Returns records where we know the actual trade result (win/loss/breakeven).
        The features JSONB stores the feature snapshot at signal generation time.
        """
        if not self.supabase:
            return []

        cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

        result = (
            self.supabase.table("signal_outcomes")
            .select("ticker, signal_type, signal_confidence, outcome, return_pct, "
                    "entry_price, exit_price, holding_days, features, signal_date")
            .in_("outcome", ["win", "loss", "breakeven"])
            .gte("signal_date", cutoff)
            .execute()
        )

        return result.data or []
```

**Step 4: Run test to verify it passes**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py::TestFetchOutcomeData -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/feature_pipeline.py python-etl-service/tests/test_feature_pipeline.py
git commit -m "feat: add _fetch_outcome_data to FeaturePipeline"
```

---

### Task 4: Implement `prepare_outcome_training_data()` in FeaturePipeline

**Files:**
- Modify: `python-etl-service/app/services/feature_pipeline.py` — add method after `prepare_training_data()`
- Test: `python-etl-service/tests/test_feature_pipeline.py`

**Step 1: Write the failing test**

```python
class TestPrepareOutcomeTrainingData:
    """Tests for prepare_outcome_training_data() — blends outcome + market data."""

    @pytest.fixture
    def pipeline(self):
        with patch("app.services.feature_pipeline.get_supabase") as mock_sb:
            mock_client = MagicMock()
            mock_sb.return_value = mock_client
            p = FeaturePipeline()
            p.supabase = mock_client
            yield p

    @pytest.mark.asyncio
    async def test_outcome_data_converted_to_features_and_labels(self, pipeline):
        p = pipeline
        config = TrainingConfig(use_outcomes=True, outcome_weight=2.0, num_classes=3)
        feature_names = config.get_feature_names()

        # Mock _fetch_outcome_data to return one closed trade
        outcome_record = {
            "ticker": "AAPL",
            "outcome": "win",
            "return_pct": 5.2,
            "features": {name: float(i) for i, name in enumerate(feature_names)},
            "signal_date": "2026-01-15",
        }
        p._fetch_outcome_data = AsyncMock(return_value=[outcome_record])
        # Mock prepare_training_data to return empty (no market data)
        p.prepare_training_data = AsyncMock(return_value=(pd.DataFrame(), np.array([])))

        features_df, labels, sample_weights = await p.prepare_outcome_training_data(config=config)

        assert len(features_df) == 1
        assert labels[0] == 1  # win → buy label (1 for 3-class)
        assert sample_weights[0] == 2.0  # outcome_weight

    @pytest.mark.asyncio
    async def test_blends_outcome_and_market_data(self, pipeline):
        p = pipeline
        config = TrainingConfig(use_outcomes=True, outcome_weight=2.0)
        feature_names = config.get_feature_names()

        # One outcome record
        outcome_record = {
            "ticker": "AAPL",
            "outcome": "win",
            "return_pct": 5.2,
            "features": {name: 1.0 for name in feature_names},
            "signal_date": "2026-01-15",
        }
        p._fetch_outcome_data = AsyncMock(return_value=[outcome_record])

        # One market record from prepare_training_data
        market_features = pd.DataFrame([{name: 2.0 for name in feature_names}])
        market_labels = np.array([1])
        p.prepare_training_data = AsyncMock(return_value=(market_features, market_labels))

        features_df, labels, sample_weights = await p.prepare_outcome_training_data(config=config)

        assert len(features_df) == 2  # 1 outcome + 1 market
        assert sample_weights[0] == 2.0  # outcome record weighted 2x
        assert sample_weights[1] == 1.0  # market record weighted 1x

    @pytest.mark.asyncio
    async def test_skips_outcomes_with_missing_features(self, pipeline):
        p = pipeline
        config = TrainingConfig(use_outcomes=True)

        # Outcome with incomplete features (missing required fields)
        outcome_record = {
            "ticker": "AAPL",
            "outcome": "win",
            "return_pct": 5.2,
            "features": {"politician_count": 5},  # Missing most features
            "signal_date": "2026-01-15",
        }
        p._fetch_outcome_data = AsyncMock(return_value=[outcome_record])
        p.prepare_training_data = AsyncMock(return_value=(pd.DataFrame(), np.array([])))

        features_df, labels, sample_weights = await p.prepare_outcome_training_data(config=config)
        assert len(features_df) == 0  # Skipped due to missing features

    @pytest.mark.asyncio
    async def test_outcome_label_mapping(self, pipeline):
        """win → positive label, loss → negative label, breakeven → hold."""
        p = pipeline
        config = TrainingConfig(use_outcomes=True, num_classes=5)
        feature_names = config.get_feature_names()
        full_features = {name: 1.0 for name in feature_names}

        outcomes = [
            {"ticker": "A", "outcome": "win", "return_pct": 5.0, "features": full_features, "signal_date": "2026-01-01"},
            {"ticker": "B", "outcome": "loss", "return_pct": -3.0, "features": full_features, "signal_date": "2026-01-01"},
            {"ticker": "C", "outcome": "breakeven", "return_pct": 0.1, "features": full_features, "signal_date": "2026-01-01"},
        ]
        p._fetch_outcome_data = AsyncMock(return_value=outcomes)
        p.prepare_training_data = AsyncMock(return_value=(pd.DataFrame(), np.array([])))

        features_df, labels, sample_weights = await p.prepare_outcome_training_data(config=config)
        assert len(labels) == 3
        assert labels[0] > 0   # win → buy or strong_buy
        assert labels[1] < 0   # loss → sell or strong_sell
        assert labels[2] == 0  # breakeven → hold
```

**Step 2: Run test to verify it fails**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py::TestPrepareOutcomeTrainingData -v`
Expected: FAIL — `prepare_outcome_training_data` not defined.

**Step 3: Write minimal implementation**

Add to `FeaturePipeline` class, after `prepare_training_data()`:

```python
    async def prepare_outcome_training_data(
        self,
        config: Optional["TrainingConfig"] = None,
    ) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        """Prepare training data blending outcome-labeled and market-labeled records.

        Returns (features_df, labels, sample_weights) where sample_weights
        gives outcome records higher weight than yfinance-derived records.
        """
        from app.models.training_config import TrainingConfig

        if config is None:
            config = TrainingConfig(use_outcomes=True)

        feature_names = config.get_feature_names()
        outcome_weight = config.outcome_weight

        # --- Outcome-labeled data from closed trades ---
        outcome_records = await self._fetch_outcome_data(
            window_days=config.lookback_days
        )

        outcome_features_list = []
        outcome_labels = []
        for rec in outcome_records:
            features = rec.get("features", {})
            # Skip if features don't have all required fields
            if not all(name in features for name in feature_names):
                continue

            feature_vec = {name: float(features.get(name, 0.0)) for name in feature_names}
            outcome_features_list.append(feature_vec)

            # Map outcome to label
            outcome = rec["outcome"]
            return_pct = rec.get("return_pct", 0.0)
            if outcome == "win":
                label = generate_label(
                    abs(return_pct) / 100.0, config.num_classes, config.thresholds
                )
                if label <= 0:
                    label = 1  # At minimum, a win is a buy signal
            elif outcome == "loss":
                label = generate_label(
                    -abs(return_pct) / 100.0, config.num_classes, config.thresholds
                )
                if label >= 0:
                    label = -1  # At minimum, a loss is a sell signal
            else:  # breakeven
                label = 0

            outcome_labels.append(label)

        # --- Market-labeled data from yfinance forward returns ---
        market_features_df, market_labels = await self.prepare_training_data(
            lookback_days=config.lookback_days,
            config=config,
        )

        # --- Blend both sources ---
        all_features = []
        all_labels = []
        all_weights = []

        # Add outcome data with higher weight
        if outcome_features_list:
            outcome_df = pd.DataFrame(outcome_features_list)
            all_features.append(outcome_df)
            all_labels.extend(outcome_labels)
            all_weights.extend([outcome_weight] * len(outcome_labels))

        # Add market data with weight 1.0
        if len(market_features_df) > 0:
            all_features.append(market_features_df)
            all_labels.extend(market_labels.tolist())
            all_weights.extend([1.0] * len(market_labels))

        if not all_features:
            return pd.DataFrame(), np.array([]), np.array([])

        combined_df = pd.concat(all_features, ignore_index=True)
        return combined_df, np.array(all_labels), np.array(all_weights)
```

**Step 4: Run test to verify it passes**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py::TestPrepareOutcomeTrainingData -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py -v`
Expected: ALL PASS (existing 75 + new tests)

**Step 6: Commit**

```bash
git add python-etl-service/app/services/feature_pipeline.py python-etl-service/tests/test_feature_pipeline.py
git commit -m "feat: add prepare_outcome_training_data with weighted blending"
```

---

### Task 5: Wire outcome training into TrainingJob.run()

**Files:**
- Modify: `python-etl-service/app/services/feature_pipeline.py:662-771` (TrainingJob.run)
- Modify: `python-etl-service/app/services/ml_signal_model.py:263-370` (CongressSignalModel.train — accept sample_weight)
- Test: `python-etl-service/tests/test_feature_pipeline.py`

**Step 1: Write the failing test**

```python
class TestTrainingJobOutcomeAware:
    """TrainingJob.run() should use outcome data when config.use_outcomes=True."""

    @pytest.mark.asyncio
    async def test_run_uses_outcome_data_when_enabled(self):
        config = TrainingConfig(use_outcomes=True, lookback_days=365)
        job = TrainingJob(config=config)

        with patch("app.services.feature_pipeline.get_supabase") as mock_sb, \
             patch("app.services.feature_pipeline.upload_model_to_storage"), \
             patch.object(FeaturePipeline, "prepare_outcome_training_data") as mock_outcome, \
             patch.object(FeaturePipeline, "prepare_training_data") as mock_market:

            mock_client = MagicMock()
            mock_sb.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.update.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.neq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[{"id": "test-id"}])

            # Return enough data for training
            n = 120
            features = pd.DataFrame(np.random.rand(n, 14), columns=DEFAULT_FEATURE_NAMES)
            labels = np.random.choice([-2, -1, 0, 1, 2], size=n)
            weights = np.ones(n)

            mock_outcome.return_value = (features, labels, weights)
            mock_market.return_value = (features, labels)  # Should NOT be called

            await job.run()

            # Verify outcome path was used, not the plain market path
            mock_outcome.assert_called_once()
            mock_market.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py::TestTrainingJobOutcomeAware -v`
Expected: FAIL — `run()` doesn't check `use_outcomes`.

**Step 3: Write minimal implementation**

In `TrainingJob.run()`, find the data preparation block (~lines 694-698). Replace:

```python
            # Current: always use market data
            features_df, labels = await pipeline.prepare_training_data(
                lookback_days=config.lookback_days,
                config=config,
            )
```

With:

```python
            sample_weights = None
            if config.use_outcomes:
                features_df, labels, sample_weights = await pipeline.prepare_outcome_training_data(
                    config=config,
                )
            else:
                features_df, labels = await pipeline.prepare_training_data(
                    lookback_days=config.lookback_days,
                    config=config,
                )
```

Then pass `sample_weights` to `model.train()` (~line 707):

```python
            results = model.train(
                features_df, labels,
                hyperparams=config.hyperparams,
                config=config,
                sample_weights=sample_weights,
            )
```

In `CongressSignalModel.train()` (ml_signal_model.py:263), add `sample_weights: Optional[np.ndarray] = None` to the signature. In the XGBoost fit call, pass `sample_weight`:

```python
        # Where model.fit(X_train, y_train, ...) is called:
        if sample_weights is not None:
            train_weights = sample_weights[train_indices]
            self.model.fit(X_train_scaled, y_train_shifted, sample_weight=train_weights, ...)
        else:
            self.model.fit(X_train_scaled, y_train_shifted, ...)
```

XGBoost's `fit()` natively supports `sample_weight` — no library changes needed.

**Step 4: Run test to verify it passes**

Run: `cd python-etl-service && uv run pytest tests/test_feature_pipeline.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/feature_pipeline.py python-etl-service/app/services/ml_signal_model.py python-etl-service/tests/test_feature_pipeline.py
git commit -m "feat: wire outcome-aware training into TrainingJob.run"
```

---

### Task 6: Create `ml-training` edge function

**Files:**
- Create: `supabase/functions/ml-training/index.ts`
- Reference: `supabase/functions/_shared/cors.ts` (import `corsHeaders`)
- Reference: `supabase/functions/_shared/auth.ts` (import `isServiceRoleRequest`)

**Step 1: Create the edge function**

```typescript
// supabase/functions/ml-training/index.ts
import { serve } from "https://deno.land/std@0.177.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"
import { corsHeaders } from "../_shared/cors.ts"

const ETL_API_URL = Deno.env.get('ETL_API_URL') || 'https://politician-trading-etl.fly.dev'
const ADMIN_KEY = Deno.env.get('ETL_ADMIN_KEY') || ''

// Minimum improvement thresholds for champion/challenger gate
const MIN_ACCURACY_IMPROVEMENT = 0.02  // 2%
const MIN_F1_IMPROVEMENT = 0.03        // 3%

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  const requestId = crypto.randomUUID().slice(0, 8)

  try {
    const body = await req.json()
    const {
      action = 'train',
      use_outcomes = false,
      outcome_window_days = 90,
      compare_to_current = true,
      lookback_days = 365,
      triggered_by = 'scheduler',
    } = body

    if (action !== 'train') {
      return new Response(
        JSON.stringify({ error: `Unknown action: ${action}` }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    console.log(`[ml-training:${requestId}] Starting training: use_outcomes=${use_outcomes}, compare=${compare_to_current}`)

    // Step 1: Get current active model metrics (for comparison later)
    let currentModelMetrics: any = null
    let currentModelId: string | null = null

    if (compare_to_current) {
      const supabaseUrl = Deno.env.get('SUPABASE_URL')!
      const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
      const supabase = createClient(supabaseUrl, supabaseKey)

      const { data: currentModel } = await supabase
        .from('ml_models')
        .select('id, metrics, model_version')
        .eq('status', 'active')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()

      if (currentModel) {
        currentModelMetrics = currentModel.metrics
        currentModelId = currentModel.id
        console.log(`[ml-training:${requestId}] Current model: ${currentModel.model_version}, accuracy=${currentModelMetrics?.accuracy}`)
      }
    }

    // Step 2: Trigger training via Python ETL service
    const trainResponse = await fetch(`${ETL_API_URL}/ml/train`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': ADMIN_KEY,
      },
      body: JSON.stringify({
        lookback_days,
        use_outcomes,
        outcome_weight: 2.0,
        triggered_by,
      }),
    })

    if (!trainResponse.ok) {
      const errText = await trainResponse.text()
      throw new Error(`ETL train request failed: ${trainResponse.status} - ${errText}`)
    }

    const trainResult = await trainResponse.json()
    console.log(`[ml-training:${requestId}] Training job created: ${trainResult.job_id}`)

    // Step 3: Poll for training completion (max 5 minutes)
    const jobId = trainResult.job_id
    let jobStatus = 'pending'
    let newModelMetrics: any = null
    const maxWaitMs = 300_000
    const pollIntervalMs = 10_000
    const startTime = Date.now()

    while (Date.now() - startTime < maxWaitMs) {
      await new Promise(r => setTimeout(r, pollIntervalMs))

      const statusResponse = await fetch(`${ETL_API_URL}/ml/jobs/${jobId}`, {
        headers: { 'X-Admin-Key': ADMIN_KEY },
      })

      if (statusResponse.ok) {
        const statusData = await statusResponse.json()
        jobStatus = statusData.status

        if (jobStatus === 'completed') {
          newModelMetrics = statusData.metrics
          break
        }
        if (jobStatus === 'failed') {
          throw new Error(`Training failed: ${statusData.error || 'unknown'}`)
        }
      }
    }

    if (jobStatus !== 'completed') {
      return new Response(
        JSON.stringify({
          success: true,
          message: 'Training started but not yet complete — will be promoted automatically',
          job_id: jobId,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Step 4: Champion/Challenger comparison
    let promoted = true
    let reason = 'No current model to compare against'

    if (compare_to_current && currentModelMetrics && newModelMetrics) {
      const oldAcc = currentModelMetrics.accuracy || 0
      const newAcc = newModelMetrics.accuracy || 0
      const oldF1 = currentModelMetrics.f1_weighted || 0
      const newF1 = newModelMetrics.f1_weighted || 0

      const accImprovement = newAcc - oldAcc
      const f1Improvement = newF1 - oldF1

      if (accImprovement >= MIN_ACCURACY_IMPROVEMENT || f1Improvement >= MIN_F1_IMPROVEMENT) {
        promoted = true
        reason = `Improvement: accuracy +${(accImprovement * 100).toFixed(1)}%, F1 +${(f1Improvement * 100).toFixed(1)}%`
      } else {
        promoted = false
        reason = `Below threshold: accuracy +${(accImprovement * 100).toFixed(1)}% (need ${MIN_ACCURACY_IMPROVEMENT * 100}%), F1 +${(f1Improvement * 100).toFixed(1)}% (need ${MIN_F1_IMPROVEMENT * 100}%)`
      }

      console.log(`[ml-training:${requestId}] Champion/Challenger: promoted=${promoted}, ${reason}`)

      // If not promoted, demote new model to candidate
      if (!promoted) {
        const supabaseUrl = Deno.env.get('SUPABASE_URL')!
        const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
        const supabase = createClient(supabaseUrl, supabaseKey)

        // Find the new model (most recently created active one)
        const { data: newModel } = await supabase
          .from('ml_models')
          .select('id')
          .eq('status', 'active')
          .order('created_at', { ascending: false })
          .limit(1)
          .maybeSingle()

        if (newModel && newModel.id !== currentModelId) {
          await supabase
            .from('ml_models')
            .update({ status: 'candidate' })
            .eq('id', newModel.id)

          // Restore the previous active model
          if (currentModelId) {
            await supabase
              .from('ml_models')
              .update({ status: 'active' })
              .eq('id', currentModelId)
          }
        }
      }

      // Log comparison to model_retraining_events
      const supabaseUrl = Deno.env.get('SUPABASE_URL')!
      const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
      const supabase = createClient(supabaseUrl, supabaseKey)

      await supabase.from('model_retraining_events').insert({
        old_model_id: currentModelId,
        new_model_id: trainResult.model_id || null,
        trigger_type: triggered_by === 'scheduler' ? 'scheduled' : 'manual',
        trigger_reason: `use_outcomes=${use_outcomes}`,
        old_model_metrics: currentModelMetrics,
        new_model_metrics: newModelMetrics,
        improvement_pct: newModelMetrics?.accuracy && currentModelMetrics?.accuracy
          ? (newModelMetrics.accuracy - currentModelMetrics.accuracy) * 100
          : null,
        deployed: promoted,
        deployment_reason: reason,
      })
    }

    return new Response(
      JSON.stringify({
        success: true,
        job_id: jobId,
        promoted,
        reason,
        metrics: newModelMetrics,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error(`[ml-training:${requestId}] Error: ${error.message}`)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

**Step 2: Test locally**

Run: `supabase functions serve ml-training --env-file supabase/.env.local`
Then: `curl -X POST http://localhost:54321/functions/v1/ml-training -H 'Content-Type: application/json' -d '{"action":"train","use_outcomes":false}'`
Expected: Response with `job_id` or connection error to ETL service (expected in local dev).

**Step 3: Commit**

```bash
git add supabase/functions/ml-training/index.ts
git commit -m "feat: create ml-training edge function with champion/challenger gate"
```

---

### Task 7: Database migration — add `ml_blend_weight` and widen `trading_mode`

**Files:**
- Create: `supabase/migrations/20260219100000_ml_feedback_loop_config.sql`

**Step 1: Write the migration**

```sql
-- ML Feedback Loop Configuration
-- Adds dynamic blend weight and widens trading_mode constraint

-- 1. Add ml_blend_weight to reference_portfolio_config
ALTER TABLE public.reference_portfolio_config
  ADD COLUMN IF NOT EXISTS ml_blend_weight DECIMAL(3,2) NOT NULL DEFAULT 0.20;

-- 2. Widen trading_mode constraint to allow 'live'
-- Drop existing CHECK constraint (name may vary, handle both)
DO $$
BEGIN
  ALTER TABLE public.reference_portfolio_config
    DROP CONSTRAINT IF EXISTS reference_portfolio_config_trading_mode_check;
EXCEPTION WHEN undefined_object THEN
  NULL;
END $$;

ALTER TABLE public.reference_portfolio_config
  ADD CONSTRAINT reference_portfolio_config_trading_mode_check
  CHECK (trading_mode IN ('paper', 'live'));

-- 3. Add 'candidate' to ml_models status (for champion/challenger)
-- Current CHECK: status IN ('training', 'active', 'archived', 'failed')
DO $$
BEGIN
  ALTER TABLE public.ml_models
    DROP CONSTRAINT IF EXISTS ml_models_status_check;
EXCEPTION WHEN undefined_object THEN
  NULL;
END $$;

ALTER TABLE public.ml_models
  ADD CONSTRAINT ml_models_status_check
  CHECK (status IN ('training', 'active', 'archived', 'failed', 'candidate'));

COMMENT ON COLUMN public.reference_portfolio_config.ml_blend_weight IS
  'ML model weight in blended signals (0.1-0.7). Auto-adjusted by signal-feedback evaluation.';
COMMENT ON COLUMN public.reference_portfolio_config.trading_mode IS
  'paper = Alpaca paper trading, live = real money. Requires manual switch.';
```

**Step 2: Apply the migration**

Run: `supabase db push` (or apply via Supabase dashboard)

**Step 3: Commit**

```bash
git add supabase/migrations/20260219100000_ml_feedback_loop_config.sql
git commit -m "feat: add ml_blend_weight column and widen trading_mode constraint"
```

---

### Task 8: Dynamic blend weight — read from config in `trading-signals`

**Files:**
- Modify: `supabase/functions/trading-signals/index.ts:1601` (ML_BLEND_WEIGHT constant)
- Modify: `supabase/functions/trading-signals/index.ts:2083-2113` (blendSignals function)

**Step 1: Replace hardcoded blend weight with config read**

In `trading-signals/index.ts`, find the `handleRegenerateSignals` function. Near the top where it creates the supabase client, add a config read:

```typescript
    // Read ML blend weight from config (dynamic, auto-adjusted by signal-feedback)
    const { data: portfolioConfig } = await supabaseClient
      .from('reference_portfolio_config')
      .select('ml_blend_weight')
      .limit(1)
      .maybeSingle()
    const mlBlendWeight = portfolioConfig?.ml_blend_weight ?? ML_BLEND_WEIGHT
```

Then pass `mlBlendWeight` to `blendSignals()`. Update the `blendSignals` function signature to accept the weight:

```typescript
function blendSignals(
  heuristicType: string,
  heuristicConfidence: number,
  mlPrediction: number | null,
  mlConfidence: number | null,
  blendWeight: number = ML_BLEND_WEIGHT  // backward compatible default
): { signalType: string; confidence: number; mlEnhanced: boolean } {
```

And replace `ML_BLEND_WEIGHT` usage inside `blendSignals` with the `blendWeight` parameter:

```typescript
  const blendedConfidence = heuristicConfidence * (1 - blendWeight) + mlConfidence * blendWeight
```

Update both call sites (lines ~1347 and ~2477) to pass `mlBlendWeight`.

**Step 2: Commit**

```bash
git add supabase/functions/trading-signals/index.ts
git commit -m "feat: read ML blend weight from config instead of hardcoded constant"
```

---

### Task 9: Dynamic blend weight — auto-adjust in `signal-feedback`

**Files:**
- Modify: `supabase/functions/signal-feedback/index.ts:452-561` (handleEvaluateModel)

**Step 1: Add blend weight adjustment logic**

At the end of `handleEvaluateModel()`, after saving to `model_performance_history` (~line 558), add:

```typescript
    // Auto-adjust ML blend weight based on performance comparison
    const mlWinRate = performance.high_confidence_win_rate || performance.win_rate || 0
    // Heuristic baseline: signals that were NOT ml_enhanced
    const heuristicOutcomes = outcomes.filter((o: any) => !o.ml_enhanced)
    const heuristicWins = heuristicOutcomes.filter((o: any) => o.outcome === 'win').length
    const heuristicWinRate = heuristicOutcomes.length > 0 ? heuristicWins / heuristicOutcomes.length : 0.5

    const { data: currentConfig } = await supabaseClient
      .from('reference_portfolio_config')
      .select('ml_blend_weight')
      .limit(1)
      .maybeSingle()

    if (currentConfig) {
      let newWeight = currentConfig.ml_blend_weight
      const winRateDiff = mlWinRate - heuristicWinRate

      if (winRateDiff > 0.05) {
        newWeight = Math.min(newWeight + 0.1, 0.7)
      } else if (winRateDiff < -0.05) {
        newWeight = Math.max(newWeight - 0.1, 0.1)
      }

      if (newWeight !== currentConfig.ml_blend_weight) {
        await supabaseClient
          .from('reference_portfolio_config')
          .update({ ml_blend_weight: newWeight })
          .eq('id', currentConfig.id || currentConfig)

        // Log the adjustment
        await supabaseClient.from('feature_importance_history').insert({
          analysis_date: new Date().toISOString().split('T')[0],
          analysis_window_days: windowDays,
          feature_name: '_ml_blend_weight',
          correlation_with_return: winRateDiff,
          median_value: newWeight,
          avg_return_when_high: mlWinRate,
          avg_return_when_low: heuristicWinRate,
          lift_pct: winRateDiff,
          sample_size_total: outcomes.length,
          feature_useful: winRateDiff > 0,
        })

        log.info('ML blend weight adjusted', { requestId, oldWeight: currentConfig.ml_blend_weight, newWeight, winRateDiff })
      }
    }
```

**Step 2: Commit**

```bash
git add supabase/functions/signal-feedback/index.ts
git commit -m "feat: auto-adjust ML blend weight based on win rate comparison"
```

---

### Task 10: Tighten signal quality thresholds

**Files:**
- Modify: `supabase/functions/trading-signals/index.ts:6-7` (REFERENCE_PORTFOLIO_MIN_CONFIDENCE)
- Modify: `supabase/functions/trading-signals/index.ts:1053` (minConfidence default in regenerate)
- Modify: `supabase/functions/trading-signals/index.ts:2083-2113` (blendSignals — add direction disagreement filter)
- Modify: `supabase/functions/reference-portfolio/index.ts:838` (confidence gate in execute)

**Step 1: Update threshold constants**

In `trading-signals/index.ts`:

Line 6-7: Change:
```typescript
const REFERENCE_PORTFOLIO_MIN_CONFIDENCE = 0.70
```
To:
```typescript
const REFERENCE_PORTFOLIO_MIN_CONFIDENCE = 0.75
```

Line ~1053: Change default `minConfidence` from `0.60` to `0.65`:
```typescript
const { lookbackDays = 90, minConfidence = 0.65, clearOld = true, useML = ML_ENABLED } = body
```

**Step 2: Add direction disagreement filter**

In `blendSignals()`, after the null check (line 2089), add:

```typescript
  // Filter: if heuristic and ML disagree on direction (buy vs sell), reduce confidence sharply
  const heuristicNumeric = SIGNAL_TYPE_MAP[heuristicType] ?? 0
  const heuristicIsBuy = heuristicNumeric > 0
  const mlIsBuy = mlPrediction > 0
  const heuristicIsSell = heuristicNumeric < 0
  const mlIsSell = mlPrediction < 0

  if ((heuristicIsBuy && mlIsSell) || (heuristicIsSell && mlIsBuy)) {
    // Complete directional disagreement — heavily penalize
    return {
      signalType: heuristicType,
      confidence: Math.min(heuristicConfidence, mlConfidence) * 0.5,
      mlEnhanced: true,
    }
  }
```

**Step 3: Add position-level risk check in reference-portfolio**

In `reference-portfolio/index.ts`, in `handleExecuteSignals()`, after the confidence gate (~line 838), add:

```typescript
      // Risk check: reduce exposure in uncertain conditions
      if (signal.confidence_score < 0.70 && state.open_positions >= 15) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Low confidence with high position count')
        continue
      }
```

**Step 4: Commit**

```bash
git add supabase/functions/trading-signals/index.ts supabase/functions/reference-portfolio/index.ts
git commit -m "feat: tighten signal thresholds and add direction disagreement filter"
```

---

### Task 11: Paper/live trading toggle

**Files:**
- Modify: `supabase/functions/reference-portfolio/index.ts:94-107` (getAlpacaCredentials)

**Step 1: Read trading_mode from config**

In `reference-portfolio/index.ts`, find `getAlpacaCredentials()` (line 94). Change:

```typescript
function getAlpacaCredentials() {
  const paper = Deno.env.get('ALPACA_PAPER') !== 'false'
```

To read from config (passed as a parameter):

```typescript
function getAlpacaCredentials(tradingMode: string = 'paper') {
  const paper = tradingMode === 'paper'
```

In `handleExecuteSignals()`, after reading the config, pass `trading_mode`:

```typescript
    const credentials = getAlpacaCredentials(config.trading_mode || 'paper')
```

Update the config select to include `trading_mode`:

```typescript
    const { data: config } = await supabaseClient
      .from('reference_portfolio_config')
      .select('*, trading_mode, ml_blend_weight')
```

(If the select already uses `*`, `trading_mode` is already included — just verify.)

**Step 2: Commit**

```bash
git add supabase/functions/reference-portfolio/index.ts
git commit -m "feat: read trading_mode from config for paper/live toggle"
```

---

### Task 12: Final integration test and deploy

**Files:**
- All modified files from Tasks 1-11

**Step 1: Run full Python test suite**

Run: `cd python-etl-service && uv run pytest -v --tb=short`
Expected: ALL PASS

**Step 2: Run client tests**

Run: `cd client && npx vitest run`
Expected: ALL PASS (926 tests)

**Step 3: Commit any remaining changes and push**

```bash
git push origin main
```

**Step 4: Monitor CI**

Run: `gh run watch`
Expected: CI passes

**Step 5: Deploy edge functions**

```bash
supabase functions deploy ml-training
supabase functions deploy trading-signals
supabase functions deploy signal-feedback
supabase functions deploy reference-portfolio
```

**Step 6: Apply database migration**

Apply `20260219100000_ml_feedback_loop_config.sql` via Supabase dashboard or `supabase db push`.

**Step 7: Verify the monthly feedback retrain is wired**

Check Elixir scheduler logs for `ModelFeedbackRetrainJob` — it should now successfully call the new `ml-training` edge function.

**Step 8: Trigger a test training run with outcomes**

```bash
curl -X POST https://politician-trading-etl.fly.dev/ml/train \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Key: <key>' \
  -d '{"use_outcomes": true, "lookback_days": 365}'
```

Expected: Training job starts, reads from `signal_outcomes`, blends with yfinance data.
