defmodule Server.Scheduler.Jobs.PortfolioSnapshotJob do
  @moduledoc """
  Takes daily snapshots of the reference portfolio performance.

  Runs after market close to record the portfolio value, returns,
  and other metrics for the performance chart. Creates one snapshot
  per day that tracks portfolio value over time.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "portfolio-snapshot"

  # TODO: Review this function
  @impl true
  def job_name, do: "Portfolio Daily Snapshot"

  # TODO: Review this function
  @impl true
  # Run at 10:30 PM UTC (5:30 PM EST) - after market close
  def schedule, do: "30 22 * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PortfolioSnapshotJob] Taking daily portfolio snapshot")

    case Server.SupabaseClient.invoke("reference-portfolio",
           body: %{"action" => "take-snapshot"},
           timeout: 30_000
         ) do
      {:ok, %{"success" => true, "snapshot" => snapshot}} ->
        date = snapshot["date"]
        value = snapshot["portfolio_value"]
        return_pct = snapshot["cumulative_return_pct"]

        Logger.info(
          "[PortfolioSnapshotJob] Snapshot saved: date=#{date}, value=$#{value}, return=#{return_pct}%"
        )

        {:ok, 1}

      {:ok, %{"error" => error}} ->
        Logger.error("[PortfolioSnapshotJob] Snapshot failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[PortfolioSnapshotJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Records daily portfolio value snapshots for performance tracking",
      edge_function: "reference-portfolio",
      action: "take-snapshot",
      schedule_note: "Runs at 5:30 PM EST (after market close)"
    }
  end
end
