defmodule Server.Scheduler.Jobs.PoliticianTradingCollectJob do
  @moduledoc """
  Collects politician trading disclosures.

  Invokes the politician-trading-collect edge function to scrape
  and store new trading disclosures from government sources.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "politician-trading-collect"

  @impl true
  def job_name, do: "Politician Trading Collection"

  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[PoliticianTradingCollectJob] Starting collection")

    # Web scraping takes time, use 120s timeout
    case Server.SupabaseClient.invoke("politician-trading-collect", timeout: 120_000) do
      {:ok, response} ->
        count = get_in(response, ["collected"]) || get_in(response, ["count"]) || 0
        Logger.info("[PoliticianTradingCollectJob] Collection completed, new records: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[PoliticianTradingCollectJob] Collection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Collects politician trading disclosures from government sources",
      edge_function: "politician-trading-collect"
    }
  end
end
