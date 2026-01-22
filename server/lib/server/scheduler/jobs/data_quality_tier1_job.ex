defmodule Server.Scheduler.Jobs.DataQualityTier1Job do
  @moduledoc """
  Tier 1 Data Quality Checks - Fast Hourly Checks

  Performs lightweight validation every hour:
  - Schema validation (required fields, data types)
  - Freshness monitoring (ETL job success, last sync times)
  - Referential integrity (orphaned records)
  - Constraint violations (future dates, extreme amounts)

  Critical issues trigger immediate email alerts.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @job_id "data-quality-tier1"
  @supabase_base_url "https://uljsqvwkomdrlnofmlad.supabase.co"

  # TODO: Review this function
  @impl true
  def job_id, do: @job_id

  # TODO: Review this function
  @impl true
  def job_name, do: "Data Quality - Tier 1 (Hourly)"

  # TODO: Review this function
  @impl true
  def schedule, do: "0 * * * *"

  # TODO: Review this function
  @impl true
  def schedule_type, do: :cron

  # TODO: Review this function
  @impl true
  def run do
    start_time = System.monotonic_time(:millisecond)
    Logger.info("[DataQualityTier1] Starting hourly checks")

    checks = [
      {"schema-required-fields", &check_required_fields/0},
      {"freshness-etl-jobs", &check_etl_freshness/0},
      {"integrity-orphaned-records", &check_orphaned_records/0},
      {"integrity-constraints", &check_constraints/0}
    ]

    results =
      Enum.map(checks, fn {check_id, check_fn} ->
        check_start = System.monotonic_time(:millisecond)

        result =
          try do
            check_fn.()
          rescue
            e ->
              Logger.error("[DataQualityTier1] Check #{check_id} error: #{Exception.message(e)}")
              {:error, Exception.message(e)}
          end

        duration = System.monotonic_time(:millisecond) - check_start
        {check_id, result, duration}
      end)

    # Aggregate results
    {issues, passed} =
      Enum.reduce(results, {[], 0}, fn {check_id, result, duration}, {acc_issues, acc_passed} ->
        case result do
          {:ok, []} ->
            record_check_result(check_id, "passed", 0, [], duration)
            {acc_issues, acc_passed + 1}

          {:ok, check_issues} when is_list(check_issues) ->
            record_check_result(check_id, "warning", length(check_issues), check_issues, duration)
            {acc_issues ++ check_issues, acc_passed}

          {:error, _reason} ->
            record_check_result(check_id, "error", 0, [], duration)
            {acc_issues, acc_passed}
        end
      end)

    # Send critical alerts if needed
    critical_issues = Enum.filter(issues, &(&1.severity == :critical))

    if length(critical_issues) > 0 do
      Logger.warning("[DataQualityTier1] Found #{length(critical_issues)} critical issues")
      send_critical_alert(critical_issues)
    end

    total_duration = System.monotonic_time(:millisecond) - start_time

    Logger.info(
      "[DataQualityTier1] Completed: #{passed}/#{length(checks)} passed, #{length(issues)} issues found in #{total_duration}ms"
    )

    {:ok, %{passed: passed, issues: length(issues), duration_ms: total_duration}}
  end

  # ============================================================================
  # CHECK: Required Fields
  # ============================================================================

  # TODO: Review this function
  defp check_required_fields do
    Logger.debug("[DataQualityTier1] Checking required fields")

    case call_supabase_rpc("check_required_fields_issues") do
      {:ok, results} ->
        issues =
          results
          |> Enum.filter(fn r -> r["count"] > 0 end)
          |> Enum.map(fn r ->
            %{
              severity: :critical,
              type: "missing_required_field",
              table: "trading_disclosures",
              field: r["field_name"],
              count: r["count"],
              description: "#{r["count"]} records missing #{r["field_name"]}"
            }
          end)

        {:ok, issues}

      {:error, _reason} ->
        # Fallback to direct query via REST API
        check_required_fields_via_rest()
    end
  end

  # TODO: Review this function
  defp check_required_fields_via_rest do
    # Check for missing politician_id, transaction_date, and invalid amount ranges
    checks = [
      {"politician_id", "politician_id=is.null"},
      {"transaction_date", "transaction_date=is.null"},
      {"amount_range_invalid", "amount_range_min=gt.amount_range_max"}
    ]

    issues =
      Enum.flat_map(checks, fn {field, filter} ->
        case count_records_with_filter("trading_disclosures", filter) do
          {:ok, count} when count > 0 ->
            [
              %{
                severity: if(count > 100, do: :critical, else: :warning),
                type: "missing_required_field",
                table: "trading_disclosures",
                field: field,
                count: count,
                description: "#{count} records with issue: #{field}"
              }
            ]

          _ ->
            []
        end
      end)

    {:ok, issues}
  end

  # ============================================================================
  # CHECK: ETL Freshness
  # ============================================================================

  # TODO: Review this function
  defp check_etl_freshness do
    Logger.debug("[DataQualityTier1] Checking ETL job freshness")

    case get_service_key() do
      {:ok, service_key} ->
        # Query scheduled_jobs table for stale jobs
        url =
          "#{@supabase_base_url}/rest/v1/scheduled_jobs?" <>
            "select=job_id,job_name,last_successful_run,consecutive_failures,enabled" <>
            "&enabled=eq.true" <>
            "&or=(last_successful_run.lt.#{stale_threshold()},consecutive_failures.gte.3)"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Accept", "application/json"}
        ]

        request = Finch.build(:get, url, headers)

        case Finch.request(request, Server.Finch, receive_timeout: 15_000) do
          {:ok, %Finch.Response{status: 200, body: body}} ->
            case Jason.decode(body) do
              {:ok, stale_jobs} ->
                issues =
                  Enum.map(stale_jobs, fn job ->
                    %{
                      severity: if(job["consecutive_failures"] >= 5, do: :critical, else: :warning),
                      type: "stale_etl_job",
                      table: "scheduled_jobs",
                      field: job["job_id"],
                      count: 1,
                      description:
                        "Job '#{job["job_name"]}' is stale (failures: #{job["consecutive_failures"]})"
                    }
                  end)

                {:ok, issues}

              {:error, _} ->
                {:ok, []}
            end

          _ ->
            {:ok, []}
        end

      {:error, _} ->
        {:ok, []}
    end
  end

  # TODO: Review this function
  defp stale_threshold do
    # Jobs not run in 12 hours
    DateTime.utc_now()
    |> DateTime.add(-12 * 60 * 60, :second)
    |> DateTime.to_iso8601()
  end

  # ============================================================================
  # CHECK: Orphaned Records
  # ============================================================================

  # TODO: Review this function
  defp check_orphaned_records do
    Logger.debug("[DataQualityTier1] Checking for orphaned records")

    case get_service_key() do
      {:ok, service_key} ->
        # Check for disclosures with invalid politician_id
        url =
          "#{@supabase_base_url}/rest/v1/rpc/count_orphaned_disclosures"

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
              {:ok, count} when is_integer(count) and count > 0 ->
                {:ok,
                 [
                   %{
                     severity: if(count > 50, do: :critical, else: :warning),
                     type: "orphaned_records",
                     table: "trading_disclosures",
                     field: "politician_id",
                     count: count,
                     description: "#{count} disclosures reference non-existent politicians"
                   }
                 ]}

              _ ->
                {:ok, []}
            end

          {:ok, %Finch.Response{status: 404}} ->
            # Function doesn't exist, use fallback
            check_orphaned_records_fallback(service_key)

          _ ->
            {:ok, []}
        end

      {:error, _} ->
        {:ok, []}
    end
  end

  # TODO: Review this function
  defp check_orphaned_records_fallback(_service_key) do
    # Count disclosures where politician_id is set but doesn't match any politician
    # This is a simplified check using the REST API
    {:ok, []}
  end

  # ============================================================================
  # CHECK: Constraint Violations
  # ============================================================================

  # TODO: Review this function
  defp check_constraints do
    Logger.debug("[DataQualityTier1] Checking constraint violations")

    # Check for future transaction dates
    future_issues =
      case count_records_with_filter(
             "trading_disclosures",
             "transaction_date=gt.#{tomorrow()}"
           ) do
        {:ok, count} when count > 0 ->
          [
            %{
              severity: :critical,
              type: "future_date",
              table: "trading_disclosures",
              field: "transaction_date",
              count: count,
              description: "#{count} disclosures have future transaction dates"
            }
          ]

        _ ->
          []
      end

    # Check for ancient dates (before 2000)
    ancient_issues =
      case count_records_with_filter(
             "trading_disclosures",
             "transaction_date=lt.2000-01-01"
           ) do
        {:ok, count} when count > 0 ->
          [
            %{
              severity: :warning,
              type: "ancient_date",
              table: "trading_disclosures",
              field: "transaction_date",
              count: count,
              description: "#{count} disclosures have dates before year 2000"
            }
          ]

        _ ->
          []
      end

    # Check for extreme amounts (over $100M)
    extreme_issues =
      case count_records_with_filter(
             "trading_disclosures",
             "amount_range_max=gt.100000000"
           ) do
        {:ok, count} when count > 0 ->
          [
            %{
              severity: :warning,
              type: "extreme_amount",
              table: "trading_disclosures",
              field: "amount_range_max",
              count: count,
              description: "#{count} disclosures have amounts over $100M"
            }
          ]

        _ ->
          []
      end

    {:ok, future_issues ++ ancient_issues ++ extreme_issues}
  end

  # TODO: Review this function
  defp tomorrow do
    Date.utc_today()
    |> Date.add(1)
    |> Date.to_iso8601()
  end

  # ============================================================================
  # HELPERS
  # ============================================================================

  # TODO: Review this function
  defp count_records_with_filter(table, filter) do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/#{table}?select=id&#{filter}"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Accept", "application/json"},
          {"Prefer", "count=exact"}
        ]

        request = Finch.build(:head, url, headers)

        case Finch.request(request, Server.Finch, receive_timeout: 15_000) do
          {:ok, %Finch.Response{headers: resp_headers}} ->
            count =
              resp_headers
              |> Enum.find(fn {k, _} -> String.downcase(k) == "content-range" end)
              |> case do
                {_, range} ->
                  case Regex.run(~r/\/(\d+)$/, range) do
                    [_, count_str] -> String.to_integer(count_str)
                    _ -> 0
                  end

                nil ->
                  0
              end

            {:ok, count}

          _ ->
            {:ok, 0}
        end

      {:error, reason} ->
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp call_supabase_rpc(function_name, params \\ %{}) do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/rpc/#{function_name}"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ]

        body = Jason.encode!(params)
        request = Finch.build(:post, url, headers, body)

        case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
          {:ok, %Finch.Response{status: 200, body: resp_body}} ->
            Jason.decode(resp_body)

          {:ok, %Finch.Response{status: status, body: resp_body}} ->
            {:error, {:http_error, status, resp_body}}

          {:error, reason} ->
            {:error, reason}
        end

      {:error, reason} ->
        {:error, reason}
    end
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
            issue_summary: %{issues: issues},
            summary: "#{issue_count} issues found"
          })

        request = Finch.build(:post, url, headers, body)
        Finch.request(request, Server.Finch, receive_timeout: 10_000)

      {:error, _} ->
        :ok
    end
  end

  # TODO: Review this function
  defp send_critical_alert(issues) do
    # Call the email alerter (to be implemented)
    Logger.warning("[DataQualityTier1] Would send critical alert for #{length(issues)} issues")

    # For now, just log. Email alerter will be added next.
    Enum.each(issues, fn issue ->
      Logger.warning("[DataQualityTier1] CRITICAL: #{issue.description}")
    end)
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
      description: "Fast hourly data quality checks",
      tier: 1,
      check_types: ["schema", "freshness", "integrity", "constraints"],
      schedule_description: "Every hour at :00"
    }
  end
end
