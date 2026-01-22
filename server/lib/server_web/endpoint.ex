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

  # CORS - Allow cross-origin requests from client apps
  plug Corsica,
    origins: {__MODULE__, :cors_origin_allowed?, []},
    allow_headers: ["content-type", "authorization", "accept"],
    allow_methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_credentials: true,
    max_age: 86400

  @allowed_origins [
    # Local development
    "http://localhost:9090",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:5173",
    # Production
    "https://govmarket.trade",
    "https://www.govmarket.trade"
  ]

  # TODO: Review this function
  @doc false
  def cors_origin_allowed?(_conn, origin) do
    origin in @allowed_origins or
      String.ends_with?(origin, ".fly.dev") or
      String.ends_with?(origin, ".vercel.app") or
      String.ends_with?(origin, ".netlify.app")
  end

  # Route to controllers
  plug ServerWeb.Router
end
