defmodule Server.Scheduler.Jobs.OrdersJob do
  @moduledoc """
  Syncs trading orders with Alpaca.

  Invokes the orders edge function to retrieve and update
  order status, fills, and pending orders.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "orders-sync"

  @impl true
  def job_name, do: "Orders Sync"

  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[OrdersJob] Starting orders sync")

    # Call sync-orders endpoint which syncs all orders from Alpaca
    case Server.SupabaseClient.invoke("orders", path: "sync-orders", timeout: 60_000) do
      {:ok, response} ->
        synced = get_in(response, ["summary", "synced"]) || 0
        updated = get_in(response, ["summary", "updated"]) || 0
        Logger.info("[OrdersJob] Orders sync completed, synced: #{synced}, updated: #{updated}")
        {:ok, synced + updated}

      {:error, reason} ->
        Logger.error("[OrdersJob] Orders sync failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Syncs trading orders with Alpaca",
      edge_function: "orders"
    }
  end

end
