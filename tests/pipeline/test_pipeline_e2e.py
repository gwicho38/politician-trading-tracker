"""
End-to-end pipeline tests.

These tests verify that the full pipeline works from ingestion to publishing.
"""

import pytest
from datetime import datetime


# Test that imports work
def test_pipeline_imports():
    """Test that all pipeline modules can be imported"""
    from politician_trading.pipeline import (
        PipelineStage,
        PipelineResult,
        IngestionStage,
        PipelineOrchestrator,
    )

    assert PipelineStage is not None
    assert PipelineResult is not None
    assert IngestionStage is not None
    assert PipelineOrchestrator is not None


def test_source_imports():
    """Test that source modules can be imported"""
    from politician_trading.sources import BaseSource, get_source

    assert BaseSource is not None
    assert get_source is not None


def test_transformer_imports():
    """Test that transformer modules can be imported"""
    from politician_trading.transformers import TickerExtractor, AmountParser, PoliticianMatcher

    assert TickerExtractor is not None
    assert AmountParser is not None
    assert PoliticianMatcher is not None


def test_get_source_factory():
    """Test source factory function"""
    from politician_trading.sources import get_source

    # Test known sources
    us_house = get_source("us_house")
    us_senate = get_source("us_senate")
    quiverquant = get_source("quiverquant")

    assert us_house is not None
    assert us_senate is not None
    assert quiverquant is not None

    # Test unknown source
    unknown = get_source("nonexistent")
    assert unknown is None


def test_ticker_extractor():
    """Test ticker extraction"""
    from politician_trading.transformers import TickerExtractor

    extractor = TickerExtractor()

    # Test various formats
    assert extractor.extract("Apple Inc. (AAPL)") == "AAPL"
    assert extractor.extract("MSFT - Microsoft Corporation") == "MSFT"
    assert extractor.extract("Tesla Motors Inc (TSLA)") == "TSLA"
    assert extractor.extract("GOOGL") == "GOOGL"
    assert extractor.extract("No ticker here") is None


def test_amount_parser():
    """Test amount parsing"""
    from politician_trading.transformers import AmountParser

    parser = AmountParser()

    # Test range
    min_val, max_val, exact = parser.parse("$1,001 - $15,000")
    assert min_val == 1001
    assert max_val == 15000
    assert exact is None

    # Test exact amount
    min_val, max_val, exact = parser.parse("$25,000")
    assert exact == 25000
    assert min_val is None
    assert max_val is None

    # Test over pattern
    min_val, max_val, exact = parser.parse("Over $50,000,000")
    assert min_val == 50000001
    assert max_val is None


@pytest.mark.asyncio
async def test_pipeline_context():
    """Test pipeline context creation"""
    from politician_trading.pipeline import PipelineContext

    context = PipelineContext(source_name="Test Source", source_type="test", job_id="test_job_123")

    assert context.source_name == "Test Source"
    assert context.source_type == "test"
    assert context.job_id == "test_job_123"
    assert isinstance(context.started_at, datetime)


@pytest.mark.asyncio
async def test_cleaning_stage_basic():
    """Test cleaning stage with sample data"""
    from politician_trading.pipeline import CleaningStage, PipelineContext
    from politician_trading.pipeline.base import RawDisclosure

    stage = CleaningStage(remove_duplicates=True)
    context = PipelineContext(source_name="Test", source_type="test")

    # Create sample raw disclosures
    raw_data = [
        RawDisclosure(
            source="test",
            source_type="test",
            raw_data={
                "politician_name": "John Doe",
                "transaction_date": "2025-01-15",
                "disclosure_date": "2025-01-20",
                "asset_name": "Apple Inc.",
                "transaction_type": "purchase",
            },
        ),
        # Duplicate
        RawDisclosure(
            source="test",
            source_type="test",
            raw_data={
                "politician_name": "John Doe",
                "transaction_date": "2025-01-15",
                "disclosure_date": "2025-01-20",
                "asset_name": "Apple Inc.",
                "transaction_type": "purchase",
            },
        ),
        # Different disclosure
        RawDisclosure(
            source="test",
            source_type="test",
            raw_data={
                "politician_name": "Jane Smith",
                "transaction_date": "2025-01-16",
                "disclosure_date": "2025-01-21",
                "asset_name": "Microsoft Corp",
                "transaction_type": "sale",
            },
        ),
    ]

    result = await stage.process(raw_data, context)

    assert result.success
    assert result.metrics.records_input == 3
    assert result.metrics.records_output == 2  # One duplicate removed
    assert result.metrics.records_skipped == 1
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_normalization_stage_basic():
    """Test normalization stage with sample data"""
    from politician_trading.pipeline import NormalizationStage, PipelineContext
    from politician_trading.pipeline.base import CleanedDisclosure
    from datetime import datetime

    stage = NormalizationStage()
    context = PipelineContext(source_name="Test", source_type="test")

    # Create sample cleaned disclosures
    cleaned_data = [
        CleanedDisclosure(
            source="test",
            politician_name="Sen. John Doe",
            transaction_date=datetime(2025, 1, 15),
            disclosure_date=datetime(2025, 1, 20),
            asset_name="Apple Inc. (AAPL)",
            transaction_type="purchase",
            amount_text="$15,001 - $50,000",
            raw_data={},
        )
    ]

    result = await stage.process(cleaned_data, context)

    assert result.success
    assert len(result.data) == 1

    normalized = result.data[0]
    assert normalized.politician_first_name == "John"
    assert normalized.politician_last_name == "Doe"
    assert normalized.asset_ticker == "AAPL"
    assert normalized.amount_range_min == 15001
    assert normalized.amount_range_max == 50000


def test_pipeline_result_status():
    """Test pipeline result status checks"""
    from politician_trading.pipeline.base import (
        PipelineResult,
        PipelineStatus,
        PipelineMetrics,
        PipelineContext,
    )

    context = PipelineContext(source_name="Test", source_type="test")
    metrics = PipelineMetrics()

    # Success result
    result = PipelineResult(
        status=PipelineStatus.SUCCESS, data=[], context=context, metrics=metrics, stage_name="test"
    )

    assert result.success
    assert not result.failed

    # Failed result
    result = PipelineResult(
        status=PipelineStatus.FAILED, data=[], context=context, metrics=metrics, stage_name="test"
    )

    assert not result.success
    assert result.failed


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
