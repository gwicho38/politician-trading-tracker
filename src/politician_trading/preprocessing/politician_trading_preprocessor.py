"""Main preprocessor for politician trading data"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd

from .data_cleaners import CleaningStats, MissingValueHandler, OutlierDetector, TradingDataCleaner
from .feature_extractors import (
    FeatureExtractionStats,
    MarketFeatureExtractor,
    PoliticianFeatureExtractor,
    SentimentFeatureExtractor,
    TemporalFeatureExtractor,
)

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingConfig:
    """Configuration for preprocessing pipeline"""

    # Data cleaning
    enable_data_cleaning: bool = True
    enable_outlier_detection: bool = True
    enable_missing_value_handling: bool = True
    outlier_action: str = "flag"  # "flag", "remove", or "cap"

    # Feature extraction
    enable_politician_features: bool = True
    enable_market_features: bool = True
    enable_temporal_features: bool = True
    enable_sentiment_features: bool = True

    # Temporal settings
    lookback_periods: List[int] = None
    include_future_leakage: bool = False

    # Data splitting
    train_split_ratio: float = 0.7
    val_split_ratio: float = 0.15
    test_split_ratio: float = 0.15
    split_by_time: bool = True

    # Output settings
    save_preprocessing_artifacts: bool = True
    artifacts_dir: Optional[Path] = None

    def __post_init__(self):
        if self.lookback_periods is None:
            self.lookback_periods = [7, 30, 90, 365]

        if self.artifacts_dir is None:
            self.artifacts_dir = Path("./data/preprocessing_artifacts")

        # Validate split ratios
        total_ratio = self.train_split_ratio + self.val_split_ratio + self.test_split_ratio
        if abs(total_ratio - 1.0) > 0.001:
            raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")


@dataclass
class PreprocessingResults:
    """Results from preprocessing pipeline"""

    # Processed data
    train_data: pd.DataFrame
    val_data: pd.DataFrame
    test_data: pd.DataFrame

    # Feature information
    feature_names: List[str]
    categorical_features: List[str]
    numerical_features: List[str]
    target_columns: List[str]

    # Statistics
    cleaning_stats: CleaningStats
    original_shape: Tuple[int, int]
    final_shape: Tuple[int, int]
    feature_count: int

    # Artifacts paths
    scaler_path: Optional[Path] = None
    encoder_path: Optional[Path] = None
    feature_metadata_path: Optional[Path] = None


class PoliticianTradingPreprocessor:
    """Main preprocessor for politician trading data for ML models"""

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        self.config = config or PreprocessingConfig()

        # Initialize components
        self.data_cleaner = TradingDataCleaner()
        self.outlier_detector = OutlierDetector()
        self.missing_value_handler = MissingValueHandler()

        self.politician_extractor = PoliticianFeatureExtractor()
        self.market_extractor = MarketFeatureExtractor()
        self.temporal_extractor = TemporalFeatureExtractor(
            config={"lookback_periods": self.config.lookback_periods}
        )
        self.sentiment_extractor = SentimentFeatureExtractor()

        # Preprocessing artifacts
        self.scaler = None
        self.categorical_encoder = None
        self.feature_metadata = {}

        # Create artifacts directory
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def preprocess(
        self, raw_data: Union[List[Dict[str, Any]], pd.DataFrame]
    ) -> PreprocessingResults:
        """Main preprocessing pipeline"""
        logger.info("Starting politician trading data preprocessing")

        # Convert to DataFrame if needed
        if isinstance(raw_data, list):
            df = pd.DataFrame(raw_data)
        else:
            df = raw_data.copy()

        original_shape = df.shape
        logger.info(f"Input data shape: {original_shape}")

        # Step 1: Data Cleaning
        if self.config.enable_data_cleaning:
            df, cleaning_stats = self._clean_data(df)
            logger.info(f"After cleaning: {df.shape}")
        else:
            cleaning_stats = CleaningStats(
                total_records=len(df),
                cleaned_records=len(df),
                removed_records=0,
                cleaning_operations={},
                outliers_detected=0,
                missing_values_filled=0,
            )

        # Step 2: Feature Extraction
        df = self._extract_features(df)
        logger.info(f"After feature extraction: {df.shape}")

        # Step 3: Handle outliers
        if self.config.enable_outlier_detection:
            df = self._handle_outliers(df)
            logger.info(f"After outlier handling: {df.shape}")

        # Step 4: Handle missing values
        if self.config.enable_missing_value_handling:
            df = self._handle_missing_values(df)
            logger.info(f"After missing value handling: {df.shape}")

        # Step 5: Feature engineering and encoding
        df = self._engineer_features(df)
        logger.info(f"After feature engineering: {df.shape}")

        # Step 6: Create target variables
        df = self._create_target_variables(df)
        logger.info(f"After target creation: {df.shape}")

        # Step 7: Split data
        train_data, val_data, test_data = self._split_data(df)

        # Step 8: Scale features
        train_data, val_data, test_data = self._scale_features(train_data, val_data, test_data)

        # Step 9: Save artifacts
        if self.config.save_preprocessing_artifacts:
            self._save_artifacts()

        # Prepare results
        feature_names = [col for col in df.columns if not col.startswith("target_")]
        categorical_features = self._identify_categorical_features(df)
        numerical_features = self._identify_numerical_features(df)
        target_columns = [col for col in df.columns if col.startswith("target_")]

        results = PreprocessingResults(
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            feature_names=feature_names,
            categorical_features=categorical_features,
            numerical_features=numerical_features,
            target_columns=target_columns,
            cleaning_stats=cleaning_stats,
            original_shape=original_shape,
            final_shape=df.shape,
            feature_count=len(feature_names),
            scaler_path=self.config.artifacts_dir / "scaler.joblib",
            encoder_path=self.config.artifacts_dir / "encoder.joblib",
            feature_metadata_path=self.config.artifacts_dir / "feature_metadata.joblib",
        )

        logger.info(f"Preprocessing complete. Final shape: {df.shape}")
        logger.info(f"Features: {len(feature_names)}, Targets: {len(target_columns)}")

        return results

    def _clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, CleaningStats]:
        """Clean the raw data"""
        logger.info("Cleaning data")

        # Convert to list of records for cleaner
        records = df.to_dict("records")
        cleaned_records, cleaning_stats = self.data_cleaner.clean_trading_records(records)

        # Convert back to DataFrame
        cleaned_df = pd.DataFrame(cleaned_records)

        return cleaned_df, cleaning_stats

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract all features"""
        logger.info("Extracting features")

        if self.config.enable_politician_features:
            df = self.politician_extractor.extract_politician_features(df)
            logger.info("Politician features extracted")

        if self.config.enable_market_features:
            df = self.market_extractor.extract_market_features(df)
            logger.info("Market features extracted")

        if self.config.enable_temporal_features:
            df = self.temporal_extractor.extract_temporal_features(df)
            logger.info("Temporal features extracted")

        if self.config.enable_sentiment_features:
            df = self.sentiment_extractor.extract_sentiment_features(df)
            logger.info("Sentiment features extracted")

        return df

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle outliers in the data"""
        logger.info("Handling outliers")

        df_with_outliers, outlier_info = self.outlier_detector.detect_outliers(df)

        if self.config.outlier_action == "remove":
            df_clean = df_with_outliers[~df_with_outliers["is_outlier"]]
            logger.info(f"Removed {outlier_info['total_outliers']} outliers")
        elif self.config.outlier_action == "flag":
            df_clean = df_with_outliers
            logger.info(f"Flagged {outlier_info['total_outliers']} outliers")
        else:  # cap
            df_clean = self._cap_outliers(df_with_outliers)
            logger.info(f"Capped {outlier_info['total_outliers']} outliers")

        return df_clean

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values"""
        logger.info("Handling missing values")

        df_clean, missing_info = self.missing_value_handler.handle_missing_values(df)
        logger.info(f"Handled missing values: {missing_info['final_missing_counts']}")

        return df_clean

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer additional features"""
        logger.info("Engineering features")

        # Transaction amount buckets
        if "transaction_amount_cleaned" in df.columns:
            df["amount_bucket"] = pd.cut(
                df["transaction_amount_cleaned"],
                bins=[0, 1000, 15000, 50000, 500000, float("inf")],
                labels=["micro", "small", "medium", "large", "mega"],
            )

        # Politician activity level
        if "total_transactions" in df.columns:
            df["politician_activity_level"] = pd.cut(
                df["total_transactions"],
                bins=[0, 5, 20, 50, float("inf")],
                labels=["low", "medium", "high", "very_high"],
            )

        # Market timing features
        if "transaction_date_dt" in df.columns:
            # Days since start of data
            min_date = df["transaction_date_dt"].min()
            df["days_since_start"] = (df["transaction_date_dt"] - min_date).dt.days

            # Market cycle approximation (simplified)
            df["market_cycle_phase"] = (df["days_since_start"] % 1460) / 1460  # 4-year cycle

        # Interaction features
        if all(col in df.columns for col in ["buy_ratio", "total_transactions"]):
            df["buy_volume_interaction"] = df["buy_ratio"] * df["total_transactions"]

        if all(
            col in df.columns
            for col in ["transaction_amount_cleaned", "politician_trading_frequency"]
        ):
            df["amount_frequency_interaction"] = (
                df["transaction_amount_cleaned"] * df["politician_trading_frequency"]
            )

        return df

    def _create_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create target variables for ML models"""
        logger.info("Creating target variables")

        # Sort by politician and date for future stock performance calculation
        df = df.sort_values(["politician_name_cleaned", "transaction_date_dt"])

        # Target 1: Stock performance after politician trade (simplified)
        # This would typically require external market data
        # For now, create synthetic targets based on transaction patterns

        # Target: Whether the trade was profitable (binary classification)
        # Assumption: Larger transactions from frequent traders are more likely profitable
        if all(
            col in df.columns
            for col in ["transaction_amount_cleaned", "politician_trading_frequency"]
        ):
            # Probability based on amount and frequency
            amount_score = np.log1p(df["transaction_amount_cleaned"]) / 10
            frequency_score = np.log1p(df["politician_trading_frequency"]) / 5

            profit_probability = (amount_score + frequency_score) / 2
            profit_probability = np.clip(profit_probability, 0.1, 0.9)

            # Binary target with some randomness
            np.random.seed(42)  # For reproducibility
            df["target_profitable"] = np.random.binomial(1, profit_probability)

        # Target 2: Stock recommendation score (regression)
        # Based on politician patterns and market factors
        if "transaction_type_cleaned" in df.columns:
            base_score = 0.5  # Neutral

            # Adjust based on transaction type
            type_adjustment = (
                df["transaction_type_cleaned"]
                .map({"buy": 0.2, "sell": -0.2, "exchange": 0.0})
                .fillna(0)
            )

            # Adjust based on politician track record
            if "buy_ratio" in df.columns:
                track_record_adjustment = (df["buy_ratio"] - 0.5) * 0.3

            # Adjust based on timing
            if "is_end_of_quarter" in df.columns:
                timing_adjustment = df["is_end_of_quarter"].astype(int) * 0.1

            recommendation_score = (
                base_score + type_adjustment + track_record_adjustment + timing_adjustment
            )
            df["target_recommendation_score"] = np.clip(recommendation_score, 0, 1)

        # Target 3: Risk level (multi-class classification)
        if "transaction_volatility" in df.columns:
            risk_conditions = [
                (df["transaction_volatility"] <= 0.2),
                (df["transaction_volatility"] <= 0.5),
                (df["transaction_volatility"] <= 1.0),
                (df["transaction_volatility"] > 1.0),
            ]
            risk_choices = ["low", "medium", "high", "very_high"]
            df["target_risk_level"] = np.select(risk_conditions, risk_choices, default="medium")

        return df

    def _split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data into train/val/test sets"""
        logger.info("Splitting data")

        if self.config.split_by_time and "transaction_date_dt" in df.columns:
            # Time-based split
            df_sorted = df.sort_values("transaction_date_dt")

            train_size = int(len(df_sorted) * self.config.train_split_ratio)
            val_size = int(len(df_sorted) * self.config.val_split_ratio)

            train_data = df_sorted.iloc[:train_size]
            val_data = df_sorted.iloc[train_size : train_size + val_size]
            test_data = df_sorted.iloc[train_size + val_size :]

        else:
            # Random split
            df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

            train_size = int(len(df_shuffled) * self.config.train_split_ratio)
            val_size = int(len(df_shuffled) * self.config.val_split_ratio)

            train_data = df_shuffled.iloc[:train_size]
            val_data = df_shuffled.iloc[train_size : train_size + val_size]
            test_data = df_shuffled.iloc[train_size + val_size :]

        logger.info(
            f"Split sizes - Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}"
        )

        return train_data, val_data, test_data

    def _scale_features(
        self, train_data: pd.DataFrame, val_data: pd.DataFrame, test_data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Scale numerical features"""
        logger.info("Scaling features")

        from sklearn.preprocessing import LabelEncoder, StandardScaler

        numerical_features = self._identify_numerical_features(train_data)
        categorical_features = self._identify_categorical_features(train_data)

        # Fit scaler on training data
        self.scaler = StandardScaler()
        if numerical_features:
            train_scaled = train_data.copy()
            val_scaled = val_data.copy()
            test_scaled = test_data.copy()

            train_scaled[numerical_features] = self.scaler.fit_transform(
                train_data[numerical_features]
            )
            val_scaled[numerical_features] = self.scaler.transform(val_data[numerical_features])
            test_scaled[numerical_features] = self.scaler.transform(test_data[numerical_features])
        else:
            train_scaled, val_scaled, test_scaled = train_data, val_data, test_data

        # Encode categorical features
        self.categorical_encoder = {}
        if categorical_features:
            for feature in categorical_features:
                encoder = LabelEncoder()
                # Fit on combined data to handle unseen categories
                all_values = pd.concat(
                    [train_scaled[feature], val_scaled[feature], test_scaled[feature]]
                ).astype(str)

                encoder.fit(all_values)
                self.categorical_encoder[feature] = encoder

                train_scaled[feature] = encoder.transform(train_scaled[feature].astype(str))
                val_scaled[feature] = encoder.transform(val_scaled[feature].astype(str))
                test_scaled[feature] = encoder.transform(test_scaled[feature].astype(str))

        return train_scaled, val_scaled, test_scaled

    def _identify_numerical_features(self, df: pd.DataFrame) -> List[str]:
        """Identify numerical features"""
        numerical_features = []
        for col in df.columns:
            if (
                df[col].dtype in ["int64", "float64"]
                and not col.startswith("target_")
                and not col.endswith("_cleaned")
                and col not in ["is_outlier"]
            ):
                numerical_features.append(col)
        return numerical_features

    def _identify_categorical_features(self, df: pd.DataFrame) -> List[str]:
        """Identify categorical features"""
        categorical_features = []
        for col in df.columns:
            if (
                df[col].dtype == "object"
                or df[col].dtype.name == "category"
                and not col.startswith("target_")
            ):
                categorical_features.append(col)
        return categorical_features

    def _cap_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cap outliers to percentile values"""
        df_capped = df.copy()
        numerical_cols = self._identify_numerical_features(df)

        for col in numerical_cols:
            if col in df_capped.columns:
                q1 = df_capped[col].quantile(0.01)
                q99 = df_capped[col].quantile(0.99)
                df_capped[col] = np.clip(df_capped[col], q1, q99)

        return df_capped

    def _save_artifacts(self):
        """Save preprocessing artifacts"""
        logger.info("Saving preprocessing artifacts")

        if self.scaler:
            joblib.dump(self.scaler, self.config.artifacts_dir / "scaler.joblib")

        if self.categorical_encoder:
            joblib.dump(self.categorical_encoder, self.config.artifacts_dir / "encoder.joblib")

        # Save feature metadata
        self.feature_metadata = {
            "config": asdict(self.config),
            "preprocessing_timestamp": datetime.now().isoformat(),
        }
        joblib.dump(self.feature_metadata, self.config.artifacts_dir / "feature_metadata.joblib")

    def load_artifacts(self, artifacts_dir: Path):
        """Load preprocessing artifacts"""
        logger.info(f"Loading preprocessing artifacts from {artifacts_dir}")

        scaler_path = artifacts_dir / "scaler.joblib"
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)

        encoder_path = artifacts_dir / "encoder.joblib"
        if encoder_path.exists():
            self.categorical_encoder = joblib.load(encoder_path)

        metadata_path = artifacts_dir / "feature_metadata.joblib"
        if metadata_path.exists():
            self.feature_metadata = joblib.load(metadata_path)

    def transform_new_data(
        self, new_data: Union[List[Dict[str, Any]], pd.DataFrame]
    ) -> pd.DataFrame:
        """Transform new data using fitted preprocessors"""
        logger.info("Transforming new data with fitted preprocessors")

        if self.scaler is None and self.categorical_encoder is None:
            raise ValueError("No preprocessing artifacts loaded. Call load_artifacts() first.")

        # Convert to DataFrame if needed
        if isinstance(new_data, list):
            df = pd.DataFrame(new_data)
        else:
            df = new_data.copy()

        # Apply same preprocessing steps (without fitting)
        if self.config.enable_data_cleaning:
            records = df.to_dict("records")
            cleaned_records, _ = self.data_cleaner.clean_trading_records(records)
            df = pd.DataFrame(cleaned_records)

        # Extract features
        df = self._extract_features(df)

        # Engineer features
        df = self._engineer_features(df)

        # Apply scaling and encoding
        numerical_features = self._identify_numerical_features(df)
        categorical_features = self._identify_categorical_features(df)

        if self.scaler and numerical_features:
            df[numerical_features] = self.scaler.transform(df[numerical_features])

        if self.categorical_encoder and categorical_features:
            for feature in categorical_features:
                if feature in self.categorical_encoder:
                    df[feature] = self.categorical_encoder[feature].transform(
                        df[feature].astype(str)
                    )

        return df
