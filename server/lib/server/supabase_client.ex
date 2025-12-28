defmodule Server.SupabaseClient do
  @moduledoc """
  HTTP client for calling Supabase Edge Functions.

  Uses Finch for HTTP requests with proper authentication headers.
  The service role key is required for server-side function invocations.
  """

  require Logger

  @base_url "https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1"
  @timeout 30_000

  @doc """
  Invokes a Supabase Edge Function by name.

  ## Parameters
    - `function_name` - Name of the edge function (e.g., "alpaca-account")
    - `opts` - Optional keyword list:
      - `:method` - HTTP method (default: :post)
      - `:path` - Additional path segment for routing (e.g., "update-stats")
      - `:query` - Query parameters as map (e.g., %{mode: "quick"})
      - `:body` - Request body as map (will be JSON encoded)
      - `:timeout` - Request timeout in ms (default: 30000)

  ## Returns
    - `{:ok, response_body}` on success (2xx status)
    - `{:error, reason}` on failure

  ## Example
      Server.SupabaseClient.invoke("scheduled-sync")
      Server.SupabaseClient.invoke("scheduled-sync", query: %{mode: "quick"})
      Server.SupabaseClient.invoke("sync-data", path: "update-stats")
      Server.SupabaseClient.invoke("trading-signals", path: "generate-signals", body: %{lookbackDays: 30})
  """
  @spec invoke(String.t(), keyword()) :: {:ok, map() | String.t()} | {:error, term()}
  def invoke(function_name, opts \\ []) do
    method = Keyword.get(opts, :method, :post)
    path = Keyword.get(opts, :path)
    query = Keyword.get(opts, :query, %{})
    body = Keyword.get(opts, :body, %{})
    timeout = Keyword.get(opts, :timeout, @timeout)

    base_path =
      case path do
        nil -> "#{@base_url}/#{function_name}"
        path -> "#{@base_url}/#{function_name}/#{path}"
      end

    url =
      case query do
        q when q == %{} -> base_path
        q -> "#{base_path}?#{URI.encode_query(q)}"
      end

    case get_service_key() do
      {:ok, service_key} ->
        do_request(method, url, body, service_key, timeout)

      {:error, reason} ->
        Logger.error("Failed to get Supabase service key: #{inspect(reason)}")
        {:error, reason}
    end
  end

  defp do_request(method, url, body, service_key, timeout) do
    headers = [
      {"Authorization", "Bearer #{service_key}"},
      {"Content-Type", "application/json"},
      {"apikey", service_key}
    ]

    json_body = if body == %{}, do: "{}", else: Jason.encode!(body)

    request = Finch.build(method, url, headers, json_body)

    case Finch.request(request, Server.Finch, receive_timeout: timeout) do
      {:ok, %Finch.Response{status: status, body: response_body}}
      when status >= 200 and status < 300 ->
        parse_response(response_body)

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        Logger.warning(
          "Edge function #{url} returned status #{status}: #{String.slice(response_body, 0, 500)}"
        )

        {:error, {:http_error, status, response_body}}

      {:error, reason} = error ->
        Logger.error("HTTP request to #{url} failed: #{inspect(reason)}")
        error
    end
  end

  defp parse_response(body) when byte_size(body) == 0 do
    {:ok, %{}}
  end

  defp parse_response(body) do
    case Jason.decode(body) do
      {:ok, parsed} -> {:ok, parsed}
      {:error, _} -> {:ok, body}
    end
  end

  defp get_service_key do
    case Application.get_env(:server, :supabase_service_key) do
      nil -> {:error, :missing_service_key}
      key when is_binary(key) and byte_size(key) > 0 -> {:ok, key}
      _ -> {:error, :invalid_service_key}
    end
  end
end
