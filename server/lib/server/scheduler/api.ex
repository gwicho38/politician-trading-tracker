defmodule Server.Scheduler.API do
  @moduledoc """
  Job management implementation for the scheduler.

  This module is delegated to by `Server.Scheduler`. Use the entry point
  for a cleaner API.
  """

  alias Server.Repo
  alias Server.Schemas.{ScheduledJob, JobExecution}
  alias Server.Scheduler.Job, as: JobBehaviour
  alias Server.Scheduler.Quantum, as: QuantumScheduler
  import Ecto.Query

  require Logger

  # TODO: Review this function
  @doc """
  Registers a job module with the scheduler.

  The module must implement the `Server.Scheduler.Job` behaviour.
  This will:
  1. Upsert the job definition in the database
  2. Add the job to Quantum if enabled

  Returns `{:ok, job_id}` on success.
  """
  def register_job(module) when is_atom(module) do
    job_id = module.job_id()
    job_name = module.job_name()
    schedule = module.schedule()
    schedule_type = JobBehaviour.get_schedule_type(module)
    enabled = JobBehaviour.enabled?(module)
    metadata = JobBehaviour.get_metadata(module)

    # Upsert to database
    attrs = %{
      job_id: job_id,
      job_name: job_name,
      job_function: to_string(module),
      schedule_type: to_string(schedule_type),
      schedule_value: schedule,
      enabled: enabled,
      metadata: metadata
    }

    result =
      case Repo.get_by(ScheduledJob, job_id: job_id) do
        nil -> %ScheduledJob{}
        existing -> existing
      end
      |> ScheduledJob.changeset(attrs)
      |> Repo.insert_or_update()

    case result do
      {:ok, _record} ->
        if enabled do
          add_to_quantum(module)
        end

        Logger.info("[Scheduler] Registered job: #{job_id}")
        {:ok, job_id}

      {:error, changeset} ->
        Logger.error("[Scheduler] Failed to register job #{job_id}: #{inspect(changeset.errors)}")
        {:error, changeset.errors}
    end
  end

  # TODO: Review this function
  @doc """
  Registers multiple job modules at once.
  """
  def register_jobs(modules) when is_list(modules) do
    Enum.map(modules, &register_job/1)
  end

  # TODO: Review this function
  @doc """
  Runs a job immediately by its job_id.

  This executes the job synchronously and records the execution.
  """
  def run_now(job_id) when is_binary(job_id) do
    case Repo.get_by(ScheduledJob, job_id: job_id) do
      nil ->
        {:error, :not_found}

      job_record ->
        try do
          module = String.to_existing_atom(job_record.job_function)
          execute_job(module, job_record)
        rescue
          ArgumentError ->
            Logger.warning(
              "[Scheduler] Module not loaded for job #{job_id}: #{job_record.job_function}"
            )

            {:error, {:module_not_loaded, job_record.job_function}}
        end
    end
  end

  # TODO: Review this function
  @doc """
  Enables a job by its job_id.
  """
  def enable_job(job_id) do
    update_job_enabled(job_id, true)
  end

  # TODO: Review this function
  @doc """
  Disables a job by its job_id.
  """
  def disable_job(job_id) do
    update_job_enabled(job_id, false)
  end

  # TODO: Review this function
  @doc """
  Lists all registered jobs with their current status.
  """
  def list_jobs do
    ScheduledJob
    |> order_by([j], j.job_id)
    |> Repo.all()
    |> Enum.map(fn job ->
      %{
        job_id: job.job_id,
        job_name: job.job_name,
        schedule: job.schedule_value,
        schedule_type: job.schedule_type,
        enabled: job.enabled,
        last_run_at: job.last_run_at,
        last_successful_run: job.last_successful_run,
        consecutive_failures: job.consecutive_failures
      }
    end)
  end

  # TODO: Review this function
  @doc """
  Gets the status of a specific job.
  """
  def get_job_status(job_id) do
    case Repo.get_by(ScheduledJob, job_id: job_id) do
      nil -> {:error, :not_found}
      job -> {:ok, job}
    end
  end

  # TODO: Review this function
  @doc """
  Gets recent executions for a job.
  """
  def get_executions(job_id, limit \\ 10) do
    JobExecution
    |> where([e], e.job_id == ^job_id)
    |> order_by([e], desc: e.started_at)
    |> limit(^limit)
    |> Repo.all()
  end

  # TODO: Review this function
  # Private functions

  defp add_to_quantum(module) do
    job_id = module.job_id()
    schedule = module.schedule()
    schedule_type = JobBehaviour.get_schedule_type(module)

    quantum_job =
      QuantumScheduler.new_job()
      |> Quantum.Job.set_name(String.to_atom(job_id))
      |> Quantum.Job.set_task(fn -> execute_job_async(module) end)

    quantum_job =
      case schedule_type do
        :cron ->
          case Crontab.CronExpression.Parser.parse(schedule) do
            {:ok, cron_expr} ->
              Quantum.Job.set_schedule(quantum_job, cron_expr)

            {:error, reason} ->
              Logger.error(
                "[Scheduler] Invalid cron expression for #{job_id}: #{inspect(reason)}"
              )

              nil
          end

        :interval ->
          # For intervals, we convert seconds to a simple recurring schedule
          # Quantum doesn't have native interval support, so we use extended cron
          seconds = String.to_integer(schedule)
          minutes = div(seconds, 60)

          if minutes > 0 do
            Quantum.Job.set_schedule(
              quantum_job,
              Crontab.CronExpression.Parser.parse!("*/#{minutes} * * * *")
            )
          else
            Logger.warning(
              "[Scheduler] Interval #{seconds}s is less than 1 minute for #{job_id}, using 1 minute"
            )

            Quantum.Job.set_schedule(
              quantum_job,
              Crontab.CronExpression.Parser.parse!("* * * * *")
            )
          end
      end

    if quantum_job do
      QuantumScheduler.add_job(quantum_job)
    end
  end

  # TODO: Review this function
  defp execute_job_async(module) do
    Task.start(fn ->
      job_record = Repo.get_by(ScheduledJob, job_id: module.job_id())

      if job_record && job_record.enabled do
        execute_job(module, job_record)
      end
    end)
  end

  # TODO: Review this function
  defp execute_job(module, job_record) do
    job_id = job_record.job_id
    started_at = DateTime.utc_now()

    # Update job's last_attempted_run
    job_record
    |> ScheduledJob.update_execution_changeset(%{last_attempted_run: started_at})
    |> Repo.update()

    # Execute the job
    Logger.info("[Scheduler] Starting job: #{job_id}")
    start_time = System.monotonic_time(:millisecond)

    result =
      try do
        module.run()
      rescue
        e ->
          {:error, Exception.message(e)}
      catch
        :exit, reason ->
          {:error, {:exit, reason}}
      end

    duration = (System.monotonic_time(:millisecond) - start_time) / 1000
    completed_at = DateTime.utc_now()

    # Create execution record with final status (avoid 'running' status due to DB constraint)
    {status, metadata, error} =
      case result do
        :ok -> {"success", %{}, nil}
        {:ok, count} when is_integer(count) -> {"success", %{records_processed: count}, nil}
        {:ok, _other} -> {"success", %{}, nil}
        {:error, reason} -> {"failed", %{}, inspect(reason)}
      end

    # Insert execution record at completion
    %JobExecution{}
    |> JobExecution.changeset(%{
      job_id: job_id,
      started_at: started_at,
      completed_at: completed_at,
      status: status,
      duration_seconds: duration,
      metadata: metadata,
      error_message: error
    })
    |> Repo.insert()

    # Update job record
    job_updates =
      case status do
        "success" ->
          %{
            last_run_at: completed_at,
            last_successful_run: completed_at,
            consecutive_failures: 0
          }

        "failed" ->
          %{
            last_run_at: completed_at,
            consecutive_failures: job_record.consecutive_failures + 1
          }
      end

    job_record
    |> ScheduledJob.update_execution_changeset(job_updates)
    |> Repo.update()

    Logger.info("[Scheduler] Completed job: #{job_id} (#{status}, #{duration}s)")

    result
  end

  # TODO: Review this function
  defp update_job_enabled(job_id, enabled) do
    case Repo.get_by(ScheduledJob, job_id: job_id) do
      nil ->
        {:error, :not_found}

      job ->
        result =
          job
          |> ScheduledJob.changeset(%{enabled: enabled})
          |> Repo.update()

        # Update Quantum scheduler
        quantum_name = String.to_atom(job_id)

        if enabled do
          QuantumScheduler.activate_job(quantum_name)
        else
          QuantumScheduler.deactivate_job(quantum_name)
        end

        result
    end
  end
end
