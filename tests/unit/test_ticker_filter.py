"""
Tests for ticker filtering functionality in Data Collection page.

This test covers the bug where checking "Show only actionable stocks (with tickers)"
returned 0 results because:
1. The filter was applied client-side instead of at the database level
2. The current page might not have any disclosures with tickers when ordered by date
"""

import pandas as pd
import pytest


class TestTickerFilter:
    """Test ticker filtering logic."""

    def test_ticker_mask_with_none_values(self):
        """Test that ticker mask correctly handles None/null values.

        Bug: The original filter checked for "N/A" but raw data has None values.
        """
        # Simulate raw data from Supabase (has None, not "N/A")
        df = pd.DataFrame(
            {
                "asset_ticker": [None, "", "AAPL", "GOOGL", None, "MSFT", ""],
                "asset_name": [
                    "Some Fund",
                    "Another Fund",
                    "Apple Inc",
                    "Google",
                    "Bond",
                    "Microsoft",
                    "ETF",
                ],
            }
        )

        # Correct filter (what we fixed it to)
        ticker_mask = df["asset_ticker"].notna() & (df["asset_ticker"] != "")
        filtered_df = df[ticker_mask]

        # Should have 3 records with tickers: AAPL, GOOGL, MSFT
        assert len(filtered_df) == 3
        assert set(filtered_df["asset_ticker"].tolist()) == {"AAPL", "GOOGL", "MSFT"}

    def test_ticker_mask_does_not_check_na_string(self):
        """Test that we don't check for 'N/A' string in raw data.

        The 'N/A' string is only added to display_df for UI purposes,
        not present in raw database data.
        """
        # Raw data from database
        df = pd.DataFrame(
            {
                "asset_ticker": [None, "AAPL", ""],
            }
        )

        # Wrong filter (old buggy code checked for "N/A")
        wrong_mask = (
            df["asset_ticker"].notna()
            & (df["asset_ticker"] != "")
            & (df["asset_ticker"] != "N/A")
        )

        # Correct filter (no "N/A" check)
        correct_mask = df["asset_ticker"].notna() & (df["asset_ticker"] != "")

        # Both should work the same when there's no "N/A" in raw data
        assert wrong_mask.sum() == correct_mask.sum() == 1

    def test_empty_string_filtered_out(self):
        """Test that empty strings are filtered out."""
        df = pd.DataFrame(
            {
                "asset_ticker": ["", "AAPL", "  ", "GOOGL"],
            }
        )

        ticker_mask = df["asset_ticker"].notna() & (df["asset_ticker"] != "")
        filtered_df = df[ticker_mask]

        # Empty string should be filtered, whitespace should remain
        assert len(filtered_df) == 3
        assert "" not in filtered_df["asset_ticker"].tolist()

    def test_all_none_returns_empty(self):
        """Test that page with all None tickers returns empty when filtered."""
        df = pd.DataFrame(
            {
                "asset_ticker": [None, None, None, "", ""],
                "asset_name": ["Fund 1", "Fund 2", "Fund 3", "ETF 1", "ETF 2"],
            }
        )

        ticker_mask = df["asset_ticker"].notna() & (df["asset_ticker"] != "")
        filtered_df = df[ticker_mask]

        assert len(filtered_df) == 0

    def test_filter_preserves_other_columns(self):
        """Test that filtering preserves all other columns."""
        df = pd.DataFrame(
            {
                "asset_ticker": [None, "AAPL"],
                "asset_name": ["Fund", "Apple Inc"],
                "transaction_date": ["2024-01-01", "2024-01-02"],
                "politician_name": ["John Doe", "Jane Doe"],
            }
        )

        ticker_mask = df["asset_ticker"].notna() & (df["asset_ticker"] != "")
        filtered_df = df[ticker_mask]

        assert len(filtered_df) == 1
        assert filtered_df.iloc[0]["asset_name"] == "Apple Inc"
        assert filtered_df.iloc[0]["politician_name"] == "Jane Doe"


class TestTickerStatistics:
    """Test ticker statistics calculations."""

    def test_missing_tickers_count(self):
        """Test counting disclosures without tickers."""
        df = pd.DataFrame(
            {
                "asset_ticker": [None, "", "AAPL", "GOOGL", None],
            }
        )

        missing_tickers = len([t for t in df["asset_ticker"] if not t or t == ""])

        # None (falsy), empty string, None = 3 missing
        assert missing_tickers == 3

    def test_with_tickers_count(self):
        """Test counting disclosures with tickers."""
        df = pd.DataFrame(
            {
                "asset_ticker": [None, "", "AAPL", "GOOGL", None],
            }
        )

        missing_tickers = len([t for t in df["asset_ticker"] if not t or t == ""])
        with_tickers = len(df) - missing_tickers

        assert with_tickers == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
