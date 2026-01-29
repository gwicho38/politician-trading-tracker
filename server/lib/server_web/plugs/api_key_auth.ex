defmodule ServerWeb.Plugs.ApiKeyAuth do
  @moduledoc """
  API Key authentication plug for Phoenix.

  Validates API keys sent via:
  1. X-API-Key header (preferred)
  2. Authorization: Bearer header
  3. api_key query parameter (fallback)

  Uses constant-time comparison to prevent timing attacks.

  ## Configuration

  Set `ETL_API_KEY` environment variable in production.
  In development, auth can be disabled with `ETL_AUTH_DISABLED=true`.

  ## Usage

  Add to router pipeline:

      pipeline :api do
        plug :accepts, ["json"]
        plug ServerWeb.Plugs.ApiKeyAuth
      end

  Or for specific routes:

      plug ServerWeb.Plugs.ApiKeyAuth when action in [:create, :update, :delete]
  """

  import Plug.Conn
  require Logger

  @behaviour Plug

  # Public endpoints that don't require authentication
  @public_endpoints [
    "/",
    "/health",
    "/health/ready",
    "/ready"
  ]

  @impl true
  def init(opts), do: opts

  @impl true
  def call(conn, _opts) do
    # Check if auth is disabled (for development)
    if auth_disabled?() do
      conn
    else
      # Allow public endpoints
      if public_endpoint?(conn.request_path) do
        conn
      else
        authenticate(conn)
      end
    end
  end

  @doc """
  Check if a path is a public endpoint (no auth required).
  """
  def public_endpoint?(path) do
    Enum.any?(@public_endpoints, fn public_path ->
      path == public_path or String.starts_with?(path, public_path <> "/")
    end)
  end

  @doc """
  Check if auth is disabled via environment variable.
  """
  def auth_disabled? do
    case Application.get_env(:server, :auth_disabled) do
      true -> true
      "true" -> true
      _ -> false
    end
  end

  defp authenticate(conn) do
    api_key = extract_api_key(conn)

    case validate_api_key(api_key) do
      :ok ->
        # Store validation state in conn for logging/audit
        assign(conn, :api_key_validated, true)

      {:error, reason} ->
        log_auth_failure(conn, reason)

        conn
        |> put_status(:unauthorized)
        |> put_resp_header("www-authenticate", "ApiKey")
        |> put_resp_content_type("application/json")
        |> send_resp(401, Jason.encode!(%{detail: auth_error_message(reason)}))
        |> halt()
    end
  end

  @doc """
  Extract API key from request headers or query params.

  Priority order:
  1. X-API-Key header (preferred)
  2. Authorization: Bearer header
  3. api_key query parameter (fallback)
  """
  def extract_api_key(conn) do
    get_header(conn, "x-api-key") ||
      extract_bearer_token(conn) ||
      get_query_param(conn, "api_key")
  end

  defp get_header(conn, name) do
    case get_req_header(conn, name) do
      [value | _] -> value
      _ -> nil
    end
  end

  defp extract_bearer_token(conn) do
    case get_header(conn, "authorization") do
      "Bearer " <> token -> token
      _ -> nil
    end
  end

  defp get_query_param(conn, name) do
    conn = Plug.Conn.fetch_query_params(conn)
    Map.get(conn.query_params, name)
  end

  @doc """
  Validate an API key against the configured key.

  Returns :ok if valid, {:error, reason} otherwise.
  """
  def validate_api_key(nil), do: {:error, :missing_key}
  def validate_api_key(""), do: {:error, :empty_key}

  def validate_api_key(key) when is_binary(key) do
    case get_configured_key() do
      nil ->
        # No key configured - allow for backwards compatibility
        # Log a warning in production
        Logger.warning("API key auth enabled but no ETL_API_KEY configured")
        :ok

      configured_key ->
        if constant_time_compare(key, configured_key) do
          :ok
        else
          {:error, :invalid_key}
        end
    end
  end

  @doc """
  Get the configured API key from application config.
  """
  def get_configured_key do
    Application.get_env(:server, :api_key)
  end

  @doc """
  Constant-time string comparison to prevent timing attacks.

  Uses SHA256 hashing to ensure comparison takes the same time
  regardless of where strings differ.
  """
  def constant_time_compare(a, b) when is_binary(a) and is_binary(b) do
    :crypto.hash(:sha256, a) == :crypto.hash(:sha256, b)
  end

  def constant_time_compare(_, _), do: false

  defp auth_error_message(:missing_key) do
    "API key required. Provide via X-API-Key header, Authorization: Bearer, or api_key query parameter."
  end

  defp auth_error_message(:empty_key) do
    "API key cannot be empty."
  end

  defp auth_error_message(:invalid_key) do
    "Invalid API key."
  end

  defp log_auth_failure(conn, reason) do
    metadata = %{
      reason: reason,
      path: conn.request_path,
      method: conn.method,
      remote_ip: format_ip(conn.remote_ip),
      timestamp: DateTime.utc_now() |> DateTime.to_iso8601()
    }

    Logger.warning("API key authentication failed", metadata)
  end

  defp format_ip(nil), do: "unknown"
  defp format_ip(ip) when is_tuple(ip), do: ip |> Tuple.to_list() |> Enum.join(".")
  defp format_ip(ip), do: to_string(ip)
end
