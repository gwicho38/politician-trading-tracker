defmodule Server.Scheduler.Jobs.ModelFeedbackRetrainJob do
  @moduledoc """
  Retrains the ML model using actual trade outcome data.

  This job closes the full feedback loop by:
  1. Collecting signal outcomes (actual P&L from trades)
  2. Using outcomes as training labels (instead of just price movements)
  3. Incorporating feature importance analysis into weight adjustments
  4. Comparing new model performance to existing model
  5. Deploying new model if it shows improvement

  Runs monthly to accumulate enough outcome data for meaningful retraining.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "model-feedback-retrain"

  # TODO: Review this function
  @impl true
  def job_name, do: "ML Model Feedback Retraining"

  # TODO: Review this function
  @impl true
  # Run monthly on the 1st at 3 AM UTC
  def schedule, do: "0 3 1 * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[ModelFeedbackRetrainJob] Starting outcome-based model retraining")

    # Step 1: Evaluate current model performance
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

    # Step 2: Trigger retraining with outcome labels
    Logger.info("[ModelFeedbackRetrainJob] Triggering model retraining with outcome data")

    case Server.SupabaseClient.invoke("ml-training",
           body: %{
             "action" => "train",
             "use_outcomes" => true,
             "outcome_window_days" => 90,
             "compare_to_current" => true
           },
           timeout: 300_000
         ) do
      {:ok, %{"success" => true, "model_id" => model_id, "metrics" => metrics}} ->
        Logger.info(
          "[ModelFeedbackRetrainJob] New model trained: #{model_id}, " <>
            "accuracy=#{metrics["accuracy"]}, improvement over baseline"
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

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Retrains ML model using actual trade outcomes as labels",
      edge_function: "ml-training",
      action: "train with outcomes",
      schedule_note: "Runs monthly on the 1st at 3 AM UTC"
    }
  end
end
