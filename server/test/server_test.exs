defmodule ServerTest do
  @moduledoc """
  Tests for the main Server module.

  Tests:
  - version/0 - Returns application version
  - health_check/0 - Database connectivity check
  """

  use ExUnit.Case, async: true

  describe "version/0" do
    test "returns a version string" do
      version = Server.version()

      assert is_binary(version)
    end

    test "returns semantic version format" do
      version = Server.version()

      # Should match semver pattern (X.Y.Z)
      assert Regex.match?(~r/^\d+\.\d+\.\d+/, version)
    end

    test "returns 0.1.0" do
      assert Server.version() == "0.1.0"
    end
  end

  describe "health_check/0" do
    @describetag :database

    @tag :database
    test "returns :ok when database is connected" do
      # This test requires a database connection
      # Skip if database is not available
      assert Server.health_check() == :ok
    end

    @tag :database
    test "executes a simple query to verify connectivity" do
      # This implicitly tests that health_check runs SELECT 1
      result = Server.health_check()

      assert result == :ok
    end
  end
end
