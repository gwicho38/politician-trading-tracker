defmodule Server.Scheduler.Jobs.LLMAnomalyDetectionJob do
  @moduledoc """
  LLM Anomaly Detection for trading disclosures.

  Triggers the Python ETL service to:
  1. Query recent trading disclosures within a lookback window
  2. Use the LLM to detect anomalous patterns (unusual amounts, timing, etc.)
  3. Score and flag anomalies for investigation
  4. Record anomaly audit trail in the database
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "llm-anomaly-detection"

  @impl true
  def job_name, do: "LLM Anomaly Detection"

  @impl true
  # Run daily at 01:00 UTC
  def schedule, do: "0 1 * * *"

  @impl true
  def run do
    Logger.info("[LLMAnomalyDetectionJob] Starting anomaly detection")

    case trigger_anomaly_detection() do
      {:ok, result} ->
        Logger.info("[LLMAnomalyDetectionJob] Anomaly detection completed: #{inspect(result)}")
        {:ok, result}

      {:error, reason} ->
        Logger.error("[LLMAnomalyDetectionJob] Anomaly detection failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_anomaly_detection do
    url = "#{@etl_service_url}/llm/detect-anomalies"
    api_key = System.get_env("ETL_API_KEY") || ""

    body = Jason.encode!(%{days_back: 30})

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"},
          {"X-API-Key", api_key}
        ],
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 600_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"anomalies_found" => count}} ->
            Logger.info("[LLMAnomalyDetectionJob] Found #{count} anomalies")
            {:ok, count}

          {:ok, response} ->
            Logger.info("[LLMAnomalyDetectionJob] Response: #{inspect(response)}")
            {:ok, Map.get(response, "anomalies_found", 0)}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        Logger.error("[LLMAnomalyDetectionJob] HTTP #{status}: #{response_body}")
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @impl true
  def metadata do
    %{
      description: "LLM-powered anomaly detection for trading disclosures",
      etl_service: @etl_service_url,
      lookback_days: 30,
      schedule_description: "Daily at 01:00 UTC"
    }
  end
end
