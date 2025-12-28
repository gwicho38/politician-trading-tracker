defmodule Server do
  @moduledoc """
  Politician Trading Tracker Server

  A minimal Phoenix API server that connects to Supabase PostgreSQL for
  tracking politician stock trading disclosures.

  ## Architecture

  ```
  ┌─────────────────────────────────────────────────────────────┐
  │                    Server Application                        │
  ├─────────────────────────────────────────────────────────────┤
  │  ServerWeb.Endpoint    │  HTTP API (port 4000)              │
  │  Server.Repo           │  Ecto PostgreSQL (Supabase)        │
  │  Phoenix.PubSub        │  Real-time messaging               │
  │  Finch                 │  HTTP client for external APIs     │
  └─────────────────────────────────────────────────────────────┘
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              Supabase PostgreSQL Database                    │
  │  Host: db.uljsqvwkomdrlnofmlad.supabase.co                  │
  │  Port: 5432                                                  │
  └─────────────────────────────────────────────────────────────┘
  ```

  ## Quick Start

      # Start the server
      mix phx.server

      # Or in IEx
      iex -S mix phx.server

  ## Database Access

      # Query the database
      Server.Repo.query("SELECT current_timestamp")

      # List tables
      Server.Repo.query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

  ## Project Structure

  ```
  server/
  ├── config/
  │   ├── config.exs     # Base configuration
  │   ├── dev.exs        # Development (Supabase direct connection)
  │   ├── test.exs       # Test (local PostgreSQL)
  │   └── runtime.exs    # Production (environment variables)
  ├── lib/
  │   ├── server/
  │   │   ├── application.ex  # OTP Application
  │   │   └── repo.ex         # Ecto Repository
  │   ├── server.ex           # This module
  │   └── server_web/
  │       ├── endpoint.ex     # Phoenix Endpoint
  │       ├── router.ex       # HTTP Routes
  │       └── controllers/    # API Controllers
  └── priv/
      └── repo/
          └── migrations/     # Database migrations
  ```

  ## Configuration

  | Environment | Database | Configuration |
  |-------------|----------|---------------|
  | Development | Supabase hosted | `config/dev.exs` |
  | Test | Local PostgreSQL | `config/test.exs` |
  | Production | Supabase via env vars | `config/runtime.exs` |
  """

  @doc """
  Returns the current application version.
  """
  def version, do: "0.1.0"

  @doc """
  Checks if the database connection is healthy.

  ## Examples

      iex> Server.health_check()
      :ok

      iex> Server.health_check()
      {:error, "Connection refused"}
  """
  def health_check do
    case Server.Repo.query("SELECT 1") do
      {:ok, _result} -> :ok
      {:error, error} -> {:error, Exception.message(error)}
    end
  end
end
