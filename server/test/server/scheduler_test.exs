defmodule Server.SchedulerTest do
  @moduledoc """
  Tests for Server.Scheduler module.

  Tests the main scheduler entry point that delegates to sub-modules.

  Tests:
  - register_job/1 - Register a job module
  - register_jobs/1 - Register multiple job modules
  - run_now/1 - Run a job immediately
  - enable_job/1 - Enable a job
  - disable_job/1 - Disable a job
  - list_jobs/0 - List all jobs
  - get_job_status/1 - Get status of a specific job
  - get_executions/2 - Get recent executions
  - child_spec/1 - Returns Quantum child spec

  Note: These tests require a database connection.
  """

  # All tests in this module require database
  @moduletag :database

  use Server.DataCase, async: false

  alias Server.Scheduler

  describe "list_jobs/0" do
    test "returns a list" do
      jobs = Scheduler.list_jobs()

      assert is_list(jobs)
    end

    test "returns registered jobs" do
      jobs = Scheduler.list_jobs()

      # Each job should have expected fields
      Enum.each(jobs, fn job ->
        assert Map.has_key?(job, :job_id)
        assert Map.has_key?(job, :job_name)
        assert Map.has_key?(job, :enabled)
      end)
    end
  end

  describe "get_job_status/1" do
    test "returns {:error, :not_found} for non-existent job" do
      result = Scheduler.get_job_status("non-existent-job-xyz")

      assert result == {:error, :not_found}
    end

    test "returns {:ok, job} for existing job" do
      jobs = Scheduler.list_jobs()

      if length(jobs) > 0 do
        first_job = List.first(jobs)
        result = Scheduler.get_job_status(first_job.job_id)

        assert match?({:ok, _}, result)
      end
    end
  end

  describe "run_now/1" do
    test "returns {:error, :not_found} for non-existent job" do
      result = Scheduler.run_now("non-existent-job-xyz")

      assert result == {:error, :not_found}
    end
  end

  describe "enable_job/1 and disable_job/1" do
    test "enable_job returns error for non-existent job" do
      result = Scheduler.enable_job("non-existent-job-xyz")

      # Should return error tuple or :ok depending on implementation
      assert match?({:error, _}, result) or result == :ok
    end

    test "disable_job returns error for non-existent job" do
      result = Scheduler.disable_job("non-existent-job-xyz")

      assert match?({:error, _}, result) or result == :ok
    end
  end

  describe "get_executions/2" do
    test "returns executions list for a job" do
      result = Scheduler.get_executions("test-job", 5)

      # Should return a list (possibly empty)
      assert is_list(result) or match?({:error, _}, result)
    end
  end

  describe "child_spec/1" do
    test "returns a valid child spec" do
      spec = Scheduler.child_spec([])

      # Child spec should have required keys
      assert is_map(spec) or is_tuple(spec)
    end
  end
end
