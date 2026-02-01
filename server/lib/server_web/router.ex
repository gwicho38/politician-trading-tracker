defmodule ServerWeb.Router do
  @moduledoc """
  Phoenix Router for the Politician Trading Tracker API.

  ## Authentication

  All `/api/*` routes require API key authentication via:
  - `X-API-Key` header (preferred)
  - `Authorization: Bearer <key>` header
  - `?api_key=<key>` query parameter (fallback)

  Set `ETL_API_KEY` environment variable to enable authentication.
  Set `ETL_AUTH_DISABLED=true` to disable auth in development.

  ## Routes

  ### Public (no auth required)
  - `GET /` - Health check (server running)
  - `GET /health` - Liveness check
  - `GET /health/ready` - Readiness check (database connected)
  - `GET /ready` - Readiness check (alias)
  - `GET /api/jobs/sync-status` - Last sync time (public)
  - `GET /api/ml/models/active` - Active ML model info (read-only)
  - `GET /api/ml/health` - ML service health check

  ### Protected (API key required)
  - `GET /api/jobs` - List scheduled jobs
  - `POST /api/jobs/:job_id/run` - Trigger a specific job
  - `POST /api/jobs/run-all` - Trigger all jobs
  - `POST /api/ml/predict` - ML predictions
  - `POST /api/ml/train` - Trigger model training
  """

  use ServerWeb, :router

  # ===========================================================================
  # Pipelines
  # ===========================================================================

  pipeline :api do
    plug :accepts, ["json"]
    plug ServerWeb.Plugs.ApiKeyAuth
  end

  pipeline :public_api do
    plug :accepts, ["json"]
  end

  # ===========================================================================
  # Base  Routes (no pipeline - always accessible)
  # ===========================================================================

  scope "/", ServerWeb do
    get "/", HealthController, :index
    get "/ready", HealthController, :ready
  end

  # ===========================================================================
  # Health Check Routes (no pipeline - always accessible)
  # ===========================================================================

  scope "/health", ServerWeb do
    get "/", HealthController, :index
    get "/ready", HealthController, :ready
  end

  # ===========================================================================
  # Public API Routes (no auth required)
  # ===========================================================================

  scope "/api", ServerWeb do
    pipe_through :public_api

    # Sync status is public - shows last sync time (non-sensitive)
    get "/jobs/sync-status", JobController, :sync_status

    # Active ML model info is public - read-only model metadata
    get "/ml/models/active", MlController, :active_model
    get "/ml/health", MlController, :health
  end

  # ===========================================================================
  # Protected API Routes (API key required)
  # ===========================================================================

  scope "/api", ServerWeb do
    pipe_through :api

    # Job management
    get "/jobs", JobController, :index
    get "/jobs/:job_id", JobController, :show
    post "/jobs/:job_id/run", JobController, :run
    post "/jobs/run-all", JobController, :run_all

    # ML prediction and model management (protected endpoints)
    post "/ml/predict", MlController, :predict
    post "/ml/batch-predict", MlController, :batch_predict
    get "/ml/models", MlController, :list_models
    get "/ml/models/:model_id", MlController, :show_model
    get "/ml/models/:model_id/feature-importance", MlController, :feature_importance
    post "/ml/train", MlController, :trigger_training
    get "/ml/train/:job_id", MlController, :training_status
  end
end
