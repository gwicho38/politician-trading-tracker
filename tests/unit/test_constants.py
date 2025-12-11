"""Test constants configuration."""

import pytest

from politician_trading.constants.urls import ConfigDefaults


class TestConfigDefaults:
    """Tests for ConfigDefaults constants."""

    def test_max_lookback_days_equals_five_years(self):
        """MAX_LOOKBACK_DAYS should equal 5 years in days."""
        expected_five_years = 5 * 365  # 1825 days
        assert ConfigDefaults.MAX_LOOKBACK_DAYS == expected_five_years

    def test_default_lookback_days_is_reasonable(self):
        """DEFAULT_LOOKBACK_DAYS should be a sensible default."""
        assert ConfigDefaults.DEFAULT_LOOKBACK_DAYS == 30
        assert ConfigDefaults.DEFAULT_LOOKBACK_DAYS >= 1
        assert ConfigDefaults.DEFAULT_LOOKBACK_DAYS <= ConfigDefaults.MAX_LOOKBACK_DAYS

    def test_max_lookback_greater_than_default(self):
        """MAX_LOOKBACK_DAYS should be greater than DEFAULT_LOOKBACK_DAYS."""
        assert ConfigDefaults.MAX_LOOKBACK_DAYS > ConfigDefaults.DEFAULT_LOOKBACK_DAYS

    def test_retention_days_defined(self):
        """RETENTION_DAYS should be defined."""
        assert ConfigDefaults.RETENTION_DAYS == 365

    def test_timeout_values(self):
        """Timeout values should be reasonable."""
        assert ConfigDefaults.DEFAULT_TIMEOUT == 30
        assert ConfigDefaults.LONG_TIMEOUT == 60
        assert ConfigDefaults.SHORT_TIMEOUT == 10
        assert ConfigDefaults.SHORT_TIMEOUT < ConfigDefaults.DEFAULT_TIMEOUT < ConfigDefaults.LONG_TIMEOUT

    def test_confidence_thresholds(self):
        """Confidence thresholds should be between 0 and 1."""
        assert 0 <= ConfigDefaults.MIN_CONFIDENCE <= 1
        assert 0 <= ConfigDefaults.HIGH_CONFIDENCE <= 1
        assert ConfigDefaults.MIN_CONFIDENCE <= ConfigDefaults.HIGH_CONFIDENCE
