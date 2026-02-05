defmodule Server.Scheduler.Jobs.BioguideEnrichmentJob do
  @moduledoc """
  Enriches politician records with BioGuide IDs from Congress.gov.

  Triggers the Python ETL service to:
  1. Fetch current Congress members from Congress.gov API
  2. Match them to politicians in our database by name
  3. Update the bioguide_id column for matched politicians

  BioGuide IDs are unique identifiers from the Biographical Directory
  of the United States Congress, enabling cross-referencing with
  official Congress data sources.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "bioguide-enrichment"

  @impl true
  def job_name, do: "BioGuide ID Enrichment"

  @impl true
  # Run weekly on Sunday at 4 AM UTC (less frequent since Congress membership changes slowly)
  def schedule, do: "0 4 * * 0"

  @impl true
  def run do
    Logger.info("[BioguideEnrichmentJob] Triggering bioguide enrichment service")

    case trigger_enrichment() do
      {:ok, job_id} ->
        Logger.info("[BioguideEnrichmentJob] Enrichment job started: #{job_id}")
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[BioguideEnrichmentJob] Enrichment trigger failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_enrichment do
    url = "#{@etl_service_url}/etl/enrich-bioguide"
    api_key = System.get_env("ETL_API_KEY") || ""

    # Process all politicians without bioguide_id (typically few hundred max)
    body = Jason.encode!(%{limit: nil})

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

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning("[BioguideEnrichmentJob] Unexpected response: #{inspect(response)}")
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
      description: "Enriches politician records with BioGuide IDs from Congress.gov API",
      etl_service: @etl_service_url,
      congress_api: "https://api.congress.gov/v3",
      frequency: "weekly"
    }
  end
end
