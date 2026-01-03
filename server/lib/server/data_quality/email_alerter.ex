defmodule Server.DataQuality.EmailAlerter do
  @moduledoc """
  Email alerting for data quality issues.

  Supports three notification modes:
  - Immediate: Critical issues trigger instant email
  - Daily Digest: Warnings accumulate and send at 8 AM UTC
  - Weekly Summary: Full report sent Sunday morning

  Uses Swoosh with Resend adapter for delivery.
  """

  import Swoosh.Email

  require Logger

  alias Server.DataQuality.DigestStore
  alias Server.Mailer

  @supabase_base_url "https://uljsqvwkomdrlnofmlad.supabase.co"

  # ============================================================================
  # Public API
  # ============================================================================

  @doc """
  Sends an immediate alert for critical issues.

  ## Parameters
    - issues: List of critical issue maps
    - opts: Options like :subject_prefix
  """
  @spec send_immediate([map()], keyword()) :: :ok | {:error, term()}
  def send_immediate(issues, opts \\ []) do
    unless email_enabled?() do
      Logger.info("[EmailAlerter] Email disabled, skipping immediate alert")
      {:error, :email_disabled}
    else
      critical_count = length(issues)
      subject_prefix = Keyword.get(opts, :subject_prefix, "[CRITICAL]")

      email =
        new()
        |> to(admin_email())
        |> from({app_name(), from_email()})
        |> subject("#{subject_prefix} #{critical_count} Data Quality Issue(s) Detected")
        |> html_body(render_critical_email(issues))
        |> text_body(render_critical_text(issues))

      case Mailer.deliver(email) do
        {:ok, _} ->
          log_email_sent("critical_alert", critical_count)
          :ok

        {:error, reason} ->
          Logger.error("[EmailAlerter] Failed to send critical alert: #{inspect(reason)}")
          {:error, reason}
      end
    end
  end

  @doc """
  Queues an issue for the daily digest.

  ## Parameters
    - issue: Map with :severity, :type, :description, etc.
  """
  @spec queue_digest(map()) :: :ok
  def queue_digest(issue) when is_map(issue) do
    DigestStore.add_issue(issue)
  end

  @doc """
  Sends the daily digest email with accumulated issues.

  Called by EmailDigestJob at 8 AM UTC.
  """
  @spec send_daily_digest() :: :ok | {:error, term()}
  def send_daily_digest do
    unless email_enabled?() do
      Logger.info("[EmailAlerter] Email disabled, skipping daily digest")
      {:error, :email_disabled}
    else
      issues = DigestStore.flush_issues()

      if length(issues) == 0 do
        Logger.info("[EmailAlerter] No issues to send in daily digest")
        :ok
      else
        email =
          new()
          |> to(admin_email())
          |> from({app_name(), from_email()})
          |> subject("[Daily Digest] #{length(issues)} Data Quality Issue(s)")
          |> html_body(render_digest_email(issues))
          |> text_body(render_digest_text(issues))

        case Mailer.deliver(email) do
          {:ok, _} ->
            log_email_sent("daily_digest", length(issues))
            :ok

          {:error, reason} ->
            Logger.error("[EmailAlerter] Failed to send daily digest: #{inspect(reason)}")
            # Re-queue issues so they're not lost
            Enum.each(issues, &DigestStore.add_issue/1)
            {:error, reason}
        end
      end
    end
  end

  @doc """
  Sends a weekly summary report.

  ## Parameters
    - summary: Map with aggregated stats from the week
  """
  @spec send_weekly_summary(map()) :: :ok | {:error, term()}
  def send_weekly_summary(summary) do
    unless email_enabled?() do
      Logger.info("[EmailAlerter] Email disabled, skipping weekly summary")
      {:error, :email_disabled}
    else
      email =
        new()
        |> to(admin_email())
        |> from({app_name(), from_email()})
        |> subject("[Weekly Report] Data Quality Summary")
        |> html_body(render_weekly_email(summary))
        |> text_body(render_weekly_text(summary))

      case Mailer.deliver(email) do
        {:ok, _} ->
          log_email_sent("weekly_summary", 1)
          :ok

        {:error, reason} ->
          Logger.error("[EmailAlerter] Failed to send weekly summary: #{inspect(reason)}")
          {:error, reason}
      end
    end
  end

  # ============================================================================
  # Email Rendering - Critical Alert
  # ============================================================================

  defp render_critical_email(issues) do
    issue_rows =
      issues
      |> Enum.take(20)
      |> Enum.map(fn issue ->
        """
        <tr style="border-bottom: 1px solid #e0e0e0;">
          <td style="padding: 12px; color: #dc2626; font-weight: 600;">#{escape_html(issue[:type] || "unknown")}</td>
          <td style="padding: 12px;">#{escape_html(issue[:table] || "—")}</td>
          <td style="padding: 12px;">#{escape_html(issue[:description] || "No description")}</td>
          <td style="padding: 12px; text-align: center;">#{issue[:count] || 1}</td>
        </tr>
        """
      end)
      |> Enum.join("\n")

    """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc2626; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; background: white; border-radius: 8px; overflow: hidden; }
        th { background: #f3f4f6; padding: 12px; text-align: left; font-weight: 600; }
        .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }
        .btn { display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1 style="margin: 0; font-size: 24px;">⚠️ Critical Data Quality Alert</h1>
          <p style="margin: 8px 0 0 0; opacity: 0.9;">#{length(issues)} critical issue(s) require immediate attention</p>
        </div>
        <div class="content">
          <p>The following critical data quality issues were detected:</p>
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Table</th>
                <th>Description</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              #{issue_rows}
            </tbody>
          </table>
          #{if length(issues) > 20, do: "<p style=\"color: #6b7280;\">...and #{length(issues) - 20} more issues</p>", else: ""}
          <p style="margin-top: 20px;">
            <a href="https://politician-trading.netlify.app/admin/data-quality" class="btn">View Dashboard →</a>
          </p>
        </div>
        <div class="footer">
          <p>This is an automated alert from Politician Trading Tracker.</p>
          <p>Generated at #{DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
      </div>
    </body>
    </html>
    """
  end

  defp render_critical_text(issues) do
    issue_lines =
      issues
      |> Enum.take(20)
      |> Enum.map(fn issue ->
        "• [#{issue[:type]}] #{issue[:description]} (#{issue[:count] || 1} affected)"
      end)
      |> Enum.join("\n")

    """
    CRITICAL DATA QUALITY ALERT
    ===========================

    #{length(issues)} critical issue(s) require immediate attention:

    #{issue_lines}

    #{if length(issues) > 20, do: "...and #{length(issues) - 20} more issues", else: ""}

    View dashboard: https://politician-trading.netlify.app/admin/data-quality

    ---
    Politician Trading Tracker
    Generated at #{DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M:%S UTC")}
    """
  end

  # ============================================================================
  # Email Rendering - Daily Digest
  # ============================================================================

  defp render_digest_email(issues) do
    grouped = Enum.group_by(issues, fn i -> i[:severity] || :info end)

    severity_sections =
      [:critical, :warning, :info, "critical", "warning", "info"]
      |> Enum.uniq_by(&normalize_severity/1)
      |> Enum.map(fn sev ->
        items = Map.get(grouped, sev, []) ++ Map.get(grouped, to_string(sev), [])
        if length(items) > 0, do: render_severity_section(sev, items), else: ""
      end)
      |> Enum.join("\n")

    """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; }
        .section { background: white; border-radius: 8px; padding: 16px; margin: 16px 0; border-left: 4px solid #e5e7eb; }
        .section.critical { border-left-color: #dc2626; }
        .section.warning { border-left-color: #f59e0b; }
        .section.info { border-left-color: #3b82f6; }
        .issue-item { padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
        .issue-item:last-child { border-bottom: none; }
        .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1 style="margin: 0; font-size: 24px;">📊 Daily Data Quality Digest</h1>
          <p style="margin: 8px 0 0 0; opacity: 0.9;">#{length(issues)} issue(s) detected in the last 24 hours</p>
        </div>
        <div class="content">
          #{severity_sections}
          <p style="margin-top: 20px; text-align: center;">
            <a href="https://politician-trading.netlify.app/admin/data-quality" style="color: #2563eb; font-weight: 500;">View Full Dashboard →</a>
          </p>
        </div>
        <div class="footer">
          <p>This is your daily data quality digest from Politician Trading Tracker.</p>
          <p>Generated at #{DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
      </div>
    </body>
    </html>
    """
  end

  defp render_severity_section(severity, items) do
    severity_str = normalize_severity(severity)
    color = severity_color(severity_str)
    icon = severity_icon(severity_str)

    issue_items =
      items
      |> Enum.take(10)
      |> Enum.map(fn item ->
        """
        <div class="issue-item">
          <strong>#{escape_html(item[:type] || "unknown")}</strong>
          <span style="color: #6b7280; margin-left: 8px;">#{escape_html(item[:table] || "")}</span>
          <p style="margin: 4px 0 0 0; color: #4b5563;">#{escape_html(item[:description] || "")}</p>
        </div>
        """
      end)
      |> Enum.join("\n")

    """
    <div class="section #{severity_str}">
      <h3 style="margin: 0 0 12px 0; color: #{color};">#{icon} #{String.capitalize(severity_str)} (#{length(items)})</h3>
      #{issue_items}
      #{if length(items) > 10, do: "<p style=\"color: #6b7280; margin: 8px 0 0 0;\">...and #{length(items) - 10} more</p>", else: ""}
    </div>
    """
  end

  defp render_digest_text(issues) do
    grouped = Enum.group_by(issues, fn i -> normalize_severity(i[:severity]) end)

    sections =
      ["critical", "warning", "info"]
      |> Enum.map(fn sev ->
        items = Map.get(grouped, sev, [])

        if length(items) > 0 do
          item_lines =
            items
            |> Enum.take(10)
            |> Enum.map(fn i -> "  • [#{i[:type]}] #{i[:description]}" end)
            |> Enum.join("\n")

          """
          #{String.upcase(sev)} (#{length(items)})
          #{String.duplicate("-", 40)}
          #{item_lines}
          #{if length(items) > 10, do: "  ...and #{length(items) - 10} more", else: ""}
          """
        else
          ""
        end
      end)
      |> Enum.filter(&(&1 != ""))
      |> Enum.join("\n\n")

    """
    DAILY DATA QUALITY DIGEST
    =========================

    #{length(issues)} issue(s) detected in the last 24 hours.

    #{sections}

    View dashboard: https://politician-trading.netlify.app/admin/data-quality

    ---
    Politician Trading Tracker
    Generated at #{DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M:%S UTC")}
    """
  end

  # ============================================================================
  # Email Rendering - Weekly Summary
  # ============================================================================

  defp render_weekly_email(summary) do
    """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #059669; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; }
        .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 20px 0; }
        .metric { background: white; padding: 16px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 32px; font-weight: 700; color: #1f2937; }
        .metric-label { font-size: 14px; color: #6b7280; }
        .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1 style="margin: 0; font-size: 24px;">📈 Weekly Data Quality Report</h1>
          <p style="margin: 8px 0 0 0; opacity: 0.9;">Summary for the past 7 days</p>
        </div>
        <div class="content">
          <div class="metrics">
            <div class="metric">
              <div class="metric-value">#{Map.get(summary, :total_checks, 0)}</div>
              <div class="metric-label">Checks Run</div>
            </div>
            <div class="metric">
              <div class="metric-value" style="color: #{if Map.get(summary, :pass_rate, 0) >= 95, do: "#059669", else: "#dc2626"};">#{Float.round(Map.get(summary, :pass_rate, 0.0) * 1.0, 1)}%</div>
              <div class="metric-label">Pass Rate</div>
            </div>
            <div class="metric">
              <div class="metric-value">#{Map.get(summary, :issues_found, 0)}</div>
              <div class="metric-label">Issues Found</div>
            </div>
            <div class="metric">
              <div class="metric-value" style="color: #059669;">#{Map.get(summary, :auto_corrected, 0)}</div>
              <div class="metric-label">Auto-Corrected</div>
            </div>
          </div>

          #{render_weekly_sections(summary)}

          <p style="margin-top: 20px; text-align: center;">
            <a href="https://politician-trading.netlify.app/admin/data-quality" style="color: #059669; font-weight: 500;">View Full Dashboard →</a>
          </p>
        </div>
        <div class="footer">
          <p>This is your weekly data quality report from Politician Trading Tracker.</p>
          <p>Generated at #{DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
      </div>
    </body>
    </html>
    """
  end

  defp render_weekly_sections(summary) do
    sections = []

    # Accuracy section
    sections =
      if accuracy = Map.get(summary, :accuracy_audit) do
        sections ++
          [
            """
            <h3 style="margin: 20px 0 12px 0;">🎯 Accuracy Audit</h3>
            <p>Sampled #{accuracy[:records_sampled] || 0} records and compared against source.</p>
            <p><strong>Accuracy Rate:</strong> #{Float.round((accuracy[:accuracy_rate] || 0.0) * 100, 1)}%</p>
            """
          ]
      else
        sections
      end

    # Signal backtest section
    sections =
      if backtest = Map.get(summary, :signal_backtest) do
        sections ++
          [
            """
            <h3 style="margin: 20px 0 12px 0;">📊 Signal Accuracy</h3>
            <p>Backtested #{backtest[:signals_tested] || 0} signals against actual returns.</p>
            <p><strong>Hit Rate:</strong> #{Float.round((backtest[:hit_rate] || 0.0) * 100, 1)}%</p>
            """
          ]
      else
        sections
      end

    # User reports section
    sections =
      if reports = Map.get(summary, :user_reports) do
        sections ++
          [
            """
            <h3 style="margin: 20px 0 12px 0;">🗣️ User Reports</h3>
            <p>#{reports[:total] || 0} user-submitted error reports this week.</p>
            <p>#{reports[:resolved] || 0} resolved, #{reports[:pending] || 0} pending review.</p>
            """
          ]
      else
        sections
      end

    Enum.join(sections, "\n")
  end

  defp render_weekly_text(summary) do
    """
    WEEKLY DATA QUALITY REPORT
    ==========================

    Summary for the past 7 days:

    METRICS
    -------
    Checks Run:     #{Map.get(summary, :total_checks, 0)}
    Pass Rate:      #{Float.round(Map.get(summary, :pass_rate, 0.0) * 1.0, 1)}%
    Issues Found:   #{Map.get(summary, :issues_found, 0)}
    Auto-Corrected: #{Map.get(summary, :auto_corrected, 0)}

    #{render_weekly_text_sections(summary)}

    View dashboard: https://politician-trading.netlify.app/admin/data-quality

    ---
    Politician Trading Tracker
    Generated at #{DateTime.utc_now() |> Calendar.strftime("%Y-%m-%d %H:%M:%S UTC")}
    """
  end

  defp render_weekly_text_sections(summary) do
    sections = []

    sections =
      if accuracy = Map.get(summary, :accuracy_audit) do
        sections ++
          [
            """
            ACCURACY AUDIT
            --------------
            Sampled: #{accuracy[:records_sampled] || 0} records
            Accuracy Rate: #{Float.round((accuracy[:accuracy_rate] || 0.0) * 100, 1)}%
            """
          ]
      else
        sections
      end

    sections =
      if backtest = Map.get(summary, :signal_backtest) do
        sections ++
          [
            """
            SIGNAL ACCURACY
            ---------------
            Signals Tested: #{backtest[:signals_tested] || 0}
            Hit Rate: #{Float.round((backtest[:hit_rate] || 0.0) * 100, 1)}%
            """
          ]
      else
        sections
      end

    sections =
      if reports = Map.get(summary, :user_reports) do
        sections ++
          [
            """
            USER REPORTS
            ------------
            Total: #{reports[:total] || 0}
            Resolved: #{reports[:resolved] || 0}
            Pending: #{reports[:pending] || 0}
            """
          ]
      else
        sections
      end

    Enum.join(sections, "\n")
  end

  # ============================================================================
  # Helpers
  # ============================================================================

  defp email_enabled? do
    Application.get_env(:server, :email_enabled, false)
  end

  defp from_email do
    Application.get_env(:server, :email_from, "alerts@politiciantrading.app")
  end

  defp admin_email do
    Application.get_env(:server, :email_admin, "admin@politiciantrading.app")
  end

  defp app_name, do: "Politician Trading Tracker"

  defp normalize_severity(severity) when is_atom(severity), do: to_string(severity)
  defp normalize_severity(severity) when is_binary(severity), do: severity
  defp normalize_severity(_), do: "info"

  defp severity_color("critical"), do: "#dc2626"
  defp severity_color("warning"), do: "#f59e0b"
  defp severity_color(_), do: "#3b82f6"

  defp severity_icon("critical"), do: "🔴"
  defp severity_icon("warning"), do: "🟡"
  defp severity_icon(_), do: "🔵"

  defp escape_html(nil), do: ""

  defp escape_html(text) when is_binary(text) do
    text
    |> String.replace("&", "&amp;")
    |> String.replace("<", "&lt;")
    |> String.replace(">", "&gt;")
    |> String.replace("\"", "&quot;")
  end

  defp escape_html(other), do: escape_html(to_string(other))

  defp log_email_sent(alert_type, issue_count) do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/email_alert_log"

        headers = [
          {"Authorization", "Bearer #{service_key}"},
          {"apikey", service_key},
          {"Content-Type", "application/json"},
          {"Prefer", "return=minimal"}
        ]

        body =
          Jason.encode!(%{
            alert_type: alert_type,
            recipient: admin_email(),
            subject: "Data Quality Alert",
            issue_count: issue_count,
            status: "sent"
          })

        request = Finch.build(:post, url, headers, body)
        Finch.request(request, Server.Finch, receive_timeout: 5_000)

      {:error, _} ->
        :ok
    end
  end

  defp get_service_key do
    case Application.get_env(:server, :supabase_service_key) do
      nil -> {:error, :missing_service_key}
      key when is_binary(key) and byte_size(key) > 0 -> {:ok, key}
      _ -> {:error, :invalid_service_key}
    end
  end
end
