defmodule Server.Schemas.ScheduledJob do
  @moduledoc """
  Ecto schema for jobs.scheduled_jobs table.

  Represents a scheduled job definition with its cron/interval schedule,
  execution tracking, and failure handling configuration.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @timestamps_opts [type: :utc_datetime]

  schema "jobs.scheduled_jobs" do
    field :job_id, :string
    field :job_name, :string
    field :job_function, :string
    field :schedule_type, :string
    field :schedule_value, :string
    field :enabled, :boolean, default: true
    field :last_run_at, :utc_datetime
    field :last_successful_run, :utc_datetime
    field :last_attempted_run, :utc_datetime
    field :next_scheduled_run, :utc_datetime
    field :consecutive_failures, :integer, default: 0
    field :max_consecutive_failures, :integer, default: 3
    field :auto_retry_on_startup, :boolean, default: true
    field :metadata, :map, default: %{}

    timestamps(inserted_at: :created_at, updated_at: :updated_at)
  end

  @required_fields ~w(job_id job_name job_function schedule_type schedule_value)a
  @optional_fields ~w(enabled last_run_at last_successful_run last_attempted_run
                      next_scheduled_run consecutive_failures max_consecutive_failures
                      auto_retry_on_startup metadata)a

  def changeset(job, attrs) do
    job
    |> cast(attrs, @required_fields ++ @optional_fields)
    |> validate_required(@required_fields)
    |> validate_inclusion(:schedule_type, ["cron", "interval"])
    |> unique_constraint(:job_id)
  end

  def update_execution_changeset(job, attrs) do
    job
    |> cast(attrs, [:last_run_at, :last_attempted_run, :last_successful_run,
                    :next_scheduled_run, :consecutive_failures])
  end
end
