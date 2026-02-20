defmodule Server.Scheduler.Jobs.LLMFeedbackJob do
  @moduledoc """
  LLM Feedback Loop for prompt pipeline optimization.

  Triggers the Python ETL service to:
  1. Collect validation and anomaly detection outcomes from the past week
  2. Evaluate LLM prompt effectiveness (accuracy, false positive rates)
  3. Generate prompt improvement suggestions based on feedback
  4. Record feedback metrics in the lineage audit trail
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "llm-feedback"

  @impl true
  def job_name, do: "LLM Feedback Loop"

  @impl true
  # Run weekly on Sunday at 02:00 UTC
  def schedule, do: "0 2 * * 0"

  @impl true
  def run do
    Logger.info("[LLMFeedbackJob] Starting feedback loop")

    case trigger_feedback_loop() do
      {:ok, result} ->
        Logger.info("[LLMFeedbackJob] Feedback loop completed: #{inspect(result)}")
        {:ok, result}

      {:error, reason} ->
        Logger.error("[LLMFeedbackJob] Feedback loop failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_feedback_loop do
    url = "#{@etl_service_url}/llm/run-feedback"
    api_key = System.get_env("ETL_API_KEY") || ""

    body = Jason.encode!(%{days_back: 7})

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
          {:ok, %{"improvements" => improvements}} ->
            count = length(improvements)

            Logger.info(
              "[LLMFeedbackJob] Generated #{count} prompt improvement suggestions"
            )

            {:ok, count}

          {:ok, response} ->
            Logger.info("[LLMFeedbackJob] Response: #{inspect(response)}")
            {:ok, Map.get(response, "improvements_count", 0)}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        Logger.error("[LLMFeedbackJob] HTTP #{status}: #{response_body}")
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Weekly feedback loop for LLM prompt pipeline optimization",
      etl_service: @etl_service_url,
      lookback_days: 7,
      schedule_description: "Weekly on Sunday at 02:00 UTC"
    }
  end
end
