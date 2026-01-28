"""
Tests for ML Signal Model Service.

Tests cover:
- Storage functions (ensure_storage_bucket_exists, upload/download)
- compute_feature_hash() function
- CongressSignalModel class
- Model management functions (get_active_model, load_active_model)
- Prediction caching functions
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta

from app.services.ml_signal_model import (
    ensure_storage_bucket_exists,
    upload_model_to_storage,
    download_model_from_storage,
    compute_feature_hash,
    CongressSignalModel,
    get_active_model,
    load_active_model,
    cache_prediction,
    get_cached_prediction,
    FEATURE_NAMES,
    SIGNAL_LABELS,
    MODEL_STORAGE_BUCKET,
    _active_model,
)


class TestStorageBucketExists:
    """Tests for ensure_storage_bucket_exists function."""

    def test_bucket_exists(self):
        """Test when bucket already exists."""
        mock_supabase = MagicMock()
        mock_supabase.storage.from_.return_value.list.return_value = []

        result = ensure_storage_bucket_exists(mock_supabase)

        assert result is True
        mock_supabase.storage.from_.assert_called_with(MODEL_STORAGE_BUCKET)

    def test_bucket_does_not_exist_creates_it(self):
        """Test bucket creation when it doesn't exist."""
        mock_supabase = MagicMock()
        mock_supabase.storage.from_.return_value.list.side_effect = Exception("Not found")
        mock_supabase.storage.create_bucket.return_value = None

        result = ensure_storage_bucket_exists(mock_supabase)

        assert result is True
        mock_supabase.storage.create_bucket.assert_called_once()

    def test_bucket_creation_fails(self):
        """Test when bucket creation fails."""
        mock_supabase = MagicMock()
        mock_supabase.storage.from_.return_value.list.side_effect = Exception("Not found")
        mock_supabase.storage.create_bucket.side_effect = Exception("Permission denied")

        result = ensure_storage_bucket_exists(mock_supabase)

        assert result is False


class TestUploadModelToStorage:
    """Tests for upload_model_to_storage function."""

    def test_upload_success(self):
        """Test successful model upload."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            with patch("app.services.ml_signal_model.ensure_storage_bucket_exists") as mock_ensure:
                mock_supabase = MagicMock()
                mock_get_supabase.return_value = mock_supabase
                mock_ensure.return_value = True

                # Create a temp file to upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
                    f.write(b"model data")
                    temp_path = f.name

                try:
                    result = upload_model_to_storage("test-model-id", temp_path)

                    assert result == "models/test-model-id.pkl"
                    mock_supabase.storage.from_.assert_called_with(MODEL_STORAGE_BUCKET)
                finally:
                    os.unlink(temp_path)

    def test_upload_failure(self):
        """Test upload failure returns None."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_get_supabase.side_effect = Exception("Connection failed")

            result = upload_model_to_storage("test-id", "/nonexistent/path.pkl")

            assert result is None


class TestDownloadModelFromStorage:
    """Tests for download_model_from_storage function."""

    def test_download_success(self):
        """Test successful model download."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.storage.from_.return_value.download.return_value = b"model data"

            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "model.pkl")

                result = download_model_from_storage("test-model-id", local_path)

                assert result is True
                assert Path(local_path).exists()
                with open(local_path, 'rb') as f:
                    assert f.read() == b"model data"

    def test_download_failure(self):
        """Test download failure returns False."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.storage.from_.return_value.download.side_effect = Exception("Not found")

            result = download_model_from_storage("nonexistent", "/tmp/test.pkl")

            assert result is False


class TestComputeFeatureHash:
    """Tests for compute_feature_hash function."""

    def test_hash_consistency(self):
        """Test same features produce same hash."""
        features = {'a': 1, 'b': 2, 'c': 3}

        hash1 = compute_feature_hash(features)
        hash2 = compute_feature_hash(features)

        assert hash1 == hash2

    def test_hash_order_independence(self):
        """Test hash is independent of key order."""
        features1 = {'a': 1, 'b': 2, 'c': 3}
        features2 = {'c': 3, 'a': 1, 'b': 2}

        hash1 = compute_feature_hash(features1)
        hash2 = compute_feature_hash(features2)

        assert hash1 == hash2

    def test_different_features_different_hash(self):
        """Test different features produce different hash."""
        features1 = {'a': 1, 'b': 2}
        features2 = {'a': 1, 'b': 3}

        hash1 = compute_feature_hash(features1)
        hash2 = compute_feature_hash(features2)

        assert hash1 != hash2

    def test_hash_length(self):
        """Test hash is truncated to 16 characters."""
        features = {'ticker': 'AAPL', 'count': 100}

        result = compute_feature_hash(features)

        assert len(result) == 16


class TestCongressSignalModelInit:
    """Tests for CongressSignalModel initialization."""

    def test_init_without_model_path(self):
        """Test initialization without pre-trained model."""
        model = CongressSignalModel()

        assert model.model is None
        assert model.is_trained is False
        assert model.feature_names == FEATURE_NAMES
        assert model.model_version == "1.0.0"
        assert model.model_type == "xgboost"

    def test_init_with_model_path(self):
        """Test initialization with model path calls load."""
        with patch.object(CongressSignalModel, 'load') as mock_load:
            model = CongressSignalModel(model_path="/path/to/model.pkl")

            mock_load.assert_called_once_with("/path/to/model.pkl")


class TestCongressSignalModelPrepareFeatures:
    """Tests for CongressSignalModel.prepare_features method."""

    @pytest.fixture
    def model(self):
        """Create a model instance."""
        return CongressSignalModel()

    def test_prepare_features_basic(self, model):
        """Test basic feature extraction."""
        ticker_data = {
            'politician_count': 5,
            'buy_sell_ratio': 2.0,
            'recent_activity_30d': 10,
            'bipartisan': True,
            'net_volume': 50000,
            'party_alignment': 0.7,
            'committee_relevance': 0.6,
            'disclosure_delay': 15,
            'sentiment_score': 0.5,
            'market_momentum': 0.02,
            'sector_performance': 0.01,
        }

        features = model.prepare_features(ticker_data)

        assert features[0] == 5  # politician_count
        assert features[1] == 2.0  # buy_sell_ratio
        assert features[2] == 10  # recent_activity_30d
        assert features[3] == 1  # bipartisan (converted to 1)
        assert features[4] == 50000  # net_volume

    def test_prepare_features_with_defaults(self, model):
        """Test feature extraction uses defaults for missing values."""
        ticker_data = {}

        features = model.prepare_features(ticker_data)

        assert features[0] == 0  # politician_count default
        assert features[1] == 1.0  # buy_sell_ratio default
        assert features[2] == 0  # recent_activity_30d default
        assert features[3] == 0  # bipartisan default (False -> 0)
        assert features[6] == 0.5  # party_alignment default
        assert features[7] == 0.5  # committee_relevance default
        assert features[8] == 30  # disclosure_delay default

    def test_prepare_features_bipartisan_false(self, model):
        """Test bipartisan False converts to 0."""
        ticker_data = {'bipartisan': False}

        features = model.prepare_features(ticker_data)

        assert features[3] == 0

    def test_prepare_features_volume_magnitude_log(self, model):
        """Test volume magnitude uses log1p transform."""
        ticker_data = {'net_volume': 1000}

        features = model.prepare_features(ticker_data)

        expected = np.log1p(1000)
        assert features[5] == pytest.approx(expected)

    def test_prepare_features_returns_correct_length(self, model):
        """Test feature vector has correct length."""
        ticker_data = {}

        features = model.prepare_features(ticker_data)

        assert len(features) == len(FEATURE_NAMES)

    def test_prepare_features_dtype(self, model):
        """Test features are float32."""
        ticker_data = {'politician_count': 5}

        features = model.prepare_features(ticker_data)

        assert features.dtype == np.float32


class TestCongressSignalModelPredict:
    """Tests for CongressSignalModel.predict method."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model with mocked internals."""
        model = CongressSignalModel()
        model.is_trained = True
        model.model = MagicMock()
        model.scaler = MagicMock()
        return model

    def test_predict_untrained_model_raises(self):
        """Test predicting with untrained model raises ValueError."""
        model = CongressSignalModel()

        with pytest.raises(ValueError, match="Model is not trained"):
            model.predict(np.array([1, 2, 3]))

    def test_predict_returns_tuple(self, trained_model):
        """Test predict returns (prediction, confidence) tuple."""
        trained_model.scaler.transform.return_value = np.array([[1, 2, 3]])
        trained_model.model.predict.return_value = np.array([2])  # Label 0 (hold after -2 shift)
        trained_model.model.predict_proba.return_value = np.array([[0.1, 0.1, 0.6, 0.1, 0.1]])

        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        prediction, confidence = trained_model.predict(features)

        assert prediction == 0  # 2 - 2 = 0 (hold)
        assert confidence == 0.6

    def test_predict_reshapes_1d_array(self, trained_model):
        """Test 1D array is reshaped to 2D."""
        trained_model.scaler.transform.return_value = np.array([[1]])
        trained_model.model.predict.return_value = np.array([3])
        trained_model.model.predict_proba.return_value = np.array([[0.1, 0.1, 0.1, 0.6, 0.1]])

        features = np.array([1, 2, 3])

        prediction, confidence = trained_model.predict(features)

        # Check scaler received 2D array
        call_args = trained_model.scaler.transform.call_args[0][0]
        assert call_args.ndim == 2


class TestCongressSignalModelPredictBatch:
    """Tests for CongressSignalModel.predict_batch method."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model with mocked internals."""
        model = CongressSignalModel()
        model.is_trained = True
        model.model = MagicMock()
        model.scaler = MagicMock()
        model.scaler.transform.return_value = np.array([[0] * 12])
        model.model.predict.return_value = np.array([3])  # buy
        model.model.predict_proba.return_value = np.array([[0.1, 0.1, 0.1, 0.6, 0.1]])
        return model

    def test_predict_batch_basic(self, trained_model):
        """Test batch prediction returns list of results."""
        features_list = [
            {'ticker': 'AAPL', 'politician_count': 5},
            {'ticker': 'MSFT', 'politician_count': 3},
        ]

        results = trained_model.predict_batch(features_list)

        assert len(results) == 2
        assert results[0]['ticker'] == 'AAPL'
        assert results[1]['ticker'] == 'MSFT'

    def test_predict_batch_includes_signal_type(self, trained_model):
        """Test batch results include signal type label."""
        features_list = [{'ticker': 'AAPL'}]

        results = trained_model.predict_batch(features_list)

        assert 'signal_type' in results[0]
        assert results[0]['signal_type'] in SIGNAL_LABELS.values()

    def test_predict_batch_handles_errors(self, trained_model):
        """Test batch handles prediction errors gracefully."""
        trained_model.model.predict.side_effect = Exception("Prediction failed")

        features_list = [{'ticker': 'AAPL'}]

        results = trained_model.predict_batch(features_list)

        assert len(results) == 1
        assert 'error' in results[0]
        assert results[0]['ticker'] == 'AAPL'

    def test_predict_batch_includes_feature_hash(self, trained_model):
        """Test batch results include feature hash."""
        features_list = [{'ticker': 'AAPL', 'politician_count': 5}]

        results = trained_model.predict_batch(features_list)

        assert 'feature_hash' in results[0]
        assert len(results[0]['feature_hash']) == 16


class TestCongressSignalModelSaveLoad:
    """Tests for CongressSignalModel.save and .load methods."""

    def test_save_creates_file(self):
        """Test save creates a pickle file."""
        model = CongressSignalModel()
        model.is_trained = True
        model.training_metrics = {'accuracy': 0.85}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "model.pkl")
            model.save(path)

            assert Path(path).exists()

    def test_save_and_load_roundtrip(self):
        """Test model can be saved and loaded."""
        model = CongressSignalModel()
        model.is_trained = True
        model.model_version = "2.0.0"
        model.training_metrics = {'accuracy': 0.85}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.pkl")
            model.save(path)

            loaded_model = CongressSignalModel()
            loaded_model.load(path)

            assert loaded_model.model_version == "2.0.0"
            assert loaded_model.is_trained is True
            assert loaded_model.training_metrics == {'accuracy': 0.85}


class TestCongressSignalModelGetFeatureImportance:
    """Tests for CongressSignalModel.get_feature_importance method."""

    def test_untrained_returns_empty(self):
        """Test untrained model returns empty dict."""
        model = CongressSignalModel()

        result = model.get_feature_importance()

        assert result == {}

    def test_trained_returns_importance(self):
        """Test trained model returns feature importance."""
        model = CongressSignalModel()
        model.is_trained = True
        model.model = MagicMock()
        model.model.feature_importances_ = np.array([0.1] * len(FEATURE_NAMES))

        result = model.get_feature_importance()

        assert len(result) == len(FEATURE_NAMES)
        assert all(isinstance(v, float) for v in result.values())


class TestGetActiveModel:
    """Tests for get_active_model function."""

    def test_returns_none_initially(self):
        """Test returns None when no model loaded."""
        import app.services.ml_signal_model as module
        original = module._active_model
        module._active_model = None

        try:
            result = get_active_model()
            assert result is None
        finally:
            module._active_model = original

    def test_returns_model_when_set(self):
        """Test returns model when one is loaded."""
        import app.services.ml_signal_model as module
        original = module._active_model
        mock_model = MagicMock()
        module._active_model = mock_model

        try:
            result = get_active_model()
            assert result is mock_model
        finally:
            module._active_model = original


class TestLoadActiveModel:
    """Tests for load_active_model function."""

    def test_load_with_model_id(self):
        """Test loading specific model by ID."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase

            # Mock database query
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={'id': 'model-123', 'model_artifact_path': None, 'model_name': 'test', 'model_version': '1.0'}
            )

            # Mock download failure (no local file, no storage)
            with patch("app.services.ml_signal_model.download_model_from_storage", return_value=False):
                result = load_active_model(model_id="model-123")

            assert result is None  # Download failed

    def test_load_no_active_model(self):
        """Test returns None when no model found."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase

            # Mock empty result
            mock_result = MagicMock()
            mock_result.data = None
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            result = load_active_model()

            assert result is None

    def test_load_database_error(self):
        """Test returns None on database error."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_get_supabase.side_effect = Exception("Connection failed")

            result = load_active_model()

            assert result is None


class TestCachePrediction:
    """Tests for cache_prediction function."""

    def test_cache_success(self):
        """Test successful caching."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase

            result = cache_prediction(
                model_id="model-123",
                ticker="AAPL",
                feature_hash="abc123",
                prediction=1,
                confidence=0.8,
            )

            assert result is True
            mock_supabase.table.assert_called_with('ml_predictions_cache')

    def test_cache_failure(self):
        """Test cache failure returns False."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.table.return_value.upsert.return_value.execute.side_effect = Exception("Failed")

            result = cache_prediction(
                model_id="model-123",
                ticker="AAPL",
                feature_hash="abc123",
                prediction=1,
                confidence=0.8,
            )

            assert result is False

    def test_cache_sets_expiration(self):
        """Test cache sets expiration time."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase

            cache_prediction(
                model_id="model-123",
                ticker="AAPL",
                feature_hash="abc123",
                prediction=1,
                confidence=0.8,
                ttl_hours=24,
            )

            # Check upsert was called with expires_at
            call_args = mock_supabase.table.return_value.upsert.call_args[0][0]
            assert 'expires_at' in call_args


class TestGetCachedPrediction:
    """Tests for get_cached_prediction function."""

    def test_cache_hit(self):
        """Test successful cache retrieval."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase

            mock_result = MagicMock()
            mock_result.data = {
                'prediction': 1,
                'confidence': 0.85,
                'model_id': 'model-123',
            }
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.single.return_value.execute.return_value = mock_result

            result = get_cached_prediction("AAPL", "abc123")

            assert result is not None
            assert result['prediction'] == 1
            assert result['confidence'] == 0.85
            assert result['cached'] is True

    def test_cache_miss(self):
        """Test cache miss returns None."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_get_supabase.return_value = mock_supabase

            mock_result = MagicMock()
            mock_result.data = None
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.single.return_value.execute.return_value = mock_result

            result = get_cached_prediction("AAPL", "abc123")

            assert result is None

    def test_cache_error(self):
        """Test cache error returns None."""
        with patch("app.services.ml_signal_model.get_supabase") as mock_get_supabase:
            mock_get_supabase.side_effect = Exception("Connection failed")

            result = get_cached_prediction("AAPL", "abc123")

            assert result is None


class TestSignalLabels:
    """Tests for SIGNAL_LABELS configuration."""

    def test_all_labels_present(self):
        """Test all signal labels are defined."""
        expected_labels = ['strong_sell', 'sell', 'hold', 'buy', 'strong_buy']

        for label in expected_labels:
            assert label in SIGNAL_LABELS.values()

    def test_label_values(self):
        """Test label values map correctly."""
        assert SIGNAL_LABELS[-2] == 'strong_sell'
        assert SIGNAL_LABELS[-1] == 'sell'
        assert SIGNAL_LABELS[0] == 'hold'
        assert SIGNAL_LABELS[1] == 'buy'
        assert SIGNAL_LABELS[2] == 'strong_buy'


class TestFeatureNames:
    """Tests for FEATURE_NAMES configuration."""

    def test_feature_count(self):
        """Test correct number of features."""
        assert len(FEATURE_NAMES) == 12

    def test_expected_features_present(self):
        """Test expected feature names are present."""
        expected = [
            'politician_count', 'buy_sell_ratio', 'recent_activity_30d',
            'bipartisan', 'net_volume', 'volume_magnitude', 'party_alignment',
            'committee_relevance', 'disclosure_delay', 'sentiment_score',
            'market_momentum', 'sector_performance',
        ]

        for feature in expected:
            assert feature in FEATURE_NAMES
