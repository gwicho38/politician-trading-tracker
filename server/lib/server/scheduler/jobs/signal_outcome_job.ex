defmodule Server.Scheduler.Jobs.SignalOutcomeJob do
  @moduledoc """
  Records trading outcomes for closed positions.

  This job closes the feedback loop by:
  1. Finding closed positions from the reference portfolio
  2. Calculating win/loss outcomes and returns
  3. Extracting features from the original signals
  4. Storing outcomes for model retraining analysis

  Runs daily after market close to capture the day's closed positions.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "signal-outcomes"

  @impl true
  def job_name, do: "Signal Outcome Recording"

  @impl true
  # Run daily at 11 PM UTC (6 PM EST) - after market close
  def schedule, do: "0 23 * * *"

  @impl true
  def run do
    Logger.info("[SignalOutcomeJob] Recording signal outcomes for closed positions")

    case Server.SupabaseClient.invoke("signal-feedback",
           body: %{"action" => "record-outcomes"},
           timeout: 60_000
         ) do
      {:ok, %{"success" => true, "recorded" => recorded, "summary" => summary}} ->
        Logger.info(
          "[SignalOutcomeJob] Outcomes recorded: #{recorded} (wins: #{summary["wins"]}, losses: #{summary["losses"]}, win rate: #{summary["winRate"]}%)"
        )

        {:ok, recorded}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.info("[SignalOutcomeJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[SignalOutcomeJob] Failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[SignalOutcomeJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Records trading outcomes for closed positions to enable model feedback",
      edge_function: "signal-feedback",
      action: "record-outcomes",
      schedule_note: "Runs daily at 6 PM EST (after market close)"
    }
  end
end
