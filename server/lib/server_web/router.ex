defmodule ServerWeb.Router do
  @moduledoc """
  Phoenix Router for the Politician Trading Tracker API.

  ## Routes

  - `GET /health` - Liveness check (server running)
  - `GET /health/ready` - Readiness check (database connected)
  - `GET /api/*` - API endpoints (to be added)
  """

  use ServerWeb, :router

  # ===========================================================================
  # Pipelines
  # ===========================================================================

  pipeline :api do
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
  # API Routes
  # ===========================================================================

  scope "/api", ServerWeb do
    pipe_through :api

    # Job management
    get "/jobs", JobController, :index
    get "/jobs/sync-status", JobController, :sync_status
    get "/jobs/:job_id", JobController, :show
    post "/jobs/:job_id/run", JobController, :run
    post "/jobs/run-all", JobController, :run_all

    # ML prediction and model management
    post "/ml/predict", MlController, :predict
    post "/ml/batch-predict", MlController, :batch_predict
    get "/ml/models", MlController, :list_models
    get "/ml/models/active", MlController, :active_model
    get "/ml/models/:model_id", MlController, :show_model
    get "/ml/models/:model_id/feature-importance", MlController, :feature_importance
    post "/ml/train", MlController, :trigger_training
    get "/ml/train/:job_id", MlController, :training_status
    get "/ml/health", MlController, :health
  end
end
