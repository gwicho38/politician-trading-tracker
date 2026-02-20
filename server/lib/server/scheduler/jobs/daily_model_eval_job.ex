defmodule Server.Scheduler.Jobs.DailyModelEvalJob do
  @moduledoc """
  Evaluates ML model performance daily after market close.

  Runs after SignalOutcomeJob (23:00 UTC) records new outcomes.
  Computes win rate, Sharpe ratio, benchmark alpha, and auto-adjusts
  the ML blend weight based on ML vs heuristic performance delta.

  This replaces the monthly-only eval in ModelFeedbackRetrainJob,
  giving continuous visibility into model quality and faster
  blend weight adaptation.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "daily-model-eval"

  @impl true
  def job_name, do: "Daily Model Evaluation"

  @impl true
  # Run daily at 23:30 UTC (30 min after SignalOutcomeJob records outcomes)
  def schedule, do: "30 23 * * *"

  @impl true
  def run do
    Logger.info("[DailyModelEvalJob] Starting daily model evaluation")

    case Server.SupabaseClient.invoke("signal-feedback",
           body: %{"action" => "evaluate-model", "windowDays" => 7},
           timeout: 60_000
         ) do
      {:ok, %{"success" => true, "performance" => perf} = result} ->
        Logger.info(
          "[DailyModelEvalJob] 7-day eval: win_rate=#{perf["win_rate"]}, " <>
            "sharpe=#{perf["sharpe_ratio"]}, avg_return=#{perf["avg_return_pct"]}%"
        )

        if result["weightAdjustment"] do
          adj = result["weightAdjustment"]

          Logger.info(
            "[DailyModelEvalJob] Blend weight adjusted: #{adj["oldWeight"]} -> #{adj["newWeight"]} " <>
              "(ML vs heuristic delta: #{adj["winRateDiff"]})"
          )
        end

        # Check if model needs retraining based on performance degradation
        win_rate = perf["win_rate"] || 0
        sharpe = perf["sharpe_ratio"] || 0

        cond do
          win_rate < 0.05 and sharpe < -1.0 ->
            Logger.warn(
              "[DailyModelEvalJob] Model performance critically degraded " <>
                "(win_rate=#{win_rate}, sharpe=#{sharpe}). Consider emergency retraining."
            )

          win_rate < 0.10 ->
            Logger.warn(
              "[DailyModelEvalJob] Model win rate below 10% threshold (#{win_rate})"
            )

          true ->
            :ok
        end

        {:ok, 1}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.info("[DailyModelEvalJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[DailyModelEvalJob] Failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[DailyModelEvalJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Evaluates model performance daily and adjusts ML blend weight",
      edge_function: "signal-feedback",
      action: "evaluate-model",
      schedule_note: "Runs daily at 23:30 UTC (after outcomes are recorded at 23:00)"
    }
  end
end
