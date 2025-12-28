defmodule Server.Scheduler.Job do
  @moduledoc """
  Behaviour for scheduled job modules.

  Implement this behaviour to define a cron job. Each job module
  is self-contained with its schedule and execution logic.

  ## Example

      defmodule MyApp.Jobs.DailyReport do
        @behaviour Server.Scheduler.Job

        @impl true
        def job_id, do: "daily-report"

        @impl true
        def job_name, do: "Daily Report Generation"

        @impl true
        def schedule, do: "0 8 * * *"  # 8 AM daily

        @impl true
        def run do
          # Your job logic here
          :ok
        end
      end
  """

  @doc "Unique identifier for the job (used in database)"
  @callback job_id() :: String.t()

  @doc "Human-readable name for the job"
  @callback job_name() :: String.t()

  @doc "Cron expression (e.g., '0 */4 * * *') or interval in seconds as string"
  @callback schedule() :: String.t()

  @doc "The job execution logic. Returns :ok or {:ok, count} on success, {:error, reason} on failure"
  @callback run() :: :ok | {:ok, integer()} | {:error, term()}

  @doc "Whether the job is enabled by default (optional, defaults to true)"
  @callback enabled?() :: boolean()

  @doc "Additional metadata for the job (optional)"
  @callback metadata() :: map()

  @doc "Schedule type: :cron or :interval (optional, defaults to :cron)"
  @callback schedule_type() :: :cron | :interval

  @optional_callbacks [enabled?: 0, metadata: 0, schedule_type: 0]

  @doc """
  Returns the schedule type for a job module.
  Falls back to :cron if not implemented.
  """
  def get_schedule_type(module) do
    if function_exported?(module, :schedule_type, 0) do
      module.schedule_type()
    else
      :cron
    end
  end

  @doc """
  Returns whether the job is enabled.
  Falls back to true if not implemented.
  """
  def enabled?(module) do
    if function_exported?(module, :enabled?, 0) do
      module.enabled?()
    else
      true
    end
  end

  @doc """
  Returns the job metadata.
  Falls back to empty map if not implemented.
  """
  def get_metadata(module) do
    if function_exported?(module, :metadata, 0) do
      module.metadata()
    else
      %{}
    end
  end
end
