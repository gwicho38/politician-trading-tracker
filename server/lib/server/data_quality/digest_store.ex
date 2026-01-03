defmodule Server.DataQuality.DigestStore do
  @moduledoc """
  GenServer for accumulating data quality issues between digest sends.

  Issues are stored in memory and cleared after the daily digest is sent.
  This provides thread-safe accumulation of warnings for batch notifications.
  """

  use GenServer

  require Logger

  # ============================================================================
  # Client API
  # ============================================================================

  @doc """
  Starts the DigestStore GenServer.
  """
  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc """
  Adds an issue to the digest queue.

  ## Parameters
    - issue: Map with keys :severity, :type, :table, :description, etc.
  """
  @spec add_issue(map()) :: :ok
  def add_issue(issue) when is_map(issue) do
    GenServer.cast(__MODULE__, {:add_issue, issue})
  end

  @doc """
  Gets all accumulated issues without clearing them.
  """
  @spec get_issues() :: [map()]
  def get_issues do
    GenServer.call(__MODULE__, :get_issues)
  end

  @doc """
  Gets and clears all accumulated issues (used when sending digest).
  """
  @spec flush_issues() :: [map()]
  def flush_issues do
    GenServer.call(__MODULE__, :flush_issues)
  end

  @doc """
  Gets the count of accumulated issues by severity.
  """
  @spec get_counts() :: %{critical: integer(), warning: integer(), info: integer()}
  def get_counts do
    GenServer.call(__MODULE__, :get_counts)
  end

  @doc """
  Clears all accumulated issues without returning them.
  """
  @spec clear() :: :ok
  def clear do
    GenServer.cast(__MODULE__, :clear)
  end

  # ============================================================================
  # Server Callbacks
  # ============================================================================

  @impl true
  def init(_opts) do
    Logger.info("[DigestStore] Started data quality digest store")
    {:ok, %{issues: [], started_at: DateTime.utc_now()}}
  end

  @impl true
  def handle_cast({:add_issue, issue}, state) do
    issue_with_timestamp = Map.put(issue, :queued_at, DateTime.utc_now())
    {:noreply, %{state | issues: [issue_with_timestamp | state.issues]}}
  end

  @impl true
  def handle_cast(:clear, state) do
    {:noreply, %{state | issues: [], started_at: DateTime.utc_now()}}
  end

  @impl true
  def handle_call(:get_issues, _from, state) do
    {:reply, Enum.reverse(state.issues), state}
  end

  @impl true
  def handle_call(:flush_issues, _from, state) do
    issues = Enum.reverse(state.issues)
    {:reply, issues, %{state | issues: [], started_at: DateTime.utc_now()}}
  end

  @impl true
  def handle_call(:get_counts, _from, state) do
    counts =
      state.issues
      |> Enum.group_by(fn issue ->
        case issue[:severity] do
          :critical -> :critical
          "critical" -> :critical
          :warning -> :warning
          "warning" -> :warning
          _ -> :info
        end
      end)
      |> Enum.map(fn {severity, issues} -> {severity, length(issues)} end)
      |> Map.new()

    result = %{
      critical: Map.get(counts, :critical, 0),
      warning: Map.get(counts, :warning, 0),
      info: Map.get(counts, :info, 0)
    }

    {:reply, result, state}
  end
end
