defmodule Server.Scheduler.Jobs.TradingSignalsJob do
  @moduledoc """
  Generates trading signals from politician trades.

  Invokes the trading-signals edge function to analyze politician
  trading patterns and generate ML-enhanced actionable trading signals.

  Runs hourly during US market hours to keep signals fresh for
  the reference portfolio execution job.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "trading-signals"

  @impl true
  def job_name, do: "Trading Signals Generation"

  @impl true
  # Hourly during market hours: 14:00-20:00 UTC (9 AM - 3 PM EST), Monday-Friday
  # This ensures fresh ML-enhanced signals for each trading window
  def schedule, do: "0 14-20 * * 1-5"

  @impl true
  def run do
    Logger.info("[TradingSignalsJob] Starting signal regeneration")

    # Call regenerate-signals endpoint (service-level, clears old and generates fresh)
    case Server.SupabaseClient.invoke("trading-signals",
           path: "regenerate-signals",
           body: %{lookbackDays: 90, minConfidence: 0.60, clearOld: true},
           timeout: 120_000
         ) do
      {:ok, response} ->
        signals = get_in(response, ["signals"]) || []
        count = length(signals)
        stats = get_in(response, ["stats"]) || %{}

        Logger.info(
          "[TradingSignalsJob] Signal regeneration completed: #{count} signals from #{stats["totalDisclosures"] || 0} disclosures"
        )

        {:ok, count}

      {:error, reason} ->
        Logger.error("[TradingSignalsJob] Signal regeneration failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Generates ML-enhanced trading signals from politician trading patterns",
      edge_function: "trading-signals",
      schedule_note: "Runs hourly during market hours (9 AM - 3 PM EST, Mon-Fri)"
    }
  end
end
