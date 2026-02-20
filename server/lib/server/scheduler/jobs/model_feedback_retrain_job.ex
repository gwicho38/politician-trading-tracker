defmodule Server.Scheduler.Jobs.ModelFeedbackRetrainJob do
  @moduledoc """
  Retrains the ML model using actual trade outcome data.

  This job closes the full feedback loop by:
  1. Evaluating current model over a 30-day window (monthly sanity check)
  2. Deciding whether to fine-tune or train from scratch
  3. Triggering training with outcome labels
  4. Champion/challenger gate (handled by ml-training edge function)

  The fine-tune vs scratch decision is delegated to the ml-training edge
  function which inspects model age and recent performance trends.

  Runs monthly to accumulate enough outcome data for meaningful retraining.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "model-feedback-retrain"

  @impl true
  def job_name, do: "ML Model Feedback Retraining"

  @impl true
  # Run monthly on the 1st at 3 AM UTC
  def schedule, do: "0 3 1 * *"

  @impl true
  def run do
    Logger.info("[ModelFeedbackRetrainJob] Starting outcome-based model retraining")

    # Step 1: Evaluate current model performance (30-day window for monthly check)
    Logger.info("[ModelFeedbackRetrainJob] Evaluating current model performance")

    current_performance =
      case Server.SupabaseClient.invoke("signal-feedback",
             body: %{"action" => "evaluate-model", "windowDays" => 30},
             timeout: 60_000
           ) do
        {:ok, %{"success" => true, "performance" => perf}} -> perf
        _ -> nil
      end

    if current_performance do
      Logger.info(
        "[ModelFeedbackRetrainJob] Current model: win_rate=#{current_performance["win_rate"]}, " <>
          "avg_return=#{current_performance["avg_return_pct"]}%, sharpe=#{current_performance["sharpe_ratio"]}"
      )
    end

    # Step 2: Trigger retraining — ml-training edge function decides fine-tune vs scratch
    Logger.info("[ModelFeedbackRetrainJob] Triggering model retraining with outcome data")

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
      {:ok, %{"success" => true, "model_id" => model_id, "metrics" => metrics} = result} ->
        training_mode = result["training_mode"] || "unknown"

        Logger.info(
          "[ModelFeedbackRetrainJob] New model trained (#{training_mode}): #{model_id}, " <>
            "accuracy=#{metrics["accuracy"]}, promoted=#{result["promoted"]}"
        )

        {:ok, 1}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.info("[ModelFeedbackRetrainJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[ModelFeedbackRetrainJob] Retraining failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[ModelFeedbackRetrainJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Retrains ML model using actual trade outcomes with auto fine-tune/scratch decision",
      edge_function: "ml-training",
      action: "train with outcomes (auto training mode)",
      schedule_note: "Runs monthly on the 1st at 3 AM UTC"
    }
  end
end
