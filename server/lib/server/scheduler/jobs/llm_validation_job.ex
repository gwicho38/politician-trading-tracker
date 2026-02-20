defmodule Server.Scheduler.Jobs.LLMValidationJob do
  @moduledoc """
  LLM Validation Gate for trading disclosures.

  Triggers the Python ETL service to:
  1. Query unvalidated trading disclosures in batches
  2. Use the LLM to validate data quality and consistency
  3. Flag records that fail validation for human review
  4. Pass validated records through the pipeline
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "llm-validation"

  @impl true
  def job_name, do: "LLM Validation Gate"

  @impl true
  # Run hourly at :30 to validate new disclosures
  def schedule, do: "30 * * * *"

  @impl true
  def run do
    Logger.info("[LLMValidationJob] Starting batch validation")

    case trigger_validation() do
      {:ok, result} ->
        Logger.info("[LLMValidationJob] Batch validation completed: #{inspect(result)}")
        {:ok, result}

      {:error, reason} ->
        Logger.error("[LLMValidationJob] Batch validation failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_validation do
    url = "#{@etl_service_url}/llm/validate-batch"
    api_key = System.get_env("ETL_API_KEY") || ""

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"},
          {"X-API-Key", api_key}
        ],
        "{}"
      )

    case Finch.request(request, Server.Finch, receive_timeout: 300_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"validated" => validated, "flagged" => flagged}} ->
            Logger.info(
              "[LLMValidationJob] Validated #{validated} records, flagged #{flagged} for review"
            )

            {:ok, validated}

          {:ok, response} ->
            Logger.info("[LLMValidationJob] Response: #{inspect(response)}")
            {:ok, Map.get(response, "validated", 0)}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        Logger.error("[LLMValidationJob] HTTP #{status}: #{response_body}")
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @impl true
  def metadata do
    %{
      description: "LLM-powered batch validation gate for trading disclosures",
      etl_service: @etl_service_url,
      schedule_description: "Hourly at :30"
    }
  end
end
