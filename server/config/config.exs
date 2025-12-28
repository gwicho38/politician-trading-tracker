# =============================================================================
# Politician Trading Tracker Server - Configuration
# =============================================================================
#
# This is the base configuration file. Environment-specific config is loaded
# from dev.exs, test.exs, or prod.exs, and runtime config from runtime.exs.
#
# Configuration hierarchy:
#   1. config.exs (this file) - base defaults
#   2. {env}.exs - environment-specific overrides
#   3. runtime.exs - runtime configuration (secrets, env vars)

import Config

# =============================================================================
# Application Configuration
# =============================================================================

config :server,
  # Ecto repositories to start
  ecto_repos: [Server.Repo],
  # Use UUIDs for primary keys (matches Supabase defaults)
  generators: [timestamp_type: :utc_datetime, binary_id: true]

# =============================================================================
# Database Configuration (Supabase PostgreSQL)
# =============================================================================
#
# Base config - credentials are set per-environment in dev.exs/runtime.exs
# Supabase Project: uljsqvwkomdrlnofmlad

config :server, Server.Repo,
  database: "postgres",
  pool_size: 10,
  parameters: [application_name: "politician_trading_server"]

# =============================================================================
# Phoenix Endpoint Configuration
# =============================================================================

config :server, ServerWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [
    formats: [json: ServerWeb.ErrorJSON],
    layout: false
  ],
  pubsub_server: Server.PubSub,
  live_view: [signing_salt: "AHAjt8QT"]

# =============================================================================
# Logging
# =============================================================================

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

# =============================================================================
# Phoenix JSON Library
# =============================================================================

config :phoenix, :json_library, Jason

# =============================================================================
# Scheduler Configuration (Quantum)
# =============================================================================
#
# The scheduler starts with no jobs. Jobs are registered dynamically via:
#   Server.Scheduler.register_job(MyApp.Jobs.SomeJob)
#
# See Server.Scheduler for full API.

config :server, Server.Scheduler.Quantum,
  jobs: [],
  timezone: "Etc/UTC"

# =============================================================================
# Import Environment-Specific Config
# =============================================================================

import_config "#{config_env()}.exs"
