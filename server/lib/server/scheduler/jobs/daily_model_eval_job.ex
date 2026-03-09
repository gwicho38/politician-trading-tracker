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
          win_rate > 0 and win_rate < 0.05 and sharpe < -1.0 ->
            Logger.error(
              "[DailyModelEvalJob] CRITICAL: win_rate=#{win_rate}, sharpe=#{sharpe}. " <>
                "Triggering emergency retrain."
            )

            trigger_emergency_retrain()

          needs_retrain?(%{"win_rate" => win_rate}) ->
            Logger.warning(
              "[DailyModelEvalJob] Win rate #{Float.round(win_rate * 100, 1)}% below 35% threshold. " <>
                "Triggering scheduled retrain."
            )

            trigger_emergency_retrain()

          true ->
            Logger.info(
              "[DailyModelEvalJob] Model performance acceptable (win_rate=#{Float.round((win_rate || 0) * 100, 1)}%)"
            )

            :ok
        end

        # Check challenger model promotion regardless of retrain outcome
        check_challenger_promotion()

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

  @doc """
  Returns true if model performance is below the 35% win rate threshold
  and should trigger retraining.
  """
  def needs_retrain?(perf) do
    win_rate = perf["win_rate"] || 0
    win_rate > 0 and win_rate < 0.35
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

  defp check_challenger_promotion do
    Logger.info("[DailyModelEvalJob] Checking challenger model promotion eligibility")

    case Server.SupabaseClient.invoke("signal-feedback",
           body: %{"action" => "check-challenger-promotion"},
           timeout: 30_000
         ) do
      {:ok, %{"success" => true, "promoted" => true, "model_id" => model_id}} ->
        Logger.info("[DailyModelEvalJob] Challenger promoted: #{model_id}")

      {:ok, %{"success" => true, "promoted" => false}} ->
        Logger.info("[DailyModelEvalJob] No challenger promotion needed")

      {:ok, %{"success" => true, "message" => msg}} ->
        Logger.info("[DailyModelEvalJob] Challenger check: #{msg}")

      {:ok, unexpected} ->
        Logger.warning("[DailyModelEvalJob] Challenger check unexpected: #{inspect(unexpected)}")

      {:error, reason} ->
        Logger.error("[DailyModelEvalJob] Challenger check failed: #{inspect(reason)}")
    end
  end

  defp trigger_emergency_retrain do
    Logger.info("[DailyModelEvalJob] Invoking ml-training edge function for emergency retrain")

    case Server.SupabaseClient.invoke("ml-training",
           body: %{
             "action" => "train",
             "use_outcomes" => true,
             "outcome_window_days" => 90,
             "compare_to_current" => true,
             "auto_training_mode" => true
           },
           timeout: 300_000
         ) do
      {:ok, %{"success" => true, "model_id" => model_id}} ->
        Logger.info("[DailyModelEvalJob] Emergency retrain complete: #{model_id}")

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.info("[DailyModelEvalJob] Emergency retrain: #{message}")

      {:ok, %{"error" => error}} ->
        Logger.error("[DailyModelEvalJob] Emergency retrain failed: #{error}")

      {:error, reason} ->
        Logger.error("[DailyModelEvalJob] Emergency retrain request failed: #{inspect(reason)}")

      {:ok, unexpected} ->
        Logger.warning("[DailyModelEvalJob] Emergency retrain unexpected response: #{inspect(unexpected)}")
    end
  end
end
