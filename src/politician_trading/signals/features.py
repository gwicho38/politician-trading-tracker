"""
Feature engineering for politician trading signals
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Feature engineering for politician trading signal generation.

    This class creates features from politician trading disclosures
    that can be used for ML-based signal generation.
    """

    def __init__(self):
        self.feature_names = []

    def extract_features(
        self, ticker: str, disclosures: List[Dict[str, Any]], market_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Extract features for a given ticker from politician disclosures.

        Args:
            ticker: Stock ticker symbol
            disclosures: List of trading disclosures for this ticker
            market_data: Optional market data (price, volume, etc.)

        Returns:
            Dictionary of features
        """
        if not disclosures:
            return self._get_default_features()

        features = {}

        # Time-based features
        features.update(self._extract_temporal_features(disclosures))

        # Transaction features
        features.update(self._extract_transaction_features(disclosures))

        # Politician features
        features.update(self._extract_politician_features(disclosures))

        # Party and role features
        features.update(self._extract_party_role_features(disclosures))

        # Volume and amount features
        features.update(self._extract_volume_features(disclosures))

        # Market data features (if available)
        if market_data is not None and not market_data.empty:
            features.update(self._extract_market_features(market_data))

        # Momentum and trend features
        features.update(self._extract_momentum_features(disclosures))

        return features

    def _get_default_features(self) -> Dict[str, Any]:
        """Return default feature values when no disclosures are available."""
        return {
            "total_transactions": 0,
            "unique_politicians": 0,
            "buy_count": 0,
            "sell_count": 0,
            "buy_sell_ratio": 0.0,
            "avg_days_since_transaction": 0,
            "recent_activity_7d": 0,
            "recent_activity_30d": 0,
            "recent_activity_90d": 0,
            "democrat_buy_count": 0,
            "democrat_sell_count": 0,
            "republican_buy_count": 0,
            "republican_sell_count": 0,
            "senator_buy_count": 0,
            "senator_sell_count": 0,
            "house_buy_count": 0,
            "house_sell_count": 0,
            "avg_transaction_amount": 0,
            "total_buy_volume": 0,
            "total_sell_volume": 0,
            "net_volume": 0,
        }

    def _extract_temporal_features(self, disclosures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract time-based features."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        features = {}

        # Get transaction dates
        dates = []
        for d in disclosures:
            if "transaction_date" in d:
                if isinstance(d["transaction_date"], str):
                    try:
                        dates.append(datetime.fromisoformat(d["transaction_date"].replace("Z", "+00:00")))
                    except:
                        continue
                elif isinstance(d["transaction_date"], datetime):
                    dates.append(d["transaction_date"])

        if dates:
            # Days since most recent transaction
            features["days_since_last_transaction"] = (now - max(dates)).days

            # Average days since transactions
            features["avg_days_since_transaction"] = np.mean([(now - d).days for d in dates])

            # Recent activity counts
            features["recent_activity_7d"] = sum(1 for d in dates if (now - d).days <= 7)
            features["recent_activity_30d"] = sum(1 for d in dates if (now - d).days <= 30)
            features["recent_activity_90d"] = sum(1 for d in dates if (now - d).days <= 90)

            # Acceleration of trading (recent vs older activity)
            recent_30d = sum(1 for d in dates if (now - d).days <= 30)
            older_30_60d = sum(1 for d in dates if 30 < (now - d).days <= 60)
            features["activity_acceleration"] = recent_30d - older_30_60d if older_30_60d > 0 else recent_30d
        else:
            features["days_since_last_transaction"] = 999
            features["avg_days_since_transaction"] = 999
            features["recent_activity_7d"] = 0
            features["recent_activity_30d"] = 0
            features["recent_activity_90d"] = 0
            features["activity_acceleration"] = 0

        return features

    def _extract_transaction_features(self, disclosures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract transaction type features."""
        features = {}

        # Count transaction types
        buy_count = 0
        sell_count = 0
        option_count = 0

        for d in disclosures:
            tx_type = d.get("transaction_type", "").lower()
            if "purchase" in tx_type or tx_type == "buy":
                buy_count += 1
            elif "sale" in tx_type or tx_type == "sell":
                sell_count += 1
            if "option" in tx_type:
                option_count += 1

        features["total_transactions"] = len(disclosures)
        features["buy_count"] = buy_count
        features["sell_count"] = sell_count
        features["option_count"] = option_count

        # Buy-sell ratio (with smoothing to avoid division by zero)
        features["buy_sell_ratio"] = buy_count / (sell_count + 1)

        # Net sentiment (buys - sells)
        features["net_sentiment"] = buy_count - sell_count

        return features

    def _extract_politician_features(self, disclosures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract politician-specific features."""
        features = {}

        # Unique politicians
        unique_pols = set()
        for d in disclosures:
            pol_id = d.get("politician_id") or d.get("politician_bioguide_id")
            if pol_id:
                unique_pols.add(pol_id)

        features["unique_politicians"] = len(unique_pols)

        # Concentration - what percentage of trades come from top politician
        if disclosures:
            politician_counts = {}
            for d in disclosures:
                pol_id = d.get("politician_id") or d.get("politician_bioguide_id")
                if pol_id:
                    politician_counts[pol_id] = politician_counts.get(pol_id, 0) + 1

            if politician_counts:
                max_count = max(politician_counts.values())
                features["top_politician_concentration"] = max_count / len(disclosures)
            else:
                features["top_politician_concentration"] = 0
        else:
            features["top_politician_concentration"] = 0

        return features

    def _extract_party_role_features(self, disclosures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract features related to political party and role."""
        features = {}

        # Party-based transaction counts
        democrat_buys = 0
        democrat_sells = 0
        republican_buys = 0
        republican_sells = 0

        # Role-based transaction counts
        senator_buys = 0
        senator_sells = 0
        house_buys = 0
        house_sells = 0

        for d in disclosures:
            party = d.get("party", "").lower()
            role = d.get("role", "").lower()
            tx_type = d.get("transaction_type", "").lower()

            is_buy = "purchase" in tx_type or tx_type == "buy"
            is_sell = "sale" in tx_type or tx_type == "sell"

            # Party counts
            if "democrat" in party or party == "d":
                if is_buy:
                    democrat_buys += 1
                elif is_sell:
                    democrat_sells += 1
            elif "republican" in party or party == "r":
                if is_buy:
                    republican_buys += 1
                elif is_sell:
                    republican_sells += 1

            # Role counts
            if "senator" in role:
                if is_buy:
                    senator_buys += 1
                elif is_sell:
                    senator_sells += 1
            elif "house" in role or "representative" in role:
                if is_buy:
                    house_buys += 1
                elif is_sell:
                    house_sells += 1

        features["democrat_buy_count"] = democrat_buys
        features["democrat_sell_count"] = democrat_sells
        features["republican_buy_count"] = republican_buys
        features["republican_sell_count"] = republican_sells
        features["senator_buy_count"] = senator_buys
        features["senator_sell_count"] = senator_sells
        features["house_buy_count"] = house_buys
        features["house_sell_count"] = house_sells

        # Party agreement scores
        features["democrat_bullish"] = democrat_buys - democrat_sells
        features["republican_bullish"] = republican_buys - republican_sells
        features["bipartisan_agreement"] = (
            1 if (democrat_buys > democrat_sells and republican_buys > republican_sells)
            or (democrat_sells > democrat_buys and republican_sells > republican_buys)
            else 0
        )

        return features

    def _extract_volume_features(self, disclosures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract features related to transaction volumes and amounts."""
        features = {}

        buy_amounts = []
        sell_amounts = []

        for d in disclosures:
            tx_type = d.get("transaction_type", "").lower()
            is_buy = "purchase" in tx_type or tx_type == "buy"
            is_sell = "sale" in tx_type or tx_type == "sell"

            # Try to get transaction amount
            amount = None
            if "amount_exact" in d and d["amount_exact"]:
                amount = float(d["amount_exact"])
            elif "amount_range_min" in d and "amount_range_max" in d:
                # Use midpoint of range
                min_amt = d.get("amount_range_min", 0)
                max_amt = d.get("amount_range_max", 0)
                if min_amt and max_amt:
                    amount = (float(min_amt) + float(max_amt)) / 2

            if amount:
                if is_buy:
                    buy_amounts.append(amount)
                elif is_sell:
                    sell_amounts.append(amount)

        # Amount statistics
        all_amounts = buy_amounts + sell_amounts
        if all_amounts:
            features["avg_transaction_amount"] = np.mean(all_amounts)
            features["median_transaction_amount"] = np.median(all_amounts)
            features["max_transaction_amount"] = np.max(all_amounts)
            features["std_transaction_amount"] = np.std(all_amounts)
        else:
            features["avg_transaction_amount"] = 0
            features["median_transaction_amount"] = 0
            features["max_transaction_amount"] = 0
            features["std_transaction_amount"] = 0

        # Buy vs sell volume
        features["total_buy_volume"] = sum(buy_amounts) if buy_amounts else 0
        features["total_sell_volume"] = sum(sell_amounts) if sell_amounts else 0
        features["net_volume"] = features["total_buy_volume"] - features["total_sell_volume"]

        # Volume ratio
        if features["total_sell_volume"] > 0:
            features["buy_sell_volume_ratio"] = features["total_buy_volume"] / features["total_sell_volume"]
        else:
            features["buy_sell_volume_ratio"] = features["total_buy_volume"]

        return features

    def _extract_market_features(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Extract features from market data."""
        features = {}

        if market_data.empty:
            return features

        # Price features
        if "close" in market_data.columns:
            prices = market_data["close"].values
            if len(prices) > 0:
                features["current_price"] = prices[-1]
                features["price_change_1d"] = (prices[-1] / prices[-2] - 1) if len(prices) > 1 else 0
                features["price_change_5d"] = (prices[-1] / prices[-5] - 1) if len(prices) > 5 else 0
                features["price_change_20d"] = (prices[-1] / prices[-20] - 1) if len(prices) > 20 else 0

                # Volatility
                returns = np.diff(prices) / prices[:-1]
                features["volatility_20d"] = np.std(returns[-20:]) if len(returns) >= 20 else 0

        # Volume features
        if "volume" in market_data.columns:
            volumes = market_data["volume"].values
            if len(volumes) > 0:
                features["avg_volume_20d"] = np.mean(volumes[-20:]) if len(volumes) >= 20 else 0
                features["volume_trend"] = (
                    (volumes[-1] / np.mean(volumes[-20:])) if len(volumes) >= 20 else 1
                )

        return features

    def _extract_momentum_features(self, disclosures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract momentum and trend features from disclosure patterns."""
        features = {}

        # Sort disclosures by date
        dated_disclosures = []
        for d in disclosures:
            if "transaction_date" in d:
                if isinstance(d["transaction_date"], str):
                    try:
                        date = datetime.fromisoformat(d["transaction_date"].replace("Z", "+00:00"))
                        dated_disclosures.append((date, d))
                    except:
                        continue
                elif isinstance(d["transaction_date"], datetime):
                    dated_disclosures.append((d["transaction_date"], d))

        dated_disclosures.sort(key=lambda x: x[0])

        if len(dated_disclosures) >= 3:
            # Calculate trend in buying activity (are more recent transactions buys or sells?)
            recent_half = dated_disclosures[len(dated_disclosures)//2:]
            older_half = dated_disclosures[:len(dated_disclosures)//2]

            recent_buys = sum(1 for _, d in recent_half if "purchase" in d.get("transaction_type", "").lower())
            older_buys = sum(1 for _, d in older_half if "purchase" in d.get("transaction_type", "").lower())

            features["buying_momentum"] = recent_buys - older_buys

            # Frequency trend (are transactions accelerating?)
            if len(dated_disclosures) > 1:
                recent_days = (dated_disclosures[-1][0] - dated_disclosures[len(dated_disclosures)//2][0]).days
                older_days = (dated_disclosures[len(dated_disclosures)//2][0] - dated_disclosures[0][0]).days

                if recent_days > 0 and older_days > 0:
                    recent_freq = len(recent_half) / max(recent_days, 1)
                    older_freq = len(older_half) / max(older_days, 1)
                    features["frequency_momentum"] = recent_freq - older_freq
                else:
                    features["frequency_momentum"] = 0
            else:
                features["frequency_momentum"] = 0
        else:
            features["buying_momentum"] = 0
            features["frequency_momentum"] = 0

        return features

    def create_feature_dataframe(
        self, ticker_features: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Create a pandas DataFrame from extracted features.

        Args:
            ticker_features: Dictionary mapping tickers to their features

        Returns:
            DataFrame with tickers as index and features as columns
        """
        if not ticker_features:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(ticker_features, orient="index")
        df.index.name = "ticker"
        return df
