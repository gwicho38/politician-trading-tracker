defmodule Server.Scheduler.Jobs.PartyEnrichmentJob do
  @moduledoc """
  Enriches politician party data using Ollama LLM.

  Triggers the Python ETL service to:
  1. Query politicians with missing party data
  2. Use Ollama to determine party affiliation
  3. Update politician records in Supabase
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "party-enrichment"

  @impl true
  def job_name, do: "Party Data Enrichment (Ollama)"

  @impl true
  # Run daily at 3 AM UTC
  def schedule, do: "0 3 * * *"

  @impl true
  def run do
    Logger.info("[PartyEnrichmentJob] Triggering party enrichment service")

    case trigger_enrichment() do
      {:ok, job_id} ->
        Logger.info("[PartyEnrichmentJob] Enrichment job started: #{job_id}")
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[PartyEnrichmentJob] Enrichment trigger failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_enrichment do
    url = "#{@etl_service_url}/enrichment/trigger"

    # Process up to 100 politicians per run to avoid overwhelming Ollama
    body = Jason.encode!(%{limit: 100})

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

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning("[PartyEnrichmentJob] Unexpected response: #{inspect(response)}")
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
      description: "Enriches politician party data using Ollama LLM",
      etl_service: @etl_service_url,
      ollama_url: "https://ollama.lefv.info",
      batch_size: 100
    }
  end
end
