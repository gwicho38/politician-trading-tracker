defmodule Server.Scheduler.Jobs.PoliticianTradingQuiverJob do
  @moduledoc """
  Collects QuiverQuant congress trading data.

  Lightweight job that collects from a single source to avoid timeouts.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "politician-trading-quiver"

  @impl true
  def job_name, do: "QuiverQuant Congress Trading"

  @impl true
  # Every minute (testing) - production: every 6 hours
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[PoliticianTradingQuiverJob] Starting QuiverQuant collection")

    case Server.SupabaseClient.invoke("politician-trading-collect",
           query: %{source: "quiver"},
           timeout: 60_000
         ) do
      {:ok, response} ->
        count = get_in(response, ["data", "disclosures_found"]) || 0
        Logger.info("[PoliticianTradingQuiverJob] Collection completed, disclosures: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[PoliticianTradingQuiverJob] Collection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Collects QuiverQuant congress trading data",
      edge_function: "politician-trading-collect",
      source: "quiver"
    }
  end
end
