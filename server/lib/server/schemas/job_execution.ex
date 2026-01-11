defmodule Server.Schemas.JobExecution do
  @moduledoc """
  Ecto schema for public.job_executions table.

  Tracks individual job execution runs with status, duration,
  and optional logs/error messages.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}

  schema "job_executions" do
    field :job_id, :string
    field :started_at, :utc_datetime
    field :completed_at, :utc_datetime
    field :status, :string, default: "running"
    field :duration_seconds, :decimal
    field :error_message, :string
    field :logs, :string
    # Maps to 'metadata' column in database
    field :metadata, :map, default: %{}

    timestamps(inserted_at: :created_at, updated_at: false, type: :utc_datetime)
  end

  @valid_statuses ~w(running success failed completed cancelled)

  def changeset(execution, attrs) do
    execution
    |> cast(attrs, [
      :job_id,
      :started_at,
      :completed_at,
      :status,
      :duration_seconds,
      :error_message,
      :logs,
      :metadata
    ])
    |> validate_required([:job_id])
    |> validate_inclusion(:status, @valid_statuses)
  end

  def start_changeset(job_id) do
    %__MODULE__{}
    |> cast(%{job_id: job_id, started_at: DateTime.utc_now(), status: "running"}, [
      :job_id,
      :started_at,
      :status
    ])
  end

  def complete_changeset(execution, result) do
    now = DateTime.utc_now()
    duration = DateTime.diff(now, execution.started_at, :millisecond) / 1000

    attrs =
      case result do
        :ok ->
          %{completed_at: now, status: "success", duration_seconds: duration}

        {:ok, records} when is_integer(records) ->
          # Store records count in metadata since we don't have a dedicated column
          %{
            completed_at: now,
            status: "success",
            duration_seconds: duration,
            metadata: %{records_processed: records}
          }

        {:ok, _other} ->
          %{completed_at: now, status: "success", duration_seconds: duration}

        {:error, message} ->
          %{
            completed_at: now,
            status: "failed",
            duration_seconds: duration,
            error_message: inspect(message)
          }
      end

    execution
    |> cast(attrs, [:completed_at, :status, :duration_seconds, :error_message, :metadata])
  end
end
