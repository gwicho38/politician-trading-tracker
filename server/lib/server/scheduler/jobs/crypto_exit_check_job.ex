defmodule Server.Scheduler.Jobs.CryptoExitCheckJob do
  @moduledoc """
  Monitors open crypto positions for stop-loss and take-profit triggers.

  Runs 24/7 (every 15 minutes) since crypto markets never close.
  Calls the same check-exits action but the edge function handles
  crypto positions with wider exit bands and crypto quote endpoints.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "crypto-exit-check"

  @impl true
  def job_name, do: "Crypto Position Exit Check"

  @impl true
  # Run every 15 minutes, 24/7, all days (crypto never sleeps)
  def schedule, do: "*/15 * * * *"

  @impl true
  def run do
    Logger.info("[CryptoExitCheckJob] Checking crypto positions for exit triggers")
    check_exits()
  end

  defp check_exits do
    case Server.SupabaseClient.invoke("reference-portfolio",
           body: %{"action" => "check-exits"},
           timeout: 120_000
         ) do
      {:ok, %{"success" => true, "closed" => closed, "summary" => summary}} ->
        wins = summary["wins"] || 0
        losses = summary["losses"] || 0

        if closed > 0 do
          Logger.info(
            "[CryptoExitCheckJob] Closed #{closed} positions (#{wins} wins, #{losses} losses)"
          )
        else
          Logger.debug("[CryptoExitCheckJob] No crypto exit triggers found")
        end

        {:ok, closed}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.debug("[CryptoExitCheckJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[CryptoExitCheckJob] Exit check failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[CryptoExitCheckJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Monitors crypto positions for stop-loss and take-profit triggers (24/7)",
      edge_function: "reference-portfolio",
      action: "check-exits",
      schedule_note: "Runs every 15 minutes, 24/7 (crypto markets never close)"
    }
  end
end
