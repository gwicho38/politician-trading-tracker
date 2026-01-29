defmodule ServerWeb.Plugs.ApiKeyAuthTest do
  @moduledoc """
  Tests for API key authentication plug.
  """
  use ExUnit.Case, async: true
  use Plug.Test

  alias ServerWeb.Plugs.ApiKeyAuth

  @valid_api_key "etl_sk_test_1234567890abcdef"

  # ===========================================================================
  # Setup
  # ===========================================================================

  setup do
    # Store original config
    original_key = Application.get_env(:server, :api_key)
    original_disabled = Application.get_env(:server, :auth_disabled)

    on_exit(fn ->
      # Restore original config
      if original_key do
        Application.put_env(:server, :api_key, original_key)
      else
        Application.delete_env(:server, :api_key)
      end

      if original_disabled do
        Application.put_env(:server, :auth_disabled, original_disabled)
      else
        Application.delete_env(:server, :auth_disabled)
      end
    end)

    :ok
  end

  # ===========================================================================
  # Public Endpoint Tests
  # ===========================================================================

  describe "public_endpoint?/1" do
    test "returns true for root path" do
      assert ApiKeyAuth.public_endpoint?("/")
    end

    test "returns true for /health" do
      assert ApiKeyAuth.public_endpoint?("/health")
    end

    test "returns true for /health/ready" do
      assert ApiKeyAuth.public_endpoint?("/health/ready")
    end

    test "returns true for /ready" do
      assert ApiKeyAuth.public_endpoint?("/ready")
    end

    test "returns false for /api/jobs" do
      refute ApiKeyAuth.public_endpoint?("/api/jobs")
    end

    test "returns false for /api/ml/predict" do
      refute ApiKeyAuth.public_endpoint?("/api/ml/predict")
    end
  end

  # ===========================================================================
  # Auth Disabled Tests
  # ===========================================================================

  describe "auth_disabled?/0" do
    test "returns false when not configured" do
      Application.delete_env(:server, :auth_disabled)
      refute ApiKeyAuth.auth_disabled?()
    end

    test "returns true when set to true" do
      Application.put_env(:server, :auth_disabled, true)
      assert ApiKeyAuth.auth_disabled?()
    end

    test "returns true when set to string 'true'" do
      Application.put_env(:server, :auth_disabled, "true")
      assert ApiKeyAuth.auth_disabled?()
    end

    test "returns false when set to false" do
      Application.put_env(:server, :auth_disabled, false)
      refute ApiKeyAuth.auth_disabled?()
    end
  end

  # ===========================================================================
  # API Key Extraction Tests
  # ===========================================================================

  describe "extract_api_key/1" do
    test "extracts from X-API-Key header" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("x-api-key", @valid_api_key)

      assert ApiKeyAuth.extract_api_key(conn) == @valid_api_key
    end

    test "extracts from Authorization Bearer header" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("authorization", "Bearer #{@valid_api_key}")

      assert ApiKeyAuth.extract_api_key(conn) == @valid_api_key
    end

    test "extracts from query parameter" do
      conn = conn(:get, "/api/jobs?api_key=#{@valid_api_key}")

      assert ApiKeyAuth.extract_api_key(conn) == @valid_api_key
    end

    test "returns nil when no key provided" do
      conn = conn(:get, "/api/jobs")

      assert ApiKeyAuth.extract_api_key(conn) == nil
    end

    test "prefers X-API-Key over Bearer token" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("x-api-key", "header_key")
        |> put_req_header("authorization", "Bearer bearer_key")

      assert ApiKeyAuth.extract_api_key(conn) == "header_key"
    end

    test "prefers Bearer token over query param" do
      conn =
        conn(:get, "/api/jobs?api_key=query_key")
        |> put_req_header("authorization", "Bearer bearer_key")

      assert ApiKeyAuth.extract_api_key(conn) == "bearer_key"
    end

    test "ignores non-Bearer authorization headers" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("authorization", "Basic dXNlcjpwYXNz")

      assert ApiKeyAuth.extract_api_key(conn) == nil
    end
  end

  # ===========================================================================
  # API Key Validation Tests
  # ===========================================================================

  describe "validate_api_key/1" do
    test "returns error for nil key" do
      Application.put_env(:server, :api_key, @valid_api_key)
      assert {:error, :missing_key} = ApiKeyAuth.validate_api_key(nil)
    end

    test "returns error for empty key" do
      Application.put_env(:server, :api_key, @valid_api_key)
      assert {:error, :empty_key} = ApiKeyAuth.validate_api_key("")
    end

    test "returns error for invalid key" do
      Application.put_env(:server, :api_key, @valid_api_key)
      assert {:error, :invalid_key} = ApiKeyAuth.validate_api_key("wrong_key")
    end

    test "returns ok for valid key" do
      Application.put_env(:server, :api_key, @valid_api_key)
      assert :ok = ApiKeyAuth.validate_api_key(@valid_api_key)
    end

    test "returns ok when no key configured (backwards compatibility)" do
      Application.delete_env(:server, :api_key)
      assert :ok = ApiKeyAuth.validate_api_key("any_key")
    end
  end

  # ===========================================================================
  # Constant Time Comparison Tests
  # ===========================================================================

  describe "constant_time_compare/2" do
    test "returns true for equal strings" do
      assert ApiKeyAuth.constant_time_compare("abc", "abc")
    end

    test "returns false for different strings" do
      refute ApiKeyAuth.constant_time_compare("abc", "def")
    end

    test "returns false for different length strings" do
      refute ApiKeyAuth.constant_time_compare("abc", "abcd")
    end

    test "returns false for empty vs non-empty" do
      refute ApiKeyAuth.constant_time_compare("", "abc")
    end

    test "returns true for both empty" do
      assert ApiKeyAuth.constant_time_compare("", "")
    end

    test "returns false for non-binary inputs" do
      refute ApiKeyAuth.constant_time_compare(123, "abc")
      refute ApiKeyAuth.constant_time_compare("abc", 123)
      refute ApiKeyAuth.constant_time_compare(nil, nil)
    end

    test "handles long API keys" do
      long_key = String.duplicate("a", 256)
      assert ApiKeyAuth.constant_time_compare(long_key, long_key)
      refute ApiKeyAuth.constant_time_compare(long_key, long_key <> "x")
    end
  end

  # ===========================================================================
  # Plug Call Tests
  # ===========================================================================

  describe "call/2 with auth enabled" do
    setup do
      Application.put_env(:server, :api_key, @valid_api_key)
      Application.put_env(:server, :auth_disabled, false)
      :ok
    end

    test "allows public endpoints without auth" do
      conn =
        conn(:get, "/health")
        |> ApiKeyAuth.call([])

      refute conn.halted
    end

    test "allows requests with valid X-API-Key header" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("x-api-key", @valid_api_key)
        |> ApiKeyAuth.call([])

      refute conn.halted
      assert conn.assigns[:api_key_validated] == true
    end

    test "allows requests with valid Bearer token" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("authorization", "Bearer #{@valid_api_key}")
        |> ApiKeyAuth.call([])

      refute conn.halted
      assert conn.assigns[:api_key_validated] == true
    end

    test "rejects requests without API key" do
      conn =
        conn(:get, "/api/jobs")
        |> ApiKeyAuth.call([])

      assert conn.halted
      assert conn.status == 401
      assert get_resp_header(conn, "www-authenticate") == ["ApiKey"]

      body = Jason.decode!(conn.resp_body)
      assert body["detail"] =~ "API key required"
    end

    test "rejects requests with invalid API key" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("x-api-key", "invalid_key")
        |> ApiKeyAuth.call([])

      assert conn.halted
      assert conn.status == 401

      body = Jason.decode!(conn.resp_body)
      assert body["detail"] == "Invalid API key."
    end
  end

  describe "call/2 with auth disabled" do
    setup do
      Application.put_env(:server, :api_key, @valid_api_key)
      Application.put_env(:server, :auth_disabled, true)
      :ok
    end

    test "allows all requests when auth is disabled" do
      conn =
        conn(:get, "/api/jobs")
        |> ApiKeyAuth.call([])

      refute conn.halted
    end

    test "allows requests without API key when auth is disabled" do
      conn =
        conn(:post, "/api/ml/train")
        |> ApiKeyAuth.call([])

      refute conn.halted
    end
  end

  # ===========================================================================
  # Integration Tests
  # ===========================================================================

  describe "integration with router pipeline" do
    setup do
      Application.put_env(:server, :api_key, @valid_api_key)
      Application.put_env(:server, :auth_disabled, false)
      :ok
    end

    test "rejects unauthenticated requests to /api/jobs" do
      conn =
        conn(:get, "/api/jobs")
        |> ApiKeyAuth.call([])

      assert conn.halted
      assert conn.status == 401
    end

    test "accepts authenticated requests to /api/jobs" do
      conn =
        conn(:get, "/api/jobs")
        |> put_req_header("x-api-key", @valid_api_key)
        |> ApiKeyAuth.call([])

      refute conn.halted
    end

    test "rejects unauthenticated POST to /api/ml/train" do
      conn =
        conn(:post, "/api/ml/train")
        |> ApiKeyAuth.call([])

      assert conn.halted
      assert conn.status == 401
    end
  end
end
