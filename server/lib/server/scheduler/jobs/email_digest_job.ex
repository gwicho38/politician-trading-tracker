defmodule Server.Scheduler.Jobs.EmailDigestJob do
  @moduledoc """
  Daily Email Digest Job

  Runs at 8 AM UTC to send accumulated data quality warnings.
  Uses the DigestStore GenServer to collect and flush issues.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  alias Server.DataQuality.EmailAlerter

  @job_id "email-digest"

  @impl true
  def job_id, do: @job_id

  @impl true
  def job_name, do: "Email Digest (Daily)"

  @impl true
  def schedule, do: "0 8 * * *"

  @impl true
  def schedule_type, do: :cron

  @impl true
  def run do
    start_time = System.monotonic_time(:millisecond)
    Logger.info("[EmailDigestJob] Starting daily digest send")

    result =
      case EmailAlerter.send_daily_digest() do
        :ok ->
          {:ok, %{status: "sent"}}

        {:error, :email_disabled} ->
          Logger.info("[EmailDigestJob] Email disabled, skipping digest")
          {:ok, %{status: "skipped", reason: "email_disabled"}}

        {:error, reason} ->
          Logger.error("[EmailDigestJob] Failed to send digest: #{inspect(reason)}")
          {:error, reason}
      end

    duration = System.monotonic_time(:millisecond) - start_time
    Logger.info("[EmailDigestJob] Completed in #{duration}ms")

    result
  end

  @impl true
  def metadata do
    %{
      description: "Sends daily data quality digest email",
      schedule_description: "Daily at 8 AM UTC"
    }
  end
end
