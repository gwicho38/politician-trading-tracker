defmodule ServerWeb.MlController do
  @moduledoc """
  Controller for ML prediction and model management API endpoints.

  Acts as a proxy to the Python ETL service's ML endpoints,
  with optional caching for predictions.
  """

  use ServerWeb, :controller

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  defp etl_api_key do
    Application.get_env(:server, :api_key) || System.get_env("ETL_API_KEY") || ""
  end

  # TODO: Review this function
  @doc """
  Get ML prediction for a ticker's features.
  POST /api/ml/predict

  Request body:
    {
      "features": {
        "ticker": "AAPL",
        "politician_count": 5,
        "buy_sell_ratio": 2.5,
        ...
      },
      "use_cache": true
    }
  """
  def predict(conn, %{"features" => features} = params) do
    use_cache = Map.get(params, "use_cache", true)

    case call_etl_predict(features, use_cache) do
      {:ok, prediction} ->
        json(conn, prediction)

      {:error, reason} ->
        Logger.error("[MlController] Prediction failed: #{inspect(reason)}")

        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  Batch prediction for multiple tickers.
  POST /api/ml/batch-predict

  Request body:
    {
      "tickers": [
        {"ticker": "AAPL", "politician_count": 5, ...},
        {"ticker": "MSFT", "politician_count": 3, ...}
      ],
      "use_cache": true
    }
  """
  def batch_predict(conn, %{"tickers" => tickers} = params) do
    use_cache = Map.get(params, "use_cache", true)

    case call_etl_batch_predict(tickers, use_cache) do
      {:ok, predictions} ->
        json(conn, %{predictions: predictions})

      {:error, reason} ->
        Logger.error("[MlController] Batch prediction failed: #{inspect(reason)}")

        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  List trained models.
  GET /api/ml/models
  """
  def list_models(conn, _params) do
    case call_etl_get("/ml/models") do
      {:ok, data} ->
        json(conn, data)

      {:error, reason} ->
        Logger.error("[MlController] Failed to list models: #{inspect(reason)}")

        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable"})
    end
  end

  # TODO: Review this function
  @doc """
  Get the active model's info.
  GET /api/ml/models/active
  """
  def active_model(conn, _params) do
    case call_etl_get("/ml/models/active") do
      {:ok, data} ->
        json(conn, data)

      {:error, {:http_error, 404, _}} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "No active model found"})

      {:error, reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  Get model details.
  GET /api/ml/models/:model_id
  """
  def show_model(conn, %{"model_id" => model_id}) do
    case call_etl_get("/ml/models/#{model_id}") do
      {:ok, data} ->
        json(conn, data)

      {:error, {:http_error, 404, _}} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Model not found"})

      {:error, reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  Get feature importance for a model.
  GET /api/ml/models/:model_id/feature-importance
  """
  def feature_importance(conn, %{"model_id" => model_id}) do
    case call_etl_get("/ml/models/#{model_id}/feature-importance") do
      {:ok, data} ->
        json(conn, data)

      {:error, {:http_error, 404, _}} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Model not found"})

      {:error, reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  Trigger model training.
  POST /api/ml/train
  """
  def trigger_training(conn, params) do
    lookback_days = Map.get(params, "lookback_days", 365)
    model_type = Map.get(params, "model_type", "xgboost")

    case call_etl_post("/ml/train", %{lookback_days: lookback_days, model_type: model_type}) do
      {:ok, data} ->
        json(conn, data)

      {:error, reason} ->
        Logger.error("[MlController] Training trigger failed: #{inspect(reason)}")

        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  Get training job status.
  GET /api/ml/train/:job_id
  """
  def training_status(conn, %{"job_id" => job_id}) do
    case call_etl_get("/ml/train/#{job_id}") do
      {:ok, data} ->
        json(conn, data)

      {:error, {:http_error, 404, _}} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Training job not found"})

      {:error, reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", details: inspect(reason)})
    end
  end

  # TODO: Review this function
  @doc """
  ML service health check.
  GET /api/ml/health
  """
  def health(conn, _params) do
    case call_etl_get("/ml/health") do
      {:ok, data} ->
        json(conn, Map.put(data, "proxy", "phoenix"))

      {:error, _reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{error: "ML service unavailable", status: "unhealthy"})
    end
  end

  # ============================================================================
  # Private HTTP Helpers
  # ============================================================================

  # TODO: Review this function
  defp call_etl_predict(features, use_cache) do
    body = Jason.encode!(%{features: features, use_cache: use_cache})
    call_etl_post("/ml/predict", body, raw: true)
  end

  # TODO: Review this function
  defp call_etl_batch_predict(tickers, use_cache) do
    body = Jason.encode!(%{tickers: tickers, use_cache: use_cache})
    call_etl_post("/ml/batch-predict", body, raw: true)
  end

  # TODO: Review this function
  defp call_etl_get(path) do
    url = "#{@etl_service_url}#{path}"

    request =
      Finch.build(
        :get,
        url,
        [{"Accept", "application/json"}, {"X-API-Key", etl_api_key()}]
      )

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        Jason.decode(response_body)

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  # TODO: Review this function
  defp call_etl_post(path, body, opts \\ [])

  # TODO: Review this function
  defp call_etl_post(path, body, opts) when is_map(body) do
    call_etl_post(path, Jason.encode!(body), opts)
  end

  # TODO: Review this function
  defp call_etl_post(path, body, _opts) when is_binary(body) do
    url = "#{@etl_service_url}#{path}"

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"},
          {"X-API-Key", etl_api_key()}
        ],
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        Jason.decode(response_body)

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end
end
