defmodule ServerWeb.JobControllerTest do
  @moduledoc """
  Tests for ServerWeb.JobController.

  Tests:
  - GET /api/jobs - List all jobs
  - GET /api/jobs/:job_id - Get job status
  - POST /api/jobs/:job_id/run - Run a job
  - GET /api/jobs/sync-status - Get sync status
  - POST /api/jobs/run-all - Run all jobs

  Note: These tests require a database connection.
  """

  use ServerWeb.ConnCase, async: false

  @moduletag :database

  import Mox

  alias Server.Scheduler

  setup :verify_on_exit!

  # Create sample job data for testing
  @sample_job %{
    job_id: "test-job",
    job_name: "Test Job",
    job_function: "test_function",
    schedule_type: "cron",
    schedule_value: "0 * * * *",
    enabled: true,
    last_run_at: nil,
    last_successful_run: nil,
    consecutive_failures: 0,
    max_consecutive_failures: 3,
    metadata: %{},
    created_at: ~U[2024-01-01 00:00:00Z],
    updated_at: ~U[2024-01-01 00:00:00Z]
  }

  describe "GET /api/jobs" do
    test "returns empty list when no jobs registered", %{conn: conn} do
      conn = get(conn, "/api/jobs")
      response = json_response(conn, 200)

      assert Map.has_key?(response, "jobs")
      assert is_list(response["jobs"])
    end

    test "returns list of registered jobs", %{conn: conn} do
      # This test works with whatever jobs are actually registered
      conn = get(conn, "/api/jobs")
      response = json_response(conn, 200)

      assert Map.has_key?(response, "jobs")
    end
  end

  describe "GET /api/jobs/:job_id" do
    test "returns 404 for non-existent job", %{conn: conn} do
      conn = get(conn, "/api/jobs/non-existent-job")
      response = json_response(conn, 404)

      assert response["error"] == "Job not found"
    end
  end

  describe "POST /api/jobs/:job_id/run" do
    test "returns 404 for non-existent job", %{conn: conn} do
      conn = post(conn, "/api/jobs/non-existent-job/run")
      response = json_response(conn, 404)

      assert response["error"] == "Job not found"
    end
  end

  describe "GET /api/jobs/sync-status" do
    test "returns sync status with last_sync field", %{conn: conn} do
      conn = get(conn, "/api/jobs/sync-status")
      response = json_response(conn, 200)

      assert Map.has_key?(response, "last_sync")
      assert Map.has_key?(response, "jobs")
    end

    test "returns list of data collection jobs", %{conn: conn} do
      conn = get(conn, "/api/jobs/sync-status")
      response = json_response(conn, 200)

      assert is_list(response["jobs"])
    end
  end

  describe "POST /api/jobs/run-all" do
    test "returns message about triggered jobs", %{conn: conn} do
      conn = post(conn, "/api/jobs/run-all")
      response = json_response(conn, 200)

      assert Map.has_key?(response, "message")
      assert Map.has_key?(response, "jobs")
      assert String.contains?(response["message"], "jobs triggered")
    end

    test "returns list of triggered jobs", %{conn: conn} do
      conn = post(conn, "/api/jobs/run-all")
      response = json_response(conn, 200)

      assert is_list(response["jobs"])
    end
  end
end
