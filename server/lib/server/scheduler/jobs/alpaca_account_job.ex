defmodule Server.Scheduler.Jobs.AlpacaAccountJob do
  @moduledoc """
  Syncs Alpaca trading account information.

  Invokes the alpaca-account edge function to retrieve and update
  account balance, buying power, and trading status.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "alpaca-account"

  # TODO: Review this function
  @impl true
  def job_name, do: "Alpaca Account Sync"

  # TODO: Review this function
  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  # TODO: Review this function
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

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Syncs Alpaca trading account information",
      edge_function: "alpaca-account"
    }
  end

end
