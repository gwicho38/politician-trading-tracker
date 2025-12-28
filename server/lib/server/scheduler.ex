defmodule Server.Scheduler do
  @moduledoc """
  Single entry point for scheduled job management.

  This module delegates to specialized sub-modules:
  - API: Job registration, execution, and management
  - Job: Behaviour definition for job modules
  - Quantum: Internal Quantum scheduler process

  ## Usage

      alias Server.Scheduler

      # Register a job module
      Scheduler.register_job(MyApp.Jobs.DailySync)

      # List all jobs
      Scheduler.list_jobs()

      # Run a job immediately
      Scheduler.run_now("daily-sync")

      # Enable/disable jobs
      Scheduler.enable_job("daily-sync")
      Scheduler.disable_job("daily-sync")

  ## Defining Jobs

  Jobs implement the `Server.Scheduler.Job` behaviour:

      defmodule MyApp.Jobs.DailySync do
        @behaviour Server.Scheduler.Job

        @impl true
        def job_id, do: "daily-sync"

        @impl true
        def job_name, do: "Daily Data Sync"

        @impl true
        def schedule, do: "0 2 * * *"  # 2 AM daily

        @impl true
        def run do
          # Your job logic here
          :ok
        end
      end

  ## Database Sync

  All jobs are persisted to the `jobs.scheduled_jobs` table.
  Executions are logged to `jobs.job_executions`.
  """

  alias Server.Scheduler.{API, Quantum}

  # ═══════════════════════════════════════════════════════════════
  # JOB REGISTRATION
  # ═══════════════════════════════════════════════════════════════

  @doc """
  Registers a job module with the scheduler.

  The module must implement the `Server.Scheduler.Job` behaviour.
  """
  defdelegate register_job(module), to: API

  @doc """
  Registers multiple job modules at once.
  """
  defdelegate register_jobs(modules), to: API

  # ═══════════════════════════════════════════════════════════════
  # JOB EXECUTION
  # ═══════════════════════════════════════════════════════════════

  @doc """
  Runs a job immediately by its job_id.
  """
  defdelegate run_now(job_id), to: API

  # ═══════════════════════════════════════════════════════════════
  # JOB MANAGEMENT
  # ═══════════════════════════════════════════════════════════════

  @doc """
  Enables a job by its job_id.
  """
  defdelegate enable_job(job_id), to: API

  @doc """
  Disables a job by its job_id.
  """
  defdelegate disable_job(job_id), to: API

  # ═══════════════════════════════════════════════════════════════
  # JOB QUERIES
  # ═══════════════════════════════════════════════════════════════

  @doc """
  Lists all registered jobs with their current status.
  """
  defdelegate list_jobs(), to: API

  @doc """
  Gets the status of a specific job.
  """
  defdelegate get_job_status(job_id), to: API

  @doc """
  Gets recent executions for a job.
  """
  defdelegate get_executions(job_id, limit \\ 10), to: API

  # ═══════════════════════════════════════════════════════════════
  # QUANTUM ACCESS (for advanced usage)
  # ═══════════════════════════════════════════════════════════════

  @doc """
  Returns the child spec for the Quantum scheduler.

  Use this when adding to your supervision tree.
  """
  def child_spec(opts) do
    Quantum.child_spec(opts)
  end

  @doc """
  Lists all Quantum jobs (raw Quantum structs).
  """
  defdelegate quantum_jobs(), to: Quantum, as: :jobs
end
