defmodule Server.Scheduler.Jobs.PoliticianTradingEuJob do
  @moduledoc """
  Collects EU Parliament declarations.

  Lightweight job that collects from a single source to avoid timeouts.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "politician-trading-eu"

  # TODO: Review this function
  @impl true
  def job_name, do: "EU Parliament Declarations"

  # TODO: Review this function
  @impl true
  # Every minute (testing) - production: every 6 hours
  def schedule, do: "* * * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PoliticianTradingEuJob] Starting EU Parliament collection")

    case Server.SupabaseClient.invoke("politician-trading-collect",
           query: %{source: "eu"},
           timeout: 60_000
         ) do
      {:ok, response} ->
        count = get_in(response, ["data", "disclosures_found"]) || 0
        Logger.info("[PoliticianTradingEuJob] Collection completed, disclosures: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[PoliticianTradingEuJob] Collection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Collects EU Parliament financial declarations",
      edge_function: "politician-trading-collect",
      source: "eu"
    }
  end
end
