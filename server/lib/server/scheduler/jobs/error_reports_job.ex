defmodule Server.Scheduler.Jobs.ErrorReportsJob do
  @moduledoc """
  Automated processing of user error reports using Ollama LLM.

  Triggers the Python ETL service to:
  1. Query pending error reports from user_error_reports
  2. Use Ollama to interpret user descriptions and determine corrections
  3. Apply high-confidence corrections automatically
  4. Flag low-confidence corrections for human review
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"
  @supabase_base_url "https://uljsqvwkomdrlnofmlad.supabase.co"

  # TODO: Review this function
  @impl true
  def job_id, do: "error-reports"

  # TODO: Review this function
  @impl true
  def job_name, do: "Error Report Processing (Ollama)"

  # TODO: Review this function
  @impl true
  # Run every 4 hours
  def schedule, do: "0 */4 * * *"

  # TODO: Review this function
  @impl true
  def run do
    Logger.info("[ErrorReportsJob] Starting error report processing")

    # First check if there are any pending reports
    case count_pending_reports() do
      {:ok, 0} ->
        Logger.info("[ErrorReportsJob] No pending reports to process")
        {:ok, 0}

      {:ok, count} ->
        Logger.info("[ErrorReportsJob] Found #{count} pending reports")
        process_reports()

      {:error, reason} ->
        Logger.error("[ErrorReportsJob] Failed to count pending reports: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp count_pending_reports do
    case get_service_key() do
      {:ok, service_key} ->
        url = "#{@supabase_base_url}/rest/v1/user_error_reports?select=id&status=eq.pending"

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

          {:error, reason} ->
            {:error, reason}
        end

      {:error, reason} ->
        {:error, reason}
    end
  end

  # TODO: Review this function
  defp process_reports do
    url = "#{@etl_service_url}/error-reports/process"

    # Process up to 10 reports per run to avoid overwhelming Ollama
    body = Jason.encode!(%{limit: 10, model: "llama3.1:8b"})

    request =
      Finch.build(
        :post,
        url,
        [
          {"Content-Type", "application/json"},
          {"Accept", "application/json"}
        ],
        body
      )

    case Finch.request(request, Server.Finch, receive_timeout: 120_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"processed" => processed, "fixed" => fixed, "needs_review" => needs_review}} ->
            Logger.info(
              "[ErrorReportsJob] Processed #{processed} reports: #{fixed} fixed, #{needs_review} need review"
            )

            {:ok, processed}

          {:ok, response} ->
            Logger.info("[ErrorReportsJob] Response: #{inspect(response)}")
            {:ok, Map.get(response, "processed", 0)}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        Logger.error("[ErrorReportsJob] HTTP #{status}: #{response_body}")
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
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
      description: "Processes user-submitted error reports using Ollama LLM",
      etl_service: @etl_service_url,
      ollama_url: "https://ollama.lefv.info",
      batch_size: 10,
      confidence_threshold: 0.8
    }
  end
end
