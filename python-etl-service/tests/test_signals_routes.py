"""
Tests for Signal Lambda Routes (app/routes/signals.py).

Tests:
- POST /signals/apply-lambda - Apply lambda to signals
- POST /signals/validate-lambda - Validate lambda code
- GET /signals/lambda-help - Get lambda help documentation
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# =============================================================================
# POST /signals/apply-lambda Tests
# =============================================================================

class TestApplyLambda:
    """Tests for POST /signals/apply-lambda endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_apply_lambda_empty_signals(self, client):
        """POST /signals/apply-lambda with empty signals returns success."""
        response = client.post("/signals/apply-lambda", json={
            "signals": [],
            "lambdaCode": "result = signal"
        })

        data = response.json()
        assert data["success"] is True
        assert data["signals"] == []
        assert "No signals provided" in data["message"]

    def test_apply_lambda_empty_code(self, client):
        """POST /signals/apply-lambda with empty code returns original signals."""
        response = client.post("/signals/apply-lambda", json={
            "signals": [
                {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}
            ],
            "lambdaCode": ""
        })

        data = response.json()
        assert data["success"] is True
        assert len(data["signals"]) == 1
        assert "Empty lambda code" in data["message"]

    def test_apply_lambda_invalid_code_returns_400(self, client):
        """POST /signals/apply-lambda with invalid code returns 400."""
        response = client.post("/signals/apply-lambda", json={
            "signals": [
                {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}
            ],
            "lambdaCode": "import os"  # Imports are forbidden
        })

        assert response.status_code == 400
        assert "Invalid lambda code" in response.json()["detail"]

    def test_apply_lambda_success_with_transformation(self, client):
        """POST /signals/apply-lambda successfully transforms signals."""
        response = client.post("/signals/apply-lambda", json={
            "signals": [
                {"ticker": "AAPL", "confidence_score": 0.7, "signal_type": "buy"},
                {"ticker": "GOOGL", "confidence_score": 0.3, "signal_type": "sell"},
            ],
            "lambdaCode": "signal['confidence_score'] = signal['confidence_score'] * 2\nresult = signal"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["signals"]) == 2
        # Check transformation applied
        assert data["signals"][0]["confidence_score"] == 1.4  # 0.7 * 2
        assert data["signals"][1]["confidence_score"] == 0.6  # 0.3 * 2
        # Check trace is included
        assert "trace" in data
        assert data["trace"]["signals_processed"] == 2

    def test_apply_lambda_success_returns_trace(self, client):
        """POST /signals/apply-lambda returns execution trace."""
        response = client.post("/signals/apply-lambda", json={
            "signals": [
                {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}
            ],
            "lambdaCode": "result = signal"
        })

        assert response.status_code == 200
        data = response.json()
        assert "trace" in data
        trace = data["trace"]
        assert "console_output" in trace
        assert "execution_time_ms" in trace
        assert "signals_processed" in trace
        assert "signals_modified" in trace
        assert "errors" in trace
        assert trace["signals_processed"] == 1

    def test_apply_lambda_execution_error_tracked_in_trace(self, client):
        """POST /signals/apply-lambda tracks per-signal errors in trace."""
        response = client.post("/signals/apply-lambda", json={
            "signals": [
                {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}
            ],
            "lambdaCode": "result = signal['nonexistent_key']"  # KeyError at runtime
        })

        # The sandbox handles per-signal errors gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Errors are tracked in the trace
        assert "trace" in data
        assert len(data["trace"]["errors"]) > 0

    def test_apply_lambda_raises_execution_error(self, client):
        """POST /signals/apply-lambda returns 400 for LambdaExecutionError."""
        from app.services.sandbox import LambdaExecutionError

        with patch("app.routes.signals.apply_lambda_to_signals") as mock_apply:
            mock_apply.side_effect = LambdaExecutionError("Fatal execution error")

            response = client.post("/signals/apply-lambda", json={
                "signals": [
                    {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}
                ],
                "lambdaCode": "result = signal"
            })

            assert response.status_code == 400
            assert "Lambda execution error" in response.json()["detail"]

    def test_apply_lambda_internal_error_returns_500(self, client):
        """POST /signals/apply-lambda handles unexpected internal errors."""
        with patch("app.routes.signals.apply_lambda_to_signals") as mock_apply:
            mock_apply.side_effect = RuntimeError("Unexpected internal error")

            response = client.post("/signals/apply-lambda", json={
                "signals": [
                    {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}
                ],
                "lambdaCode": "result = signal"
            })

            assert response.status_code == 500
            assert "Internal error" in response.json()["detail"]


# =============================================================================
# POST /signals/validate-lambda Tests
# =============================================================================

class TestValidateLambda:
    """Tests for POST /signals/validate-lambda endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_validate_invalid_import(self, client):
        """POST /signals/validate-lambda rejects import statements."""
        response = client.post("/signals/validate-lambda", json={
            "lambdaCode": "import os"
        })

        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_empty_code(self, client):
        """POST /signals/validate-lambda rejects empty code."""
        response = client.post("/signals/validate-lambda", json={
            "lambdaCode": ""
        })

        data = response.json()
        assert data["valid"] is False
        assert "Empty code" in data["error"]

    def test_validate_forbidden_eval(self, client):
        """POST /signals/validate-lambda rejects eval calls."""
        response = client.post("/signals/validate-lambda", json={
            "lambdaCode": "eval('print(1)')"
        })

        data = response.json()
        assert data["valid"] is False

    def test_validate_valid_code_returns_true(self, client):
        """POST /signals/validate-lambda returns valid=True for valid code."""
        response = client.post("/signals/validate-lambda", json={
            "lambdaCode": "result = signal"
        })

        data = response.json()
        assert data["valid"] is True
        assert "error" not in data or data.get("error") is None

    def test_validate_code_with_modification(self, client):
        """POST /signals/validate-lambda accepts code that modifies signals."""
        response = client.post("/signals/validate-lambda", json={
            "lambdaCode": "signal['confidence_score'] = signal['confidence_score'] * 1.1\nresult = signal"
        })

        data = response.json()
        assert data["valid"] is True

    def test_validate_syntax_error_returns_invalid(self, client):
        """POST /signals/validate-lambda rejects code with syntax errors."""
        response = client.post("/signals/validate-lambda", json={
            "lambdaCode": "if True\n  x = 1"  # Missing colon
        })

        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    def test_validate_unexpected_error_returns_invalid(self, client):
        """POST /signals/validate-lambda handles unexpected validation errors."""
        with patch("app.routes.signals.SignalLambdaSandbox") as mock_sandbox_class:
            mock_sandbox = MagicMock()
            mock_sandbox.validate_code.side_effect = Exception("Unexpected error")
            mock_sandbox_class.return_value = mock_sandbox

            response = client.post("/signals/validate-lambda", json={
                "lambdaCode": "result = signal"
            })

            data = response.json()
            assert data["valid"] is False
            assert "Validation error" in data["error"]


# =============================================================================
# GET /signals/lambda-help Tests
# =============================================================================

class TestLambdaHelp:
    """Tests for GET /signals/lambda-help endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_lambda_help_returns_200(self, client):
        """GET /signals/lambda-help returns 200."""
        response = client.get("/signals/lambda-help")

        assert response.status_code == 200

    def test_lambda_help_contains_description(self, client):
        """GET /signals/lambda-help contains description."""
        response = client.get("/signals/lambda-help")
        data = response.json()

        assert "description" in data

    def test_lambda_help_contains_signal_fields(self, client):
        """GET /signals/lambda-help contains signal field documentation."""
        response = client.get("/signals/lambda-help")
        data = response.json()

        assert "signal_fields" in data
        assert "ticker" in data["signal_fields"]
        assert "confidence_score" in data["signal_fields"]

    def test_lambda_help_contains_examples(self, client):
        """GET /signals/lambda-help contains examples."""
        response = client.get("/signals/lambda-help")
        data = response.json()

        assert "examples" in data
        assert len(data["examples"]) > 0

    def test_lambda_help_contains_available_builtins(self, client):
        """GET /signals/lambda-help contains available builtins list."""
        response = client.get("/signals/lambda-help")
        data = response.json()

        assert "available_builtins" in data
        assert "len" in data["available_builtins"]
        assert "min" in data["available_builtins"]
        assert "max" in data["available_builtins"]

    def test_lambda_help_contains_forbidden_operations(self, client):
        """GET /signals/lambda-help contains forbidden operations."""
        response = client.get("/signals/lambda-help")
        data = response.json()

        assert "forbidden_operations" in data
        assert any("import" in op.lower() for op in data["forbidden_operations"])

    def test_lambda_help_contains_tips(self, client):
        """GET /signals/lambda-help contains tips."""
        response = client.get("/signals/lambda-help")
        data = response.json()

        assert "tips" in data
        assert len(data["tips"]) > 0
