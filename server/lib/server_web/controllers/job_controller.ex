defmodule ServerWeb.JobController do
  @moduledoc """
  Controller for job management API endpoints.
  """

  use ServerWeb, :controller

  alias Server.Scheduler

  @doc """
  Lists all registered jobs with their status.
  GET /api/jobs
  """
  def index(conn, _params) do
    jobs = Scheduler.list_jobs()
    json(conn, %{jobs: jobs})
  end

  @doc """
  Gets the status of a specific job.
  GET /api/jobs/:job_id
  """
  def show(conn, %{"job_id" => job_id}) do
    case Scheduler.get_job_status(job_id) do
      {:ok, job} ->
        # Transform Ecto struct to JSON-serializable map
        job_data = %{
          job_id: job.job_id,
          job_name: job.job_name,
          job_function: job.job_function,
          schedule_type: job.schedule_type,
          schedule: job.schedule_value,
          enabled: job.enabled,
          last_run_at: job.last_run_at,
          last_successful_run: job.last_successful_run,
          consecutive_failures: job.consecutive_failures,
          max_consecutive_failures: job.max_consecutive_failures,
          metadata: job.metadata,
          created_at: job.created_at,
          updated_at: job.updated_at
        }

        json(conn, %{job: job_data})

      {:error, :not_found} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Job not found"})
    end
  end

  @doc """
  Manually triggers a job to run immediately.
  POST /api/jobs/:job_id/run
  """
  def run(conn, %{"job_id" => job_id}) do
    case Scheduler.run_now(job_id) do
      :ok ->
        json(conn, %{status: "success", job_id: job_id, message: "Job completed successfully"})

      {:ok, result} ->
        json(conn, %{status: "success", job_id: job_id, result: result})

      {:error, :not_found} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Job not found"})

      {:error, reason} ->
        conn
        |> put_status(:internal_server_error)
        |> json(%{status: "failed", job_id: job_id, error: inspect(reason)})
    end
  end

  @doc """
  Gets the latest sync status across all data collection jobs.
  GET /api/jobs/sync-status

  Returns the most recent successful run time for data collection jobs.
  """
  def sync_status(conn, _params) do
    jobs = Scheduler.list_jobs()

    # Find the most recent successful run across data collection jobs
    # Include all ETL and data collection jobs for accurate sync status
    data_jobs = [
      "politician-trading-house",
      "politician-trading-senate",
      "politician-trading-quiver",
      "sync-data",
      "trading-signals",
      "data_collection",
      "data_collection_daily",
      "daily-scheduled-sync",
      "signal-generation"
    ]

    last_sync =
      jobs
      |> Enum.filter(fn job -> job.job_id in data_jobs end)
      |> Enum.map(& &1.last_successful_run)
      |> Enum.reject(&is_nil/1)
      |> Enum.max(DateTime, fn -> nil end)

    json(conn, %{
      last_sync: last_sync,
      jobs:
        jobs
        |> Enum.filter(fn job -> job.job_id in data_jobs end)
        |> Enum.map(fn job ->
          %{
            job_id: job.job_id,
            job_name: job.job_name,
            last_successful_run: job.last_successful_run
          }
        end)
    })
  end

  @doc """
  Runs all jobs manually (async).
  POST /api/jobs/run-all

  Jobs are triggered asynchronously and this endpoint returns immediately
  with the list of jobs that were started.
  """
  def run_all(conn, _params) do
    jobs = Scheduler.list_jobs()

    enabled_jobs =
      jobs
      |> Enum.filter(& &1.enabled)

    # Start all jobs asynchronously
    Enum.each(enabled_jobs, fn job ->
      Task.start(fn -> Scheduler.run_now(job.job_id) end)
    end)

    triggered =
      Enum.map(enabled_jobs, fn job ->
        %{job_id: job.job_id, job_name: job.job_name, status: "triggered"}
      end)

    json(conn, %{
      message: "#{length(triggered)} jobs triggered",
      jobs: triggered
    })
  end
end
