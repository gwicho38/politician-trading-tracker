# =============================================================================
# Runtime Configuration
# =============================================================================
#
# This file is executed at runtime (not compile time), making it ideal for:
# - Loading secrets from environment variables
# - Production configuration that varies by deployment
#
# For releases, start with: PHX_SERVER=true bin/server start

import Config

# =============================================================================
# Start Phoenix Server (for releases)
# =============================================================================

if System.get_env("PHX_SERVER") do
  config :server, ServerWeb.Endpoint, server: true
end

# =============================================================================
# Production Configuration
# =============================================================================

if config_env() == :prod do
  # ---------------------------------------------------------------------------
  # Database Configuration (Supabase PostgreSQL)
  # ---------------------------------------------------------------------------
  #
  # Set DATABASE_URL for the full connection string, or set individual vars:
  # - DATABASE_HOST (default: db.uljsqvwkomdrlnofmlad.supabase.co)
  # - DATABASE_PASSWORD (required)
  # - DATABASE_PORT (default: 5432)
  # - POOL_SIZE (default: 10)

  database_url = System.get_env("DATABASE_URL")

  if database_url do
    # Supabase requires SSL for external connections
    config :server, Server.Repo,
      url: database_url,
      ssl: [verify: :verify_none],
      pool_size: String.to_integer(System.get_env("POOL_SIZE", "10")),
      # Supabase uses pgbouncer which requires prepared statements to be unnamed
      prepare: :unnamed
  else
    database_password =
      System.get_env("DATABASE_PASSWORD") ||
        raise """
        Environment variable DATABASE_PASSWORD is missing.
        Get this from Supabase Dashboard > Project Settings > Database
        """

    config :server, Server.Repo,
      hostname: System.get_env("DATABASE_HOST", "aws-1-eu-north-1.pooler.supabase.com"),
      port: String.to_integer(System.get_env("DATABASE_PORT", "6543")),
      username: System.get_env("DATABASE_USER", "postgres.uljsqvwkomdrlnofmlad"),
      password: database_password,
      database: "postgres",
      ssl: [verify: :verify_none],
      pool_size: String.to_integer(System.get_env("POOL_SIZE", "10")),
      socket_options: if(System.get_env("ECTO_IPV6") in ~w(true 1), do: [:inet6], else: [])
  end

  # ---------------------------------------------------------------------------
  # Phoenix Endpoint Configuration
  # ---------------------------------------------------------------------------

  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise """
      Environment variable SECRET_KEY_BASE is missing.
      Generate one with: mix phx.gen.secret
      """

  host = System.get_env("PHX_HOST", "localhost")
  port = String.to_integer(System.get_env("PORT", "4000"))

  config :server, ServerWeb.Endpoint,
    url: [host: host, port: 443, scheme: "https"],
    http: [ip: {0, 0, 0, 0, 0, 0, 0, 0}, port: port],
    secret_key_base: secret_key_base

  # ---------------------------------------------------------------------------
  # DNS Clustering (optional)
  # ---------------------------------------------------------------------------

  config :server, :dns_cluster_query, System.get_env("DNS_CLUSTER_QUERY")

  # ---------------------------------------------------------------------------
  # Supabase Edge Functions Configuration
  # ---------------------------------------------------------------------------
  #
  # SUPABASE_SERVICE_KEY is required to invoke edge functions
  # Get this from Supabase Dashboard > Project Settings > API > service_role key

  supabase_service_key =
    System.get_env("SUPABASE_SERVICE_KEY") ||
      raise """
      Environment variable SUPABASE_SERVICE_KEY is missing.
      Get this from Supabase Dashboard > Project Settings > API > service_role key
      """

  config :server, :supabase_service_key, supabase_service_key

  # ---------------------------------------------------------------------------
  # Email Configuration (Resend)
  # ---------------------------------------------------------------------------
  #
  # RESEND_API_KEY is required for sending data quality alerts
  # Get this from Resend Dashboard > API Keys

  if resend_api_key = System.get_env("RESEND_API_KEY") do
    config :server, Server.Mailer,
      adapter: Swoosh.Adapters.Resend,
      api_key: resend_api_key

    config :server, :email_enabled, true
    config :server, :email_from, System.get_env("EMAIL_FROM", "alerts@politiciantrading.app")
    config :server, :email_admin, System.get_env("EMAIL_ADMIN", "admin@politiciantrading.app")
  else
    # Email disabled if no API key
    config :server, Server.Mailer, adapter: Swoosh.Adapters.Local
    config :server, :email_enabled, false
  end
end

# =============================================================================
# API Key Authentication (All Environments)
# =============================================================================
#
# ETL_API_KEY - Required API key for authenticating to /api/* endpoints
# ETL_AUTH_DISABLED - Set to "true" to disable auth (development only)
#
# Same API key should be used for both Phoenix server and Python ETL service.

config :server, :api_key, System.get_env("ETL_API_KEY")
config :server, :auth_disabled, System.get_env("ETL_AUTH_DISABLED") == "true"

# =============================================================================
# Development & Test Configuration
# =============================================================================
#
# Load Supabase service key from env for non-prod environments too

if config_env() in [:dev, :test] do
  # Allow optional service key in dev/test (jobs will fail gracefully if missing)
  config :server, :supabase_service_key, System.get_env("SUPABASE_SERVICE_KEY")

  # Disable auth by default in test environment for easier testing
  if config_env() == :test do
    config :server, :auth_disabled, true
  end
end
