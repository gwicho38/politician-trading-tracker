"""
Tests for SectorCache helper.

Covers initialization, get_sector, batch_resolve, preseed validation,
file persistence, and singleton behavior.
"""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.services.sector_cache import (
    CACHE_FILE,
    SECTOR_ETFS,
    SectorCache,
    _PRESEED,
    get_sector_cache,
)


# ---------------------------------------------------------------------------
# TestSectorCacheInit
# ---------------------------------------------------------------------------
class TestSectorCacheInit:
    """Test that SectorCache initializes correctly with preseed data."""

    @patch.object(SectorCache, "_load_from_file")
    def test_cache_starts_with_preseed_data(self, mock_load):
        cache = SectorCache()
        # Every preseed key should be present
        for ticker, etf in _PRESEED.items():
            assert cache.get_sector(ticker) == etf

    @patch.object(SectorCache, "_load_from_file")
    def test_known_ticker_aapl_resolves(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("AAPL") == "XLK"

    @patch.object(SectorCache, "_load_from_file")
    def test_known_ticker_jpm_resolves(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("JPM") == "XLF"

    @patch.object(SectorCache, "_load_from_file")
    def test_known_ticker_xom_resolves(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("XOM") == "XLE"

    @patch.object(SectorCache, "_load_from_file")
    def test_known_ticker_jnj_resolves(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("JNJ") == "XLV"

    @patch.object(SectorCache, "_load_from_file")
    def test_known_ticker_ba_resolves(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("BA") == "XLI"


# ---------------------------------------------------------------------------
# TestSectorCacheGetSector
# ---------------------------------------------------------------------------
class TestSectorCacheGetSector:
    """Test get_sector() lookup behavior."""

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_correct_etf_for_known_ticker(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("MSFT") == "XLK"
        assert cache.get_sector("GS") == "XLF"
        assert cache.get_sector("NEE") == "XLU"
        assert cache.get_sector("LIN") == "XLB"
        assert cache.get_sector("AMT") == "XLRE"

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_none_for_unknown_ticker(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("ZZZZZ") is None
        assert cache.get_sector("FAKETICKER") is None

    @patch.object(SectorCache, "_load_from_file")
    def test_case_insensitive_lookup(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("aapl") == "XLK"
        assert cache.get_sector("Aapl") == "XLK"
        assert cache.get_sector("jpm") == "XLF"
        assert cache.get_sector("xom") == "XLE"

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_none_for_empty_string(self, mock_load):
        cache = SectorCache()
        assert cache.get_sector("") is None


# ---------------------------------------------------------------------------
# TestSectorCacheBatchResolve
# ---------------------------------------------------------------------------
class TestSectorCacheBatchResolve:
    """Test batch_resolve() with cache hits and yfinance misses."""

    @patch.object(SectorCache, "_load_from_file")
    def test_resolves_all_known_tickers_from_cache(self, mock_load):
        cache = SectorCache()
        tickers = ["AAPL", "JPM", "XOM"]
        result = cache.batch_resolve(tickers)
        assert result == {"AAPL": "XLK", "JPM": "XLF", "XOM": "XLE"}

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_partial_results_when_some_unknown(self, mock_load):
        cache = SectorCache()

        mock_ticker_obj = MagicMock()
        mock_ticker_obj.info = {"sector": "Technology"}

        with patch.object(cache, "_resolve_via_yfinance") as mock_resolve:
            # Simulate yfinance resolving NEWCO into cache
            def side_effect(tickers_list):
                for t in tickers_list:
                    cache._cache[t] = "XLK"

            mock_resolve.side_effect = side_effect

            result = cache.batch_resolve(["AAPL", "NEWCO"])
            assert result["AAPL"] == "XLK"
            assert result["NEWCO"] == "XLK"
            mock_resolve.assert_called_once_with(["NEWCO"])

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_only_known_when_yfinance_fails(self, mock_load):
        cache = SectorCache()

        with patch.object(cache, "_resolve_via_yfinance"):
            # yfinance does not add anything to cache
            result = cache.batch_resolve(["AAPL", "UNKNOWNTICKER"])
            assert result == {"AAPL": "XLK"}
            assert "UNKNOWNTICKER" not in result

    @patch.object(SectorCache, "_load_from_file")
    def test_empty_list_returns_empty_dict(self, mock_load):
        cache = SectorCache()
        result = cache.batch_resolve([])
        assert result == {}

    @patch.object(SectorCache, "_load_from_file")
    def test_batch_resolve_uppercases_tickers(self, mock_load):
        cache = SectorCache()
        result = cache.batch_resolve(["aapl", "jpm"])
        assert result == {"AAPL": "XLK", "JPM": "XLF"}


# ---------------------------------------------------------------------------
# TestSectorCachePreseed
# ---------------------------------------------------------------------------
class TestSectorCachePreseed:
    """Validate the preseed mapping data."""

    def test_all_sector_etfs_represented_in_preseed(self):
        preseed_etfs = set(_PRESEED.values())
        for etf in SECTOR_ETFS:
            assert etf in preseed_etfs, f"Sector ETF {etf} has no ticker in _PRESEED"

    def test_preseed_has_reasonable_count(self):
        assert len(_PRESEED) > 50, (
            f"Expected > 50 pre-seeded tickers, got {len(_PRESEED)}"
        )

    def test_all_preseed_values_are_valid_sector_etfs(self):
        valid_etfs = set(SECTOR_ETFS)
        for ticker, etf in _PRESEED.items():
            assert etf in valid_etfs, (
                f"Ticker {ticker} maps to {etf} which is not in SECTOR_ETFS"
            )

    def test_preseed_keys_are_uppercase(self):
        for ticker in _PRESEED:
            assert ticker == ticker.upper(), (
                f"Preseed ticker {ticker} is not uppercase"
            )


# ---------------------------------------------------------------------------
# TestSectorCacheFilePersistence
# ---------------------------------------------------------------------------
class TestSectorCacheFilePersistence:
    """Test JSON file persistence (_load_from_file / _save_to_file)."""

    @patch("app.services.sector_cache.Path")
    def test_load_from_file_merges_stored_data(self, mock_path_cls):
        stored_data = {"NEWTICKER": "XLK", "ANOTHER": "XLF"}
        mock_path_instance = MagicMock()
        mock_path_cls.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True

        m = mock_open(read_data=json.dumps(stored_data))
        with patch("builtins.open", m):
            cache = SectorCache()

        # Original preseed should still exist
        assert cache.get_sector("AAPL") == "XLK"
        # Loaded data should also be present
        assert cache.get_sector("NEWTICKER") == "XLK"
        assert cache.get_sector("ANOTHER") == "XLF"

    @patch("app.services.sector_cache.Path")
    def test_load_from_file_handles_file_not_found(self, mock_path_cls):
        mock_path_instance = MagicMock()
        mock_path_cls.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False

        # Should not raise - gracefully skips loading
        cache = SectorCache()
        # Preseed should still work
        assert cache.get_sector("AAPL") == "XLK"

    @patch("app.services.sector_cache.Path")
    def test_load_from_file_handles_corrupt_json(self, mock_path_cls):
        mock_path_instance = MagicMock()
        mock_path_cls.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True

        m = mock_open(read_data="not valid json {{{")
        with patch("builtins.open", m):
            # Should not raise - exception is caught
            cache = SectorCache()

        # Preseed should still work despite corrupt file
        assert cache.get_sector("AAPL") == "XLK"

    @patch.object(SectorCache, "_load_from_file")
    def test_save_to_file_writes_json(self, mock_load):
        cache = SectorCache()

        m = mock_open()
        with patch("builtins.open", m):
            cache._save_to_file()

        m.assert_called_once_with(CACHE_FILE, "w")
        handle = m()
        written = "".join(
            call.args[0] for call in handle.write.call_args_list
        )
        saved_data = json.loads(written)
        # Saved data should contain preseed entries
        assert saved_data["AAPL"] == "XLK"
        assert saved_data["JPM"] == "XLF"

    @patch.object(SectorCache, "_load_from_file")
    def test_save_to_file_handles_write_error(self, mock_load):
        cache = SectorCache()

        with patch("builtins.open", side_effect=PermissionError("denied")):
            # Should not raise - exception is caught
            cache._save_to_file()


# ---------------------------------------------------------------------------
# TestResolveViaYfinance
# ---------------------------------------------------------------------------
class TestResolveViaYfinance:
    """Test _resolve_via_yfinance integration with yfinance."""

    @patch.object(SectorCache, "_load_from_file")
    @patch.object(SectorCache, "_save_to_file")
    def test_resolves_ticker_via_yfinance(self, mock_save, mock_load):
        cache = SectorCache()

        mock_ticker_obj = MagicMock()
        mock_ticker_obj.info = {"sector": "Technology"}

        with patch.dict("sys.modules", {"yfinance": MagicMock()}) as _:
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_yf.Ticker.return_value = mock_ticker_obj

            cache._resolve_via_yfinance(["NEWCO"])

        assert cache.get_sector("NEWCO") == "XLK"
        mock_save.assert_called_once()

    @patch.object(SectorCache, "_load_from_file")
    @patch.object(SectorCache, "_save_to_file")
    def test_skips_ticker_with_unknown_sector(self, mock_save, mock_load):
        cache = SectorCache()

        mock_ticker_obj = MagicMock()
        mock_ticker_obj.info = {"sector": "UnknownSector"}

        with patch.dict("sys.modules", {"yfinance": MagicMock()}) as _:
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_yf.Ticker.return_value = mock_ticker_obj

            cache._resolve_via_yfinance(["MYSTERY"])

        assert cache.get_sector("MYSTERY") is None
        # No resolution happened so save should not be called
        mock_save.assert_not_called()

    @patch.object(SectorCache, "_load_from_file")
    @patch.object(SectorCache, "_save_to_file")
    def test_limits_to_20_tickers(self, mock_save, mock_load):
        cache = SectorCache()

        call_count = 0

        mock_ticker_obj = MagicMock()
        mock_ticker_obj.info = {"sector": "Technology"}

        with patch.dict("sys.modules", {"yfinance": MagicMock()}) as _:
            import sys
            mock_yf = sys.modules["yfinance"]

            def track_calls(ticker):
                nonlocal call_count
                call_count += 1
                return mock_ticker_obj

            mock_yf.Ticker.side_effect = track_calls

            tickers = [f"TICK{i}" for i in range(30)]
            cache._resolve_via_yfinance(tickers)

        # Should only process first 20
        assert call_count == 20

    @patch.object(SectorCache, "_load_from_file")
    @patch.object(SectorCache, "_save_to_file")
    def test_handles_yfinance_exception_per_ticker(self, mock_save, mock_load):
        cache = SectorCache()

        with patch.dict("sys.modules", {"yfinance": MagicMock()}) as _:
            import sys
            mock_yf = sys.modules["yfinance"]
            mock_yf.Ticker.side_effect = Exception("API error")

            # Should not raise
            cache._resolve_via_yfinance(["BADTICKER"])

        assert cache.get_sector("BADTICKER") is None


# ---------------------------------------------------------------------------
# TestGetSectorCacheSingleton
# ---------------------------------------------------------------------------
class TestGetSectorCacheSingleton:
    """Test the module-level singleton accessor."""

    def setup_method(self):
        """Reset the module-level singleton before each test."""
        import app.services.sector_cache as module
        module._sector_cache = None

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_sector_cache_instance(self, mock_load):
        result = get_sector_cache()
        assert isinstance(result, SectorCache)

    @patch.object(SectorCache, "_load_from_file")
    def test_returns_same_instance_on_second_call(self, mock_load):
        first = get_sector_cache()
        second = get_sector_cache()
        assert first is second

    def teardown_method(self):
        """Clean up singleton after each test."""
        import app.services.sector_cache as module
        module._sector_cache = None
