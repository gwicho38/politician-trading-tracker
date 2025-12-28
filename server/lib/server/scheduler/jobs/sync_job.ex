defmodule Server.Scheduler.Jobs.SyncJob do
  @moduledoc """
  Scheduled sync job for politician trading data.

  Invokes the scheduled-sync edge function which orchestrates
  the full data synchronization workflow.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "scheduled-sync"

  @impl true
  def job_name, do: "Scheduled Sync"

  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[SyncJob] Starting scheduled sync (quick mode)")

    # Use quick mode for faster execution (skips politician-parties update)
    case Server.SupabaseClient.invoke("scheduled-sync", query: %{mode: "quick"}, timeout: 60_000) do
      {:ok, response} ->
        Logger.info("[SyncJob] Scheduled sync completed: #{inspect(response)}")
        :ok

      {:error, reason} ->
        Logger.error("[SyncJob] Scheduled sync failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Quick data sync (chart data + stats)",
      edge_function: "scheduled-sync",
      mode: "quick"
    }
  end
end
