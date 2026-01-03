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

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "ml-training"

  @impl true
  def job_name, do: "ML Model Training"

  @impl true
  # Run weekly on Sunday at 2 AM UTC
  def schedule, do: "0 2 * * 0"

  @impl true
  def run do
    Logger.info("[MlTrainingJob] Triggering ML model training")

    case trigger_training() do
      {:ok, job_id} ->
        Logger.info("[MlTrainingJob] Training job started: #{job_id}")
        # Optionally poll for completion (but don't block the scheduler)
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[MlTrainingJob] Training trigger failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_training do
    url = "#{@etl_service_url}/ml/train"

    # Training configuration
    body =
      Jason.encode!(%{
        lookback_days: 365,
        model_type: "xgboost",
        triggered_by: "scheduler"
      })

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ],
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning("[MlTrainingJob] Unexpected response: #{inspect(response)}")
            {:ok, "unknown"}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @doc """
  Manually trigger training (useful for testing or on-demand retraining).
  """
  def trigger_manual(lookback_days \\ 365, model_type \\ "xgboost") do
    url = "#{@etl_service_url}/ml/train"

    body =
      Jason.encode!(%{
        lookback_days: lookback_days,
        model_type: model_type
      })

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ],
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        Jason.decode(response_body)

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @doc """
  Check training job status.
  """
  def check_status(job_id) do
    url = "#{@etl_service_url}/ml/train/#{job_id}"

    request =
      Finch.build(
        :get,
        url,
        [{"Accept", "application/json"}]
      )

    case Finch.request(request, Server.Finch, receive_timeout: 10_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        Jason.decode(response_body)

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Trains XGBoost model for congress trading signal prediction",
      etl_service: @etl_service_url,
      schedule_description: "Weekly on Sunday at 2 AM UTC",
      model_type: "xgboost",
      lookback_days: 365
    }
  end
end
