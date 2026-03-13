defmodule Server.Scheduler.Jobs.DailyModelEvalJobTest do
  use ExUnit.Case, async: true

  alias Server.Scheduler.Jobs.DailyModelEvalJob

  describe "job_id/0" do
    test "returns daily-model-eval" do
      assert DailyModelEvalJob.job_id() == "daily-model-eval"
    end
  end

  describe "job_name/0" do
    test "returns a binary string" do
      name = DailyModelEvalJob.job_name()

      assert is_binary(name)
    end
  end

  describe "schedule/0" do
    test "returns a cron string running at 23:30" do
      schedule = DailyModelEvalJob.schedule()

      assert is_binary(schedule)
      assert String.starts_with?(schedule, "30 23")
    end
  end

  describe "metadata/0" do
    test "returns a map" do
      metadata = DailyModelEvalJob.metadata()

      assert is_map(metadata)
    end

    test "includes :description key" do
      metadata = DailyModelEvalJob.metadata()

      assert Map.has_key?(metadata, :description)
    end

    test "includes :edge_function key with value signal-feedback" do
      metadata = DailyModelEvalJob.metadata()

      assert metadata.edge_function == "signal-feedback"
    end

    test "includes :action key" do
      metadata = DailyModelEvalJob.metadata()

      assert Map.has_key?(metadata, :action)
    end
  end

  describe "needs_retrain?/1" do
    test "win_rate below 0.35 triggers retrain" do
      perf = %{"win_rate" => 0.20, "sharpe_ratio" => 0.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == true
    end

    test "win_rate at exactly 0.35 does not trigger" do
      perf = %{"win_rate" => 0.35, "sharpe_ratio" => 0.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == false
    end

    test "win_rate above 0.35 does not trigger" do
      perf = %{"win_rate" => 0.40, "sharpe_ratio" => 0.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == false
    end

    test "critical: win_rate below 0.05 always triggers" do
      perf = %{"win_rate" => 0.03, "sharpe_ratio" => -1.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == true
    end

    test "win_rate = 0.03 triggers regardless of sharpe (needs_retrain? is sharpe-agnostic)" do
      # needs_retrain? only checks win_rate; the cond in run/0 handles the sharpe guard separately
      perf_good_sharpe = %{"win_rate" => 0.03, "sharpe_ratio" => 1.5}
      perf_bad_sharpe  = %{"win_rate" => 0.03, "sharpe_ratio" => -2.0}
      assert DailyModelEvalJob.needs_retrain?(perf_good_sharpe) == true
      assert DailyModelEvalJob.needs_retrain?(perf_bad_sharpe)  == true
    end

    test "nil win_rate does not crash, returns false" do
      perf = %{"win_rate" => nil, "sharpe_ratio" => nil}
      assert DailyModelEvalJob.needs_retrain?(perf) == false
    end
  end
end
