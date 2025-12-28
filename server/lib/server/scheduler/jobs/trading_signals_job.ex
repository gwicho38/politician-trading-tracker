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
  # Every minute (testing)
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[TradingSignalsJob] Starting signal generation")

    # trading-signals uses path-based routing, call get-signals endpoint (public read)
    case Server.SupabaseClient.invoke("trading-signals", path: "get-signals", timeout: 60_000) do
      {:ok, response} ->
        signals = get_in(response, ["signals"]) || []
        count = length(signals)
        Logger.info("[TradingSignalsJob] Signal fetch completed, signals: #{count}")
        {:ok, count}

      {:error, reason} ->
        Logger.error("[TradingSignalsJob] Signal generation failed: #{inspect(reason)}")
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
