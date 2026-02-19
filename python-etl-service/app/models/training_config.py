"""
TrainingConfig - Single source of truth for all ML training parameters.

Flows through the entire pipeline: admin UI -> API -> TrainingJob -> FeaturePipeline -> model.
Stored in ml_models.hyperparameters JSONB column for reproducibility.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field, model_validator


# Default label thresholds for 5-class classification
DEFAULT_THRESHOLDS_5CLASS = {
    "strong_buy": 0.05,
    "buy": 0.02,
    "sell": -0.02,
    "strong_sell": -0.05,
}

# Default label thresholds for 3-class classification
DEFAULT_THRESHOLDS_3CLASS = {
    "buy": 0.02,
    "sell": -0.02,
}


class FeatureToggles(BaseModel):
    """Controls which optional feature groups are enabled during training."""
    enable_sentiment: bool = False
    enable_sector: bool = True
    enable_market_regime: bool = True


class TrainingConfig(BaseModel):
    """
    Complete training configuration that flows through the ML pipeline.

    All parameters needed to reproduce a training run are captured here.
    Stored in ml_models.hyperparameters after training completes.
    """
    lookback_days: int = Field(default=365, ge=30, le=730)
    model_type: str = Field(default="xgboost", pattern="^(xgboost|lightgbm)$")
    prediction_window_days: int = Field(default=7, description="Forward return window for labeling")
    num_classes: int = Field(default=5, description="3 (buy/hold/sell) or 5 (strong_buy/buy/hold/sell/strong_sell)")
    thresholds: Dict[str, float] = Field(default_factory=lambda: DEFAULT_THRESHOLDS_5CLASS.copy())
    features: FeatureToggles = Field(default_factory=FeatureToggles)
    hyperparams: Dict[str, object] = Field(default_factory=lambda: {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
    })
    triggered_by: str = Field(default="api")
    use_outcomes: bool = Field(default=False, description="Use signal_outcomes for training labels")
    outcome_weight: float = Field(default=2.0, ge=0.1, le=10.0, description="Weight multiplier for outcome-labeled data vs yfinance-labeled data")

    @model_validator(mode="after")
    def validate_config(self):
        if self.prediction_window_days not in (7, 14, 30):
            raise ValueError("prediction_window_days must be 7, 14, or 30")
        if self.num_classes not in (3, 5):
            raise ValueError("num_classes must be 3 or 5")
        if self.num_classes == 3:
            self.thresholds = {
                k: v for k, v in self.thresholds.items()
                if k in ("buy", "sell")
            }
            if "buy" not in self.thresholds:
                self.thresholds["buy"] = DEFAULT_THRESHOLDS_3CLASS["buy"]
            if "sell" not in self.thresholds:
                self.thresholds["sell"] = DEFAULT_THRESHOLDS_3CLASS["sell"]
        return self

    def get_feature_names(self) -> list[str]:
        """Return the ordered list of feature names for this config."""
        names = [
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
        if self.features.enable_sector:
            names.extend(["committee_relevance", "sector_performance"])
        if self.features.enable_market_regime:
            names.extend(["vix_level", "market_return_20d", "market_breadth"])
        if self.features.enable_sentiment:
            names.append("sentiment_score")
        return names

    def to_hyperparameters_dict(self) -> dict:
        """Serialize to dict for storage in ml_models.hyperparameters JSONB."""
        return {
            "lookback_days": self.lookback_days,
            "model_type": self.model_type,
            "prediction_window_days": self.prediction_window_days,
            "num_classes": self.num_classes,
            "thresholds": self.thresholds,
            "features": self.features.model_dump(),
            "hyperparams": self.hyperparams,
            "triggered_by": self.triggered_by,
            "use_outcomes": self.use_outcomes,
            "outcome_weight": self.outcome_weight,
            "feature_names": self.get_feature_names(),
        }

    @classmethod
    def from_hyperparameters_dict(cls, data: dict) -> "TrainingConfig":
        """Reconstruct from stored hyperparameters JSONB."""
        features_data = data.get("features", {})
        return cls(
            lookback_days=data.get("lookback_days", 365),
            model_type=data.get("model_type", "xgboost"),
            prediction_window_days=data.get("prediction_window_days", 7),
            num_classes=data.get("num_classes", 5),
            thresholds=data.get("thresholds", DEFAULT_THRESHOLDS_5CLASS.copy()),
            features=FeatureToggles(**features_data) if features_data else FeatureToggles(),
            hyperparams=data.get("hyperparams", {}),
            triggered_by=data.get("triggered_by", "api"),
            use_outcomes=data.get("use_outcomes", False),
            outcome_weight=data.get("outcome_weight", 2.0),
        )
