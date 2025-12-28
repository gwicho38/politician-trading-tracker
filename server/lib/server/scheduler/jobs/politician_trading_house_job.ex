defmodule Server.Scheduler.Jobs.PoliticianTradingHouseJob do
  @moduledoc """
  Collects US House financial disclosures.

  Lightweight job that collects from a single source to avoid timeouts.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "politician-trading-house"

  @impl true
  def job_name, do: "US House Disclosures"

  @impl true
  # Every minute (testing) - production: every 6 hours
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[PoliticianTradingHouseJob] Starting US House collection")

    case Server.SupabaseClient.invoke("politician-trading-collect",
           query: %{source: "house"},
           timeout: 60_000
         ) do
      {:ok, response} ->
        count = get_in(response, ["data", "disclosures_found"]) || 0
        Logger.info("[PoliticianTradingHouseJob] Collection completed, disclosures: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[PoliticianTradingHouseJob] Collection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Collects US House financial disclosures",
      edge_function: "politician-trading-collect",
      source: "house"
    }
  end
end
