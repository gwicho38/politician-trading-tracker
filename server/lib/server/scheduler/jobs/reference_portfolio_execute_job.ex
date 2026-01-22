defmodule Server.Scheduler.Jobs.ReferencePortfolioExecuteJob do
  @moduledoc """
  Executes queued trading signals for the reference portfolio.

  Runs during market hours to process pending signals from the queue
  and execute trades via Alpaca. The reference portfolio automatically
  trades based on high-confidence ML-enhanced signals.

  Signal Queue Flow:
  1. TradingSignalsJob generates ML-enhanced signals every 6 hours
  2. High-confidence signals are queued in reference_portfolio_signal_queue
  3. This job executes pending signals during market hours
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "reference-portfolio-execute"

  # TODO: Review this function
  @impl true
  def job_name, do: "Reference Portfolio Signal Execution"

  @impl true
  # Run every 15 minutes during US market hours (14:30-21:00 UTC = 9:30 AM-4:00 PM EST)
  # Cron: minute 0,15,30,45 of hours 14-20 UTC, Monday-Friday
  # TODO: Review this function
  def schedule, do: "0,15,30,45 14-20 * * 1-5"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[ReferencePortfolioExecuteJob] Checking for pending signals to execute")

    # First check if market is open (edge function will also check, but we can skip early)
    if market_likely_open?() do
      execute_signals()
    else
      Logger.info("[ReferencePortfolioExecuteJob] Market appears closed, skipping execution")
      {:ok, 0}
    end
  end

  # TODO: Review this function
  defp execute_signals do
    case Server.SupabaseClient.invoke("reference-portfolio",
           body: %{"action" => "execute-signals"},
           timeout: 60_000
         ) do
      {:ok, %{"success" => true, "executed" => executed, "skipped" => skipped, "failed" => failed}} ->
        Logger.info(
          "[ReferencePortfolioExecuteJob] Execution complete: #{executed} executed, #{skipped} skipped, #{failed} failed"
        )

        {:ok, executed}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.info("[ReferencePortfolioExecuteJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[ReferencePortfolioExecuteJob] Execution failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[ReferencePortfolioExecuteJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # Quick check if we're likely in market hours (UTC-based)
  # This is approximate - the edge function does the authoritative check
  # TODO: Review this function
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
      description: "Executes queued ML-enhanced trading signals for the reference portfolio",
      edge_function: "reference-portfolio",
      action: "execute-signals",
      schedule_note: "Runs every 15 minutes during US market hours (9:30 AM - 4:00 PM EST)"
    }
  end
end
