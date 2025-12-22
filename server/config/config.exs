# This file is responsible for configuring your application
# and its dependencies with the aid of the Config module.
#
# This configuration file is loaded before any dependency and
# is restricted to this project.

# General application configuration
import Config

config :server,
  ecto_repos: [Server.Repo, Server.JobsRepo],
  generators: [timestamp_type: :utc_datetime, binary_id: true]

# =============================================================================
# Supabase Database Configuration
# =============================================================================
#
# Connection to Supabase Postgres database
# Project: uljsqvwkomdrlnofmlad
# Region: eu-north-1
#
# The database URL should be set via environment variable DATABASE_URL
# Format: postgres://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Main Repo - connects to public schema
config :server, Server.Repo,
  database: "postgres",
  hostname: "aws-0-eu-north-1.pooler.supabase.com",
  port: 6543,
  username: "postgres.uljsqvwkomdrlnofmlad",
  # Password should be set via DATABASE_PASSWORD env var in runtime.exs
  pool_size: 10,
  ssl: true,
  ssl_opts: [
    verify: :verify_none
  ],
  # Use transaction mode for connection pooling (Supavisor)
  prepare: :unnamed,
  parameters: [
    application_name: "politician_trading_server"
  ]

# Jobs Repo - connects to jobs schema for scheduled job management
config :server, Server.JobsRepo,
  database: "postgres",
  hostname: "aws-0-eu-north-1.pooler.supabase.com",
  port: 6543,
  username: "postgres.uljsqvwkomdrlnofmlad",
  pool_size: 5,
  ssl: true,
  ssl_opts: [
    verify: :verify_none
  ],
  prepare: :unnamed,
  # Use the jobs schema prefix for all queries
  after_connect: {Postgrex, :query!, ["SET search_path TO jobs, public", []]},
  parameters: [
    application_name: "politician_trading_jobs"
  ]

# =============================================================================
# Oban Job Processing (optional - for background jobs)
# =============================================================================
#
# If you want to use Oban for job scheduling instead of pg_cron:
# config :server, Oban,
#   repo: Server.JobsRepo,
#   plugins: [
#     {Oban.Plugins.Pruner, max_age: 60 * 60 * 24 * 7},  # 7 days
#     {Oban.Plugins.Cron,
#       crontab: [
#         {"0 */4 * * *", Server.Jobs.ScheduledSync},      # Every 4 hours
#         {"30 */4 * * *", Server.Jobs.SignalGeneration},  # Every 4 hours at :30
#         {"0 * * * *", Server.Jobs.UpdateStats}           # Hourly
#       ]}
#   ],
#   queues: [default: 10, scheduled: 5]

# Configures the endpoint
config :server, ServerWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [
    formats: [json: ServerWeb.ErrorJSON],
    layout: false
  ],
  pubsub_server: Server.PubSub,
  live_view: [signing_salt: "AHAjt8QT"]

# Configures the mailer
#
# By default it uses the "Local" adapter which stores the emails
# locally. You can see the emails in your browser, at "/dev/mailbox".
#
# For production it's recommended to configure a different adapter
# at the `config/runtime.exs`.
config :server, Server.Mailer, adapter: Swoosh.Adapters.Local

# Configure esbuild (the version is required)
config :esbuild,
  version: "0.17.11",
  server: [
    args:
      ~w(js/app.js --bundle --target=es2017 --outdir=../priv/static/assets --external:/fonts/* --external:/images/*),
    cd: Path.expand("../assets", __DIR__),
    env: %{"NODE_PATH" => Path.expand("../deps", __DIR__)}
  ]

# Configure tailwind (the version is required)
config :tailwind,
  version: "3.4.3",
  server: [
    args: ~w(
      --config=tailwind.config.js
      --input=css/app.css
      --output=../priv/static/assets/app.css
    ),
    cd: Path.expand("../assets", __DIR__)
  ]

# Configures Elixir's Logger
config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

# Use Jason for JSON parsing in Phoenix
config :phoenix, :json_library, Jason

# Import environment specific config. This must remain at the bottom
# of this file so it overrides the configuration defined above.
import_config "#{config_env()}.exs"
