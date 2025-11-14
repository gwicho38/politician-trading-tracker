"""
Test data fixtures for E2E testing

Provides realistic test data for politician trades, signals, and trading operations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from uuid import uuid4

from models import (
    Politician,
    TradingDisclosure,
    TransactionType,
    TradingSignal,
    SignalType,
    SignalStrength,
    PoliticianRole,
)


class TestDataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_nancy_pelosi() -> Politician:
        """Create Nancy Pelosi politician record"""
        return Politician(
            id=str(uuid4()),
            first_name="Nancy",
            last_name="Pelosi",
            full_name="Nancy Pelosi",
            role=PoliticianRole.US_HOUSE_REP.value,
            party="Democrat",
            state_or_country="California",
            district="11",
            bioguide_id="P000197",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @staticmethod
    def create_aapl_sale_disclosure(politician_id: str) -> TradingDisclosure:
        """Create Apple stock sale disclosure"""
        transaction_date = datetime.utcnow() - timedelta(days=15)
        disclosure_date = datetime.utcnow() - timedelta(days=10)

        return TradingDisclosure(
            id=str(uuid4()),
            politician_id=politician_id,
            transaction_date=transaction_date,
            disclosure_date=disclosure_date,
            transaction_type=TransactionType.SALE,
            asset_name="Apple Inc.",
            asset_ticker="AAPL",
            asset_type="stock",
            amount_range_min=Decimal("50000"),
            amount_range_max=Decimal("100000"),
            amount_exact=None,
            source_url="https://disclosures.house.gov/test",
            source_document_id="test_doc_001",
            status="processed",
            raw_data={
                "politician_name": "Nancy Pelosi",
                "transaction_date": transaction_date.isoformat(),
                "asset": "Apple Inc. (AAPL)",
                "type": "Sale",
                "amount": "$50,001 - $100,000",
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @staticmethod
    def create_test_signal(disclosure_ids: List[str]) -> TradingSignal:
        """Create a trading signal based on disclosures"""
        return TradingSignal(
            id=str(uuid4()),
            ticker="AAPL",
            asset_name="Apple Inc.",
            signal_type=SignalType.SELL,
            signal_strength=SignalStrength.STRONG,
            confidence_score=0.75,
            target_price=Decimal("145.50"),
            stop_loss=Decimal("165.00"),
            take_profit=Decimal("135.00"),
            generated_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            model_version="v1.0_test",
            politician_activity_count=1,
            total_transaction_volume=Decimal("75000"),
            buy_sell_ratio=0.0,  # All sales
            avg_politician_return=None,
            features={
                "momentum": -0.05,
                "volume_spike": 1.2,
                "insider_sentiment": -0.8,
                "pelosi_trade": True,
            },
            disclosure_ids=disclosure_ids,
            is_active=True,
            notes="Signal generated from Nancy Pelosi AAPL sale",
        )

    @staticmethod
    def create_test_user_pro_tier() -> Dict[str, Any]:
        """Create test user with Pro tier subscription"""
        return {
            "user_id": str(uuid4()),
            "email": "test_user_pro@example.com",
            "tier": "pro",
            "user_subscribed": True,
            "subscriptions": [
                {
                    "id": "sub_test_123",
                    "status": "active",
                    "metadata": {"tier": "pro"},
                    "current_period_end": (datetime.utcnow() + timedelta(days=30)).timestamp(),
                }
            ],
        }

    @staticmethod
    def create_test_user_free_tier() -> Dict[str, Any]:
        """Create test user with Free tier (no subscription)"""
        return {
            "user_id": str(uuid4()),
            "email": "test_user_free@example.com",
            "tier": "free",
            "user_subscribed": False,
            "subscriptions": [],
        }

    @staticmethod
    def to_disclosure_dict(disclosure: TradingDisclosure) -> Dict[str, Any]:
        """Convert TradingDisclosure to dictionary for database insertion"""
        return {
            "id": disclosure.id,
            "politician_id": disclosure.politician_id,
            "transaction_date": disclosure.transaction_date.isoformat(),
            "disclosure_date": disclosure.disclosure_date.isoformat(),
            "transaction_type": (
                disclosure.transaction_type.value
                if hasattr(disclosure.transaction_type, "value")
                else disclosure.transaction_type
            ),
            "asset_name": disclosure.asset_name,
            "asset_ticker": disclosure.asset_ticker,
            "asset_type": disclosure.asset_type,
            "amount_range_min": (
                float(disclosure.amount_range_min) if disclosure.amount_range_min else None
            ),
            "amount_range_max": (
                float(disclosure.amount_range_max) if disclosure.amount_range_max else None
            ),
            "amount_exact": float(disclosure.amount_exact) if disclosure.amount_exact else None,
            "source_url": disclosure.source_url,
            "source_document_id": disclosure.source_document_id,
            "status": disclosure.status,
            "raw_data": disclosure.raw_data,
            "created_at": disclosure.created_at.isoformat(),
            "updated_at": disclosure.updated_at.isoformat(),
        }

    @staticmethod
    def to_politician_dict(politician: Politician) -> Dict[str, Any]:
        """Convert Politician to dictionary for database insertion"""
        return {
            "id": politician.id,
            "first_name": politician.first_name,
            "last_name": politician.last_name,
            "full_name": politician.full_name,
            "role": politician.role,
            "party": politician.party,
            "state_or_country": politician.state_or_country,
            "district": politician.district,
            "bioguide_id": politician.bioguide_id,
            "created_at": politician.created_at.isoformat(),
            "updated_at": politician.updated_at.isoformat(),
        }

    @staticmethod
    def to_signal_dict(signal: TradingSignal) -> Dict[str, Any]:
        """Convert TradingSignal to dictionary for database insertion"""
        return {
            "id": signal.id,
            "ticker": signal.ticker,
            "asset_name": signal.asset_name,
            "signal_type": (
                signal.signal_type.value
                if hasattr(signal.signal_type, "value")
                else signal.signal_type
            ),
            "signal_strength": (
                signal.signal_strength.value
                if hasattr(signal.signal_strength, "value")
                else signal.signal_strength
            ),
            "confidence_score": float(signal.confidence_score),
            "target_price": float(signal.target_price) if signal.target_price else None,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
            "generated_at": signal.generated_at.isoformat(),
            "valid_until": signal.valid_until.isoformat() if signal.valid_until else None,
            "model_version": signal.model_version,
            "politician_activity_count": signal.politician_activity_count,
            "total_transaction_volume": (
                float(signal.total_transaction_volume) if signal.total_transaction_volume else None
            ),
            "buy_sell_ratio": signal.buy_sell_ratio,
            "avg_politician_return": signal.avg_politician_return,
            "features": signal.features,
            "disclosure_ids": signal.disclosure_ids,
            "is_active": signal.is_active,
            "notes": signal.notes,
        }
