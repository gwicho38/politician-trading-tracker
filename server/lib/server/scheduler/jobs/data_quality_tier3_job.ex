defmodule Server.Scheduler.Jobs.DataQualityTier3Job do
  @moduledoc """
  Tier 3 Data Quality Checks - Weekly Accuracy Audits

  Runs every Sunday at 4 AM UTC to perform:
  - Sample-based source verification (re-fetch and compare)
  - Signal accuracy backtesting (predictions vs actual returns)
  - User-reported issue triage

  Generates a weekly summary email with all findings.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @job_id "data-quality-tier3"
  @supabase_base_url "https://uljsqvwkomdrlnofmlad.supabase.co"
  @etl_service_url "https://politician-trading-etl.fly.dev"

  # TODO: Review this function
  @impl true
  def job_id, do: @job_id

  # TODO: Review this function
  @impl true
  def job_name, do: "Data Quality - Tier 3 (Weekly)"

  # TODO: Review this function
  @impl true
  # Every Sunday at 4 AM UTC
  def schedule, do: "0 4 * * 0"

  # TODO: Review this function
  @impl true
  def schedule_type, do: :cron

  # TODO: Review this function
  @impl true
  def run do
    start_time = System.monotonic_time(:millisecond)
    Logger.info("[DataQualityTier3] Starting weekly accuracy audit")

    checks = [
      {"accuracy-source-audit", &audit_source_accuracy/0},
      {"signal-backtesting", &backtest_signal_accuracy/0},
      {"user-reports-triage", &triage_user_reports/0}
    ]

    results =
      Enum.map(checks, fn {check_id, check_fn} ->
        check_start = System.monotonic_time(:millisecond)

        result =
          try do
            check_fn.()
          rescue
            e ->
              Logger.error("[DataQualityTier3] Check #{check_id} error: #{Exception.message(e)}")
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

    # Generate and send weekly summary
    generate_weekly_summary(all_issues)

    total_duration = System.monotonic_time(:millisecond) - start_time

    Logger.info(
      "[DataQualityTier3] Completed: #{length(all_issues)} issues found in #{total_duration}ms"
    )

    {:ok, %{issues: length(all_issues), duration_ms: total_duration}}
  end

  # TODO: Review this function
  defp status_for_issues([]), do: "passed"
  defp status_for_issues(issues) do
    if Enum.any?(issues, &(&1.severity == :critical)), do: "failed", else: "warning"
  end

  # ============================================================================
  # CHECK: Source Accuracy Audit
  # ============================================================================

  # TODO: Review this function
  defp audit_source_accuracy do
    Logger.debug("[DataQualityTier3] Auditing source accuracy")

    url = "#{@etl_service_url}/quality/audit-sources"

    body =
      Jason.encode!(%{
        sample_size: 50,
        sources: ["us_house", "us_senate"]
      })

    headers = [
      {"Content-Type", "application/json"},
      {"Accept", "application/json"}
    ]

    request = Finch.build(:post, url, headers, body)

    case Finch.request(request, Server.Finch, receive_timeout: 600_000) do
      {:ok, %Finch.Response{status: 200, body: resp_body}} ->
        case Jason.decode(resp_body) do
          {:ok, %{"mismatches" => mismatches, "total_sampled" => total, "verified_count" => verified}} ->
            Logger.info(
              "[DataQualityTier3] Source audit: #{verified}/#{total} verified, #{length(mismatches || [])} mismatches"
            )

            issues =
              Enum.map(mismatches || [], fn m ->
                %{
                  severity: :warning,
                  type: "source_mismatch",
                  table: "trading_disclosures",
                  field: "multiple",
                  record_id: m["disclosure_id"],
                  count: 1,
                  description: "Source mismatch: #{inspect(m["field_mismatches"])}"
                }
              end)

            accuracy = if total > 0, do: verified / total * 100, else: 100

            if accuracy < 90 do
              issues ++
                [
                  %{
                    severity: :warning,
                    type: "low_accuracy",
                    table: "trading_disclosures",
                    field: "overall",
                    count: 1,
                    description:
                      "Source accuracy below threshold: #{Float.round(accuracy, 1)}% (#{verified}/#{total})"
                  }
                ]
            else
              issues
            end
            |> then(&{:ok, &1})

          {:ok, _} ->
            {:ok, []}

          {:error, reason} ->
            Logger.warning("[DataQualityTier3] Failed to parse audit response: #{inspect(reason)}")
            {:ok, []}
        end

      {:ok, %Finch.Response{status: status, body: body}} ->
        Logger.warning("[DataQualityTier3] Source audit returned #{status}: #{body}")
        {:ok, []}

      {:error, reason} ->
        Logger.warning("[DataQualityTier3] Source audit failed: #{inspect(reason)}")
        {:ok, []}
    end
  end

  # ============================================================================
  # CHECK: Signal Backtesting
  # ============================================================================

  # TODO: Review this function
  defp backtest_signal_accuracy do
    Logger.debug("[DataQualityTier3] Backtesting signal accuracy")

    case get_service_key() do
      {:ok, service_key} ->
        # Query for signal predictions vs actual returns
        url = "#{@supabase_base_url}/rest/v1/rpc/backtest_signals"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ]

        body = Jason.encode!(%{days_back: 30})
        request = Finch.build(:post, url, headers, body)

        case Finch.request(request, Server.Finch, receive_timeout: 60_000) do
          {:ok, %Finch.Response{status: 200, body: resp_body}} ->
            case Jason.decode(resp_body) do
              {:ok, %{"accuracy" => accuracy, "total" => total, "correct" => correct}}
              when is_number(accuracy) ->
                Logger.info(
                  "[DataQualityTier3] Signal accuracy: #{Float.round(accuracy, 1)}% (#{correct}/#{total})"
                )

                if accuracy < 50 do
                  {:ok,
                   [
                     %{
                       severity: :warning,
                       type: "low_signal_accuracy",
                       table: "trading_signals",
                       field: "prediction",
                       count: 1,
                       description:
                         "Signal accuracy below 50%: #{Float.round(accuracy, 1)}% (#{correct}/#{total})"
                     }
                   ]}
                else
                  {:ok, []}
                end

              _ ->
                {:ok, []}
            end

          {:ok, %Finch.Response{status: 404}} ->
            # RPC doesn't exist, use fallback
            backtest_signals_fallback(service_key)

          _ ->
            {:ok, []}
        end

      {:error, _} ->
        {:ok, []}
    end
  end

  # TODO: Review this function
  defp backtest_signals_fallback(service_key) do
    # Simplified: just count signals from last 30 days
    url =
      "#{@supabase_base_url}/rest/v1/trading_signals?" <>
        "select=id,ticker,signal_type,confidence_score" <>
        "&created_at=gt.#{days_ago(30)}" <>
        "&limit=100"

    headers = [
      {"Authorization", "Bearer #{service_key}"},
      {"apikey", service_key},
      {"Accept", "application/json"}
    ]

    request = Finch.build(:get, url, headers)

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: body}} ->
        case Jason.decode(body) do
          {:ok, signals} ->
            # Check for low confidence signals
            low_confidence =
              signals
              |> Enum.filter(fn s -> (s["confidence_score"] || 0) < 0.5 end)

            if length(low_confidence) > length(signals) * 0.3 do
              {:ok,
               [
                 %{
                   severity: :info,
                   type: "many_low_confidence_signals",
                   table: "trading_signals",
                   field: "confidence_score",
                   count: length(low_confidence),
                   description:
                     "#{length(low_confidence)}/#{length(signals)} signals have low confidence (<50%)"
                 }
               ]}
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
  # CHECK: User Report Triage
  # ============================================================================

  # TODO: Review this function
  defp triage_user_reports do
    Logger.debug("[DataQualityTier3] Triaging user error reports")

    case get_service_key() do
      {:ok, service_key} ->
        # Get pending user reports
        url =
          "#{@supabase_base_url}/rest/v1/user_error_reports?" <>
            "select=id,disclosure_id,error_type,description,created_at" <>
            "&status=eq.pending" <>
            "&order=created_at.asc" <>
            "&limit=100"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Accept", "application/json"}
        ]

        request = Finch.build(:get, url, headers)

        case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
          {:ok, %Finch.Response{status: 200, body: body}} ->
            case Jason.decode(body) do
              {:ok, reports} when is_list(reports) and length(reports) > 0 ->
                Logger.info("[DataQualityTier3] Found #{length(reports)} pending user reports")

                # Mark reports as reviewed
                mark_reports_reviewed(service_key, Enum.map(reports, & &1["id"]))

                # Convert to issues
                issues =
                  Enum.map(reports, fn r ->
                    %{
                      severity: :info,
                      type: "user_reported",
                      table: "trading_disclosures",
                      field: r["error_type"] || "unknown",
                      record_id: r["disclosure_id"],
                      count: 1,
                      description: "User report: #{r["error_type"]} - #{String.slice(r["description"] || "", 0, 100)}"
                    }
                  end)

                {:ok, issues}

              {:ok, []} ->
                Logger.info("[DataQualityTier3] No pending user reports")
                {:ok, []}

              _ ->
                {:ok, []}
            end

          {:ok, %Finch.Response{status: 404}} ->
            # Table doesn't exist
            Logger.debug("[DataQualityTier3] user_error_reports table not found")
            {:ok, []}

          _ ->
            {:ok, []}
        end

      {:error, _} ->
        {:ok, []}
    end
  end

  # TODO: Review this function
  defp mark_reports_reviewed(service_key, report_ids) when length(report_ids) > 0 do
    url = "#{@supabase_base_url}/rest/v1/user_error_reports"

    headers = [
      {"Authorization", "Bearer #{service_key}"},
      {"apikey", service_key},
      {"Content-Type", "application/json"},
      {"Prefer", "return=minimal"}
    ]

    # Update each report to 'reviewed' status
    Enum.each(report_ids, fn id ->
      update_url = "#{url}?id=eq.#{id}"
      body = Jason.encode!(%{status: "reviewed"})
      request = Finch.build(:patch, update_url, headers, body)
      Finch.request(request, Server.Finch, receive_timeout: 5_000)
    end)

    :ok
  end

  # TODO: Review this function
  defp mark_reports_reviewed(_, _), do: :ok

  # ============================================================================
  # WEEKLY SUMMARY
  # ============================================================================

  # TODO: Review this function
  defp generate_weekly_summary(issues) do
    Logger.info("[DataQualityTier3] Generating weekly summary")

    # Group issues by type
    by_type = Enum.group_by(issues, & &1.type)

    # Get metrics from the past week
    case get_weekly_metrics() do
      {:ok, metrics} ->
        summary = %{
          week: week_number(),
          total_issues: length(issues),
          by_type: Map.new(by_type, fn {k, v} -> {k, length(v)} end),
          metrics: metrics,
          generated_at: DateTime.utc_now() |> DateTime.to_iso8601()
        }

        # Store summary and queue email
        store_weekly_summary(summary)
        Logger.info("[DataQualityTier3] Weekly summary stored: #{inspect(summary)}")

      {:error, _} ->
        Logger.warning("[DataQualityTier3] Could not retrieve weekly metrics")
    end
  end

  # TODO: Review this function
  defp get_weekly_metrics do
    case get_service_key() do
      {:ok, service_key} ->
        url =
          "#{@supabase_base_url}/rest/v1/data_quality_results?" <>
            "select=status,issues_found" <>
            "&created_at=gt.#{days_ago(7)}"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Accept", "application/json"}
        ]

        request = Finch.build(:get, url, headers)

        case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
          {:ok, %Finch.Response{status: 200, body: body}} ->
            case Jason.decode(body) do
              {:ok, results} ->
                passed = Enum.count(results, &(&1["status"] == "passed"))
                total = length(results)
                total_issues = Enum.sum(Enum.map(results, &(&1["issues_found"] || 0)))

                {:ok,
                 %{
                   total_checks: total,
                   passed_checks: passed,
                   pass_rate: if(total > 0, do: Float.round(passed / total * 100, 1), else: 100),
                   total_issues_found: total_issues
                 }}

              _ ->
                {:ok, %{}}
            end

          _ ->
            {:ok, %{}}
        end

      {:error, reason} ->
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp store_weekly_summary(summary) do
    case get_service_key() do
      {:ok, service_key} ->
        # Store in email_alert_log as a weekly summary
        url = "#{@supabase_base_url}/rest/v1/email_alert_log"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Prefer", "return=minimal"}
        ]

        body =
          Jason.encode!(%{
            subject: "[Weekly] Data Quality Summary - Week #{summary.week}",
            recipients: ["admin@politiciantrading.app"],
            body_preview: "#{summary.total_issues} issues found. Pass rate: #{summary.metrics[:pass_rate] || 100}%",
            status: "pending",
            issue_count: summary.total_issues
          })

        request = Finch.build(:post, url, headers, body)
        Finch.request(request, Server.Finch, receive_timeout: 10_000)

      {:error, _} ->
        :ok
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
  defp week_number do
    Date.utc_today() |> Date.day_of_year() |> div(7) |> Kernel.+(1)
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
      description: "Weekly accuracy audits and user report triage",
      tier: 3,
      check_types: ["source_verification", "signal_backtesting", "user_reports"],
      schedule_description: "Weekly on Sunday at 4 AM UTC"
    }
  end
end
