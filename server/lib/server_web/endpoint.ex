defmodule ServerWeb.Endpoint do
  @moduledoc """
  Phoenix Endpoint for the Politician Trading Tracker API.

  Handles HTTP request processing pipeline including:
  - Request ID generation
  - Telemetry
  - JSON parsing
  - Routing
  """

  use Phoenix.Endpoint, otp_app: :server

  # ---------------------------------------------------------------------------
  # Static Files (minimal - API only)
  # ---------------------------------------------------------------------------

  plug Plug.Static,
    at: "/",
    from: :server,
    gzip: false,
    only: ServerWeb.static_paths()

  # ---------------------------------------------------------------------------
  # Development Reloading
  # ---------------------------------------------------------------------------

  if code_reloading? do
    plug Phoenix.CodeReloader
    plug Phoenix.Ecto.CheckRepoStatus, otp_app: :server
  end

  # ---------------------------------------------------------------------------
  # Request Pipeline
  # ---------------------------------------------------------------------------

  # Add unique request ID to each request
  plug Plug.RequestId

  # Emit telemetry events for monitoring
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]

  # Parse request body (JSON, form data)
  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Phoenix.json_library()

  plug Plug.MethodOverride
  plug Plug.Head

  # Route to controllers
  plug ServerWeb.Router
end
