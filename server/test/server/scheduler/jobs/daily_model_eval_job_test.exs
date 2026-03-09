defmodule Server.Scheduler.Jobs.DailyModelEvalJobTest do
  use ExUnit.Case, async: true

  alias Server.Scheduler.Jobs.DailyModelEvalJob

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

    test "nil win_rate does not crash, returns false" do
      perf = %{"win_rate" => nil, "sharpe_ratio" => nil}
      assert DailyModelEvalJob.needs_retrain?(perf) == false
    end
  end
end
