# =============================================================================
# Development Configuration
# =============================================================================

import Config

# =============================================================================
# Database Configuration - Supabase PostgreSQL
# =============================================================================
#
# Supabase Project: uljsqvwkomdrlnofmlad
#
# CONNECTION OPTIONS:
#
# Option 1: Via Pooler (recommended for external connections)
#   Host: aws-1-eu-north-1.pooler.supabase.com
#   Port: 6543
#   Username: postgres.uljsqvwkomdrlnofmlad
#
# Option 2: Direct connection (may have network restrictions)
#   Host: db.uljsqvwkomdrlnofmlad.supabase.co
#   Port: 5432
#   Username: postgres
#
# Get your password from Supabase Dashboard:
#   Project Settings > Database > Database password

# Using pooler connection for better connectivity
config :server, Server.Repo,
  hostname: "aws-1-eu-north-1.pooler.supabase.com",
  port: 6543,
  username: "postgres.uljsqvwkomdrlnofmlad",
  password: System.get_env("DATABASE_PASSWORD", "servicetoanothertoast"),
  database: "postgres",
  ssl: [verify: :verify_none],
  pool_size: 10,
  # Required for Supabase pgbouncer in transaction mode
  prepare: :unnamed,
  stacktrace: true,
  show_sensitive_data_on_connection_error: true

# =============================================================================
# Phoenix Endpoint Configuration
# =============================================================================

config :server, ServerWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4000],
  check_origin: false,
  code_reloader: true,
  debug_errors: true,
  secret_key_base: "Hr8rKs6uda9rTug0oLeK4ZzdpV/gge3ada1ON7dn8vSQqoxahKaJeOp0cgdAZGrk",
  watchers: []

# =============================================================================
# Development Settings
# =============================================================================

# Enable dev routes (health checks, debug endpoints)
config :server, dev_routes: true

# Simplified log format for development
config :logger, :console, format: "[$level] $message\n"

# Higher stacktrace depth for debugging
config :phoenix, :stacktrace_depth, 20

# Runtime plug initialization for faster compilation
config :phoenix, :plug_init_mode, :runtime
