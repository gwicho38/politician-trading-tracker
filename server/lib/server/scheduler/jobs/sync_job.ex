defmodule Server.Scheduler.Jobs.SyncJob do
  @moduledoc """
  Scheduled sync job for politician trading data.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "scheduled-sync"

  @impl true
  def job_name, do: "Scheduled Sync"

  @impl true
  def schedule, do: "* * * * *"

  @impl true
  def run do
    Logger.info("TODO -- implement sync logic")
    :ok
  end
end
