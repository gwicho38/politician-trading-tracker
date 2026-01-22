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

  require Logger

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

      # Data quality digest store (accumulates issues for daily digest)
      Server.DataQuality.DigestStore,

      # Phoenix HTTP endpoint (must be last)
      ServerWeb.Endpoint
    ]

    opts = [strategy: :one_for_one, name: Server.Supervisor]
    result = Supervisor.start_link(children, opts)

    # Register scheduled jobs after supervisor starts (skip in test mode)
    unless Application.get_env(:server, :skip_job_registration, false) do
      register_jobs()
    end

    result
  end

  defp register_jobs do
    jobs = [
      # Core sync jobs
      Server.Scheduler.Jobs.SyncJob,
      Server.Scheduler.Jobs.SyncDataJob,
      Server.Scheduler.Jobs.TradingSignalsJob,
      # Alpaca trading jobs
      Server.Scheduler.Jobs.AlpacaAccountJob,
      Server.Scheduler.Jobs.OrdersJob,
      Server.Scheduler.Jobs.PortfolioJob,
      Server.Scheduler.Jobs.PortfolioSnapshotJob,
      # Reference portfolio automation
      Server.Scheduler.Jobs.ReferencePortfolioExecuteJob,
      Server.Scheduler.Jobs.ReferencePortfolioExitCheckJob,
      Server.Scheduler.Jobs.ReferencePortfolioSyncJob,
      Server.Scheduler.Jobs.ReferencePortfolioDailyResetJob,
      # Politician trading collection (split by source to avoid timeouts)
      Server.Scheduler.Jobs.PoliticianTradingHouseJob,
      Server.Scheduler.Jobs.PoliticianTradingSenateJob,
      Server.Scheduler.Jobs.PoliticianTradingQuiverJob,
      Server.Scheduler.Jobs.PoliticianTradingEuJob,
      Server.Scheduler.Jobs.PoliticianTradingCaliforniaJob,
      # Data quality jobs
      Server.Scheduler.Jobs.TickerBackfillJob,
      # Party enrichment (Ollama LLM)
      Server.Scheduler.Jobs.PartyEnrichmentJob,
      # BioGuide ID enrichment (Congress.gov API)
      Server.Scheduler.Jobs.BioguideEnrichmentJob,
      # ML model training jobs
      Server.Scheduler.Jobs.MlTrainingJob,
      Server.Scheduler.Jobs.BatchRetrainingJob,
      # ML feedback loop jobs (outcomes → feature analysis → retraining)
      Server.Scheduler.Jobs.SignalOutcomeJob,
      Server.Scheduler.Jobs.FeatureAnalysisJob,
      Server.Scheduler.Jobs.ModelFeedbackRetrainJob,
      # Data quality monitoring jobs
      Server.Scheduler.Jobs.DataQualityTier1Job,
      Server.Scheduler.Jobs.DataQualityTier2Job,
      Server.Scheduler.Jobs.DataQualityTier3Job,
      Server.Scheduler.Jobs.EmailDigestJob,
      # User feedback processing
      Server.Scheduler.Jobs.ErrorReportsJob,
      # Data cleanup
      Server.Scheduler.Jobs.PoliticianDedupJob,
      Server.Scheduler.Jobs.JobExecutionCleanupJob
    ]

    Enum.each(jobs, fn job_module ->
      case Server.Scheduler.register_job(job_module) do
        {:ok, _} ->
          Logger.info("Registered job: #{job_module.job_name()}")

        {:error, reason} ->
          Logger.warning("Failed to register job #{job_module.job_name()}: #{inspect(reason)}")
      end
    end)
  end

  @impl true
  def config_change(changed, _new, removed) do
    ServerWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
