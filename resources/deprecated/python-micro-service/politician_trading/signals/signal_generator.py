"""
Signal generation engine for politician trading tracker.

This module generates buy/sell/hold trading signals based on politician
trading activity. It combines ML models with rule-based heuristics to
predict which stocks may perform well based on insider knowledge patterns.

Key Classes:
    SignalGenerator: Main signal generation engine
    FeatureEngineer: Extracts features from trading data (in features.py)

Signal Generation Process:
    1. Aggregate recent politician trades by ticker
    2. Extract features (politician count, buy/sell ratio, volume, etc.)
    3. Fetch market data for context (price, volume, sector)
    4. Run ML model to generate confidence scores
    5. Apply rules-based filters (min politicians, min volume)
    6. Output TradingSignal objects with type, confidence, and targets

Signal Types:
    - STRONG_BUY: High confidence buy signal
    - BUY: Moderate confidence buy signal
    - HOLD: No clear direction
    - SELL: Moderate confidence sell signal
    - STRONG_SELL: High confidence sell signal

Example:
    from politician_trading.signals import SignalGenerator

    generator = SignalGenerator()
    signals = await generator.generate_signals(
        lookback_days=30,
        min_confidence=0.6
    )

    for signal in signals:
        print(f"{signal.ticker}: {signal.signal_type} ({signal.confidence:.2f})")

Note:
    - Signals are informational only and not financial advice
    - Model accuracy depends on training data quality
    - Market data fetched from Yahoo Finance (yfinance)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
from uuid import uuid4
import hashlib
import logging
import pickle

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import yfinance as yf

from politician_trading.signals.features import FeatureEngineer
from models import (
    TradingSignal,
    SignalType,
    SignalStrength,
)

logger = logging.getLogger(__name__)

# Feature keys used for ML training (consistent ordering)
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


class SignalGenerator:
    """
    Generates buy/sell/hold signals based on politician trading activity.

    This class uses ML models and heuristics to analyze politician trading
    disclosures and generate actionable trading signals.
    """

    def __init__(
        self,
        model_version: str = "v1.0",
        use_ml: bool = True,
        confidence_threshold: float = 0.6,
    ):
        """
        Initialize signal generator.

        Args:
            model_version: Version identifier for the model
            use_ml: Whether to use ML models (if False, uses heuristics only)
            confidence_threshold: Minimum confidence score to generate signals
        """
        self.model_version = model_version
        self.use_ml = use_ml
        self.confidence_threshold = confidence_threshold

        self.feature_engineer = FeatureEngineer()
        self.scaler = StandardScaler()
        self.classifier = None

        if use_ml:
            # Initialize ML model
            self.classifier = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
            )

    def generate_signals(
        self,
        disclosures_by_ticker: Dict[str, List[Dict[str, Any]]],
        fetch_market_data: bool = True,
    ) -> List[TradingSignal]:
        """
        Generate trading signals for multiple tickers.

        Args:
            disclosures_by_ticker: Dictionary mapping tickers to their disclosures
            fetch_market_data: Whether to fetch real-time market data

        Returns:
            List of TradingSignal objects
        """
        signals = []

        for ticker, disclosures in disclosures_by_ticker.items():
            try:
                signal = self.generate_signal(ticker, disclosures, fetch_market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal for {ticker}: {e}")
                continue

        return signals

    def generate_signal(
        self,
        ticker: str,
        disclosures: List[Dict[str, Any]],
        fetch_market_data: bool = True,
    ) -> Optional[TradingSignal]:
        """
        Generate a trading signal for a single ticker.

        Args:
            ticker: Stock ticker symbol
            disclosures: List of trading disclosures for this ticker
            fetch_market_data: Whether to fetch real-time market data

        Returns:
            TradingSignal object or None if no signal generated
        """
        if not disclosures:
            logger.debug(f"No disclosures for {ticker}, skipping signal generation")
            return None

        # Fetch market data if requested
        market_data = None
        if fetch_market_data:
            try:
                market_data = self._fetch_market_data(ticker)
            except Exception as e:
                logger.warning(f"Could not fetch market data for {ticker}: {e}")

        # Extract features
        features = self.feature_engineer.extract_features(ticker, disclosures, market_data)

        # Generate signal using heuristics
        signal_type, confidence, strength = self._generate_heuristic_signal(features, disclosures)

        # If using ML and model is trained, adjust with ML prediction
        if self.use_ml and self.classifier is not None:
            try:
                ml_signal, ml_confidence = self._generate_ml_signal(features)
                # Combine heuristic and ML signals (weighted average)
                signal_type, confidence = self._combine_signals(
                    signal_type, confidence, ml_signal, ml_confidence
                )
            except Exception as e:
                logger.warning(f"ML signal generation failed for {ticker}: {e}")

        # Only return signal if confidence meets threshold
        if confidence < self.confidence_threshold:
            logger.debug(f"Signal confidence {confidence} below threshold for {ticker}")
            return None

        # Calculate price targets
        target_price, stop_loss, take_profit = self._calculate_price_targets(
            ticker, signal_type, market_data
        )



        # Create signal object
        now_utc = datetime.now(timezone.utc)
        signal = TradingSignal(
            ticker=ticker,
            asset_name=disclosures[0].get("asset_name", ticker),
            signal_type=signal_type,
            signal_strength=strength,
            confidence_score=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            generated_at=now_utc,
            valid_until=now_utc + timedelta(days=7),  # Valid for 1 week
            model_version=self.model_version,
            politician_activity_count=features.get("unique_politicians", 0),
            total_transaction_volume=Decimal(str(features.get("net_volume", 0))),
            buy_sell_ratio=features.get("buy_sell_ratio", 0.0),
            features=features,
            disclosure_ids=[d.get("id") for d in disclosures if d.get("id")],
            is_active=True,
        )

        logger.info(
            f"Generated {signal_type.value} signal for {ticker} "
            f"with confidence {confidence:.2%}"
        )

        return signal

    def _generate_heuristic_signal(
        self, features: Dict[str, Any], disclosures: List[Dict[str, Any]]
    ) -> tuple[SignalType, float, SignalStrength]:
        """
        Generate signal using heuristic rules.

        Returns:
            Tuple of (signal_type, confidence, strength)
        """
        # Initialize scores
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

        # Rule 3: Unique politicians (more politicians = more confidence)
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

        # Rule 6: Volume (larger volume = more confidence)
        net_volume = features.get("net_volume", 0)
        if abs(net_volume) > 1000000:  # > $1M
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

    def _generate_ml_signal(self, features: Dict[str, Any]) -> tuple[SignalType, float]:
        """
        Generate signal using ML model.

        Returns:
            Tuple of (signal_type, confidence)
        """
        # Prepare features for ML model
        feature_vector = self._prepare_feature_vector(features)

        # Get prediction and confidence
        prediction = self.classifier.predict([feature_vector])[0]
        confidence = np.max(self.classifier.predict_proba([feature_vector]))

        # Map prediction to signal type
        if prediction == 2:  # Strong buy
            signal_type = SignalType.STRONG_BUY
        elif prediction == 1:  # Buy
            signal_type = SignalType.BUY
        elif prediction == -1:  # Sell
            signal_type = SignalType.SELL
        elif prediction == -2:  # Strong sell
            signal_type = SignalType.STRONG_SELL
        else:  # Hold
            signal_type = SignalType.HOLD

        return signal_type, confidence

    def _combine_signals(
        self,
        heuristic_signal: SignalType,
        heuristic_confidence: float,
        ml_signal: SignalType,
        ml_confidence: float,
    ) -> tuple[SignalType, float]:
        """
        Combine heuristic and ML signals.

        Returns:
            Tuple of (combined_signal_type, combined_confidence)
        """
        # Weight: 60% heuristic, 40% ML
        heuristic_weight = 0.6
        ml_weight = 0.4

        # If signals agree, boost confidence
        if heuristic_signal == ml_signal:
            combined_confidence = (
                heuristic_confidence * heuristic_weight + ml_confidence * ml_weight
            ) * 1.1
            return heuristic_signal, min(combined_confidence, 0.99)

        # If signals disagree, reduce confidence and use higher-confidence signal
        combined_confidence = (
            heuristic_confidence * heuristic_weight + ml_confidence * ml_weight
        ) * 0.8

        if heuristic_confidence > ml_confidence:
            return heuristic_signal, combined_confidence
        else:
            return ml_signal, combined_confidence

    def _prepare_feature_vector(self, features: Dict[str, Any]) -> List[float]:
        """Prepare feature vector for ML model."""
        vector = [features.get(key, 0) for key in FEATURE_KEYS]
        return vector

    def _fetch_market_data(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        """
        Fetch market data from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol
            period: Time period (e.g., "1mo", "3mo", "1y")

        Returns:
            DataFrame with OHLCV data
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            return data
        except Exception as e:
            logger.error(f"Error fetching market data for {ticker}: {e}")
            return pd.DataFrame()

    def _calculate_price_targets(
        self,
        ticker: str,
        signal_type: SignalType,
        market_data: Optional[pd.DataFrame],
    ) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        Calculate price targets for the signal.

        Returns:
            Tuple of (target_price, stop_loss, take_profit)
        """
        if market_data is None or market_data.empty:
            return None, None, None

        try:
            current_price = Decimal(str(market_data["Close"].iloc[-1]))

            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                # For buy signals
                target_price = current_price * Decimal("1.10")  # 10% upside target
                stop_loss = current_price * Decimal("0.95")  # 5% stop loss
                take_profit = current_price * Decimal("1.15")  # 15% take profit

                if signal_type == SignalType.STRONG_BUY:
                    # More aggressive targets for strong buy
                    target_price = current_price * Decimal("1.15")
                    take_profit = current_price * Decimal("1.20")

            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                # For sell signals (if shorting)
                target_price = current_price * Decimal("0.90")  # 10% downside target
                stop_loss = current_price * Decimal("1.05")  # 5% stop loss
                take_profit = current_price * Decimal("0.85")  # 15% take profit

                if signal_type == SignalType.STRONG_SELL:
                    target_price = current_price * Decimal("0.85")
                    take_profit = current_price * Decimal("0.80")
            else:
                return None, None, None

            return target_price, stop_loss, take_profit

        except Exception as e:
            logger.error(f"Error calculating price targets for {ticker}: {e}")
            return None, None, None

    def train_model(
        self,
        training_data: pd.DataFrame,
        labels: np.ndarray,
        supabase_client: Optional[Any] = None,
        save_to_db: bool = True,
    ) -> Optional[str]:
        """
        Train the ML model on historical data and optionally save weights to Supabase.

        Args:
            training_data: DataFrame with features
            labels: Array of labels (-2: strong sell, -1: sell, 0: hold, 1: buy, 2: strong buy)
            supabase_client: Optional Supabase client for saving model to database
            save_to_db: Whether to save model metadata and weights to Supabase

        Returns:
            Model ID if saved to database, None otherwise
        """
        if not self.use_ml:
            logger.warning("ML is disabled, cannot train model")
            return None

        logger.info(f"Training model on {len(training_data)} samples")

        X = training_data[FEATURE_KEYS].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train classifier
        self.classifier.fit(X_scaled, labels)

        logger.info("Model training completed")

        # Extract feature importance
        feature_importance = dict(zip(FEATURE_KEYS, self.classifier.feature_importances_.tolist()))

        # Calculate training metrics
        train_predictions = self.classifier.predict(X_scaled)
        train_accuracy = (train_predictions == labels).mean()
        train_proba = self.classifier.predict_proba(X_scaled)
        train_confidence = train_proba.max(axis=1).mean()

        metrics = {
            "train_accuracy": float(train_accuracy),
            "train_confidence_mean": float(train_confidence),
            "train_samples": len(training_data),
            "unique_labels": len(np.unique(labels)),
            "label_distribution": {int(k): int(v) for k, v in zip(*np.unique(labels, return_counts=True))},
        }

        logger.info(f"Training metrics: accuracy={train_accuracy:.4f}, confidence={train_confidence:.4f}")

        # Save to Supabase if client provided and save_to_db is True
        model_id = None
        if save_to_db and supabase_client:
            model_id = self._save_model_to_supabase(
                supabase_client,
                feature_importance,
                metrics,
                len(training_data),
            )

        return model_id

    def _save_model_to_supabase(
        self,
        supabase_client: Any,
        feature_importance: Dict[str, float],
        metrics: Dict[str, Any],
        training_samples: int,
    ) -> Optional[str]:
        """
        Save trained model metadata and weights to Supabase.

        Args:
            supabase_client: Supabase client instance
            feature_importance: Dictionary of feature importance scores
            metrics: Training metrics
            training_samples: Number of training samples

        Returns:
            Model ID if saved successfully, None otherwise
        """
        try:
            model_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()

            # Serialize model and scaler for storage
            model_blob = pickle.dumps({
                "classifier": self.classifier,
                "scaler": self.scaler,
                "feature_keys": FEATURE_KEYS,
            })

            # Compute hash of weights for integrity verification
            weights_hash = hashlib.sha256(model_blob).hexdigest()

            # Create model record
            model_data = {
                "id": model_id,
                "model_name": "politician-trading-signals",
                "model_version": self.model_version,
                "model_type": "gradient_boosting",
                "status": "active",
                "training_completed_at": now,
                "metrics": metrics,
                "feature_importance": feature_importance,
                "training_samples": training_samples,
                "hyperparameters": {
                    "n_estimators": self.classifier.n_estimators,
                    "learning_rate": self.classifier.learning_rate,
                    "max_depth": self.classifier.max_depth,
                },
            }

            # Deactivate previous active models
            try:
                supabase_client.table("ml_models").update({
                    "status": "archived",
                }).eq("model_name", "politician-trading-signals").eq("status", "active").execute()
                logger.info("Deactivated previous active models")
            except Exception as e:
                logger.warning(f"Could not deactivate previous models: {e}")

            # Insert new model record
            result = supabase_client.table("ml_models").insert(model_data).execute()
            if not result.data:
                logger.error("Failed to insert model record")
                return None

            logger.info(f"Created model record: {model_id}")

            # Create weights snapshot
            weights_snapshot_id = str(uuid4())
            weights_data = {
                "id": weights_snapshot_id,
                "model_id": model_id,
                "weights_hash": weights_hash,
                "weights_blob": model_blob.hex(),  # Store as hex string
                "scaler_state": {
                    "mean": self.scaler.mean_.tolist() if hasattr(self.scaler, 'mean_') else [],
                    "scale": self.scaler.scale_.tolist() if hasattr(self.scaler, 'scale_') else [],
                    "var": self.scaler.var_.tolist() if hasattr(self.scaler, 'var_') else [],
                },
                "validation_metrics": metrics,
                "sample_predictions": {
                    "feature_keys": FEATURE_KEYS,
                    "created_at": now,
                },
            }

            result = supabase_client.table("model_weights_snapshots").insert(weights_data).execute()
            if not result.data:
                logger.warning("Failed to insert weights snapshot")
            else:
                logger.info(f"Created weights snapshot: {weights_snapshot_id}")

            # Create or update feature definition
            feature_def_id = self._ensure_feature_definition(supabase_client)
            if feature_def_id:
                # Link model to feature definition by updating model record
                supabase_client.table("ml_models").update({
                    "feature_importance": {
                        **feature_importance,
                        "feature_definition_id": feature_def_id,
                    }
                }).eq("id", model_id).execute()

            return model_id

        except Exception as e:
            logger.error(f"Failed to save model to Supabase: {e}")
            return None

    def _ensure_feature_definition(self, supabase_client: Any) -> Optional[str]:
        """
        Ensure feature definition exists in database.

        Returns:
            Feature definition ID if exists or created, None otherwise
        """
        try:
            version = "v1.0"

            # Check if feature definition already exists
            result = supabase_client.table("feature_definitions").select("id").eq("version", version).execute()
            if result.data:
                return result.data[0]["id"]

            # Create new feature definition
            feature_def_id = str(uuid4())
            feature_def_data = {
                "id": feature_def_id,
                "version": version,
                "feature_names": FEATURE_KEYS,
                "feature_schema": {
                    "type": "object",
                    "properties": {key: {"type": "number"} for key in FEATURE_KEYS},
                },
                "computation_config": {
                    "lookback_periods": [7, 14, 30],
                    "normalization": "standard_scaler",
                },
                "default_weights": {key: 1.0 / len(FEATURE_KEYS) for key in FEATURE_KEYS},
                "is_active": True,
                "activated_at": datetime.now(timezone.utc).isoformat(),
            }

            result = supabase_client.table("feature_definitions").insert(feature_def_data).execute()
            if result.data:
                logger.info(f"Created feature definition: {feature_def_id}")
                return feature_def_id

            return None

        except Exception as e:
            logger.warning(f"Could not ensure feature definition: {e}")
            return None

    def load_model_from_supabase(self, supabase_client: Any, model_id: Optional[str] = None) -> bool:
        """
        Load a trained model from Supabase.

        Args:
            supabase_client: Supabase client instance
            model_id: Specific model ID to load, or None to load active model

        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Get model record
            if model_id:
                result = supabase_client.table("ml_models").select("*").eq("id", model_id).execute()
            else:
                result = supabase_client.table("ml_models").select("*").eq(
                    "model_name", "politician-trading-signals"
                ).eq("status", "active").order("training_completed_at", desc=True).limit(1).execute()

            if not result.data:
                logger.warning("No model found in database")
                return False

            model_record = result.data[0]
            model_id = model_record["id"]

            # Get weights snapshot
            weights_result = supabase_client.table("model_weights_snapshots").select("*").eq(
                "model_id", model_id
            ).order("created_at", desc=True).limit(1).execute()

            if not weights_result.data:
                logger.warning(f"No weights snapshot found for model {model_id}")
                return False

            weights_record = weights_result.data[0]

            # Deserialize model
            weights_blob = bytes.fromhex(weights_record["weights_blob"])
            model_data = pickle.loads(weights_blob)

            self.classifier = model_data["classifier"]
            self.scaler = model_data["scaler"]
            self.model_version = model_record["model_version"]

            logger.info(f"Loaded model {model_id} (version {self.model_version})")
            return True

        except Exception as e:
            logger.error(f"Failed to load model from Supabase: {e}")
            return False
