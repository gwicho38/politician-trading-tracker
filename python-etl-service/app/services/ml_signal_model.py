"""
ML Signal Model Service

XGBoost-based model for congress trading signal prediction.
Combines features from disclosure data, market context, and sentiment analysis.
"""

import os
import json
import pickle
import hashlib
import logging
import io
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from supabase import create_client, Client
from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
MODEL_STORAGE_PATH = os.environ.get("MODEL_STORAGE_PATH", "/tmp/models")
MODEL_STORAGE_BUCKET = "ml-models"  # Supabase Storage bucket for persistent model storage

# Feature configuration
FEATURE_NAMES = [
    'politician_count',      # Number of unique politicians trading the ticker
    'buy_sell_ratio',        # Buys / Sells ratio
    'recent_activity_30d',   # Trades in last 30 days
    'bipartisan',            # Both D and R trading (0 or 1)
    'net_volume',            # Buy volume - sell volume
    'volume_magnitude',      # Log of total volume
    'party_alignment',       # Majority party agreement score
    'committee_relevance',   # Committee-sector alignment score
    'disclosure_delay',      # Days between trade and disclosure
    'sentiment_score',       # LLM-derived news sentiment (-1 to 1)
    'market_momentum',       # 20-day price momentum
    'sector_performance',    # Sector ETF performance
]

# Signal labels
SIGNAL_LABELS = {
    -2: 'strong_sell',
    -1: 'sell',
    0: 'hold',
    1: 'buy',
    2: 'strong_buy',
}


def ensure_storage_bucket_exists(supabase: Client) -> bool:
    """Ensure the ML models storage bucket exists."""
    try:
        # Try to list files in bucket (will fail if bucket doesn't exist)
        supabase.storage.from_(MODEL_STORAGE_BUCKET).list()
        return True
    except Exception:
        try:
            # Create the bucket if it doesn't exist
            supabase.storage.create_bucket(MODEL_STORAGE_BUCKET, options={
                "public": False,
                "file_size_limit": 100 * 1024 * 1024,  # 100MB max
            })
            logger.info(f"Created storage bucket: {MODEL_STORAGE_BUCKET}")
            return True
        except Exception as e:
            logger.error(f"Failed to create storage bucket: {e}")
            return False


def upload_model_to_storage(model_id: str, local_path: str) -> Optional[str]:
    """
    Upload a model artifact to Supabase Storage.

    Args:
        model_id: The model's unique ID
        local_path: Path to the local .pkl file

    Returns:
        Storage path (e.g., "models/uuid.pkl") or None on failure
    """
    try:
        supabase = get_supabase()
        ensure_storage_bucket_exists(supabase)

        storage_path = f"models/{model_id}.pkl"

        with open(local_path, 'rb') as f:
            file_data = f.read()

        # Upload to storage (upsert to overwrite if exists)
        supabase.storage.from_(MODEL_STORAGE_BUCKET).upload(
            storage_path,
            file_data,
            file_options={"content-type": "application/octet-stream", "upsert": "true"}
        )

        logger.info(f"Uploaded model to storage: {storage_path}")
        return storage_path

    except Exception as e:
        logger.error(f"Failed to upload model to storage: {e}")
        return None


def download_model_from_storage(model_id: str, local_path: str) -> bool:
    """
    Download a model artifact from Supabase Storage.

    Args:
        model_id: The model's unique ID
        local_path: Path to save the downloaded .pkl file

    Returns:
        True if download succeeded, False otherwise
    """
    try:
        supabase = get_supabase()
        storage_path = f"models/{model_id}.pkl"

        # Download from storage
        data = supabase.storage.from_(MODEL_STORAGE_BUCKET).download(storage_path)

        # Save to local path
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(data)

        logger.info(f"Downloaded model from storage: {storage_path} -> {local_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to download model from storage: {e}")
        return False


def compute_feature_hash(features: Dict[str, Any]) -> str:
    """Compute hash of feature vector for caching."""
    # Sort keys for consistent hashing
    sorted_features = json.dumps(features, sort_keys=True)
    return hashlib.md5(sorted_features.encode()).hexdigest()[:16]


class CongressSignalModel:
    """
    XGBoost model for congress trading signal prediction.

    Predicts signal type (strong_buy, buy, hold, sell, strong_sell)
    based on political trading features and market context.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the model.

        Args:
            model_path: Path to load a pre-trained model from.
                        If None, starts with an untrained model.
        """
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = FEATURE_NAMES.copy()
        self.model_version = "1.0.0"
        self.model_type = "xgboost"
        self.is_trained = False
        self.training_metrics = {}

        if model_path:
            self.load(model_path)

    def prepare_features(self, ticker_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract feature vector from ticker aggregation data.

        Args:
            ticker_data: Dictionary with ticker aggregation fields

        Returns:
            Feature vector as numpy array
        """
        features = []

        # Extract each feature with defaults
        features.append(ticker_data.get('politician_count', 0))
        features.append(ticker_data.get('buy_sell_ratio', 1.0))
        features.append(ticker_data.get('recent_activity_30d', 0))
        features.append(1 if ticker_data.get('bipartisan', False) else 0)
        features.append(ticker_data.get('net_volume', 0))

        # Volume magnitude (log scale)
        total_volume = abs(ticker_data.get('net_volume', 0))
        features.append(np.log1p(total_volume) if total_volume > 0 else 0)

        # Political features (defaults if not available)
        features.append(ticker_data.get('party_alignment', 0.5))
        features.append(ticker_data.get('committee_relevance', 0.5))
        features.append(ticker_data.get('disclosure_delay', 30))

        # Sentiment and market features
        features.append(ticker_data.get('sentiment_score', 0.0))
        features.append(ticker_data.get('market_momentum', 0.0))
        features.append(ticker_data.get('sector_performance', 0.0))

        return np.array(features, dtype=np.float32)

    def train(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        validation_split: float = 0.2,
        hyperparams: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Train the XGBoost model on labeled data.

        Args:
            X: Feature dataframe with columns matching feature_names
            y: Labels array (-2 to 2 for signal types)
            validation_split: Fraction of data for validation
            hyperparams: Optional hyperparameters override

        Returns:
            Dictionary with training metrics
        """
        try:
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, f1_score, classification_report
        except ImportError:
            raise ImportError("XGBoost not installed. Run: pip install xgboost")

        logger.info(f"Training model on {len(X)} samples...")

        # Default hyperparameters
        default_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'objective': 'multi:softmax',
            'num_class': 5,
            'random_state': 42,
            'n_jobs': -1,
        }

        if hyperparams:
            default_params.update(hyperparams)

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Shift labels from [-2, 2] to [0, 4] for XGBoost
        y_train_shifted = y_train + 2
        y_val_shifted = y_val + 2

        # Train model
        self.model = xgb.XGBClassifier(**default_params)
        self.model.fit(
            X_train_scaled, y_train_shifted,
            eval_set=[(X_val_scaled, y_val_shifted)],
            verbose=False,
        )

        # Evaluate
        y_pred_shifted = self.model.predict(X_val_scaled)
        y_pred = y_pred_shifted - 2  # Shift back

        accuracy = accuracy_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred, average='weighted')

        # Get feature importance
        importance = dict(zip(self.feature_names, self.model.feature_importances_.tolist()))

        self.training_metrics = {
            'accuracy': float(accuracy),
            'f1_weighted': float(f1),
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'classification_report': classification_report(y_val, y_pred, output_dict=True),
        }

        self.is_trained = True
        logger.info(f"Model trained - Accuracy: {accuracy:.3f}, F1: {f1:.3f}")

        return {
            'metrics': self.training_metrics,
            'feature_importance': importance,
            'hyperparameters': default_params,
        }

    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Predict signal type and confidence for a feature vector.

        Args:
            features: Feature vector (1D array)

        Returns:
            Tuple of (prediction: int, confidence: float)
            prediction is in range [-2, 2]
            confidence is probability of predicted class
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model is not trained")

        # Ensure 2D array
        if features.ndim == 1:
            features = features.reshape(1, -1)

        # Scale features
        features_scaled = self.scaler.transform(features)

        # Get prediction and probabilities
        pred_shifted = self.model.predict(features_scaled)[0]
        probas = self.model.predict_proba(features_scaled)[0]

        prediction = int(pred_shifted - 2)  # Shift from [0,4] to [-2,2]
        confidence = float(probas[int(pred_shifted)])

        return prediction, confidence

    def predict_batch(self, features_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch prediction for multiple tickers.

        Args:
            features_list: List of feature dictionaries

        Returns:
            List of prediction results
        """
        results = []

        for features_dict in features_list:
            try:
                feature_vector = self.prepare_features(features_dict)
                prediction, confidence = self.predict(feature_vector)

                results.append({
                    'ticker': features_dict.get('ticker', 'UNKNOWN'),
                    'prediction': prediction,
                    'signal_type': SIGNAL_LABELS.get(prediction, 'hold'),
                    'confidence': confidence,
                    'feature_hash': compute_feature_hash(features_dict),
                })
            except Exception as e:
                logger.error(f"Prediction error for {features_dict.get('ticker')}: {e}")
                results.append({
                    'ticker': features_dict.get('ticker', 'UNKNOWN'),
                    'error': str(e),
                })

        return results

    def save(self, path: str):
        """Save model to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_version': self.model_version,
            'model_type': self.model_type,
            'training_metrics': self.training_metrics,
            'is_trained': self.is_trained,
            'saved_at': datetime.utcnow().isoformat(),
        }

        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """Load model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.model_version = model_data.get('model_version', '1.0.0')
        self.model_type = model_data.get('model_type', 'xgboost')
        self.training_metrics = model_data.get('training_metrics', {})
        self.is_trained = model_data.get('is_trained', True)

        logger.info(f"Model loaded from {path}")

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        if not self.is_trained or self.model is None:
            return {}

        return dict(zip(self.feature_names, self.model.feature_importances_.tolist()))


# Global model instance (loaded on startup)
_active_model: Optional[CongressSignalModel] = None


def get_active_model() -> Optional[CongressSignalModel]:
    """Get the currently active model."""
    global _active_model
    return _active_model


def load_active_model(model_id: Optional[str] = None) -> Optional[CongressSignalModel]:
    """
    Load the active model from database or storage.

    First checks local cache, then downloads from Supabase Storage if needed.

    Args:
        model_id: Specific model ID to load. If None, loads the latest active model.

    Returns:
        Loaded model or None if no model available.
    """
    global _active_model

    try:
        supabase = get_supabase()

        # Query for active model
        if model_id:
            result = supabase.table('ml_models').select('*').eq('id', model_id).single().execute()
        else:
            result = supabase.table('ml_models').select('*').eq('status', 'active').order(
                'training_completed_at', desc=True
            ).limit(1).execute()

        if not result.data:
            logger.warning("No active model found in database")
            return None

        model_record = result.data[0] if isinstance(result.data, list) else result.data
        db_model_id = model_record.get('id')
        model_path = model_record.get('model_artifact_path')

        # Check if local file exists
        if model_path and Path(model_path).exists():
            logger.info(f"Loading model from local cache: {model_path}")
        else:
            # Try to download from Supabase Storage
            local_path = f"{MODEL_STORAGE_PATH}/{db_model_id}.pkl"
            logger.info(f"Local model not found, downloading from storage...")

            if download_model_from_storage(db_model_id, local_path):
                model_path = local_path
                logger.info(f"Downloaded model from storage: {model_path}")
            else:
                logger.warning(f"Model artifact not found in storage: {db_model_id}")
                return None

        _active_model = CongressSignalModel(model_path)
        logger.info(f"Loaded active model: {model_record.get('model_name')} v{model_record.get('model_version')}")

        return _active_model

    except Exception as e:
        logger.error(f"Failed to load active model: {e}")
        return None


def cache_prediction(
    model_id: str,
    ticker: str,
    feature_hash: str,
    prediction: int,
    confidence: float,
    ttl_hours: int = 1,
) -> bool:
    """Cache a prediction result."""
    try:
        supabase = get_supabase()
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

        supabase.table('ml_predictions_cache').upsert({
            'model_id': model_id,
            'ticker': ticker,
            'feature_hash': feature_hash,
            'prediction': prediction,
            'confidence': confidence,
            'expires_at': expires_at.isoformat(),
        }).execute()

        return True
    except Exception as e:
        logger.error(f"Failed to cache prediction: {e}")
        return False


def get_cached_prediction(ticker: str, feature_hash: str) -> Optional[Dict[str, Any]]:
    """Get cached prediction if available and not expired."""
    try:
        supabase = get_supabase()
        now = datetime.utcnow().isoformat()

        result = supabase.table('ml_predictions_cache').select(
            'prediction, confidence, model_id'
        ).eq('ticker', ticker).eq('feature_hash', feature_hash).gt(
            'expires_at', now
        ).single().execute()

        if result.data:
            return {
                'prediction': result.data['prediction'],
                'confidence': result.data['confidence'],
                'model_id': result.data['model_id'],
                'cached': True,
            }

        return None

    except Exception as e:
        logger.debug(f"Cache miss for {ticker}: {e}")
        return None
