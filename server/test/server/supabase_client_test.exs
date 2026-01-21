defmodule Server.SupabaseClientTest do
  @moduledoc """
  Tests for Server.SupabaseClient module.

  Tests:
  - invoke/2 - Invoke edge function
  - invoke/3 - Invoke edge function with options
  - base_url/0 - Returns base URL
  """

  use ExUnit.Case, async: true

  alias Server.SupabaseClient

  describe "base_url/0" do
    test "returns a string" do
      url = SupabaseClient.base_url()

      assert is_binary(url)
    end

    test "returns supabase URL format" do
      url = SupabaseClient.base_url()

      assert String.contains?(url, "supabase")
    end
  end

  describe "invoke/2" do
    @tag :external_service
    test "returns {:error, _} for non-existent function" do
      result = SupabaseClient.invoke("non-existent-function-xyz", [])

      # Should return an error for non-existent function
      assert match?({:error, _}, result)
    end
  end

  describe "invoke/3" do
    @tag :external_service
    test "accepts timeout option" do
      result = SupabaseClient.invoke("test-function", [], timeout: 5_000)

      # Should accept the option without crashing
      assert match?({:ok, _}, result) or match?({:error, _}, result)
    end

    @tag :external_service
    test "accepts query option" do
      result = SupabaseClient.invoke("test-function", query: %{mode: "test"})

      assert match?({:ok, _}, result) or match?({:error, _}, result)
    end
  end
end
