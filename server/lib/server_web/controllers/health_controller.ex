defmodule ServerWeb.HealthController do
  @moduledoc """
  Health check endpoints for monitoring and load balancers.
  """

  use ServerWeb, :controller

  # TODO: Review this function
  @doc """
  Basic liveness check - returns 200 if the server is running.

  GET /health
  """
  def index(conn, _params) do
    json(conn, %{status: "ok", version: Server.version()})
  end

  # TODO: Review this function
  @doc """
  Readiness check - verifies database connectivity.

  GET /health/ready
  """
  def ready(conn, _params) do
    case Server.health_check() do
      :ok ->
        json(conn, %{
          status: "ok",
          database: "connected",
          version: Server.version()
        })

      {:error, reason} ->
        conn
        |> put_status(:service_unavailable)
        |> json(%{
          status: "error",
          database: "disconnected",
          error: reason
        })
    end
  end
end
