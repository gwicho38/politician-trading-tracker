defmodule Server.Scheduler.Jobs.PoliticianDedupJob do
  @moduledoc """
  Deduplicates politician records by merging records with matching normalized names.

  Triggers the Python ETL service to:
  1. Find politicians with duplicate names (case/prefix variations)
  2. Merge them by keeping the most complete record
  3. Update all trading_disclosures to point to the winner
  4. Delete duplicate records
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  # TODO: Review this function
  @impl true
  def job_id, do: "politician-dedup"

  # TODO: Review this function
  @impl true
  def job_name, do: "Politician Deduplication"

  # TODO: Review this function
  @impl true
  # Run weekly on Sunday at 5 AM UTC
  def schedule, do: "0 5 * * 0"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PoliticianDedupJob] Starting politician deduplication")

    case trigger_dedup() do
      {:ok, result} ->
        Logger.info("[PoliticianDedupJob] Deduplication complete: #{inspect(result)}")
        {:ok, result}

      {:error, reason} ->
        Logger.error("[PoliticianDedupJob] Deduplication failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp trigger_dedup do
    url = "#{@etl_service_url}/dedup/process"

    # Process up to 100 duplicate groups per run
    body = Jason.encode!(%{limit: 100, dry_run: false})

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

    case Finch.request(request, Server.Finch, receive_timeout: 120_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"merged" => merged, "disclosures_updated" => updated}} ->
            {:ok, %{merged: merged, disclosures_updated: updated}}

          {:ok, response} ->
            {:ok, response}

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
      description: "Merges duplicate politician records with matching names",
      etl_service: @etl_service_url,
      batch_size: 100
    }
  end
end
