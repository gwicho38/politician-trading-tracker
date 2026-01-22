defmodule Server.Scheduler.Jobs.PoliticianTradingHouseJob do
  @moduledoc """
  Collects US House financial disclosures via Python ETL service.

  Triggers the Python ETL service deployed on Fly.io to:
  1. Download the House disclosure index ZIP
  2. Parse PTR filings from PDFs using pdfplumber
  3. Extract real politician names, tickers, and value ranges
  4. Upload to Supabase trading_disclosures table
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  # TODO: Review this function
  @impl true
  def job_id, do: "politician-trading-house"

  # TODO: Review this function
  @impl true
  def job_name, do: "US House Disclosures (ETL)"

  # TODO: Review this function
  @impl true
  # Every 6 hours
  def schedule, do: "0 */6 * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PoliticianTradingHouseJob] Triggering Python ETL service")

    case trigger_etl() do
      {:ok, job_id} ->
        Logger.info("[PoliticianTradingHouseJob] ETL job started: #{job_id}")
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[PoliticianTradingHouseJob] ETL trigger failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp trigger_etl do
    url = "#{@etl_service_url}/etl/trigger"

    body =
      Jason.encode!(%{
        source: "house",
        year: Date.utc_today().year,
        max_pdfs: 100
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

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning("[PoliticianTradingHouseJob] Unexpected response: #{inspect(response)}")
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
      description: "Collects US House financial disclosures via Python ETL",
      etl_service: @etl_service_url,
      source: "house"
    }
  end
end
