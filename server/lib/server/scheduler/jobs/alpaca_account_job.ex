defmodule Server.Scheduler.Jobs.AlpacaAccountJob do
  @moduledoc """
  Syncs Alpaca trading account information.

  Invokes the alpaca-account edge function to retrieve and update
  account balance, buying power, and trading status.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "alpaca-account"

  @impl true
  def job_name, do: "Alpaca Account Sync"

  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("[AlpacaAccountJob] Starting account sync")

    case Server.SupabaseClient.invoke("alpaca-account") do
      {:ok, response} ->
        Logger.info("[AlpacaAccountJob] Account sync completed: #{inspect(response)}")
        :ok

      {:error, reason} ->
        Logger.error("[AlpacaAccountJob] Account sync failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Syncs Alpaca trading account information",
      edge_function: "alpaca-account"
    }
  end

end
