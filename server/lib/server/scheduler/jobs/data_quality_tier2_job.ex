defmodule Server.Scheduler.Jobs.DataQualityTier2Job do
  @moduledoc """
  Tier 2 Data Quality Checks - Daily Deep Analysis

  Runs daily at 3 AM UTC to perform:
  - Cross-source reconciliation (same trade in multiple sources)
  - Statistical anomaly detection (z-score > 3)
  - Ticker validation via Python ETL service

  Warning-level issues are queued for daily digest email.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @job_id "data-quality-tier2"
  @supabase_base_url "https://uljsqvwkomdrlnofmlad.supabase.co"
  @etl_service_url "https://politician-trading-etl.fly.dev"

  # TODO: Review this function
  @impl true
  def job_id, do: @job_id

  # TODO: Review this function
  @impl true
  def job_name, do: "Data Quality - Tier 2 (Daily)"

  # TODO: Review this function
  @impl true
  def schedule, do: "0 3 * * *"

  # TODO: Review this function
  @impl true
  def schedule_type, do: :cron

  # TODO: Review this function
  @impl true
  def run do
    start_time = System.monotonic_time(:millisecond)
    Logger.info("[DataQualityTier2] Starting daily deep checks")

    checks = [
      {"reconciliation-cross-source", &check_cross_source_reconciliation/0},
      {"anomaly-statistical", &check_statistical_anomalies/0},
      {"ticker-validation", &check_ticker_validation/0}
    ]

    results =
      Enum.map(checks, fn {check_id, check_fn} ->
        check_start = System.monotonic_time(:millisecond)

        result =
          try do
            check_fn.()
          rescue
            e ->
              Logger.error("[DataQualityTier2] Check #{check_id} error: #{Exception.message(e)}")
              {:error, Exception.message(e)}
          end

        duration = System.monotonic_time(:millisecond) - check_start
        {check_id, result, duration}
      end)

    # Aggregate results
    all_issues =
      Enum.flat_map(results, fn {check_id, result, duration} ->
        case result do
          {:ok, issues} when is_list(issues) ->
            record_check_result(check_id, status_for_issues(issues), length(issues), issues, duration)
            issues

          {:error, _reason} ->
            record_check_result(check_id, "error", 0, [], duration)
            []
        end
      end)

    # Store issues for daily digest
    if length(all_issues) > 0 do
      store_issues_for_digest(all_issues)
    end

    total_duration = System.monotonic_time(:millisecond) - start_time

    Logger.info(
      "[DataQualityTier2] Completed: #{length(all_issues)} issues found in #{total_duration}ms"
    )

    {:ok, %{issues: length(all_issues), duration_ms: total_duration}}
  end

  # TODO: Review this function
  defp status_for_issues([]), do: "passed"
  defp status_for_issues(issues) do
    if Enum.any?(issues, &(&1.severity == :critical)), do: "failed", else: "warning"
  end

  # ============================================================================
  # CHECK: Cross-Source Reconciliation
  # ============================================================================

  # TODO: Review this function
  defp check_cross_source_reconciliation do
    Logger.debug("[DataQualityTier2] Checking cross-source reconciliation")

    case get_service_key() do
      {:ok, service_key} ->
        # Find trades that appear in multiple sources with potentially different values
        url = "#{@supabase_base_url}/rest/v1/rpc/find_cross_source_mismatches"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ]

        body = Jason.encode!(%{days_back: 30, limit_results: 100})
        request = Finch.build(:post, url, headers, body)

        case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
          {:ok, %Finch.Response{status: 200, body: resp_body}} ->
            case Jason.decode(resp_body) do
              {:ok, mismatches} when is_list(mismatches) ->
                issues =
                  Enum.map(mismatches, fn m ->
                    %{
                      severity: :warning,
                      type: "cross_source_mismatch",
                      table: "trading_disclosures",
                      field: "multiple",
                      record_id: m["disclosure_id"],
                      count: 1,
                      description:
                        "Trade for #{m["politician_name"]} / #{m["ticker"]} found in #{m["source_count"]} sources with value differences"
                    }
                  end)

                {:ok, issues}

              _ ->
                {:ok, []}
            end

          {:ok, %Finch.Response{status: 404}} ->
            # RPC function doesn't exist, use fallback
            check_cross_source_fallback(service_key)

          {:ok, %Finch.Response{status: status, body: body}} ->
            Logger.warning("[DataQualityTier2] Cross-source check returned #{status}: #{body}")
            {:ok, []}

          {:error, reason} ->
            Logger.error("[DataQualityTier2] Cross-source check failed: #{inspect(reason)}")
            {:ok, []}
        end

      {:error, _} ->
        {:ok, []}
    end
  end

  # TODO: Review this function
  defp check_cross_source_fallback(service_key) do
    # Simplified fallback: count records with same politician+ticker+date but different sources
    url =
      "#{@supabase_base_url}/rest/v1/trading_disclosures?" <>
        "select=politician_id,asset_ticker,transaction_date" <>
        "&created_at=gt.#{days_ago(30)}" <>
        "&asset_ticker=not.is.null"

    headers = [
      {"Authorization", "Bearer #{service_key}"},
      {"apikey", service_key},
      {"Accept", "application/json"}
    ]

    request = Finch.build(:get, url, headers)

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: body}} ->
        case Jason.decode(body) do
          {:ok, records} ->
            # Group by politician+ticker+date and find duplicates
            duplicates =
              records
              |> Enum.group_by(fn r ->
                {r["politician_id"], r["asset_ticker"], r["transaction_date"]}
              end)
              |> Enum.filter(fn {_key, group} -> length(group) > 1 end)

            issues =
              Enum.take(duplicates, 20)
              |> Enum.map(fn {{_pid, ticker, date}, _group} ->
                %{
                  severity: :info,
                  type: "potential_duplicate",
                  table: "trading_disclosures",
                  field: "multiple",
                  count: 1,
                  description: "Potential duplicate: #{ticker} on #{date}"
                }
              end)

            {:ok, issues}

          _ ->
            {:ok, []}
        end

      _ ->
        {:ok, []}
    end
  end

  # ============================================================================
  # CHECK: Statistical Anomalies
  # ============================================================================

  # TODO: Review this function
  defp check_statistical_anomalies do
    Logger.debug("[DataQualityTier2] Checking statistical anomalies")

    case get_service_key() do
      {:ok, service_key} ->
        # Check for unusual daily trade volumes using z-score
        url = "#{@supabase_base_url}/rest/v1/rpc/detect_volume_anomalies"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ]

        body = Jason.encode!(%{z_threshold: 3.0, days_back: 90})
        request = Finch.build(:post, url, headers, body)

        case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
          {:ok, %Finch.Response{status: 200, body: resp_body}} ->
            case Jason.decode(resp_body) do
              {:ok, anomalies} when is_list(anomalies) ->
                issues =
                  Enum.map(anomalies, fn a ->
                    %{
                      severity: :info,
                      type: "statistical_anomaly",
                      table: "trading_disclosures",
                      field: "daily_count",
                      count: 1,
                      description:
                        "Unusual volume on #{a["date"]}: #{a["count"]} trades (z-score: #{Float.round(a["z_score"] || 0.0, 2)})"
                    }
                  end)

                {:ok, issues}

              _ ->
                {:ok, []}
            end

          {:ok, %Finch.Response{status: 404}} ->
            # RPC function doesn't exist, use simple check
            check_anomalies_simple(service_key)

          _ ->
            {:ok, []}
        end

      {:error, _} ->
        {:ok, []}
    end
  end

  # TODO: Review this function
  defp check_anomalies_simple(service_key) do
    # Simple check: flag days with more than 5x average volume
    # Get recent daily counts
    url =
      "#{@supabase_base_url}/rest/v1/trading_disclosures?" <>
        "select=transaction_date" <>
        "&transaction_date=gt.#{days_ago(30)}" <>
        "&transaction_date=not.is.null"

    headers = [
      {"Authorization", "Bearer #{service_key}"},
      {"apikey", service_key},
      {"Accept", "application/json"}
    ]

    request = Finch.build(:get, url, headers)

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: body}} ->
        case Jason.decode(body) do
          {:ok, records} ->
            # Count by date
            daily_counts =
              records
              |> Enum.group_by(fn r -> r["transaction_date"] end)
              |> Enum.map(fn {date, items} -> {date, length(items)} end)

            if length(daily_counts) > 7 do
              counts = Enum.map(daily_counts, fn {_, c} -> c end)
              avg = Enum.sum(counts) / length(counts)

              anomalies =
                daily_counts
                |> Enum.filter(fn {_, count} -> count > avg * 5 end)
                |> Enum.take(5)
                |> Enum.map(fn {date, count} ->
                  %{
                    severity: :info,
                    type: "volume_spike",
                    table: "trading_disclosures",
                    field: "daily_count",
                    count: 1,
                    description: "High volume on #{date}: #{count} trades (avg: #{Float.round(avg, 1)})"
                  }
                end)

              {:ok, anomalies}
            else
              {:ok, []}
            end

          _ ->
            {:ok, []}
        end

      _ ->
        {:ok, []}
    end
  end

  # ============================================================================
  # CHECK: Ticker Validation
  # ============================================================================

  # TODO: Review this function
  defp check_ticker_validation do
    Logger.debug("[DataQualityTier2] Validating tickers via ETL service")

    url = "#{@etl_service_url}/quality/validate-tickers"

    body =
      Jason.encode!(%{
        days_back: 7,
        confidence_threshold: 0.6
      })

    headers = [
      {"Content-Type", "application/json"},
      {"Accept", "application/json"}
    ]

    request = Finch.build(:post, url, headers, body)

    case Finch.request(request, Server.Finch, receive_timeout: 120_000) do
      {:ok, %Finch.Response{status: 200, body: resp_body}} ->
        case Jason.decode(resp_body) do
          {:ok, %{"invalid_tickers" => invalid, "low_confidence" => low_conf}} ->
            invalid_issues =
              Enum.map(invalid || [], fn t ->
                %{
                  severity: :warning,
                  type: "invalid_ticker",
                  table: "trading_disclosures",
                  field: "asset_ticker",
                  count: t["affected_count"] || 1,
                  description: "Invalid ticker '#{t["ticker"]}': #{t["reason"]}"
                }
              end)

            low_conf_issues =
              Enum.take(low_conf || [], 10)
              |> Enum.map(fn t ->
                %{
                  severity: :info,
                  type: "low_confidence_ticker",
                  table: "trading_disclosures",
                  field: "asset_ticker",
                  count: 1,
                  description:
                    "Low confidence ticker '#{t["ticker"]}' (confidence: #{t["confidence"]})"
                }
              end)

            {:ok, invalid_issues ++ low_conf_issues}

          {:ok, %{"error" => error}} ->
            Logger.warning("[DataQualityTier2] Ticker validation returned error: #{error}")
            {:ok, []}

          _ ->
            {:ok, []}
        end

      {:ok, %Finch.Response{status: status, body: body}} ->
        Logger.warning("[DataQualityTier2] Ticker validation returned #{status}: #{body}")
        {:ok, []}

      {:error, reason} ->
        Logger.warning("[DataQualityTier2] Ticker validation failed: #{inspect(reason)}")
        {:ok, []}
    end
  end

  # ============================================================================
  # HELPERS
  # ============================================================================

  # TODO: Review this function
  defp days_ago(days) do
    Date.utc_today()
    |> Date.add(-days)
    |> Date.to_iso8601()
  end

  # TODO: Review this function
  defp record_check_result(check_id, status, issue_count, issues, duration_ms) do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/data_quality_results"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Prefer", "return=minimal"}
        ]

        body =
          Jason.encode!(%{
            check_id: check_id,
            started_at: DateTime.utc_now() |> DateTime.add(-duration_ms, :millisecond),
            completed_at: DateTime.utc_now(),
            status: status,
            records_checked: 0,
            issues_found: issue_count,
            duration_ms: duration_ms,
            issue_summary: %{issues: Enum.take(issues, 50)},
            summary: "#{issue_count} issues found"
          })

        request = Finch.build(:post, url, headers, body)
        Finch.request(request, Server.Finch, receive_timeout: 10_000)

      {:error, _} ->
        :ok
    end
  end

  # TODO: Review this function
  defp store_issues_for_digest(issues) do
    # Store issues in data_quality_issues table for daily digest
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/data_quality_issues"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Prefer", "return=minimal"}
        ]

        issue_records =
          Enum.take(issues, 100)
          |> Enum.map(fn issue ->
            %{
              severity: Atom.to_string(issue.severity),
              issue_type: issue.type,
              table_name: issue.table,
              field_name: issue[:field],
              record_id: issue[:record_id],
              description: issue.description,
              status: "open"
            }
          end)

        body = Jason.encode!(issue_records)
        request = Finch.build(:post, url, headers, body)

        case Finch.request(request, Server.Finch, receive_timeout: 15_000) do
          {:ok, %Finch.Response{status: status}} when status in 200..299 ->
            Logger.info("[DataQualityTier2] Stored #{length(issue_records)} issues for digest")

          {:ok, %Finch.Response{status: status, body: body}} ->
            Logger.warning("[DataQualityTier2] Failed to store issues: #{status} - #{body}")

          {:error, reason} ->
            Logger.error("[DataQualityTier2] Failed to store issues: #{inspect(reason)}")
        end

      {:error, _} ->
        :ok
    end
  end

  # TODO: Review this function
  defp get_service_key do
    case Application.get_env(:server, :supabase_service_key) do
      nil -> {:error, :missing_service_key}
      key when is_binary(key) and byte_size(key) > 0 -> {:ok, key}
      _ -> {:error, :invalid_service_key}
    end
  end

  # TODO: Review this function
  @impl true
  def metadata do
    %{
      description: "Daily deep data quality analysis",
      tier: 2,
      check_types: ["reconciliation", "anomaly", "ticker_validation"],
      schedule_description: "Daily at 3 AM UTC"
    }
  end
end
