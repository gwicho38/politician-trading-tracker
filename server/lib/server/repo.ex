defmodule Server.Repo do
  @moduledoc """
  Ecto repository for Supabase PostgreSQL database.

  ## Configuration

  The repository connects to Supabase's hosted PostgreSQL. Configuration is
  loaded from:
  - `config/dev.exs` - Development (direct credentials)
  - `config/runtime.exs` - Production (environment variables)

  ## Usage Examples

      # Raw SQL query
      Server.Repo.query("SELECT current_timestamp")

      # Check database connection
      Server.Repo.query("SELECT 1")

      # List all tables in public schema
      Server.Repo.query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

  ## Environment Variables (Production)

  - `DATABASE_URL` - Full connection string (overrides individual vars)
  - `DATABASE_PASSWORD` - Required if DATABASE_URL not set
  - `DATABASE_HOST` - Defaults to db.uljsqvwkomdrlnofmlad.supabase.co
  - `DATABASE_PORT` - Defaults to 5432
  - `POOL_SIZE` - Defaults to 10
  """

  use Ecto.Repo,
    otp_app: :server,
    adapter: Ecto.Adapters.Postgres
end
