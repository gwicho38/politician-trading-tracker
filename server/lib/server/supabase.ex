defmodule Server.Supabase do
  @moduledoc """
  Supabase REST API client for interacting with Supabase.
  Uses PostgREST API for database operations instead of direct Postgres connection.
  """

  # Supabase project URL (hosted)
  @base_url System.get_env("SUPABASE_URL") || "https://uljsqvwkomdrlnofmlad.supabase.co"

  # Service role key for full database access
  @service_key System.get_env("SUPABASE_SERVICE_KEY") ||
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjgwMjI0NCwiZXhwIjoyMDcyMzc4MjQ0fQ.4364sQbTJQd4IcxEQG6mPiOUw1iJ2bdKfV6W4oRqHvs"

  @doc """
  Query a table with optional parameters.

  ## Examples

      # Get all scheduled jobs
      Server.Supabase.query("scheduled_jobs")

      # Get jobs with filters
      Server.Supabase.query("scheduled_jobs", select: "*", enabled: "eq.true")

      # Query from jobs schema
      Server.Supabase.query("scheduled_jobs", schema: "jobs")
  """
  def query(table, opts \\ []) do
    {schema, params} = Keyword.pop(opts, :schema, "public")

    headers = base_headers(schema)

    case Req.get("#{@base_url}/rest/v1/#{table}", headers: headers, params: params) do
      {:ok, %{status: status, body: body}} when status in 200..299 ->
        {:ok, body}

      {:ok, %{status: status, body: body}} ->
        {:error, %{status: status, body: body}}

      {:error, reason} ->
        {:error, reason}
    end
  end

  @doc """
  Get a single record by column value.

  ## Examples

      Server.Supabase.get_by("scheduled_jobs", :job_id, "scheduled-sync", schema: "jobs")
  """
  def get_by(table, column, value, opts \\ []) do
    {schema, params} = Keyword.pop(opts, :schema, "public")
    params = Keyword.merge(params, [{column, "eq.#{value}"}])

    headers = base_headers(schema) ++ [{"Accept", "application/vnd.pgrst.object+json"}]

    case Req.get("#{@base_url}/rest/v1/#{table}", headers: headers, params: params) do
      {:ok, %{status: 200, body: body}} ->
        {:ok, body}

      {:ok, %{status: 406, body: _}} ->
        {:ok, nil}

      {:ok, %{status: status, body: body}} ->
        {:error, %{status: status, body: body}}

      {:error, reason} ->
        {:error, reason}
    end
  end

  @doc """
  Insert a record into a table.

  ## Examples

      Server.Supabase.insert("job_executions", %{
        job_id: "scheduled-sync",
        status: "running"
      }, schema: "jobs")
  """
  def insert(table, data, opts \\ []) do
    {schema, _params} = Keyword.pop(opts, :schema, "public")

    headers =
      base_headers(schema) ++
        [
          {"Content-Type", "application/json"},
          {"Prefer", "return=representation"}
        ]

    case Req.post("#{@base_url}/rest/v1/#{table}", headers: headers, json: data) do
      {:ok, %{status: status, body: body}} when status in 200..299 ->
        {:ok, body}

      {:ok, %{status: status, body: body}} ->
        {:error, %{status: status, body: body}}

      {:error, reason} ->
        {:error, reason}
    end
  end

  @doc """
  Update records in a table matching the filter.

  ## Examples

      Server.Supabase.update("scheduled_jobs", %{last_run_at: DateTime.utc_now()},
        job_id: "eq.scheduled-sync", schema: "jobs")
  """
  def update(table, data, opts) do
    {schema, filters} = Keyword.pop(opts, :schema, "public")

    headers =
      base_headers(schema) ++
        [
          {"Content-Type", "application/json"},
          {"Prefer", "return=representation"}
        ]

    case Req.patch("#{@base_url}/rest/v1/#{table}", headers: headers, json: data, params: filters) do
      {:ok, %{status: status, body: body}} when status in 200..299 ->
        {:ok, body}

      {:ok, %{status: status, body: body}} ->
        {:error, %{status: status, body: body}}

      {:error, reason} ->
        {:error, reason}
    end
  end

  @doc """
  Delete records from a table matching the filter.

  ## Examples

      Server.Supabase.delete("job_executions", job_id: "eq.old-job", schema: "jobs")
  """
  def delete(table, opts) do
    {schema, filters} = Keyword.pop(opts, :schema, "public")

    headers = base_headers(schema)

    case Req.delete("#{@base_url}/rest/v1/#{table}", headers: headers, params: filters) do
      {:ok, %{status: status}} when status in 200..299 ->
        :ok

      {:ok, %{status: status, body: body}} ->
        {:error, %{status: status, body: body}}

      {:error, reason} ->
        {:error, reason}
    end
  end

  @doc """
  Call a Supabase Edge Function.

  ## Options

  - `:timeout` - Request timeout in milliseconds (default: 30_000)

  ## Examples

      Server.Supabase.invoke("scheduled-sync", %{type: "update-stats"})
      Server.Supabase.invoke("scheduled-sync", %{type: "update-stats"}, timeout: 60_000)
  """
  def invoke(function_name, body \\ %{}, opts \\ []) do
    timeout = Keyword.get(opts, :timeout, 30_000)

    headers = [
      {"Authorization", "Bearer #{@service_key}"},
      {"Content-Type", "application/json"}
    ]

    case Req.post("#{@base_url}/functions/v1/#{function_name}",
           headers: headers,
           json: body,
           receive_timeout: timeout
         ) do
      {:ok, %{status: status, body: body}} when status in 200..299 ->
        {:ok, body}

      {:ok, %{status: status, body: body}} ->
        {:error, %{status: status, body: body}}

      {:error, reason} ->
        {:error, reason}
    end
  end

  # Private helpers

  defp base_headers(schema) do
    [
      {"apikey", @service_key},
      {"Authorization", "Bearer #{@service_key}"},
      {"Accept-Profile", schema}
    ]
  end
end
