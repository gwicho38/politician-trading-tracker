defmodule Server.Scheduler.Jobs.MlTrainingJob do
  @moduledoc """
  Triggers ML model retraining via Python ETL service.

  Runs weekly to retrain the congress trading signal prediction model
  using historical disclosure data and stock returns.

  The model uses XGBoost/LightGBM to predict signal types (buy/sell/hold)
  with confidence scores, which are then blended with heuristic signals.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "ml-training"

  @impl true
  def job_name, do: "ML Model Training"

  @impl true
  # Run weekly on Sunday at 2 AM UTC
  def schedule, do: "0 2 * * 0"

  @impl true
  def run do
    Logger.info("[MlTrainingJob] Triggering ML model training via edge function (async)")

    # Route through ml-training edge function so the C/C gate runs via DailyModelEvalJob.
    case Server.SupabaseClient.invoke("ml-training",
           body: %{
             "action" => "train",
             "lookback_days" => 365,
             "use_outcomes" => false,
             "compare_to_current" => true,
             "auto_training_mode" => true,
             "triggered_by" => "scheduler"
           },
           timeout: 30_000
         ) do
      {:ok, %{"status" => "training_queued", "job_id" => job_id}} ->
        Logger.info("[MlTrainingJob] Training queued: job_id=#{job_id}")
        {:ok, job_id}

      {:ok, %{"error" => error}} ->
        Logger.error("[MlTrainingJob] Training failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[MlTrainingJob] Request failed: #{inspect(reason)}")
        {:error, reason}

      {:ok, unexpected} ->
        Logger.warning("[MlTrainingJob] Unexpected response: #{inspect(unexpected)}")
        {:ok, "unknown"}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Trains XGBoost model for congress trading signal prediction (weekly fallback)",
      edge_function: "ml-training",
      schedule_description: "Weekly on Sunday at 2 AM UTC",
      lookback_days: 365
    }
  end
end
