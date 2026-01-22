defmodule Server.Scheduler.Jobs.ReferencePortfolioExitCheckJob do
  @moduledoc """
  Monitors open positions for stop-loss and take-profit triggers.

  Runs during market hours to check if any positions have hit their
  stop-loss or take-profit price levels. When triggered, automatically
  places sell orders to close the position.

  Exit Conditions:
  - Stop Loss: current_price <= stop_loss_price (default 5% below entry)
  - Take Profit: current_price >= take_profit_price (default 15% above entry)
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "reference-portfolio-exit-check"

  # TODO: Review this function
  @impl true
  def job_name, do: "Reference Portfolio Exit Check"

  @impl true
  # Run every 5 minutes during US market hours (14:30-21:00 UTC = 9:30 AM-4:00 PM EST)
  # Cron: every 5 minutes (0,5,10,...,55) of hours 14-20 UTC, Monday-Friday
  # TODO: Review this function
  def schedule, do: "*/5 14-20 * * 1-5"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[ReferencePortfolioExitCheckJob] Checking positions for exit triggers")

    # First check if market is open
    if market_likely_open?() do
      check_exits()
    else
      Logger.info("[ReferencePortfolioExitCheckJob] Market appears closed, skipping check")
      {:ok, 0}
    end
  end

  # TODO: Review this function
  defp check_exits do
    case Server.SupabaseClient.invoke("reference-portfolio",
           body: %{"action" => "check-exits"},
           timeout: 120_000
         ) do
      {:ok, %{"success" => true, "closed" => closed, "summary" => summary}} ->
        wins = summary["wins"] || 0
        losses = summary["losses"] || 0

        if closed > 0 do
          Logger.info(
            "[ReferencePortfolioExitCheckJob] Closed #{closed} positions (#{wins} wins, #{losses} losses)"
          )
        else
          Logger.debug("[ReferencePortfolioExitCheckJob] No exit triggers found")
        end

        {:ok, closed}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.debug("[ReferencePortfolioExitCheckJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[ReferencePortfolioExitCheckJob] Exit check failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[ReferencePortfolioExitCheckJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  # Quick check if we're likely in market hours (UTC-based)
  defp market_likely_open? do
    now = DateTime.utc_now()
    day_of_week = Date.day_of_week(DateTime.to_date(now))
    hour = now.hour

    # Weekday (Monday=1 to Friday=5) and between 14:00-21:00 UTC
    day_of_week >= 1 and day_of_week <= 5 and hour >= 14 and hour < 21
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Monitors positions for stop-loss and take-profit triggers, closes positions when hit",
      edge_function: "reference-portfolio",
      action: "check-exits",
      schedule_note: "Runs every 5 minutes during US market hours (9:30 AM - 4:00 PM EST)"
    }
  end
end
