defmodule Server.Scheduler.Jobs.BatchRetrainingJob do
  @moduledoc """
  Checks for data changes and triggers ML model retraining when threshold reached.

  Runs every hour, counts trading disclosures changed since last training.
  If changes >= threshold (default 500), triggers retraining via Python ETL service.

  Uses Supabase RPC functions:
  - `get_retraining_stats()` - returns last_training_at, threshold, and live change count
  - `reset_retraining_stats(timestamp)` - resets baseline after training triggered

  The weekly MlTrainingJob remains as a fallback for guaranteed retraining.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @job_id "batch-retraining"
  @default_threshold 500
  @etl_base_url "https://politician-trading-etl.fly.dev"
  @supabase_base_url "https://uljsqvwkomdrlnofmlad.supabase.co"

  @impl true
  def job_id, do: @job_id

  @impl true
  def job_name, do: "Batch ML Retraining Check"

  @impl true
  # Every hour at :00 minutes
  def schedule, do: "0 * * * *"

  @impl true
  def schedule_type, do: :cron

  @impl true
  def run do
    Logger.info("[BatchRetrainingJob] Checking for data changes...")

    with {:ok, stats} <- get_retraining_stats(),
         {:ok, result} <- maybe_trigger_retrain(stats) do
      Logger.info("[BatchRetrainingJob] Completed: #{inspect(result)}")
      {:ok, result}
    else
      {:error, reason} = error ->
        Logger.error("[BatchRetrainingJob] Failed: #{inspect(reason)}")
        error
    end
  end

  # Get current retraining stats from Supabase via RPC
  defp get_retraining_stats do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/rpc/get_retraining_stats"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ]

        request = Finch.build(:post, url, headers, "{}")

        case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
          {:ok, %Finch.Response{status: 200, body: body}} ->
            case Jason.decode(body) do
              {:ok, [stats | _]} ->
                # RPC returns array, take first row
                {:ok, parse_stats(stats)}

              {:ok, []} ->
                # No stats row exists, use defaults
                Logger.warning("[BatchRetrainingJob] No retraining stats found, using defaults")
                {:ok, %{
                  last_training_at: nil,
                  threshold: @default_threshold,
                  current_change_count: 0
                }}

              {:error, decode_error} ->
                {:error, {:json_decode_error, decode_error}}
            end

          {:ok, %Finch.Response{status: status, body: body}} ->
            {:error, {:http_error, status, body}}

          {:error, reason} ->
            {:error, {:request_failed, reason}}
        end

      {:error, reason} ->
        {:error, {:no_service_key, reason}}
    end
  end

  defp parse_stats(stats) do
    %{
      last_training_at: stats["last_training_at"],
      threshold: stats["threshold"] || @default_threshold,
      current_change_count: stats["current_change_count"] || 0
    }
  end

  # Trigger training if threshold reached
  defp maybe_trigger_retrain(%{current_change_count: count, threshold: threshold} = _stats)
       when count >= threshold do
    Logger.info(
      "[BatchRetrainingJob] Threshold reached: #{count} changes >= #{threshold}, triggering retrain..."
    )

    case trigger_training() do
      {:ok, training_job_id} ->
        # Reset stats baseline to now
        case reset_stats_after_trigger() do
          :ok ->
            {:ok, %{
              action: :triggered,
              changes: count,
              threshold: threshold,
              training_job_id: training_job_id
            }}

          {:error, reset_error} ->
            Logger.warning("[BatchRetrainingJob] Training triggered but stats reset failed: #{inspect(reset_error)}")
            {:ok, %{
              action: :triggered_with_reset_error,
              changes: count,
              training_job_id: training_job_id,
              reset_error: reset_error
            }}
        end

      {:error, reason} ->
        {:error, {:training_trigger_failed, reason}}
    end
  end

  defp maybe_trigger_retrain(%{current_change_count: count, threshold: threshold}) do
    Logger.info(
      "[BatchRetrainingJob] Below threshold: #{count} changes < #{threshold}, skipping"
    )

    {:ok, %{
      action: :skipped,
      changes: count,
      threshold: threshold
    }}
  end

  # Trigger ML training via Python ETL service
  defp trigger_training do
    url = "#{@etl_base_url}/ml/train"

    body =
      Jason.encode!(%{
        lookback_days: 365,
        model_type: "xgboost",
        triggered_by: "batch_retraining"
      })

    headers = [
      {"Content-Type", "application/json"},
      {"Accept", "application/json"}
    ]

    request = Finch.build(:post, url, headers, body)

    case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
      {:ok, %Finch.Response{status: 200, body: resp_body}} ->
        case Jason.decode(resp_body) do
          {:ok, %{"job_id" => job_id}} ->
            Logger.info("[BatchRetrainingJob] Training job started: #{job_id}")
            {:ok, job_id}

          {:ok, response} ->
            Logger.warning("[BatchRetrainingJob] Unexpected response: #{inspect(response)}")
            {:ok, "unknown"}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: resp_body}} ->
        {:error, {:etl_error, status, resp_body}}

      {:error, reason} ->
        {:error, {:http_error, reason}}
    end
  end

  # Reset retraining stats baseline after triggering training
  defp reset_stats_after_trigger do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/rpc/reset_retraining_stats"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"}
        ]

        # Pass current timestamp
        body = Jason.encode!(%{training_ts: DateTime.utc_now() |> DateTime.to_iso8601()})

        request = Finch.build(:post, url, headers, body)

        case Finch.request(request, Server.Finch, receive_timeout: 10_000) do
          {:ok, %Finch.Response{status: status}} when status >= 200 and status < 300 ->
            Logger.info("[BatchRetrainingJob] Stats reset successfully")
            :ok

          {:ok, %Finch.Response{status: status, body: body}} ->
            {:error, {:http_error, status, body}}

          {:error, reason} ->
            {:error, {:request_failed, reason}}
        end

      {:error, reason} ->
        {:error, {:no_service_key, reason}}
    end
  end

  defp get_service_key do
    case Application.get_env(:server, :supabase_service_key) do
      nil -> {:error, :missing_service_key}
      key when is_binary(key) and byte_size(key) > 0 -> {:ok, key}
      _ -> {:error, :invalid_service_key}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Monitors trading disclosures for changes and triggers ML retraining when threshold reached",
      threshold: @default_threshold,
      check_interval: "hourly",
      etl_service: @etl_base_url,
      schedule_description: "Every hour at :00"
    }
  end

  @doc """
  Manually check retraining status (useful for debugging).
  Returns current change count and threshold.
  """
  def check_status do
    get_retraining_stats()
  end

  @doc """
  Force trigger training regardless of threshold (useful for testing).
  """
  def force_trigger do
    Logger.info("[BatchRetrainingJob] Force triggering training...")

    case trigger_training() do
      {:ok, job_id} ->
        reset_stats_after_trigger()
        {:ok, %{action: :force_triggered, job_id: job_id}}

      error ->
        error
    end
  end
end
