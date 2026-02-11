defmodule Server.Scheduler.Jobs.PoliticianTradingSenateJob do
  @moduledoc """
  Collects US Senate financial disclosures via Python ETL service.

  Triggers the Python ETL service deployed on Fly.io to:
  1. Scrape the Senate EFD database for recent PTR filings
  2. Download and parse disclosure PDFs using pdfplumber
  3. Extract politician names, tickers, and value ranges
  4. Upload to Supabase trading_disclosures table
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  # TODO: Review this function
  @impl true
  def job_id, do: "politician-trading-senate"

  # TODO: Review this function
  @impl true
  def job_name, do: "US Senate Disclosures (ETL)"

  # TODO: Review this function
  @impl true
  # Every 6 hours (same as House)
  def schedule, do: "0 */6 * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PoliticianTradingSenateJob] Triggering Python ETL service")

    case trigger_etl() do
      {:ok, job_id} ->
        Logger.info("[PoliticianTradingSenateJob] ETL job started: #{job_id}")
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[PoliticianTradingSenateJob] ETL trigger failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp trigger_etl do
    url = "#{@etl_service_url}/etl/trigger"

    body =
      Jason.encode!(%{
        source: "senate",
        lookback_days: 30,
        limit: 100
      })

    headers = [
      {"Content-Type", "application/json"},
      {"Accept", "application/json"}
    ]

    headers =
      case Application.get_env(:server, :api_key) do
        nil -> headers
        key -> [{"X-API-Key", key} | headers]
      end

    request =
      Finch.build(
        :post,
        url,
        headers,
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning("[PoliticianTradingSenateJob] Unexpected response: #{inspect(response)}")
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

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Collects US Senate financial disclosures via Python ETL",
      etl_service: @etl_service_url,
      source: "senate"
    }
  end
end
