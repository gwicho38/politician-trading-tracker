"""Tests for TrainingConfig model and FeatureToggles."""

import pytest
from pydantic import ValidationError

from app.models.training_config import (
    DEFAULT_THRESHOLDS_3CLASS,
    DEFAULT_THRESHOLDS_5CLASS,
    FeatureToggles,
    TrainingConfig,
)


class TestTrainingConfigDefaults:
    """Test that default values are applied correctly."""

    def test_default_lookback_days(self):
        config = TrainingConfig()
        assert config.lookback_days == 365

    def test_default_model_type(self):
        config = TrainingConfig()
        assert config.model_type == "xgboost"

    def test_default_prediction_window(self):
        config = TrainingConfig()
        assert config.prediction_window_days == 7

    def test_default_num_classes(self):
        config = TrainingConfig()
        assert config.num_classes == 5

    def test_default_thresholds_are_5class(self):
        config = TrainingConfig()
        assert config.thresholds == DEFAULT_THRESHOLDS_5CLASS
        assert "strong_buy" in config.thresholds
        assert "strong_sell" in config.thresholds
        assert "buy" in config.thresholds
        assert "sell" in config.thresholds

    def test_default_features(self):
        config = TrainingConfig()
        assert config.features.enable_sector is True
        assert config.features.enable_market_regime is True
        assert config.features.enable_sentiment is False

    def test_default_hyperparams(self):
        config = TrainingConfig()
        assert config.hyperparams["n_estimators"] == 100
        assert config.hyperparams["max_depth"] == 6
        assert config.hyperparams["learning_rate"] == 0.1

    def test_default_triggered_by(self):
        config = TrainingConfig()
        assert config.triggered_by == "api"


class TestTrainingConfigValidation:
    """Test validation rules on TrainingConfig fields."""

    def test_invalid_prediction_window_raises(self):
        with pytest.raises(ValidationError, match="prediction_window_days must be 7, 14, or 30"):
            TrainingConfig(prediction_window_days=10)

    def test_invalid_num_classes_raises(self):
        with pytest.raises(ValidationError, match="num_classes must be 3 or 5"):
            TrainingConfig(num_classes=4)

    def test_invalid_model_type_raises(self):
        with pytest.raises(ValidationError):
            TrainingConfig(model_type="random_forest")

    def test_lookback_days_too_low_raises(self):
        with pytest.raises(ValidationError):
            TrainingConfig(lookback_days=29)

    def test_lookback_days_too_high_raises(self):
        with pytest.raises(ValidationError):
            TrainingConfig(lookback_days=731)

    def test_lookback_days_lower_boundary(self):
        config = TrainingConfig(lookback_days=30)
        assert config.lookback_days == 30

    def test_lookback_days_upper_boundary(self):
        config = TrainingConfig(lookback_days=730)
        assert config.lookback_days == 730

    @pytest.mark.parametrize("window", [7, 14, 30])
    def test_valid_prediction_windows(self, window):
        config = TrainingConfig(prediction_window_days=window)
        assert config.prediction_window_days == window

    @pytest.mark.parametrize("model", ["xgboost", "lightgbm"])
    def test_valid_model_types(self, model):
        config = TrainingConfig(model_type=model)
        assert config.model_type == model

    @pytest.mark.parametrize("classes", [3, 5])
    def test_valid_num_classes(self, classes):
        config = TrainingConfig(num_classes=classes)
        assert config.num_classes == classes


class TestTrainingConfig3Class:
    """Test 3-class configuration behavior."""

    def test_3class_filters_thresholds_to_buy_sell(self):
        config = TrainingConfig(num_classes=3)
        assert set(config.thresholds.keys()) == {"buy", "sell"}

    def test_3class_no_strong_buy_threshold(self):
        config = TrainingConfig(num_classes=3)
        assert "strong_buy" not in config.thresholds

    def test_3class_no_strong_sell_threshold(self):
        config = TrainingConfig(num_classes=3)
        assert "strong_sell" not in config.thresholds

    def test_3class_applies_default_thresholds(self):
        config = TrainingConfig(num_classes=3)
        assert config.thresholds["buy"] == DEFAULT_THRESHOLDS_3CLASS["buy"]
        assert config.thresholds["sell"] == DEFAULT_THRESHOLDS_3CLASS["sell"]

    def test_3class_with_custom_thresholds_preserves_buy_sell(self):
        custom = {"buy": 0.03, "sell": -0.03, "strong_buy": 0.1, "strong_sell": -0.1}
        config = TrainingConfig(num_classes=3, thresholds=custom)
        assert config.thresholds == {"buy": 0.03, "sell": -0.03}

    def test_3class_without_buy_sell_in_thresholds_applies_defaults(self):
        custom = {"strong_buy": 0.1, "strong_sell": -0.1}
        config = TrainingConfig(num_classes=3, thresholds=custom)
        assert config.thresholds["buy"] == DEFAULT_THRESHOLDS_3CLASS["buy"]
        assert config.thresholds["sell"] == DEFAULT_THRESHOLDS_3CLASS["sell"]

    def test_5class_keeps_all_thresholds(self):
        config = TrainingConfig(num_classes=5)
        assert "strong_buy" in config.thresholds
        assert "buy" in config.thresholds
        assert "sell" in config.thresholds
        assert "strong_sell" in config.thresholds


class TestTrainingConfigFeatureNames:
    """Test get_feature_names() for different feature toggle combinations."""

    CORE_FEATURES = [
        "politician_count",
        "buy_sell_ratio",
        "recent_activity_30d",
        "bipartisan",
        "net_volume",
        "volume_magnitude",
        "party_alignment",
        "disclosure_delay",
        "market_momentum",
    ]
    SECTOR_FEATURES = ["committee_relevance", "sector_performance"]
    MARKET_REGIME_FEATURES = ["vix_level", "market_return_20d", "market_breadth"]
    SENTIMENT_FEATURES = ["sentiment_score"]

    def test_default_config_returns_14_features(self):
        config = TrainingConfig()
        names = config.get_feature_names()
        # core (9) + sector (2) + market_regime (3) = 14
        assert len(names) == 14

    def test_all_features_on_returns_15_features(self):
        config = TrainingConfig(
            features=FeatureToggles(
                enable_sentiment=True,
                enable_sector=True,
                enable_market_regime=True,
            )
        )
        names = config.get_feature_names()
        # core (9) + sector (2) + market_regime (3) + sentiment (1) = 15
        assert len(names) == 15
        assert "sentiment_score" in names

    def test_all_features_off_returns_9_core_features(self):
        config = TrainingConfig(
            features=FeatureToggles(
                enable_sentiment=False,
                enable_sector=False,
                enable_market_regime=False,
            )
        )
        names = config.get_feature_names()
        assert len(names) == 9
        assert names == self.CORE_FEATURES

    def test_sector_off_removes_sector_features(self):
        config = TrainingConfig(
            features=FeatureToggles(enable_sector=False)
        )
        names = config.get_feature_names()
        for feat in self.SECTOR_FEATURES:
            assert feat not in names

    def test_market_regime_off_removes_market_features(self):
        config = TrainingConfig(
            features=FeatureToggles(enable_market_regime=False)
        )
        names = config.get_feature_names()
        for feat in self.MARKET_REGIME_FEATURES:
            assert feat not in names

    def test_sentiment_on_adds_sentiment_score(self):
        config = TrainingConfig(
            features=FeatureToggles(enable_sentiment=True)
        )
        names = config.get_feature_names()
        assert "sentiment_score" in names

    def test_feature_names_order_core_then_sector_then_regime_then_sentiment(self):
        config = TrainingConfig(
            features=FeatureToggles(
                enable_sentiment=True,
                enable_sector=True,
                enable_market_regime=True,
            )
        )
        names = config.get_feature_names()
        # Verify ordering: core features come first, then sector, then regime, then sentiment
        core_end = len(self.CORE_FEATURES)
        sector_end = core_end + len(self.SECTOR_FEATURES)
        regime_end = sector_end + len(self.MARKET_REGIME_FEATURES)

        assert names[:core_end] == self.CORE_FEATURES
        assert names[core_end:sector_end] == self.SECTOR_FEATURES
        assert names[sector_end:regime_end] == self.MARKET_REGIME_FEATURES
        assert names[regime_end:] == self.SENTIMENT_FEATURES


class TestTrainingConfigSerialization:
    """Test to_hyperparameters_dict() and from_hyperparameters_dict() round-trip."""

    def test_to_dict_includes_all_expected_keys(self):
        config = TrainingConfig()
        d = config.to_hyperparameters_dict()
        expected_keys = {
            "lookback_days",
            "model_type",
            "prediction_window_days",
            "num_classes",
            "thresholds",
            "features",
            "hyperparams",
            "triggered_by",
            "use_outcomes",
            "outcome_weight",
            "fine_tune",
            "base_model_id",
            "feature_names",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_includes_feature_names_list(self):
        config = TrainingConfig()
        d = config.to_hyperparameters_dict()
        assert isinstance(d["feature_names"], list)
        assert len(d["feature_names"]) == len(config.get_feature_names())
        assert d["feature_names"] == config.get_feature_names()

    def test_to_dict_features_is_plain_dict(self):
        config = TrainingConfig()
        d = config.to_hyperparameters_dict()
        assert isinstance(d["features"], dict)
        assert "enable_sentiment" in d["features"]
        assert "enable_sector" in d["features"]
        assert "enable_market_regime" in d["features"]

    def test_from_dict_reconstructs_defaults(self):
        config = TrainingConfig()
        d = config.to_hyperparameters_dict()
        reconstructed = TrainingConfig.from_hyperparameters_dict(d)
        assert reconstructed.lookback_days == config.lookback_days
        assert reconstructed.model_type == config.model_type
        assert reconstructed.prediction_window_days == config.prediction_window_days
        assert reconstructed.num_classes == config.num_classes
        assert reconstructed.triggered_by == config.triggered_by

    def test_from_dict_reconstructs_features(self):
        config = TrainingConfig(
            features=FeatureToggles(enable_sentiment=True)
        )
        d = config.to_hyperparameters_dict()
        reconstructed = TrainingConfig.from_hyperparameters_dict(d)
        assert reconstructed.features.enable_sentiment is True
        assert reconstructed.features.enable_sector is True
        assert reconstructed.features.enable_market_regime is True

    def test_from_dict_reconstructs_thresholds(self):
        config = TrainingConfig()
        d = config.to_hyperparameters_dict()
        reconstructed = TrainingConfig.from_hyperparameters_dict(d)
        assert reconstructed.thresholds == config.thresholds

    def test_round_trip_preserves_all_values(self):
        original = TrainingConfig(
            lookback_days=180,
            model_type="lightgbm",
            prediction_window_days=14,
            num_classes=3,
            features=FeatureToggles(
                enable_sentiment=True,
                enable_sector=False,
                enable_market_regime=True,
            ),
            hyperparams={"n_estimators": 200, "max_depth": 8},
            triggered_by="scheduler",
            use_outcomes=True,
            outcome_weight=3.5,
        )
        d = original.to_hyperparameters_dict()
        reconstructed = TrainingConfig.from_hyperparameters_dict(d)

        assert reconstructed.lookback_days == original.lookback_days
        assert reconstructed.model_type == original.model_type
        assert reconstructed.prediction_window_days == original.prediction_window_days
        assert reconstructed.num_classes == original.num_classes
        assert reconstructed.thresholds == original.thresholds
        assert reconstructed.features.enable_sentiment == original.features.enable_sentiment
        assert reconstructed.features.enable_sector == original.features.enable_sector
        assert reconstructed.features.enable_market_regime == original.features.enable_market_regime
        assert reconstructed.hyperparams == original.hyperparams
        assert reconstructed.triggered_by == original.triggered_by
        assert reconstructed.use_outcomes == original.use_outcomes
        assert reconstructed.outcome_weight == original.outcome_weight

    def test_round_trip_feature_names_match(self):
        original = TrainingConfig(
            features=FeatureToggles(enable_sentiment=True)
        )
        d = original.to_hyperparameters_dict()
        reconstructed = TrainingConfig.from_hyperparameters_dict(d)
        assert reconstructed.get_feature_names() == original.get_feature_names()

    def test_from_dict_with_empty_dict_uses_defaults(self):
        config = TrainingConfig.from_hyperparameters_dict({})
        assert config.lookback_days == 365
        assert config.model_type == "xgboost"
        assert config.prediction_window_days == 7
        assert config.num_classes == 5
        assert config.triggered_by == "api"

    def test_from_dict_with_empty_features_uses_defaults(self):
        config = TrainingConfig.from_hyperparameters_dict({"features": {}})
        assert config.features.enable_sentiment is False
        assert config.features.enable_sector is True
        assert config.features.enable_market_regime is True


class TestOutcomeFields:
    """Test use_outcomes and outcome_weight fields."""

    def test_use_outcomes_default_false(self):
        config = TrainingConfig()
        assert config.use_outcomes is False

    def test_outcome_weight_default_2(self):
        config = TrainingConfig()
        assert config.outcome_weight == 2.0

    def test_outcome_weight_validation_below_minimum(self):
        with pytest.raises(ValidationError):
            TrainingConfig(outcome_weight=0.05)

    def test_outcome_weight_validation_above_maximum(self):
        with pytest.raises(ValidationError):
            TrainingConfig(outcome_weight=10.1)

    def test_outcome_weight_at_lower_boundary(self):
        config = TrainingConfig(outcome_weight=0.1)
        assert config.outcome_weight == 0.1

    def test_outcome_weight_at_upper_boundary(self):
        config = TrainingConfig(outcome_weight=10.0)
        assert config.outcome_weight == 10.0

    def test_use_outcomes_roundtrip_serialization(self):
        original = TrainingConfig(use_outcomes=True, outcome_weight=5.0)
        d = original.to_hyperparameters_dict()
        assert d["use_outcomes"] is True
        assert d["outcome_weight"] == 5.0
        reconstructed = TrainingConfig.from_hyperparameters_dict(d)
        assert reconstructed.use_outcomes is True
        assert reconstructed.outcome_weight == 5.0

    def test_from_hyperparameters_dict_missing_outcome_fields(self):
        """Backward compat: old dicts without outcome fields use defaults."""
        data = {
            "lookback_days": 365,
            "model_type": "xgboost",
            "prediction_window_days": 7,
            "num_classes": 5,
        }
        config = TrainingConfig.from_hyperparameters_dict(data)
        assert config.use_outcomes is False
        assert config.outcome_weight == 2.0


class TestFeatureToggles:
    """Test FeatureToggles model."""

    def test_default_values(self):
        toggles = FeatureToggles()
        assert toggles.enable_sentiment is False
        assert toggles.enable_sector is True
        assert toggles.enable_market_regime is True

    def test_all_true(self):
        toggles = FeatureToggles(
            enable_sentiment=True,
            enable_sector=True,
            enable_market_regime=True,
        )
        assert toggles.enable_sentiment is True
        assert toggles.enable_sector is True
        assert toggles.enable_market_regime is True

    def test_all_false(self):
        toggles = FeatureToggles(
            enable_sentiment=False,
            enable_sector=False,
            enable_market_regime=False,
        )
        assert toggles.enable_sentiment is False
        assert toggles.enable_sector is False
        assert toggles.enable_market_regime is False

    def test_model_dump_returns_dict(self):
        toggles = FeatureToggles()
        d = toggles.model_dump()
        assert isinstance(d, dict)
        assert d == {
            "enable_sentiment": False,
            "enable_sector": True,
            "enable_market_regime": True,
        }
