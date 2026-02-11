defmodule Server.Scheduler.Jobs.BiographyEnrichmentJob do
  @moduledoc """
  Generates politician biographies using Ollama LLM.

  Triggers the Python ETL service to:
  1. Query politicians without biographies
  2. Use Ollama to generate factual bios (with template fallback)
  3. Store biographies in the politicians table

  Runs weekly on Sunday at 4 AM UTC (after party enrichment at 3 AM).
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "biography-enrichment"

  @impl true
  def job_name, do: "Biography Generation (Ollama)"

  @impl true
  def schedule, do: "0 4 * * 0"

  @impl true
  def run do
    Logger.info("[BiographyEnrichmentJob] Triggering biography generation service")

    case trigger_biography_generation() do
      {:ok, job_id} ->
        Logger.info("[BiographyEnrichmentJob] Biography job started: #{job_id}")
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[BiographyEnrichmentJob] Biography trigger failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_biography_generation do
    url = "#{@etl_service_url}/enrichment/biography/trigger"

    body = Jason.encode!(%{limit: 200, force: true})

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

    case Finch.request(request, Server.Finch, receive_timeout: 300_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning(
              "[BiographyEnrichmentJob] Unexpected response: #{inspect(response)}"
            )

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

  @impl true
  def metadata do
    %{
      description: "Generates politician biographies using Ollama LLM",
      etl_service: @etl_service_url,
      ollama_url: "https://ollama.lefv.info",
      batch_size: 200,
      schedule_note: "Weekly Sunday 4 AM UTC (after party enrichment)"
    }
  end
end
