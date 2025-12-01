"""
Tests for QuiverQuant disclosure validation.

This test covers the validation logic that prevents misaligned data from being ingested.
"""

import pytest


class TestQuiverQuantValidation:
    """Test QuiverQuant data validation logic."""

    def test_invalid_ticker_stock(self):
        """Test that 'STOCK' is detected as invalid ticker."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="John Doe",
            ticker="STOCK",
            asset_name="Apple Inc",
            transaction_date="2024-01-01",
        )
        assert result is False

    def test_invalid_ticker_purchase(self):
        """Test that 'PURCHASE' is detected as invalid ticker."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="John Doe",
            ticker="PURCHASE",
            asset_name="Apple Inc",
            transaction_date="2024-01-01",
        )
        assert result is False

    def test_percentage_in_asset_name(self):
        """Test that percentage in asset_name is detected as misaligned."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="John Doe",
            ticker="AAPL",
            asset_name="-29.78%",
            transaction_date="2024-01-01",
        )
        assert result is False

    def test_asset_name_in_politician_field(self):
        """Test that company name in politician_name is detected."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="FIGFIGMA INC CLASS AOT",
            ticker="AAPL",
            asset_name="Some Asset",
            transaction_date="2024-01-01",
        )
        assert result is False

    def test_valid_disclosure(self):
        """Test that valid disclosure passes validation."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="Nancy Pelosi",
            ticker="AAPL",
            asset_name="Apple Inc",
            transaction_date="2024-01-01",
        )
        assert result is True

    def test_valid_disclosure_no_ticker(self):
        """Test that disclosure without ticker can still be valid."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="Nancy Pelosi",
            ticker="",
            asset_name="Mutual Fund XYZ",
            transaction_date="2024-01-01",
        )
        assert result is True

    def test_missing_politician_name(self):
        """Test that missing politician_name fails validation."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="",
            ticker="AAPL",
            asset_name="Apple Inc",
            transaction_date="2024-01-01",
        )
        assert result is False

    def test_short_politician_name(self):
        """Test that very short politician_name fails validation."""
        from politician_trading.sources.quiverquant import QuiverQuantSource

        source = QuiverQuantSource()
        result = source._validate_parsed_disclosure(
            politician_name="AB",
            ticker="AAPL",
            asset_name="Apple Inc",
            transaction_date="2024-01-01",
        )
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
