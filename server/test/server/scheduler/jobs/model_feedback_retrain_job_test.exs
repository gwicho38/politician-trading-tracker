defmodule Server.Scheduler.Jobs.ModelFeedbackRetrainJobTest do
  use ExUnit.Case, async: true

  alias Server.Scheduler.Jobs.ModelFeedbackRetrainJob

  describe "job_id/0" do
    test "returns model-feedback-retrain" do
      assert ModelFeedbackRetrainJob.job_id() == "model-feedback-retrain"
    end
  end

  describe "job_name/0" do
    test "returns a binary string" do
      name = ModelFeedbackRetrainJob.job_name()

      assert is_binary(name)
    end

    test "contains Retrain or retraining (case-insensitive)" do
      name = ModelFeedbackRetrainJob.job_name()

      assert String.match?(name, ~r/retrain/i)
    end
  end

  describe "schedule/0" do
    test "returns a cron string" do
      schedule = ModelFeedbackRetrainJob.schedule()

      assert is_binary(schedule)
    end

    test "is a monthly schedule (runs on the 1st of the month)" do
      schedule = ModelFeedbackRetrainJob.schedule()

      assert String.contains?(schedule, "1 * *")
    end
  end

  describe "metadata/0" do
    test "returns a map" do
      metadata = ModelFeedbackRetrainJob.metadata()

      assert is_map(metadata)
    end

    test "includes :description key with binary value" do
      metadata = ModelFeedbackRetrainJob.metadata()

      assert Map.has_key?(metadata, :description)
      assert is_binary(metadata.description)
    end

    test "includes :edge_function key with value ml-training" do
      metadata = ModelFeedbackRetrainJob.metadata()

      assert metadata.edge_function == "ml-training"
    end

    test "includes :schedule_note key mentioning monthly (case-insensitive)" do
      metadata = ModelFeedbackRetrainJob.metadata()

      assert Map.has_key?(metadata, :schedule_note)
      assert is_binary(metadata.schedule_note)
      assert String.match?(metadata.schedule_note, ~r/monthly/i)
    end
  end
end
