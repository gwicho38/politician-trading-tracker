defmodule Server.Scheduler.Jobs.ReferencePortfolioSyncJob do
  @moduledoc """
  Syncs reference portfolio positions with current Alpaca prices.

  Runs during market hours to update position prices, market values,
  unrealized P&L, and day return calculations. This ensures the
  reference portfolio dashboard shows real-time data.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "reference-portfolio-sync"

  # TODO: Review this function
  @impl true
  def job_name, do: "Reference Portfolio Position Sync"

  @impl true
  # Run every minute during extended market hours (09:00-00:00 UTC = ~4 AM-7 PM ET)
  # Cron: every minute, hours 9-23 and 0, Monday-Friday
  # TODO: Review this function
  def schedule, do: "* 9-23,0 * * 1-5"

  # TODO: Review this function
  @impl true
  def run do
    Logger.debug("[ReferencePortfolioSyncJob] Syncing reference portfolio positions")

    if market_likely_open?() do
      sync_positions()
    else
      Logger.debug("[ReferencePortfolioSyncJob] Market appears closed, skipping sync")
      {:ok, 0}
    end
  end

  # TODO: Review this function
  defp sync_positions do
    case Server.SupabaseClient.invoke("reference-portfolio",
           body: %{"action" => "update-positions"},
           timeout: 30_000
         ) do
      {:ok, %{"success" => true, "summary" => summary}} ->
        updated = summary["updated"] || 0
        positions = summary["openPositionsCount"] || 0

        if updated > 0 do
          Logger.info(
            "[ReferencePortfolioSyncJob] Synced #{updated} positions (#{positions} open)"
          )
        end

        {:ok, updated}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.debug("[ReferencePortfolioSyncJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[ReferencePortfolioSyncJob] Sync failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[ReferencePortfolioSyncJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  # Quick check if we're likely in extended market hours (UTC-based)
  defp market_likely_open? do
    now = DateTime.utc_now()
    day_of_week = Date.day_of_week(DateTime.to_date(now))
    hour = now.hour

    # Weekday (Monday=1 to Friday=5) and between 09:00-00:00 UTC (covers pre/post market)
    day_of_week >= 1 and day_of_week <= 5 and (hour >= 9 or hour == 0)
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Syncs reference portfolio positions with current Alpaca prices",
      edge_function: "reference-portfolio",
      action: "update-positions",
      schedule_note: "Runs every minute during extended hours (4 AM - 8 PM ET, Mon-Fri)"
    }
  end
end
