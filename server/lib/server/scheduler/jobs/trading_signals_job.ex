defmodule Server.Scheduler.Jobs.TradingSignalsJob do
  @moduledoc """
  Generates trading signals from politician trades.

  Invokes the trading-signals edge function to analyze politician
  trading patterns and generate actionable trading signals.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "trading-signals"

  @impl true
  def job_name, do: "Trading Signals Generation"

  @impl true
  # Every 6 hours (0:00, 6:00, 12:00, 18:00 UTC)
  def schedule, do: "0 */6 * * *"

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
      description: "Generates trading signals from politician trading patterns",
      edge_function: "trading-signals"
    }
  end
end
