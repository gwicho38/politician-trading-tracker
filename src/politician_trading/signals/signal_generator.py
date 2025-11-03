"""
Signal generation engine for politician trading tracker
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import yfinance as yf

from politician_trading.signals.features import FeatureEngineer
from models import (
    TradingSignal,
    SignalType,
    SignalStrength,
)

logger = logging.getLogger(__name__)


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
        # Define feature order (should match training data)
        feature_keys = [
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

        vector = [features.get(key, 0) for key in feature_keys]
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

    def train_model(self, training_data: pd.DataFrame, labels: np.ndarray):
        """
        Train the ML model on historical data.

        Args:
            training_data: DataFrame with features
            labels: Array of labels (-2: strong sell, -1: sell, 0: hold, 1: buy, 2: strong buy)
        """
        if not self.use_ml:
            logger.warning("ML is disabled, cannot train model")
            return

        logger.info(f"Training model on {len(training_data)} samples")

        # Prepare features
        feature_keys = [
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

        X = training_data[feature_keys].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train classifier
        self.classifier.fit(X_scaled, labels)

        logger.info("Model training completed")
