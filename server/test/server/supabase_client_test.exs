defmodule Server.SupabaseClientTest do
  @moduledoc """
  Tests for Server.SupabaseClient module.

  Tests:
  - invoke/1 - Invoke edge function with just name
  - invoke/2 - Invoke edge function with options
  """

  use ExUnit.Case, async: true

  alias Server.SupabaseClient

  describe "invoke/1" do
    @tag :external_service
    test "returns {:error, _} for non-existent function" do
      result = SupabaseClient.invoke("non-existent-function-xyz")

      # Should return an error for non-existent function or missing service key
      assert match?({:error, _}, result)
    end
  end

  describe "invoke/2" do
    @tag :external_service
    test "accepts timeout option" do
      result = SupabaseClient.invoke("test-function", timeout: 5_000)

      # Should accept the option without crashing
      assert match?({:ok, _}, result) or match?({:error, _}, result)
    end

    @tag :external_service
    test "accepts query option" do
      result = SupabaseClient.invoke("test-function", query: %{mode: "test"})

      assert match?({:ok, _}, result) or match?({:error, _}, result)
    end

    @tag :external_service
    test "accepts body option" do
      result = SupabaseClient.invoke("test-function", body: %{test: true})

      assert match?({:ok, _}, result) or match?({:error, _}, result)
    end

    @tag :external_service
    test "accepts path option" do
      result = SupabaseClient.invoke("test-function", path: "test-path")

      assert match?({:ok, _}, result) or match?({:error, _}, result)
    end
  end
end
