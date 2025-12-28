defmodule Server.Scheduler.Jobs.PoliticianTradingSenateJob do
  @moduledoc """
  Collects US Senate financial disclosures.

  Lightweight job that collects from a single source to avoid timeouts.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "politician-trading-senate"

  @impl true
  def job_name, do: "US Senate Disclosures"

  @impl true
  # Every minute (testing) - production: every 6 hours
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[PoliticianTradingSenateJob] Starting US Senate collection")

    case Server.SupabaseClient.invoke("politician-trading-collect",
           query: %{source: "senate"},
           timeout: 60_000
         ) do
      {:ok, response} ->
        count = get_in(response, ["data", "disclosures_found"]) || 0
        Logger.info("[PoliticianTradingSenateJob] Collection completed, disclosures: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[PoliticianTradingSenateJob] Collection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Collects US Senate financial disclosures",
      edge_function: "politician-trading-collect",
      source: "senate"
    }
  end
end
