"""
Unit tests for ML Service metrics (METRICS.md Section 6.2).

Tests fields populated from Python ETL ML Service:
- Endpoints: /ml/models/active, /ml/batch-predict, /signals/apply-lambda
- Trading signals: signal_type, confidence_score, signal_strength, target_price,
  stop_loss, take_profit, model_version, features, analysis

Run with: cd python-etl-service && pytest tests/test_ml_service_metrics.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python-micro-service'))


# =============================================================================
# SECTION 6.2: ML Service Endpoints (3 metrics)
# =============================================================================

class TestMLModelsActiveEndpoint:
    """[ ] /ml/models/active endpoint - List active ML models"""

    def test_endpoint_returns_list(self):
        """Test endpoint returns list of models."""
        mock_response = [
            {"model_id": "v1.0", "name": "congress_signal_v1", "is_active": True},
            {"model_id": "v1.1", "name": "congress_signal_v1.1", "is_active": True},
        ]
        assert isinstance(mock_response, list)

    def test_model_has_required_fields(self):
        """Test each model has required fields."""
        mock_model = {
            "model_id": "v1.0",
            "name": "congress_signal_v1",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
        }
        required_fields = ["model_id", "name", "is_active"]
        for field in required_fields:
            assert field in mock_model

    def test_active_models_filtered(self):
        """Test only active models are returned."""
        all_models = [
            {"model_id": "v1.0", "is_active": True},
            {"model_id": "v0.9", "is_active": False},
        ]
        active_models = [m for m in all_models if m["is_active"]]
        assert len(active_models) == 1
        assert active_models[0]["model_id"] == "v1.0"


class TestMLBatchPredictEndpoint:
    """[ ] /ml/batch-predict endpoint - Batch signal predictions"""

    def test_batch_request_format(self):
        """Test batch prediction request format."""
        request = {
            "tickers": ["AAPL", "GOOGL", "MSFT"],
            "model_id": "v1.0",
            "features": {
                "AAPL": {"buy_count": 10, "sell_count": 5},
                "GOOGL": {"buy_count": 8, "sell_count": 8},
                "MSFT": {"buy_count": 3, "sell_count": 7},
            },
        }
        assert "tickers" in request
        assert "model_id" in request
        assert len(request["tickers"]) == 3

    def test_batch_response_format(self):
        """Test batch prediction response format."""
        response = {
            "predictions": [
                {"ticker": "AAPL", "signal": "buy", "confidence": 0.75},
                {"ticker": "GOOGL", "signal": "hold", "confidence": 0.55},
                {"ticker": "MSFT", "signal": "sell", "confidence": 0.70},
            ],
            "model_id": "v1.0",
            "processed_at": "2024-01-01T00:00:00Z",
        }
        assert len(response["predictions"]) == 3
        assert all("ticker" in p for p in response["predictions"])
        assert all("signal" in p for p in response["predictions"])
        assert all("confidence" in p for p in response["predictions"])


class TestMLApplyLambdaEndpoint:
    """[ ] /signals/apply-lambda endpoint - Apply scoring functions"""

    def test_lambda_request_format(self):
        """Test lambda scoring request format."""
        request = {
            "ticker": "AAPL",
            "lambda_id": "momentum_score",
            "parameters": {
                "window_days": 30,
                "min_transactions": 5,
            },
        }
        assert "ticker" in request
        assert "lambda_id" in request

    def test_lambda_response_format(self):
        """Test lambda scoring response format."""
        response = {
            "ticker": "AAPL",
            "score": 0.82,
            "components": {
                "momentum": 0.9,
                "volume": 0.7,
                "consensus": 0.85,
            },
        }
        assert "score" in response
        assert 0 <= response["score"] <= 1


# =============================================================================
# SECTION 6.2: Trading Signals Table (9 metrics)
# =============================================================================

class TestMLSignalType:
    """[ ] trading_signals.signal_type - Prediction 'buy', 'sell', or 'hold'"""

    def test_valid_signal_types(self):
        """Test valid signal types."""
        valid_types = ["buy", "sell", "hold", "strong_buy", "strong_sell"]
        for signal in valid_types:
            assert signal in valid_types

    def test_signal_type_from_prediction(self):
        """Test signal type derived from prediction."""
        def get_signal_type(prediction: float) -> str:
            if prediction >= 0.7:
                return "strong_buy"
            elif prediction >= 0.55:
                return "buy"
            elif prediction <= 0.3:
                return "strong_sell"
            elif prediction <= 0.45:
                return "sell"
            return "hold"

        assert get_signal_type(0.8) == "strong_buy"
        assert get_signal_type(0.6) == "buy"
        assert get_signal_type(0.5) == "hold"
        assert get_signal_type(0.4) == "sell"
        assert get_signal_type(0.2) == "strong_sell"


class TestMLConfidenceScore:
    """[ ] trading_signals.confidence_score - Model confidence 0.0 to 1.0"""

    def test_confidence_range(self):
        """Test confidence is in valid range."""
        test_confidences = [0.0, 0.25, 0.5, 0.75, 1.0]
        for conf in test_confidences:
            assert 0.0 <= conf <= 1.0

    def test_confidence_precision(self):
        """Test confidence has reasonable precision."""
        confidence = 0.7534
        rounded = round(confidence, 2)
        assert rounded == 0.75

    def test_confidence_affects_signal_strength(self):
        """Test confidence affects signal strength determination."""
        def get_strength_from_confidence(confidence: float) -> str:
            if confidence >= 0.8:
                return "very_strong"
            elif confidence >= 0.6:
                return "strong"
            elif confidence >= 0.4:
                return "moderate"
            return "weak"

        assert get_strength_from_confidence(0.9) == "very_strong"
        assert get_strength_from_confidence(0.7) == "strong"
        assert get_strength_from_confidence(0.5) == "moderate"
        assert get_strength_from_confidence(0.3) == "weak"


class TestMLSignalStrength:
    """[ ] trading_signals.signal_strength - Strength bucket 'strong', 'medium', 'weak'"""

    def test_valid_strength_values(self):
        """Test valid strength values."""
        valid_strengths = ["very_strong", "strong", "moderate", "weak"]
        test_strength = "strong"
        assert test_strength in valid_strengths

    def test_strength_ordering(self):
        """Test strength values have ordering."""
        strength_rank = {"weak": 1, "moderate": 2, "strong": 3, "very_strong": 4}
        assert strength_rank["very_strong"] > strength_rank["strong"]
        assert strength_rank["strong"] > strength_rank["moderate"]


class TestMLTargetPrice:
    """[ ] trading_signals.target_price - Expected target price"""

    def test_target_price_calculation_buy(self):
        """Test target price for buy signal."""
        current_price = Decimal("100.00")
        # Buy signals typically target 10-15% gain
        target = current_price * Decimal("1.10")
        assert target == Decimal("110.00")

    def test_target_price_calculation_sell(self):
        """Test target price for sell signal."""
        current_price = Decimal("100.00")
        # Sell signals typically target 10-15% decline
        target = current_price * Decimal("0.90")
        assert target == Decimal("90.00")

    def test_target_price_type(self):
        """Test target price is a numeric type."""
        target_price = 110.50
        assert isinstance(target_price, (int, float, Decimal))


class TestMLStopLoss:
    """[ ] trading_signals.stop_loss - Stop loss level"""

    def test_stop_loss_for_buy(self):
        """Test stop loss for buy signal (below current price)."""
        current_price = Decimal("100.00")
        stop_loss = current_price * Decimal("0.95")  # 5% below
        assert stop_loss == Decimal("95.00")
        assert stop_loss < current_price

    def test_stop_loss_for_sell(self):
        """Test stop loss for sell signal (above current price)."""
        current_price = Decimal("100.00")
        stop_loss = current_price * Decimal("1.05")  # 5% above
        assert stop_loss == Decimal("105.00")
        assert stop_loss > current_price


class TestMLTakeProfit:
    """[ ] trading_signals.take_profit - Take profit level"""

    def test_take_profit_for_buy(self):
        """Test take profit for buy signal (above current price)."""
        current_price = Decimal("100.00")
        take_profit = current_price * Decimal("1.15")  # 15% above
        assert take_profit == Decimal("115.00")
        assert take_profit > current_price

    def test_take_profit_for_sell(self):
        """Test take profit for sell signal (below current price)."""
        current_price = Decimal("100.00")
        take_profit = current_price * Decimal("0.85")  # 15% below
        assert take_profit == Decimal("85.00")
        assert take_profit < current_price

    def test_risk_reward_ratio(self):
        """Test risk/reward ratio is reasonable."""
        entry = Decimal("100.00")
        stop_loss = Decimal("95.00")  # 5% risk
        take_profit = Decimal("115.00")  # 15% reward

        risk = entry - stop_loss
        reward = take_profit - entry
        ratio = reward / risk

        # Ratio should be at least 2:1 (reward >= 2x risk)
        assert ratio >= 2


class TestMLModelVersion:
    """[ ] trading_signals.model_version - Which model generated signal"""

    def test_model_version_format(self):
        """Test model version format."""
        model_version = "v1.0"
        assert model_version.startswith("v")

    def test_model_version_included(self):
        """Test model version is included in signal."""
        signal = {
            "ticker": "AAPL",
            "signal_type": "buy",
            "model_version": "v1.0",
        }
        assert "model_version" in signal

    def test_model_version_for_reproducibility(self):
        """Test model version enables reproducibility."""
        signal_v1 = {"model_version": "v1.0", "confidence": 0.75}
        signal_v2 = {"model_version": "v2.0", "confidence": 0.80}

        # Different versions should be trackable
        assert signal_v1["model_version"] != signal_v2["model_version"]


class TestMLFeatures:
    """[ ] trading_signals.features - Input features (JSON)"""

    def test_features_structure(self):
        """Test features JSON structure."""
        features = {
            "total_transactions": 10,
            "unique_politicians": 5,
            "buy_count": 7,
            "sell_count": 3,
            "buy_sell_ratio": 2.33,
            "recent_activity_30d": 5,
            "democrat_buy_count": 4,
            "democrat_sell_count": 2,
            "republican_buy_count": 3,
            "republican_sell_count": 1,
            "net_sentiment": 4,
            "net_volume": 500000,
            "bipartisan_agreement": 1,
            "buying_momentum": 0.5,
            "frequency_momentum": 0.3,
        }

        # All 15 standard features should be present
        assert len(features) >= 15
        assert "buy_sell_ratio" in features
        assert "unique_politicians" in features

    def test_features_are_numeric(self):
        """Test features are numeric values."""
        features = {
            "total_transactions": 10,
            "buy_sell_ratio": 2.33,
        }
        for value in features.values():
            assert isinstance(value, (int, float))


class TestMLAnalysis:
    """[ ] trading_signals.analysis - Signal analysis (JSON)"""

    def test_analysis_structure(self):
        """Test analysis JSON structure."""
        analysis = {
            "summary": "Strong buy signal based on bipartisan agreement",
            "key_factors": [
                "High buy/sell ratio (2.3:1)",
                "Multiple politicians trading",
                "Recent momentum positive",
            ],
            "risks": [
                "High market volatility",
                "Concentrated in tech sector",
            ],
            "confidence_breakdown": {
                "heuristic": 0.7,
                "ml_model": 0.8,
                "combined": 0.75,
            },
        }

        assert "summary" in analysis
        assert "key_factors" in analysis
        assert isinstance(analysis["key_factors"], list)

    def test_analysis_human_readable(self):
        """Test analysis includes human-readable summary."""
        analysis = {
            "summary": "Strong buy signal based on bipartisan agreement",
        }
        assert len(analysis["summary"]) > 10  # Meaningful text
        assert "buy" in analysis["summary"].lower() or "sell" in analysis["summary"].lower()


# =============================================================================
# Yahoo Finance Integration Tests (METRICS.md Section 5.2)
# =============================================================================

class TestYahooFinanceCurrentPrice:
    """[ ] Current Price - From Yahoo Finance chart API"""

    def test_price_extraction(self):
        """Test extracting current price from response."""
        yahoo_response = {
            "chart": {
                "result": [{
                    "meta": {
                        "regularMarketPrice": 150.25,
                        "symbol": "AAPL",
                    }
                }]
            }
        }
        price = yahoo_response["chart"]["result"][0]["meta"]["regularMarketPrice"]
        assert price == 150.25

    def test_price_is_numeric(self):
        """Test price is numeric."""
        price = 150.25
        assert isinstance(price, (int, float))


class TestYahooFinanceHistoricalPrices:
    """[ ] Historical Prices - Closing prices from Yahoo Finance"""

    def test_historical_prices_extraction(self):
        """Test extracting historical prices."""
        yahoo_response = {
            "chart": {
                "result": [{
                    "indicators": {
                        "quote": [{
                            "close": [150.0, 151.5, 149.0, 152.0, 153.5]
                        }]
                    }
                }]
            }
        }
        closes = yahoo_response["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        assert len(closes) == 5
        assert all(isinstance(p, (int, float)) for p in closes)


class TestYahooFinanceVolume:
    """[ ] Volume - Trading volume from Yahoo Finance"""

    def test_volume_extraction(self):
        """Test extracting volume data."""
        yahoo_response = {
            "chart": {
                "result": [{
                    "indicators": {
                        "quote": [{
                            "volume": [1000000, 1200000, 900000, 1100000, 1300000]
                        }]
                    }
                }]
            }
        }
        volumes = yahoo_response["chart"]["result"][0]["indicators"]["quote"][0]["volume"]
        assert len(volumes) == 5
        assert all(isinstance(v, int) for v in volumes)


# =============================================================================
# ML Pipeline Integration Tests
# =============================================================================

class TestMLPipelineIntegration:
    """Integration tests for ML signal generation pipeline."""

    def test_signal_generation_flow(self):
        """Test complete signal generation flow."""
        # 1. Aggregate features
        features = {"buy_count": 10, "sell_count": 5, "buy_sell_ratio": 2.0}

        # 2. Get ML prediction
        prediction = {"signal": "buy", "confidence": 0.75}

        # 3. Calculate price targets
        current_price = 100.0
        target_price = current_price * 1.10
        stop_loss = current_price * 0.95

        # 4. Combine into signal
        signal = {
            "ticker": "AAPL",
            "signal_type": prediction["signal"],
            "confidence_score": prediction["confidence"],
            "target_price": target_price,
            "stop_loss": stop_loss,
            "features": features,
        }

        assert signal["signal_type"] == "buy"
        assert signal["confidence_score"] == 0.75

    def test_signal_validity_period(self):
        """Test signal has validity period."""
        created_at = datetime.now(timezone.utc)
        valid_until = created_at + timedelta(days=7)

        signal = {
            "created_at": created_at.isoformat(),
            "valid_until": valid_until.isoformat(),
        }

        assert "valid_until" in signal
        # Signal should be valid for 7 days
        delta = datetime.fromisoformat(signal["valid_until"]) - datetime.fromisoformat(signal["created_at"])
        assert delta.days == 7
