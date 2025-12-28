defmodule Server.Application do
  @moduledoc """
  OTP Application specification for the Politician Trading Tracker server.

  Starts the following supervision tree:
  - `Server.Repo` - Ecto repository for Supabase PostgreSQL
  - `ServerWeb.Telemetry` - Telemetry metrics
  - `Phoenix.PubSub` - PubSub for real-time features
  - `Finch` - HTTP client pool
  - `Server.Scheduler.Quantum` - Cron job scheduler
  - `ServerWeb.Endpoint` - Phoenix HTTP endpoint
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Telemetry (metrics collection)
      ServerWeb.Telemetry,

      # Database connection to Supabase PostgreSQL
      Server.Repo,

      # PubSub for real-time features
      {Phoenix.PubSub, name: Server.PubSub},

      # HTTP client pool
      {Finch, name: Server.Finch},

      # DNS-based clustering (for distributed deployments)
      {DNSCluster, query: Application.get_env(:server, :dns_cluster_query) || :ignore},

      # Cron job scheduler (starts empty, jobs registered via API)
      Server.Scheduler.Quantum,

      # Phoenix HTTP endpoint (must be last)
      ServerWeb.Endpoint
    ]

    opts = [strategy: :one_for_one, name: Server.Supervisor]
    result = Supervisor.start_link(children, opts)

    # Register scheduled jobs after supervisor starts
    register_jobs()

    result
  end

  defp register_jobs do
    Server.Scheduler.register_job(Server.Scheduler.Jobs.SyncJob)
  end

  @impl true
  def config_change(changed, _new, removed) do
    ServerWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
