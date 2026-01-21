defmodule ServerWeb.HealthControllerTest do
  @moduledoc """
  Tests for ServerWeb.HealthController.

  Tests:
  - GET / - Liveness check
  - GET /health - Liveness check (alternate route)
  - GET /ready - Readiness check
  - GET /health/ready - Readiness check (alternate route)

  Note: These tests require a database connection.
  """

  @moduletag :database

  use ServerWeb.ConnCase, async: true

  import Mox

  # Allow mocks to be called from async tests
  setup :verify_on_exit!

  describe "GET / (liveness)" do
    test "returns 200 with status ok", %{conn: conn} do
      conn = get(conn, "/")

      assert json_response(conn, 200) == %{
               "status" => "ok",
               "version" => "0.1.0"
             }
    end
  end

  describe "GET /health (liveness)" do
    test "returns 200 with status ok", %{conn: conn} do
      conn = get(conn, "/health")

      assert json_response(conn, 200) == %{
               "status" => "ok",
               "version" => "0.1.0"
             }
    end

    test "includes version string", %{conn: conn} do
      conn = get(conn, "/health")
      response = json_response(conn, 200)

      assert is_binary(response["version"])
    end
  end

  describe "GET /ready (readiness)" do
    test "returns 200 when database is connected", %{conn: conn} do
      # The DataCase setup ensures database is available
      conn = get(conn, "/ready")
      response = json_response(conn, 200)

      assert response["status"] == "ok"
      assert response["database"] == "connected"
      assert response["version"] == "0.1.0"
    end

    test "includes database status", %{conn: conn} do
      conn = get(conn, "/ready")
      response = json_response(conn, 200)

      assert Map.has_key?(response, "database")
    end
  end

  describe "GET /health/ready (readiness alternate)" do
    test "returns 200 when database is connected", %{conn: conn} do
      conn = get(conn, "/health/ready")
      response = json_response(conn, 200)

      assert response["status"] == "ok"
      assert response["database"] == "connected"
    end
  end
end
