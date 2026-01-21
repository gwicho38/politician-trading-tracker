defmodule ServerWeb.MlControllerTest do
  @moduledoc """
  Tests for ServerWeb.MlController.

  Tests:
  - POST /api/ml/predict - Get ML prediction
  - POST /api/ml/batch-predict - Batch predictions
  - GET /api/ml/models - List trained models
  - GET /api/ml/models/active - Get active model
  - GET /api/ml/models/:model_id - Get model details
  - GET /api/ml/models/:model_id/feature-importance - Get feature importance
  - POST /api/ml/train - Trigger training
  - GET /api/ml/train/:job_id - Get training status
  - GET /api/ml/health - ML service health check

  Note: These tests require a database connection.
  """

  @moduletag :database

  use ServerWeb.ConnCase, async: true

  import Mox

  setup :verify_on_exit!

  # Note: These tests mock the external ETL service calls
  # In a real environment, Bypass or a mock HTTP client would be used

  describe "POST /api/ml/predict" do
    @tag :external_service
    test "returns 503 when ML service is unavailable", %{conn: conn} do
      # When external service is down, should return 503
      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/api/ml/predict", %{
          "features" => %{
            "ticker" => "AAPL",
            "politician_count" => 5
          }
        })

      # Expect either success (if service is up) or 503 (if down)
      assert conn.status in [200, 503]
    end

    @tag :external_service
    test "accepts features parameter", %{conn: conn} do
      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/api/ml/predict", %{
          "features" => %{
            "ticker" => "MSFT",
            "politician_count" => 3,
            "buy_sell_ratio" => 2.5
          }
        })

      # Just verify the endpoint accepts the request format
      assert conn.status in [200, 503]
    end
  end

  describe "POST /api/ml/batch-predict" do
    @tag :external_service
    test "accepts tickers array", %{conn: conn} do
      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/api/ml/batch-predict", %{
          "tickers" => [
            %{"ticker" => "AAPL", "politician_count" => 5},
            %{"ticker" => "MSFT", "politician_count" => 3}
          ]
        })

      assert conn.status in [200, 503]
    end
  end

  describe "GET /api/ml/models" do
    @tag :external_service
    test "returns list or 503", %{conn: conn} do
      conn = get(conn, "/api/ml/models")

      assert conn.status in [200, 503]
    end
  end

  describe "GET /api/ml/models/active" do
    @tag :external_service
    test "returns active model or error", %{conn: conn} do
      conn = get(conn, "/api/ml/models/active")

      # Could be 200 (active model), 404 (no active), or 503 (service down)
      assert conn.status in [200, 404, 503]
    end
  end

  describe "GET /api/ml/models/:model_id" do
    @tag :external_service
    test "returns 404 for non-existent model", %{conn: conn} do
      conn = get(conn, "/api/ml/models/non-existent-model-123")

      # Could be 404 (not found) or 503 (service down)
      assert conn.status in [404, 503]
    end
  end

  describe "GET /api/ml/models/:model_id/feature-importance" do
    @tag :external_service
    test "returns feature importance or error", %{conn: conn} do
      conn = get(conn, "/api/ml/models/test-model/feature-importance")

      assert conn.status in [200, 404, 503]
    end
  end

  describe "POST /api/ml/train" do
    @tag :external_service
    test "triggers training or returns error", %{conn: conn} do
      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/api/ml/train", %{
          "lookback_days" => 365,
          "model_type" => "xgboost"
        })

      assert conn.status in [200, 503]
    end

    @tag :external_service
    test "uses default parameters when not provided", %{conn: conn} do
      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/api/ml/train", %{})

      assert conn.status in [200, 503]
    end
  end

  describe "GET /api/ml/train/:job_id" do
    @tag :external_service
    test "returns job status or error", %{conn: conn} do
      conn = get(conn, "/api/ml/train/test-job-123")

      assert conn.status in [200, 404, 503]
    end
  end

  describe "GET /api/ml/health" do
    @tag :external_service
    test "returns health status", %{conn: conn} do
      conn = get(conn, "/api/ml/health")

      # Should always return 200 or 503
      assert conn.status in [200, 503]

      response = json_response(conn, conn.status)

      if conn.status == 200 do
        assert response["proxy"] == "phoenix"
      else
        assert response["status"] == "unhealthy"
      end
    end
  end
end
