defmodule Server.Scheduler.Jobs.ReferencePortfolioDailyResetJob do
  @moduledoc """
  Resets daily trading counters at market open.

  Runs at market open (9:30 AM EST) to reset:
  - trades_today: Number of trades executed today
  - day_return: Dollar return for the day
  - day_return_pct: Percentage return for the day

  This ensures the dashboard shows accurate daily metrics.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  # TODO: Review this function
  @impl true
  def job_id, do: "reference-portfolio-daily-reset"

  # TODO: Review this function
  @impl true
  def job_name, do: "Reference Portfolio Daily Reset"

  # TODO: Review this function
  @impl true
  # Run at 2:30 PM UTC (9:30 AM EST) - market open, Monday-Friday
  def schedule, do: "30 14 * * 1-5"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[ReferencePortfolioDailyResetJob] Resetting daily trading counters")

    case Server.SupabaseClient.invoke("reference-portfolio",
           body: %{"action" => "reset-daily-trades"},
           timeout: 10_000
         ) do
      {:ok, %{"success" => true}} ->
        Logger.info("[ReferencePortfolioDailyResetJob] Daily counters reset successfully")
        {:ok, 1}

      {:ok, %{"error" => error}} ->
        Logger.error("[ReferencePortfolioDailyResetJob] Reset failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[ReferencePortfolioDailyResetJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Resets daily trading counters (trades_today, day_return) at market open",
      edge_function: "reference-portfolio",
      action: "reset-daily-trades",
      schedule_note: "Runs at 9:30 AM EST (market open), Monday-Friday"
    }
  end
end
