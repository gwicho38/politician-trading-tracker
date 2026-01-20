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
