defmodule Server.Scheduler.Jobs.PoliticianNormalizationJob do
  @moduledoc """
  Normalizes politician data daily to maintain consistency.

  Triggers the Python ETL service to:
  1. Normalize role values to canonical forms (Representative, Senator, MEP)
  2. Strip honorific prefixes from names (Hon., Mr., Sen., etc.)
  3. Backfill missing state_or_country from district data

  Runs at 2 AM UTC daily, before the dedup job (5 AM Sunday) so that
  normalized data improves deduplication accuracy.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @impl true
  def job_id, do: "politician-normalization"

  @impl true
  def job_name, do: "Politician Data Normalization"

  @impl true
  # Daily at 2 AM UTC
  def schedule, do: "0 2 * * *"

  @impl true
  def run do
    Logger.info("[PoliticianNormalizationJob] Starting politician data normalization")

    case trigger_normalization() do
      {:ok, result} ->
        Logger.info(
          "[PoliticianNormalizationJob] Normalization complete: " <>
            "#{result.total_corrections} corrections, #{result.total_errors} errors"
        )

        {:ok, result}

      {:error, reason} ->
        Logger.error("[PoliticianNormalizationJob] Normalization failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp trigger_normalization do
    url = "#{@etl_service_url}/quality/normalize-politicians"

    body =
      Jason.encode!(%{
        dry_run: false,
        limit: 500,
        steps: ["roles", "names", "state_backfill"]
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

    case Finch.request(request, Server.Finch, receive_timeout: 120_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"total_corrections" => corrections, "total_errors" => errors} = response} ->
            {:ok,
             %{
               total_corrections: corrections,
               total_errors: errors,
               steps_completed: Map.get(response, "steps_completed", []),
               duration_ms: Map.get(response, "duration_ms", 0)
             }}

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

  @impl true
  def metadata do
    %{
      description: "Normalizes politician roles, names, and state data daily",
      etl_service: @etl_service_url,
      schedule_note: "Runs before dedup job for improved accuracy"
    }
  end
end
