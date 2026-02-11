defmodule Server.Scheduler.Jobs.PoliticianTradingETLJobTest do
  @moduledoc """
  Tests for Server.Scheduler.Jobs.PoliticianTradingETLJob.

  Tests the config-driven job factory that generates ETL job modules
  from configuration maps.
  """

  use ExUnit.Case, async: true

  alias Server.Scheduler.Jobs.PoliticianTradingETLJob

  @sample_config %{
    job_id: "test-etl-source",
    job_name: "Test ETL Source",
    source: "test_source",
    schedule: "0 */6 * * *",
    params: %{lookback_days: 30, limit: 100}
  }

  describe "create_job_module/1" do
    test "creates a module implementing Job behaviour" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)

      assert is_atom(module)
      assert function_exported?(module, :job_id, 0)
      assert function_exported?(module, :job_name, 0)
      assert function_exported?(module, :schedule, 0)
      assert function_exported?(module, :run, 0)
      assert function_exported?(module, :metadata, 0)
    end

    test "module returns correct job_id" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)
      assert module.job_id() == "test-etl-source"
    end

    test "module returns correct job_name" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)
      assert module.job_name() == "Test ETL Source"
    end

    test "module returns correct schedule" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)
      assert module.schedule() == "0 */6 * * *"
    end

    test "module metadata includes source" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)
      metadata = module.metadata()

      assert metadata.source == "test_source"
    end

    test "module metadata includes params" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)
      metadata = module.metadata()

      assert metadata.params == %{lookback_days: 30, limit: 100}
    end

    test "module metadata includes etl_service url" do
      module = PoliticianTradingETLJob.create_job_module(@sample_config)
      metadata = module.metadata()

      assert is_binary(metadata.etl_service)
      assert String.contains?(metadata.etl_service, "politician-trading-etl")
    end
  end

  describe "create_all/1" do
    test "creates modules for multiple configs" do
      configs = [
        %{job_id: "multi-test-1", job_name: "Test 1", source: "src1", schedule: "0 * * * *", params: %{}},
        %{job_id: "multi-test-2", job_name: "Test 2", source: "src2", schedule: "0 2 * * 0", params: %{}}
      ]

      modules = PoliticianTradingETLJob.create_all(configs)

      assert length(modules) == 2
      assert Enum.all?(modules, &is_atom/1)
    end

    test "each module has unique job_id" do
      configs = [
        %{job_id: "unique-test-a", job_name: "A", source: "a", schedule: "* * * * *", params: %{}},
        %{job_id: "unique-test-b", job_name: "B", source: "b", schedule: "* * * * *", params: %{}}
      ]

      modules = PoliticianTradingETLJob.create_all(configs)
      job_ids = Enum.map(modules, & &1.job_id())

      assert length(Enum.uniq(job_ids)) == 2
    end
  end

  describe "resolve_dynamic_params/1" do
    test "resolves :current_year to actual year" do
      result = PoliticianTradingETLJob.resolve_dynamic_params(%{year: :current_year})
      assert result.year == Date.utc_today().year
    end

    test "passes through static values" do
      result = PoliticianTradingETLJob.resolve_dynamic_params(%{lookback_days: 30, limit: 100})
      assert result.lookback_days == 30
      assert result.limit == 100
    end

    test "handles mixed static and dynamic params" do
      result = PoliticianTradingETLJob.resolve_dynamic_params(%{year: :current_year, limit: 50})
      assert result.year == Date.utc_today().year
      assert result.limit == 50
    end

    test "handles empty params" do
      result = PoliticianTradingETLJob.resolve_dynamic_params(%{})
      assert result == %{}
    end
  end

  describe "production ETL configs" do
    # These test the actual configs used in application.ex
    @house_config %{
      job_id: "politician-trading-house",
      job_name: "US House Disclosures (ETL)",
      source: "house",
      schedule: "0 */6 * * *",
      params: %{year: :current_year, limit: 100}
    }

    @senate_config %{
      job_id: "politician-trading-senate",
      job_name: "US Senate Disclosures (ETL)",
      source: "senate",
      schedule: "0 */6 * * *",
      params: %{lookback_days: 30, limit: 100}
    }

    @quiver_config %{
      job_id: "politician-trading-quiver",
      job_name: "QuiverQuant Congress Trading",
      source: "quiverquant",
      schedule: "0 */6 * * *",
      params: %{lookback_days: 30}
    }

    test "house config produces valid module" do
      module = PoliticianTradingETLJob.create_job_module(@house_config)
      assert module.job_id() == "politician-trading-house"
      assert module.schedule() == "0 */6 * * *"
    end

    test "senate config produces valid module" do
      module = PoliticianTradingETLJob.create_job_module(@senate_config)
      assert module.job_id() == "politician-trading-senate"
      assert module.metadata().source == "senate"
    end

    test "quiver config produces valid module" do
      module = PoliticianTradingETLJob.create_job_module(@quiver_config)
      assert module.job_id() == "politician-trading-quiver"
      assert module.metadata().source == "quiverquant"
    end
  end
end
