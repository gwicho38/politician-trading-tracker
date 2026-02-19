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

  # TODO: Review this function
  @impl true
  def job_id, do: "trading-signals"

  # TODO: Review this function
  @impl true
  def job_name, do: "Trading Signals Generation"

  @impl true
  # Hourly during extended hours: 09:00-00:00 UTC (~4 AM - 7 PM ET), Monday-Friday
  # This ensures fresh ML-enhanced signals for pre-market, regular, and post-market sessions
  # TODO: Review this function
  def schedule, do: "0 9-23,0 * * 1-5"

  # TODO: Review this function
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

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Generates ML-enhanced trading signals from politician trading patterns",
      edge_function: "trading-signals",
      schedule_note: "Runs hourly during extended hours (4 AM - 8 PM ET, Mon-Fri)"
    }
  end
end
