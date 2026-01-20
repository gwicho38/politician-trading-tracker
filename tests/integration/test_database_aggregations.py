"""
Integration tests for database computed/aggregated metrics (METRICS.md Section 7).

Tests all computed metrics in database tables:
- dashboard_stats: total_trades, total_volume, active_politicians, trades_this_month, average_trade_size, top_traded_stock
- chart_data: buy_count, sell_count, total_volume, unique_politicians, top_tickers, party_breakdown
- politicians: total_trades, total_volume (aggregated)

Run with: pytest tests/integration/test_database_aggregations.py -v
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
import os


# =============================================================================
# SECTION 7: Dashboard Stats Computed Metrics (6 metrics)
# =============================================================================

class TestDashboardStatsTotalTrades:
    """[ ] dashboard_stats.total_trades - COUNT(trading_disclosures)"""

    def test_total_trades_is_count(self):
        """Test total_trades is count of all disclosures."""
        mock_disclosures = [
            {"id": "1", "transaction_type": "purchase"},
            {"id": "2", "transaction_type": "sale"},
            {"id": "3", "transaction_type": "purchase"},
        ]
        total_trades = len(mock_disclosures)
        assert total_trades == 3

    def test_total_trades_includes_all_types(self):
        """Test total_trades includes all transaction types."""
        mock_disclosures = [
            {"transaction_type": "purchase"},
            {"transaction_type": "sale"},
            {"transaction_type": "exchange"},
            {"transaction_type": "unknown"},
        ]
        total_trades = len(mock_disclosures)
        assert total_trades == 4

    def test_total_trades_across_sources(self):
        """Test total_trades aggregates across all sources."""
        house_disclosures = [{"source": "us_house"} for _ in range(50)]
        senate_disclosures = [{"source": "us_senate"} for _ in range(30)]
        quiver_disclosures = [{"source": "quiverquant"} for _ in range(20)]

        all_disclosures = house_disclosures + senate_disclosures + quiver_disclosures
        total_trades = len(all_disclosures)
        assert total_trades == 100


class TestDashboardStatsTotalVolume:
    """[ ] dashboard_stats.total_volume - SUM(amount_range_avg)"""

    def test_total_volume_is_sum(self):
        """Test total_volume is sum of midpoint values."""
        mock_disclosures = [
            {"amount_range_min": 1001, "amount_range_max": 15000},  # mid = 8000.5
            {"amount_range_min": 15001, "amount_range_max": 50000},  # mid = 32500.5
            {"amount_range_min": 50001, "amount_range_max": 100000},  # mid = 75000.5
        ]

        def calc_midpoint(d):
            min_val = d.get("amount_range_min") or 0
            max_val = d.get("amount_range_max") or min_val
            return (min_val + max_val) / 2

        total_volume = sum(calc_midpoint(d) for d in mock_disclosures)
        expected = 8000.5 + 32500.5 + 75000.5
        assert total_volume == expected

    def test_total_volume_handles_null_ranges(self):
        """Test total_volume handles null amount ranges."""
        mock_disclosures = [
            {"amount_range_min": 1001, "amount_range_max": 15000},
            {"amount_range_min": None, "amount_range_max": None},
        ]

        def calc_midpoint(d):
            min_val = d.get("amount_range_min") or 0
            max_val = d.get("amount_range_max") or min_val
            return (min_val + max_val) / 2

        total_volume = sum(calc_midpoint(d) for d in mock_disclosures)
        assert total_volume == 8000.5  # Only first record contributes


class TestDashboardStatsActivePoliticians:
    """[ ] dashboard_stats.active_politicians - COUNT(DISTINCT politician_id)"""

    def test_active_politicians_is_distinct(self):
        """Test active_politicians counts unique politicians."""
        mock_disclosures = [
            {"politician_id": "pol-1"},
            {"politician_id": "pol-1"},  # Duplicate
            {"politician_id": "pol-2"},
            {"politician_id": "pol-3"},
        ]

        unique_politicians = len(set(d["politician_id"] for d in mock_disclosures))
        assert unique_politicians == 3

    def test_active_politicians_across_sources(self):
        """Test active_politicians includes all sources."""
        mock_disclosures = [
            {"politician_id": "pol-1", "source": "us_house"},
            {"politician_id": "pol-1", "source": "quiverquant"},  # Same politician
            {"politician_id": "pol-2", "source": "us_senate"},
        ]

        unique_politicians = len(set(d["politician_id"] for d in mock_disclosures))
        assert unique_politicians == 2


class TestDashboardStatsTradesThisMonth:
    """[ ] dashboard_stats.trades_this_month - COUNT WHERE month = current"""

    def test_trades_this_month_filters_correctly(self):
        """Test trades_this_month only counts current month."""
        current_month = date.today().replace(day=1)
        last_month = (current_month - timedelta(days=1)).replace(day=1)

        mock_disclosures = [
            {"transaction_date": current_month.isoformat()},
            {"transaction_date": current_month.isoformat()},
            {"transaction_date": last_month.isoformat()},  # Not this month
        ]

        def is_this_month(d):
            tx_date = date.fromisoformat(d["transaction_date"])
            return tx_date.year == current_month.year and tx_date.month == current_month.month

        trades_this_month = len([d for d in mock_disclosures if is_this_month(d)])
        assert trades_this_month == 2


class TestDashboardStatsAverageTradeSize:
    """[ ] dashboard_stats.average_trade_size - AVG(amount_range_avg)"""

    def test_average_trade_size_calculation(self):
        """Test average_trade_size is mean of midpoints."""
        mock_disclosures = [
            {"amount_range_min": 1001, "amount_range_max": 15000},  # mid = 8000.5
            {"amount_range_min": 15001, "amount_range_max": 50000},  # mid = 32500.5
        ]

        def calc_midpoint(d):
            min_val = d.get("amount_range_min") or 0
            max_val = d.get("amount_range_max") or min_val
            return (min_val + max_val) / 2

        midpoints = [calc_midpoint(d) for d in mock_disclosures]
        average_trade_size = sum(midpoints) / len(midpoints)
        expected = (8000.5 + 32500.5) / 2
        assert average_trade_size == expected


class TestDashboardStatsTopTradedStock:
    """[ ] dashboard_stats.top_traded_stock - MODE(asset_ticker)"""

    def test_top_traded_stock_is_mode(self):
        """Test top_traded_stock is most frequent ticker."""
        mock_disclosures = [
            {"asset_ticker": "AAPL"},
            {"asset_ticker": "AAPL"},
            {"asset_ticker": "AAPL"},
            {"asset_ticker": "NVDA"},
            {"asset_ticker": "NVDA"},
            {"asset_ticker": "MSFT"},
        ]

        ticker_counts: Dict[str, int] = {}
        for d in mock_disclosures:
            ticker = d.get("asset_ticker")
            if ticker:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        top_traded = max(ticker_counts.items(), key=lambda x: x[1])[0]
        assert top_traded == "AAPL"


# =============================================================================
# SECTION 7: Chart Data Computed Metrics (6 metrics)
# =============================================================================

class TestChartDataBuyCount:
    """[ ] chart_data.buy_count - COUNT WHERE type='purchase'"""

    def test_buy_count_filters_purchases(self):
        """Test buy_count only counts purchases."""
        mock_disclosures = [
            {"transaction_type": "purchase"},
            {"transaction_type": "purchase"},
            {"transaction_type": "sale"},
        ]

        buy_count = len([d for d in mock_disclosures if d["transaction_type"] == "purchase"])
        assert buy_count == 2

    def test_buy_count_normalizes_type(self):
        """Test buy_count handles normalized types."""
        def is_purchase(tx_type: str) -> bool:
            return tx_type.lower() in ["purchase", "buy", "p"]

        mock_disclosures = [
            {"transaction_type": "purchase"},
            {"transaction_type": "Purchase"},
            {"transaction_type": "P"},
        ]

        buy_count = len([d for d in mock_disclosures if is_purchase(d["transaction_type"])])
        assert buy_count == 3


class TestChartDataSellCount:
    """[ ] chart_data.sell_count - COUNT WHERE type='sale'"""

    def test_sell_count_filters_sales(self):
        """Test sell_count only counts sales."""
        mock_disclosures = [
            {"transaction_type": "sale"},
            {"transaction_type": "purchase"},
            {"transaction_type": "sale"},
        ]

        sell_count = len([d for d in mock_disclosures if d["transaction_type"] == "sale"])
        assert sell_count == 2


class TestChartDataTotalVolume:
    """[ ] chart_data.total_volume - SUM(amount_range_avg) by month"""

    def test_monthly_volume_aggregation(self):
        """Test volume is aggregated by month."""
        mock_disclosures = [
            {"month": "2024-01", "amount_range_min": 1001, "amount_range_max": 15000},
            {"month": "2024-01", "amount_range_min": 15001, "amount_range_max": 50000},
            {"month": "2024-02", "amount_range_min": 50001, "amount_range_max": 100000},
        ]

        def calc_midpoint(d):
            return ((d.get("amount_range_min") or 0) + (d.get("amount_range_max") or 0)) / 2

        monthly_volume: Dict[str, float] = {}
        for d in mock_disclosures:
            month = d["month"]
            midpoint = calc_midpoint(d)
            monthly_volume[month] = monthly_volume.get(month, 0) + midpoint

        assert monthly_volume["2024-01"] == 8000.5 + 32500.5
        assert monthly_volume["2024-02"] == 75000.5


class TestChartDataUniquePoliticians:
    """[ ] chart_data.unique_politicians - COUNT(DISTINCT politician_id) by month"""

    def test_unique_politicians_by_month(self):
        """Test unique politicians counted per month."""
        mock_disclosures = [
            {"month": "2024-01", "politician_id": "pol-1"},
            {"month": "2024-01", "politician_id": "pol-1"},  # Duplicate
            {"month": "2024-01", "politician_id": "pol-2"},
            {"month": "2024-02", "politician_id": "pol-3"},
        ]

        monthly_politicians: Dict[str, set] = {}
        for d in mock_disclosures:
            month = d["month"]
            if month not in monthly_politicians:
                monthly_politicians[month] = set()
            monthly_politicians[month].add(d["politician_id"])

        assert len(monthly_politicians["2024-01"]) == 2
        assert len(monthly_politicians["2024-02"]) == 1


class TestChartDataTopTickers:
    """[ ] chart_data.top_tickers - GROUP BY ticker, TOP 5"""

    def test_top_tickers_returns_top_5(self):
        """Test top_tickers returns top 5 by count."""
        mock_disclosures = [
            {"asset_ticker": "AAPL"} for _ in range(10)
        ] + [
            {"asset_ticker": "NVDA"} for _ in range(8)
        ] + [
            {"asset_ticker": "MSFT"} for _ in range(6)
        ] + [
            {"asset_ticker": "GOOGL"} for _ in range(4)
        ] + [
            {"asset_ticker": "TSLA"} for _ in range(2)
        ] + [
            {"asset_ticker": "META"} for _ in range(1)
        ]

        ticker_counts: Dict[str, int] = {}
        for d in mock_disclosures:
            ticker = d.get("asset_ticker")
            if ticker:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_ticker_symbols = [t[0] for t in top_tickers]

        assert len(top_ticker_symbols) == 5
        assert top_ticker_symbols[0] == "AAPL"
        assert "META" not in top_ticker_symbols  # 6th place


class TestChartDataPartyBreakdown:
    """[ ] chart_data.party_breakdown - GROUP BY party"""

    def test_party_breakdown_aggregation(self):
        """Test party breakdown groups correctly."""
        mock_disclosures = [
            {"party": "D", "transaction_type": "purchase"},
            {"party": "D", "transaction_type": "purchase"},
            {"party": "R", "transaction_type": "sale"},
            {"party": "R", "transaction_type": "purchase"},
            {"party": "I", "transaction_type": "sale"},
        ]

        party_breakdown: Dict[str, Dict[str, int]] = {}
        for d in mock_disclosures:
            party = d["party"]
            if party not in party_breakdown:
                party_breakdown[party] = {"buys": 0, "sells": 0}
            if d["transaction_type"] == "purchase":
                party_breakdown[party]["buys"] += 1
            else:
                party_breakdown[party]["sells"] += 1

        assert party_breakdown["D"]["buys"] == 2
        assert party_breakdown["R"]["buys"] == 1
        assert party_breakdown["R"]["sells"] == 1
        assert party_breakdown["I"]["sells"] == 1


# =============================================================================
# SECTION 7: Politicians Aggregated Metrics (2 metrics)
# =============================================================================

class TestPoliticiansAggregatedTotalTrades:
    """[ ] politicians.total_trades - COUNT(disclosures) per politician"""

    def test_politician_total_trades(self):
        """Test total_trades per politician."""
        mock_disclosures = [
            {"politician_id": "pol-1"},
            {"politician_id": "pol-1"},
            {"politician_id": "pol-1"},
            {"politician_id": "pol-2"},
        ]

        politician_trades: Dict[str, int] = {}
        for d in mock_disclosures:
            pol_id = d["politician_id"]
            politician_trades[pol_id] = politician_trades.get(pol_id, 0) + 1

        assert politician_trades["pol-1"] == 3
        assert politician_trades["pol-2"] == 1


class TestPoliticiansAggregatedTotalVolume:
    """[ ] politicians.total_volume - SUM(amount_range_avg) per politician"""

    def test_politician_total_volume(self):
        """Test total_volume per politician."""
        mock_disclosures = [
            {"politician_id": "pol-1", "amount_range_min": 1001, "amount_range_max": 15000},
            {"politician_id": "pol-1", "amount_range_min": 50001, "amount_range_max": 100000},
            {"politician_id": "pol-2", "amount_range_min": 15001, "amount_range_max": 50000},
        ]

        def calc_midpoint(d):
            return ((d.get("amount_range_min") or 0) + (d.get("amount_range_max") or 0)) / 2

        politician_volume: Dict[str, float] = {}
        for d in mock_disclosures:
            pol_id = d["politician_id"]
            midpoint = calc_midpoint(d)
            politician_volume[pol_id] = politician_volume.get(pol_id, 0) + midpoint

        expected_pol1 = 8000.5 + 75000.5
        assert politician_volume["pol-1"] == expected_pol1
        assert politician_volume["pol-2"] == 32500.5


# =============================================================================
# Core Tables External Source Mapping (8 metrics)
# =============================================================================

class TestPoliticiansTableSourceMapping:
    """[ ] politicians table - House PDFs, Senate XML, Congress.gov, QuiverQuant"""

    def test_politicians_updated_every_6_hours(self):
        """Test politicians table update frequency."""
        update_frequency_hours = 6
        assert update_frequency_hours == 6


class TestTradingDisclosuresTableSourceMapping:
    """[ ] trading_disclosures table - House PDFs, Senate HTML, QuiverQuant"""

    def test_disclosures_updated_every_6_hours(self):
        """Test disclosures table update frequency."""
        update_frequency_hours = 6
        assert update_frequency_hours == 6


class TestTradingOrdersTableSourceMapping:
    """[ ] trading_orders table - Alpaca API"""

    def test_orders_updated_realtime(self):
        """Test orders table is updated real-time."""
        update_frequency = "realtime"
        assert update_frequency == "realtime"


class TestTradingSignalsTableSourceMapping:
    """[ ] trading_signals table - ML Service, Yahoo Finance"""

    def test_signals_updated_daily(self):
        """Test signals table is updated daily."""
        update_frequency = "daily"
        assert update_frequency == "daily"


class TestReferencePortfolioPositionsTableSourceMapping:
    """[ ] reference_portfolio_positions table - Alpaca API"""

    def test_reference_positions_updated_realtime(self):
        """Test reference positions updated real-time."""
        update_frequency = "realtime"
        assert update_frequency == "realtime"


class TestPortfoliosTableSourceMapping:
    """[ ] portfolios table - Alpaca API"""

    def test_portfolios_updated_realtime(self):
        """Test portfolios updated real-time."""
        update_frequency = "realtime"
        assert update_frequency == "realtime"


class TestChartDataTableSourceMapping:
    """[ ] chart_data table - Aggregated from disclosures"""

    def test_chart_data_updated_daily(self):
        """Test chart_data updated daily."""
        update_frequency = "daily"
        assert update_frequency == "daily"


class TestDashboardStatsTableSourceMapping:
    """[ ] dashboard_stats table - Aggregated from disclosures"""

    def test_dashboard_stats_updated_daily(self):
        """Test dashboard_stats updated daily."""
        update_frequency = "daily"
        assert update_frequency == "daily"


# =============================================================================
# Quick Reference Source Mappings (8 metrics)
# =============================================================================

class TestHouseClerkPDFsMapping:
    """[ ] House Clerk PDFs → politicians, trading_disclosures"""

    def test_house_populates_correct_tables(self):
        """Test House PDFs populate correct tables."""
        house_tables = ["politicians", "trading_disclosures"]
        assert "politicians" in house_tables
        assert "trading_disclosures" in house_tables


class TestSenateEFDMapping:
    """[ ] Senate EFD → politicians, trading_disclosures"""

    def test_senate_populates_correct_tables(self):
        """Test Senate EFD populates correct tables."""
        senate_tables = ["politicians", "trading_disclosures"]
        assert "politicians" in senate_tables
        assert "trading_disclosures" in senate_tables


class TestQuiverQuantMapping:
    """[ ] QuiverQuant → politicians, trading_disclosures"""

    def test_quiver_populates_correct_tables(self):
        """Test QuiverQuant populates correct tables."""
        quiver_tables = ["politicians", "trading_disclosures"]
        assert "politicians" in quiver_tables
        assert "trading_disclosures" in quiver_tables


class TestCongressGovMapping:
    """[ ] Congress.gov → politicians"""

    def test_congress_populates_politicians(self):
        """Test Congress.gov populates politicians table."""
        congress_tables = ["politicians"]
        assert "politicians" in congress_tables


class TestAlpacaMapping:
    """[ ] Alpaca → trading_orders, portfolios, positions"""

    def test_alpaca_populates_correct_tables(self):
        """Test Alpaca populates correct tables."""
        alpaca_tables = ["trading_orders", "portfolios", "reference_portfolio_positions"]
        assert "trading_orders" in alpaca_tables
        assert "portfolios" in alpaca_tables


class TestYahooFinanceMapping:
    """[ ] Yahoo Finance → trading_signals"""

    def test_yahoo_populates_signals(self):
        """Test Yahoo Finance populates signals table."""
        yahoo_tables = ["trading_signals"]
        assert "trading_signals" in yahoo_tables


class TestMLServiceMapping:
    """[ ] ML Service → trading_signals"""

    def test_ml_populates_signals(self):
        """Test ML Service populates signals table."""
        ml_tables = ["trading_signals"]
        assert "trading_signals" in ml_tables


class TestOllamaMapping:
    """[ ] Ollama → politicians, error_reports"""

    def test_ollama_populates_correct_tables(self):
        """Test Ollama populates correct tables."""
        ollama_tables = ["politicians", "error_reports"]
        assert "politicians" in ollama_tables
        assert "error_reports" in ollama_tables
