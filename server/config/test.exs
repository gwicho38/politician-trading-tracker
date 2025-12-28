# =============================================================================
# Test Configuration
# =============================================================================

import Config

# =============================================================================
# Database Configuration
# =============================================================================
#
# Uses local PostgreSQL with sandbox pool for test isolation.
# MIX_TEST_PARTITION allows parallel test execution in CI.

config :server, Server.Repo,
  username: "postgres",
  password: "postgres",
  hostname: "localhost",
  database: "server_test#{System.get_env("MIX_TEST_PARTITION")}",
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: System.schedulers_online() * 2

# =============================================================================
# Phoenix Endpoint Configuration
# =============================================================================

config :server, ServerWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: "bqp2cMPE7TrN0Tqg0NMw3a83rgjI10Si4PNJTvFcYwSIY/HbD+kzHsbbGSIYOIx1",
  server: false

# =============================================================================
# Test Settings
# =============================================================================

# Only log warnings and errors during tests
config :logger, level: :warning

# Runtime plug initialization for faster test compilation
config :phoenix, :plug_init_mode, :runtime
