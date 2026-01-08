defmodule Server.Scheduler.Jobs.FeatureAnalysisJob do
  @moduledoc """
  Analyzes feature importance and correlations with trade outcomes.

  This job:
  1. Fetches all recorded signal outcomes
  2. Calculates correlation between each feature and returns
  3. Identifies which features are predictive (bipartisan, politician_count, etc.)
  4. Stores results for model weight adjustment recommendations

  Runs weekly to have enough data for meaningful statistical analysis.
  """

  @behaviour Server.Scheduler.Job

  require Logger

  @impl true
  def job_id, do: "feature-analysis"

  @impl true
  def job_name, do: "Feature Importance Analysis"

  @impl true
  # Run weekly on Sunday at 2 AM UTC
  def schedule, do: "0 2 * * 0"

  @impl true
  def run do
    Logger.info("[FeatureAnalysisJob] Analyzing feature importance from trade outcomes")

    case Server.SupabaseClient.invoke("signal-feedback",
           body: %{"action" => "analyze-features", "windowDays" => 90},
           timeout: 120_000
         ) do
      {:ok, %{"success" => true, "features" => features, "sampleSize" => sample_size}} ->
        useful_features =
          features
          |> Enum.filter(fn f -> f["feature_useful"] end)
          |> Enum.map(fn f -> f["feature_name"] end)

        top_feature =
          features
          |> Enum.max_by(fn f -> abs(f["correlation_with_return"] || 0) end, fn -> %{} end)

        Logger.info(
          "[FeatureAnalysisJob] Analysis complete: #{length(features)} features analyzed, " <>
            "#{length(useful_features)} useful, sample size: #{sample_size}"
        )

        if map_size(top_feature) > 0 do
          Logger.info(
            "[FeatureAnalysisJob] Top feature: #{top_feature["feature_name"]} " <>
              "(correlation: #{top_feature["correlation_with_return"]}, lift: #{top_feature["lift_pct"]}%)"
          )
        end

        {:ok, length(features)}

      {:ok, %{"success" => true, "message" => message}} ->
        Logger.info("[FeatureAnalysisJob] #{message}")
        {:ok, 0}

      {:ok, %{"error" => error}} ->
        Logger.error("[FeatureAnalysisJob] Failed: #{error}")
        {:error, error}

      {:error, reason} ->
        Logger.error("[FeatureAnalysisJob] Request failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  @impl true
  def metadata do
    %{
      description: "Analyzes feature importance and correlations with trade outcomes",
      edge_function: "signal-feedback",
      action: "analyze-features",
      schedule_note: "Runs weekly on Sunday at 2 AM UTC"
    }
  end
end
