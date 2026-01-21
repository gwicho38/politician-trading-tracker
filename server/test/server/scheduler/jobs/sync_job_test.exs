defmodule Server.Scheduler.Jobs.SyncJobTest do
  @moduledoc """
  Tests for Server.Scheduler.Jobs.SyncJob.

  Tests the scheduled sync job behaviour implementation.
  """

  use ExUnit.Case, async: true

  alias Server.Scheduler.Jobs.SyncJob

  describe "job_id/0" do
    test "returns scheduled-sync" do
      assert SyncJob.job_id() == "scheduled-sync"
    end
  end

  describe "job_name/0" do
    test "returns human-readable name" do
      name = SyncJob.job_name()

      assert is_binary(name)
      assert name == "Scheduled Sync"
    end
  end

  describe "schedule/0" do
    test "returns a cron expression" do
      schedule = SyncJob.schedule()

      assert is_binary(schedule)
      # Should be a valid cron expression
      assert String.contains?(schedule, "*")
    end
  end

  describe "metadata/0" do
    test "returns metadata map" do
      metadata = SyncJob.metadata()

      assert is_map(metadata)
    end

    test "includes description" do
      metadata = SyncJob.metadata()

      assert Map.has_key?(metadata, :description)
    end

    test "includes edge_function" do
      metadata = SyncJob.metadata()

      assert metadata.edge_function == "scheduled-sync"
    end

    test "includes mode" do
      metadata = SyncJob.metadata()

      assert metadata.mode == "quick"
    end
  end

  describe "run/0" do
    @tag :external_service
    test "returns :ok or {:error, _}" do
      result = SyncJob.run()

      assert result == :ok or match?({:error, _}, result)
    end
  end
end
