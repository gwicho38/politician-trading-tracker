defmodule Server.Scheduler.Jobs.SyncDataJob do
  @moduledoc """
  General data synchronization job.

  Invokes the sync-data edge function for general data
  synchronization tasks including ticker data and market info.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "sync-data"

  # TODO: Review this function
  @impl true
  def job_name, do: "Data Sync"

  # TODO: Review this function
  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[SyncDataJob] Starting data sync")

    # sync-data uses path-based routing, call update-stats endpoint
    case Server.SupabaseClient.invoke("sync-data", path: "update-stats", timeout: 60_000) do
      {:ok, response} ->
        Logger.info("[SyncDataJob] Data sync completed: #{inspect(response)}")
        :ok

      {:error, reason} ->
        Logger.error("[SyncDataJob] Data sync failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "General data synchronization for tickers and market info",
      edge_function: "sync-data"
    }
  end
end
