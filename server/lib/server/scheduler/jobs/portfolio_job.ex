defmodule Server.Scheduler.Jobs.PortfolioJob do
  @moduledoc """
  Syncs portfolio positions and values.

  Invokes the portfolio edge function to retrieve and update
  current positions, market values, and P&L calculations.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "portfolio-sync"

  # TODO: Review this function
  @impl true
  def job_name, do: "Portfolio Sync"

  # TODO: Review this function
  @impl true
  # Every minute (testing)
  def schedule, do: "* * * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[PortfolioJob] Starting portfolio sync")

    case Server.SupabaseClient.invoke("portfolio") do
      {:ok, response} ->
        positions = get_in(response, ["positions"]) || []
        Logger.info("[PortfolioJob] Portfolio sync completed, positions: #{length(positions)}")
        {:ok, length(positions)}

      {:error, reason} ->
        Logger.error("[PortfolioJob] Portfolio sync failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Syncs portfolio positions and values from Alpaca",
      edge_function: "portfolio"
    }
  end

end
