defmodule Server.Scheduler.Jobs.JobExecutionCleanupJob do
  @moduledoc """
  Cleans up old job execution records from the database.

  Runs weekly to delete job_executions records older than 30 days.
  This prevents the job_executions table from growing indefinitely.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  # TODO: Review this function
  @impl true
  def job_id, do: "job-execution-cleanup"

  # TODO: Review this function
  @impl true
  def job_name, do: "Job Execution Cleanup"

  # TODO: Review this function
  @impl true
  # Weekly on Sunday at 6 AM UTC
  def schedule, do: "0 6 * * 0"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[JobExecutionCleanupJob] Starting cleanup of old job executions")

    case trigger_cleanup() do
      {:ok, deleted} ->
        Logger.info("[JobExecutionCleanupJob] Cleanup completed: #{deleted} records deleted")
        {:ok, deleted}

      {:error, reason} ->
        Logger.error("[JobExecutionCleanupJob] Cleanup failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp trigger_cleanup do
    url = "#{@etl_service_url}/etl/cleanup-executions"

    body =
      Jason.encode!(%{
        days: 30
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
          {:ok, %{"deleted" => deleted}} ->
            {:ok, deleted}

          {:ok, _response} ->
            {:ok, 0}

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
      description: "Deletes job execution records older than 30 days",
      etl_service: @etl_service_url,
      cleanup_days: 30
    }
  end
end
