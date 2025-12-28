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

    # Add API routes here
    # Example: resources "/trades", TradeController
  end
end
