defmodule Server.Scheduler.Jobs.PoliticianTradingCaliforniaJob do
  @moduledoc """
  Collects California NetFile disclosures.

  Lightweight job that collects from a single source to avoid timeouts.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "politician-trading-california"

  # TODO: Review this function
  @impl true
  def job_name, do: "California NetFile Disclosures"

  # TODO: Review this function
  @impl true
  # Every minute (testing) - production: every 6 hours
  def schedule, do: "* * * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PoliticianTradingCaliforniaJob] Starting California collection")

    # California NetFile sites are slow - use 90s timeout
    case Server.SupabaseClient.invoke("politician-trading-collect",
           query: %{source: "california"},
           timeout: 90_000
         ) do
      {:ok, response} ->
        count = get_in(response, ["data", "disclosures_found"]) || 0
        Logger.info("[PoliticianTradingCaliforniaJob] Collection completed, disclosures: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[PoliticianTradingCaliforniaJob] Collection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Collects California NetFile financial disclosures",
      edge_function: "politician-trading-collect",
      source: "california"
    }
  end
end
