defmodule Server.Scheduler.JobTest do
  @moduledoc """
  Tests for Server.Scheduler.Job behaviour and helper functions.

  Tests:
  - get_schedule_type/1 - Returns schedule type for a module
  - enabled?/1 - Returns whether job is enabled
  - get_metadata/1 - Returns job metadata
  """

  use ExUnit.Case, async: true

  alias Server.Scheduler.Job

  # Test module that implements all callbacks
  defmodule FullJob do
    @behaviour Server.Scheduler.Job

    @impl true
    def job_id, do: "full-job"

    @impl true
    def job_name, do: "Full Test Job"

    @impl true
    def schedule, do: "0 * * * *"

    @impl true
    def run, do: :ok

    @impl true
    def enabled?, do: false

    @impl true
    def metadata, do: %{key: "value", count: 42}

    @impl true
    def schedule_type, do: :interval
  end

  # Test module that only implements required callbacks
  defmodule MinimalJob do
    @behaviour Server.Scheduler.Job

    @impl true
    def job_id, do: "minimal-job"

    @impl true
    def job_name, do: "Minimal Test Job"

    @impl true
    def schedule, do: "30 2 * * *"

    @impl true
    def run, do: {:ok, 10}
  end

  describe "get_schedule_type/1" do
    test "returns :interval when module implements schedule_type/0" do
      assert Job.get_schedule_type(FullJob) == :interval
    end

    test "returns :cron by default when module doesn't implement schedule_type/0" do
      assert Job.get_schedule_type(MinimalJob) == :cron
    end
  end

  describe "enabled?/1" do
    test "returns false when module implements enabled?/0 returning false" do
      assert Job.enabled?(FullJob) == false
    end

    test "returns true by default when module doesn't implement enabled?/0" do
      assert Job.enabled?(MinimalJob) == true
    end
  end

  describe "get_metadata/1" do
    test "returns metadata map when module implements metadata/0" do
      metadata = Job.get_metadata(FullJob)

      assert metadata == %{key: "value", count: 42}
    end

    test "returns empty map when module doesn't implement metadata/0" do
      metadata = Job.get_metadata(MinimalJob)

      assert metadata == %{}
    end
  end

  describe "behaviour callbacks" do
    test "full job implements all required callbacks" do
      assert FullJob.job_id() == "full-job"
      assert FullJob.job_name() == "Full Test Job"
      assert FullJob.schedule() == "0 * * * *"
      assert FullJob.run() == :ok
    end

    test "minimal job implements only required callbacks" do
      assert MinimalJob.job_id() == "minimal-job"
      assert MinimalJob.job_name() == "Minimal Test Job"
      assert MinimalJob.schedule() == "30 2 * * *"
      assert MinimalJob.run() == {:ok, 10}
    end

    test "run can return :ok" do
      assert FullJob.run() == :ok
    end

    test "run can return {:ok, count}" do
      assert MinimalJob.run() == {:ok, 10}
    end
  end
end
