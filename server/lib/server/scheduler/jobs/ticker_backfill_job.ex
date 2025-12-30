defmodule Server.Scheduler.Jobs.TickerBackfillJob do
  @moduledoc """
  Daily job to backfill missing tickers in trading disclosures.

  Triggers the Python ETL service to:
  1. Query disclosures with null/empty asset_ticker
  2. Extract tickers from asset_name using regex patterns
  3. Update records with extracted tickers
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "ticker_backfill_daily"

  @impl true
  def job_name, do: "Daily Ticker Backfill"

  @impl true
  # Run daily at 2 AM UTC
  def schedule, do: "0 2 * * *"

  @impl true
  def run do
    Logger.info("[TickerBackfillJob] Triggering ticker backfill")

    case trigger_backfill() do
      {:ok, job_id} ->
        Logger.info("[TickerBackfillJob] Backfill job started: #{job_id}")
        {:ok, job_id}

      {:error, reason} ->
        Logger.error("[TickerBackfillJob] Backfill failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_backfill do
    url = "#{@etl_service_url}/etl/backfill-tickers"

    body = Jason.encode!(%{})

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
            Logger.warning("[TickerBackfillJob] Unexpected response: #{inspect(response)}")
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
      description: "Backfills missing tickers in trading disclosures",
      etl_service: @etl_service_url
    }
  end
end
