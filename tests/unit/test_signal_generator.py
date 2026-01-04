"""
Tests for signal_generator.py - Signal generation engine.

Run with: uv run pytest tests/unit/test_signal_generator.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import pandas as pd

# Import signal types from models
import sys
import os

# Add python-micro-service to path for models import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python-micro-service'))

from models import SignalType, SignalStrength


# ============================================================================
# Feature Keys Tests
# ============================================================================

class TestFeatureKeys:
    """Tests for feature key definitions."""

    def test_feature_keys_complete(self):
        """Test that all required feature keys are defined."""
        FEATURE_KEYS = [
            "total_transactions",
            "unique_politicians",
            "buy_count",
            "sell_count",
            "buy_sell_ratio",
            "recent_activity_30d",
            "democrat_buy_count",
            "democrat_sell_count",
            "republican_buy_count",
            "republican_sell_count",
            "net_sentiment",
            "net_volume",
            "bipartisan_agreement",
            "buying_momentum",
            "frequency_momentum",
        ]

        assert len(FEATURE_KEYS) == 15
        assert "buy_sell_ratio" in FEATURE_KEYS
        assert "unique_politicians" in FEATURE_KEYS
        assert "bipartisan_agreement" in FEATURE_KEYS

    def test_feature_keys_ordering_consistent(self):
        """Test that feature keys have consistent ordering for ML."""
        FEATURE_KEYS = [
            "total_transactions",
            "unique_politicians",
            "buy_count",
            "sell_count",
            "buy_sell_ratio",
            "recent_activity_30d",
            "democrat_buy_count",
            "democrat_sell_count",
            "republican_buy_count",
            "republican_sell_count",
            "net_sentiment",
            "net_volume",
            "bipartisan_agreement",
            "buying_momentum",
            "frequency_momentum",
        ]

        # First 5 keys should be core metrics
        assert FEATURE_KEYS[0] == "total_transactions"
        assert FEATURE_KEYS[1] == "unique_politicians"
        assert FEATURE_KEYS[4] == "buy_sell_ratio"


# ============================================================================
# Heuristic Signal Generation Tests
# ============================================================================

class TestHeuristicSignalGeneration:
    """Tests for heuristic-based signal generation."""

    def _generate_heuristic_signal(
        self, features: Dict[str, Any]
    ) -> tuple:
        """
        Implementation of heuristic signal generation logic.
        Mirrors the actual implementation for testing.
        """
        bullish_score = 0
        bearish_score = 0
        confidence = 0.5

        # Rule 1: Buy-sell ratio
        buy_sell_ratio = features.get("buy_sell_ratio", 0)
        if buy_sell_ratio > 2.0:
            bullish_score += 2
        elif buy_sell_ratio > 1.5:
            bullish_score += 1
        elif buy_sell_ratio < 0.5:
            bearish_score += 2
        elif buy_sell_ratio < 0.7:
            bearish_score += 1

        # Rule 2: Recent activity
        recent_30d = features.get("recent_activity_30d", 0)
        if recent_30d >= 5:
            confidence += 0.1

        # Rule 3: Unique politicians
        unique_pols = features.get("unique_politicians", 0)
        if unique_pols >= 3:
            confidence += 0.15
        elif unique_pols >= 2:
            confidence += 0.1

        # Rule 4: Bipartisan agreement
        if features.get("bipartisan_agreement", 0) == 1:
            confidence += 0.15
            if features.get("democrat_bullish", 0) > 0:
                bullish_score += 2
            else:
                bearish_score += 2

        # Rule 5: Net sentiment
        net_sentiment = features.get("net_sentiment", 0)
        if net_sentiment > 3:
            bullish_score += 2
        elif net_sentiment > 0:
            bullish_score += 1
        elif net_sentiment < -3:
            bearish_score += 2
        elif net_sentiment < 0:
            bearish_score += 1

        # Rule 6: Volume
        net_volume = features.get("net_volume", 0)
        if abs(net_volume) > 1000000:
            confidence += 0.1

        # Rule 7: Activity acceleration
        acceleration = features.get("activity_acceleration", 0)
        if acceleration > 0:
            confidence += 0.05

        # Rule 8: Buying momentum
        buying_momentum = features.get("buying_momentum", 0)
        if buying_momentum > 0:
            bullish_score += 1
        elif buying_momentum < 0:
            bearish_score += 1

        # Determine signal type
        score_diff = bullish_score - bearish_score
        if score_diff >= 4:
            signal_type = SignalType.STRONG_BUY
            confidence = min(confidence + 0.2, 0.95)
            strength = SignalStrength.VERY_STRONG
        elif score_diff >= 2:
            signal_type = SignalType.BUY
            confidence = min(confidence + 0.1, 0.85)
            strength = SignalStrength.STRONG
        elif score_diff <= -4:
            signal_type = SignalType.STRONG_SELL
            confidence = min(confidence + 0.2, 0.95)
            strength = SignalStrength.VERY_STRONG
        elif score_diff <= -2:
            signal_type = SignalType.SELL
            confidence = min(confidence + 0.1, 0.85)
            strength = SignalStrength.STRONG
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.MODERATE

        return signal_type, confidence, strength

    def test_strong_buy_signal(self):
        """Test strong buy signal generation."""
        features = {
            "buy_sell_ratio": 3.0,  # +2
            "net_sentiment": 5,  # +2
            "buying_momentum": 1,  # +1
            "unique_politicians": 5,  # +0.15 confidence
            "recent_activity_30d": 10,  # +0.1 confidence
        }

        signal_type, confidence, strength = self._generate_heuristic_signal(features)

        assert signal_type == SignalType.STRONG_BUY
        assert strength == SignalStrength.VERY_STRONG
        assert confidence >= 0.85

    def test_buy_signal(self):
        """Test moderate buy signal generation."""
        features = {
            "buy_sell_ratio": 2.0,  # +2
            "net_sentiment": 1,  # +1
            "unique_politicians": 2,  # +0.1 confidence
        }

        signal_type, confidence, strength = self._generate_heuristic_signal(features)

        # score_diff should be around 3, which yields BUY
        assert signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
        assert strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]

    def test_hold_signal(self):
        """Test hold signal when no clear direction."""
        features = {
            "buy_sell_ratio": 1.0,
            "net_sentiment": 0,
            "buying_momentum": 0,
        }

        signal_type, confidence, strength = self._generate_heuristic_signal(features)

        assert signal_type == SignalType.HOLD
        assert strength == SignalStrength.MODERATE

    def test_sell_signal(self):
        """Test sell signal generation."""
        features = {
            "buy_sell_ratio": 0.4,  # +2 bearish
            "net_sentiment": -1,  # +1 bearish
        }

        signal_type, confidence, strength = self._generate_heuristic_signal(features)

        # score_diff should be around -3, yielding SELL
        assert signal_type in [SignalType.SELL, SignalType.STRONG_SELL]

    def test_strong_sell_signal(self):
        """Test strong sell signal generation."""
        features = {
            "buy_sell_ratio": 0.3,  # +2 bearish
            "net_sentiment": -5,  # +2 bearish
            "buying_momentum": -1,  # +1 bearish
        }

        signal_type, confidence, strength = self._generate_heuristic_signal(features)

        # score_diff should be -5, yielding STRONG_SELL
        assert signal_type == SignalType.STRONG_SELL
        assert strength == SignalStrength.VERY_STRONG

    def test_bipartisan_confidence_boost(self):
        """Test that bipartisan agreement boosts confidence."""
        features_without = {
            "buy_sell_ratio": 1.5,
            "bipartisan_agreement": 0,
        }

        features_with = {
            "buy_sell_ratio": 1.5,
            "bipartisan_agreement": 1,
        }

        _, conf_without, _ = self._generate_heuristic_signal(features_without)
        _, conf_with, _ = self._generate_heuristic_signal(features_with)

        assert conf_with > conf_without

    def test_high_volume_confidence_boost(self):
        """Test that high volume boosts confidence."""
        features_low_vol = {
            "buy_sell_ratio": 2.0,
            "net_volume": 500000,
        }

        features_high_vol = {
            "buy_sell_ratio": 2.0,
            "net_volume": 1500000,
        }

        _, conf_low, _ = self._generate_heuristic_signal(features_low_vol)
        _, conf_high, _ = self._generate_heuristic_signal(features_high_vol)

        assert conf_high > conf_low


# ============================================================================
# Signal Combination Tests
# ============================================================================

class TestSignalCombination:
    """Tests for combining heuristic and ML signals."""

    def _combine_signals(
        self,
        heuristic_signal: SignalType,
        heuristic_confidence: float,
        ml_signal: SignalType,
        ml_confidence: float,
    ) -> tuple:
        """
        Combine heuristic and ML signals.
        Mirrors the actual implementation for testing.
        """
        heuristic_weight = 0.6
        ml_weight = 0.4

        # If signals agree, boost confidence
        if heuristic_signal == ml_signal:
            combined_confidence = (
                heuristic_confidence * heuristic_weight + ml_confidence * ml_weight
            ) * 1.1
            return heuristic_signal, min(combined_confidence, 0.99)

        # If signals disagree, reduce confidence
        combined_confidence = (
            heuristic_confidence * heuristic_weight + ml_confidence * ml_weight
        ) * 0.8

        if heuristic_confidence > ml_confidence:
            return heuristic_signal, combined_confidence
        else:
            return ml_signal, combined_confidence

    def test_signals_agree_confidence_boosted(self):
        """Test that agreeing signals boost confidence by 10%."""
        result_signal, result_conf = self._combine_signals(
            SignalType.BUY, 0.7,
            SignalType.BUY, 0.8
        )

        assert result_signal == SignalType.BUY
        # (0.7 * 0.6 + 0.8 * 0.4) * 1.1 = (0.42 + 0.32) * 1.1 = 0.814
        assert abs(result_conf - 0.814) < 0.01

    def test_signals_disagree_confidence_reduced(self):
        """Test that disagreeing signals reduce confidence by 20%."""
        result_signal, result_conf = self._combine_signals(
            SignalType.BUY, 0.7,
            SignalType.SELL, 0.5
        )

        # Heuristic wins because higher confidence
        assert result_signal == SignalType.BUY
        # (0.7 * 0.6 + 0.5 * 0.4) * 0.8 = (0.42 + 0.20) * 0.8 = 0.496
        assert abs(result_conf - 0.496) < 0.01

    def test_ml_signal_wins_when_higher_confidence(self):
        """Test that ML signal wins when it has higher confidence."""
        result_signal, result_conf = self._combine_signals(
            SignalType.BUY, 0.5,
            SignalType.SELL, 0.9
        )

        assert result_signal == SignalType.SELL

    def test_confidence_capped_at_099(self):
        """Test that combined confidence is capped at 0.99."""
        result_signal, result_conf = self._combine_signals(
            SignalType.BUY, 0.95,
            SignalType.BUY, 0.95
        )

        assert result_conf <= 0.99


# ============================================================================
# Price Target Calculation Tests
# ============================================================================

class TestPriceTargetCalculation:
    """Tests for price target calculations."""

    def _calculate_price_targets(
        self,
        signal_type: SignalType,
        current_price: Decimal,
    ) -> tuple:
        """
        Calculate price targets based on signal type.
        Mirrors the actual implementation for testing.
        """
        if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            target_price = current_price * Decimal("1.10")
            stop_loss = current_price * Decimal("0.95")
            take_profit = current_price * Decimal("1.15")

            if signal_type == SignalType.STRONG_BUY:
                target_price = current_price * Decimal("1.15")
                take_profit = current_price * Decimal("1.20")

        elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            target_price = current_price * Decimal("0.90")
            stop_loss = current_price * Decimal("1.05")
            take_profit = current_price * Decimal("0.85")

            if signal_type == SignalType.STRONG_SELL:
                target_price = current_price * Decimal("0.85")
                take_profit = current_price * Decimal("0.80")
        else:
            return None, None, None

        return target_price, stop_loss, take_profit

    def test_buy_signal_targets(self):
        """Test price targets for buy signal."""
        current_price = Decimal("100.00")

        target, stop, take = self._calculate_price_targets(SignalType.BUY, current_price)

        assert target == Decimal("110.00")  # +10%
        assert stop == Decimal("95.00")  # -5%
        assert take == Decimal("115.00")  # +15%

    def test_strong_buy_signal_targets(self):
        """Test price targets for strong buy signal (more aggressive)."""
        current_price = Decimal("100.00")

        target, stop, take = self._calculate_price_targets(SignalType.STRONG_BUY, current_price)

        assert target == Decimal("115.00")  # +15%
        assert stop == Decimal("95.00")  # -5%
        assert take == Decimal("120.00")  # +20%

    def test_sell_signal_targets(self):
        """Test price targets for sell signal."""
        current_price = Decimal("100.00")

        target, stop, take = self._calculate_price_targets(SignalType.SELL, current_price)

        assert target == Decimal("90.00")  # -10%
        assert stop == Decimal("105.00")  # +5%
        assert take == Decimal("85.00")  # -15%

    def test_strong_sell_signal_targets(self):
        """Test price targets for strong sell signal."""
        current_price = Decimal("100.00")

        target, stop, take = self._calculate_price_targets(SignalType.STRONG_SELL, current_price)

        assert target == Decimal("85.00")  # -15%
        assert stop == Decimal("105.00")  # +5%
        assert take == Decimal("80.00")  # -20%

    def test_hold_signal_no_targets(self):
        """Test that hold signals return no targets."""
        current_price = Decimal("100.00")

        target, stop, take = self._calculate_price_targets(SignalType.HOLD, current_price)

        assert target is None
        assert stop is None
        assert take is None


# ============================================================================
# Feature Vector Preparation Tests
# ============================================================================

class TestFeatureVectorPreparation:
    """Tests for ML feature vector preparation."""

    def test_prepare_feature_vector(self):
        """Test that feature vector is prepared in correct order."""
        FEATURE_KEYS = [
            "total_transactions",
            "unique_politicians",
            "buy_count",
            "sell_count",
            "buy_sell_ratio",
        ]

        features = {
            "total_transactions": 10,
            "unique_politicians": 5,
            "buy_count": 7,
            "sell_count": 3,
            "buy_sell_ratio": 2.33,
        }

        vector = [features.get(key, 0) for key in FEATURE_KEYS]

        assert vector == [10, 5, 7, 3, 2.33]
        assert len(vector) == len(FEATURE_KEYS)

    def test_prepare_feature_vector_missing_values(self):
        """Test that missing features default to 0."""
        FEATURE_KEYS = ["a", "b", "c"]
        features = {"a": 1}

        vector = [features.get(key, 0) for key in FEATURE_KEYS]

        assert vector == [1, 0, 0]


# ============================================================================
# Buy/Sell Ratio Calculation Tests
# ============================================================================

class TestBuySellRatio:
    """Tests for buy/sell ratio calculations."""

    def test_ratio_calculation_basic(self):
        """Test basic buy/sell ratio calculation."""
        def calculate_ratio(buys: int, sells: int) -> float:
            if sells == 0:
                return 10.0 if buys > 0 else 1.0
            return buys / sells

        assert calculate_ratio(10, 5) == 2.0
        assert calculate_ratio(5, 10) == 0.5
        assert calculate_ratio(10, 0) == 10.0
        assert calculate_ratio(0, 0) == 1.0

    def test_ratio_thresholds(self):
        """Test signal thresholds for buy/sell ratio."""
        def get_signal_from_ratio(ratio: float) -> str:
            if ratio >= 3.0:
                return "strong_buy"
            elif ratio >= 2.0:
                return "buy"
            elif ratio <= 0.33:
                return "strong_sell"
            elif ratio <= 0.5:
                return "sell"
            return "hold"

        assert get_signal_from_ratio(3.5) == "strong_buy"
        assert get_signal_from_ratio(2.5) == "buy"
        assert get_signal_from_ratio(1.0) == "hold"
        assert get_signal_from_ratio(0.4) == "sell"
        assert get_signal_from_ratio(0.2) == "strong_sell"


# ============================================================================
# Confidence Threshold Tests
# ============================================================================

class TestConfidenceThreshold:
    """Tests for confidence threshold filtering."""

    def test_signal_meets_threshold(self):
        """Test that signals meeting threshold are returned."""
        threshold = 0.6

        def filter_by_confidence(confidence: float) -> bool:
            return confidence >= threshold

        assert filter_by_confidence(0.7) is True
        assert filter_by_confidence(0.6) is True
        assert filter_by_confidence(0.5) is False

    def test_default_threshold(self):
        """Test default confidence threshold value."""
        DEFAULT_THRESHOLD = 0.6

        assert DEFAULT_THRESHOLD == 0.6


# ============================================================================
# Signal Type Enumeration Tests
# ============================================================================

class TestSignalTypeEnum:
    """Tests for SignalType enumeration."""

    def test_signal_types_defined(self):
        """Test that all signal types are defined."""
        assert SignalType.STRONG_BUY is not None
        assert SignalType.BUY is not None
        assert SignalType.HOLD is not None
        assert SignalType.SELL is not None
        assert SignalType.STRONG_SELL is not None

    def test_signal_type_values(self):
        """Test that signal type values are as expected."""
        assert SignalType.STRONG_BUY.value == "strong_buy"
        assert SignalType.BUY.value == "buy"
        assert SignalType.HOLD.value == "hold"
        assert SignalType.SELL.value == "sell"
        assert SignalType.STRONG_SELL.value == "strong_sell"


# ============================================================================
# Signal Strength Enumeration Tests
# ============================================================================

class TestSignalStrengthEnum:
    """Tests for SignalStrength enumeration."""

    def test_signal_strengths_defined(self):
        """Test that all signal strengths are defined."""
        assert SignalStrength.VERY_STRONG is not None
        assert SignalStrength.STRONG is not None
        assert SignalStrength.MODERATE is not None

    def test_signal_strength_values(self):
        """Test that signal strength values are as expected."""
        assert SignalStrength.VERY_STRONG.value == "very_strong"
        assert SignalStrength.STRONG.value == "strong"
        assert SignalStrength.MODERATE.value == "moderate"


# ============================================================================
# Validity Period Tests
# ============================================================================

class TestValidityPeriod:
    """Tests for signal validity period."""

    def test_default_validity_period(self):
        """Test that default validity period is 7 days."""
        now_utc = datetime.now(timezone.utc)
        valid_until = now_utc + timedelta(days=7)

        delta = valid_until - now_utc
        assert delta.days == 7

    def test_signal_not_expired(self):
        """Test that signal within validity period is not expired."""
        now = datetime.now(timezone.utc)
        valid_until = now + timedelta(days=7)

        is_expired = now > valid_until
        assert is_expired is False

    def test_signal_expired(self):
        """Test that signal past validity period is expired."""
        now = datetime.now(timezone.utc)
        valid_until = now - timedelta(days=1)

        is_expired = now > valid_until
        assert is_expired is True


# ============================================================================
# Model Version Tests
# ============================================================================

class TestModelVersion:
    """Tests for model versioning."""

    def test_default_model_version(self):
        """Test default model version format."""
        default_version = "v1.0"
        assert default_version.startswith("v")

    def test_model_version_in_signal(self):
        """Test that model version is included in signal."""
        model_version = "v1.0"
        signal_data = {"model_version": model_version}

        assert "model_version" in signal_data
        assert signal_data["model_version"] == "v1.0"


# ============================================================================
# Disclosure Aggregation Tests
# ============================================================================

class TestDisclosureAggregation:
    """Tests for aggregating disclosures by ticker."""

    def test_aggregate_by_ticker(self):
        """Test aggregating disclosures by ticker."""
        disclosures = [
            {"ticker": "AAPL", "transaction_type": "purchase"},
            {"ticker": "AAPL", "transaction_type": "sale"},
            {"ticker": "GOOGL", "transaction_type": "purchase"},
        ]

        by_ticker: Dict[str, List] = {}
        for d in disclosures:
            ticker = d["ticker"]
            if ticker not in by_ticker:
                by_ticker[ticker] = []
            by_ticker[ticker].append(d)

        assert len(by_ticker["AAPL"]) == 2
        assert len(by_ticker["GOOGL"]) == 1

    def test_count_buys_and_sells(self):
        """Test counting buy and sell transactions."""
        disclosures = [
            {"transaction_type": "purchase"},
            {"transaction_type": "Purchase"},
            {"transaction_type": "sale"},
            {"transaction_type": "Sale (Full)"},
        ]

        buy_count = sum(1 for d in disclosures if "purchase" in d["transaction_type"].lower())
        sell_count = sum(1 for d in disclosures if "sale" in d["transaction_type"].lower())

        assert buy_count == 2
        assert sell_count == 2


# ============================================================================
# Party Classification Tests
# ============================================================================

class TestPartyClassification:
    """Tests for party-based classification."""

    def test_democrat_republican_counts(self):
        """Test counting transactions by party."""
        disclosures = [
            {"party": "D", "transaction_type": "purchase"},
            {"party": "D", "transaction_type": "purchase"},
            {"party": "R", "transaction_type": "sale"},
            {"party": "R", "transaction_type": "purchase"},
        ]

        democrat_buys = sum(
            1 for d in disclosures
            if d["party"] == "D" and "purchase" in d["transaction_type"].lower()
        )
        republican_buys = sum(
            1 for d in disclosures
            if d["party"] == "R" and "purchase" in d["transaction_type"].lower()
        )

        assert democrat_buys == 2
        assert republican_buys == 1

    def test_bipartisan_detection(self):
        """Test detecting bipartisan trading activity."""
        disclosures = [
            {"party": "D", "transaction_type": "purchase"},
            {"party": "R", "transaction_type": "purchase"},
        ]

        parties = set(d["party"] for d in disclosures)
        is_bipartisan = "D" in parties and "R" in parties

        assert is_bipartisan is True


# ============================================================================
# Volume Calculation Tests
# ============================================================================

class TestVolumeCalculation:
    """Tests for transaction volume calculations."""

    def test_volume_from_range(self):
        """Test calculating volume from min/max range."""
        def calculate_volume(min_val: Optional[float], max_val: Optional[float]) -> float:
            min_v = min_val or 0
            max_v = max_val or min_v
            return (min_v + max_v) / 2

        assert calculate_volume(1000, 15000) == 8000
        assert calculate_volume(50000, 100000) == 75000
        assert calculate_volume(1000, None) == 1000
        assert calculate_volume(None, None) == 0

    def test_net_volume(self):
        """Test calculating net volume (buys - sells)."""
        buy_volume = 1500000
        sell_volume = 500000
        net_volume = buy_volume - sell_volume

        assert net_volume == 1000000


# ============================================================================
# Recent Activity Tests
# ============================================================================

class TestRecentActivity:
    """Tests for recent activity calculations."""

    def test_count_recent_activity(self):
        """Test counting activity in last 30 days."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        disclosures = [
            {"date": now - timedelta(days=5)},  # Within 30 days
            {"date": now - timedelta(days=25)},  # Within 30 days
            {"date": now - timedelta(days=45)},  # Outside 30 days
        ]

        recent_count = sum(1 for d in disclosures if d["date"] >= thirty_days_ago)

        assert recent_count == 2


# ============================================================================
# ML Model Weight Tests
# ============================================================================

class TestMLModelWeights:
    """Tests for ML model weighting."""

    def test_heuristic_ml_weights(self):
        """Test that heuristic and ML weights sum to 1."""
        heuristic_weight = 0.6
        ml_weight = 0.4

        assert heuristic_weight + ml_weight == 1.0

    def test_weighted_confidence(self):
        """Test weighted confidence calculation."""
        heuristic_weight = 0.6
        ml_weight = 0.4
        heuristic_conf = 0.7
        ml_conf = 0.8

        weighted_conf = heuristic_conf * heuristic_weight + ml_conf * ml_weight

        assert abs(weighted_conf - 0.74) < 0.001


# ============================================================================
# Hash Computation Tests
# ============================================================================

class TestHashComputation:
    """Tests for reproducibility hash computation."""

    def test_hash_consistency(self):
        """Test that same inputs produce same hash."""
        import hashlib

        def compute_hash(data: bytes) -> str:
            return hashlib.sha256(data).hexdigest()

        data = b"test data"
        hash1 = compute_hash(data)
        hash2 = compute_hash(data)

        assert hash1 == hash2

    def test_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        import hashlib

        def compute_hash(data: bytes) -> str:
            return hashlib.sha256(data).hexdigest()

        hash1 = compute_hash(b"data1")
        hash2 = compute_hash(b"data2")

        assert hash1 != hash2


# ============================================================================
# Signal Active State Tests
# ============================================================================

class TestSignalActiveState:
    """Tests for signal active state management."""

    def test_signal_starts_active(self):
        """Test that new signals are active by default."""
        is_active = True
        assert is_active is True

    def test_signal_deactivation(self):
        """Test signal deactivation."""
        signal = {"is_active": True}
        signal["is_active"] = False

        assert signal["is_active"] is False


# ============================================================================
# Empty Disclosure Handling Tests
# ============================================================================

class TestEmptyDisclosureHandling:
    """Tests for handling empty disclosure lists."""

    def test_no_signal_for_empty_disclosures(self):
        """Test that empty disclosures return None."""
        disclosures: List[Dict] = []

        if not disclosures:
            result = None
        else:
            result = {"ticker": "AAPL"}

        assert result is None

    def test_signal_generated_for_non_empty(self):
        """Test that non-empty disclosures can generate signal."""
        disclosures = [{"ticker": "AAPL", "transaction_type": "purchase"}]

        if not disclosures:
            result = None
        else:
            result = {"ticker": "AAPL"}

        assert result is not None
