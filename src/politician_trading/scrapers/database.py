"""
Database client and schema management for politician trading data
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from postgrest.exceptions import APIError
from supabase import Client, create_client

from .config import WorkflowConfig
from .models import DataPullJob, DataSource, Politician, TradingDisclosure

logger = logging.getLogger(__name__)


class PoliticianTradingDB:
    """Database client for politician trading data"""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """Initialize Supabase client"""
        try:
            self.client = create_client(self.config.supabase.url, self.config.supabase.key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    async def ensure_schema(self) -> bool:
        """Ensure database schema exists"""
        try:
            # Check if tables exist by trying to query them
            await self._check_table_exists("politicians")
            await self._check_table_exists("trading_disclosures")
            await self._check_table_exists("data_pull_jobs")
            await self._check_table_exists("data_sources")
            logger.info("Database schema verified")
            return True
        except Exception as e:
            logger.error(f"Schema check failed: {e}")
            logger.info("You'll need to create the database schema manually")
            return False

    async def _check_table_exists(self, table_name: str):
        """Check if table exists"""
        try:
            result = self.client.table(table_name).select("*").limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Table {table_name} may not exist: {e}")
            raise

    # Politician management
    async def get_politician(self, politician_id: str) -> Optional[Politician]:
        """Get politician by ID"""
        try:
            result = self.client.table("politicians").select("*").eq("id", politician_id).execute()
            if result.data:
                return self._dict_to_politician(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get politician {politician_id}: {e}")
            return None

    async def find_politician_by_name(
        self, first_name: str, last_name: str
    ) -> Optional[Politician]:
        """Find politician by name"""
        try:
            result = (
                self.client.table("politicians")
                .select("*")
                .eq("first_name", first_name)
                .eq("last_name", last_name)
                .execute()
            )
            if result.data:
                return self._dict_to_politician(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to find politician {first_name} {last_name}: {e}")
            return None

    async def upsert_politician(self, politician: Politician) -> str:
        """Insert or update politician"""
        try:
            # First, try to find an existing politician
            existing = await self.find_politician_by_name(
                politician.first_name, politician.last_name
            )

            if existing:
                # Update existing politician (but don't change ID)
                politician_dict = self._politician_to_dict(politician)
                politician_dict["id"] = existing.id  # Keep existing ID
                politician_dict["updated_at"] = datetime.utcnow().isoformat()

                result = (
                    self.client.table("politicians")
                    .update(politician_dict)
                    .eq("id", existing.id)
                    .execute()
                )

                if result.data:
                    return result.data[0]["id"]
                return existing.id
            else:
                # Insert new politician
                politician_dict = self._politician_to_dict(politician)
                if not politician_dict.get("id"):
                    politician_dict["id"] = str(uuid4())

                politician_dict["created_at"] = datetime.utcnow().isoformat()
                politician_dict["updated_at"] = datetime.utcnow().isoformat()

                result = self.client.table("politicians").insert(politician_dict).execute()

                if result.data:
                    return result.data[0]["id"]
                return politician_dict["id"]

        except Exception as e:
            logger.error(f"Failed to upsert politician: {e}")
            # For debugging: log the politician data that caused the error
            logger.error(f"Politician data: {politician.first_name} {politician.last_name}")
            return ""  # Return empty string instead of raising to prevent cascade failures

    # Trading disclosure management
    async def get_disclosure(self, disclosure_id: str) -> Optional[TradingDisclosure]:
        """Get trading disclosure by ID"""
        try:
            result = (
                self.client.table("trading_disclosures")
                .select("*")
                .eq("id", disclosure_id)
                .execute()
            )
            if result.data:
                return self._dict_to_disclosure(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get disclosure {disclosure_id}: {e}")
            return None

    async def find_disclosure_by_transaction(
        self, politician_id: str, transaction_date: datetime, asset_name: str, transaction_type: str
    ) -> Optional[TradingDisclosure]:
        """Find existing disclosure by transaction details"""
        try:
            result = (
                self.client.table("trading_disclosures")
                .select("*")
                .eq("politician_id", politician_id)
                .eq("transaction_date", transaction_date.isoformat())
                .eq("asset_name", asset_name)
                .eq("transaction_type", transaction_type)
                .execute()
            )
            if result.data:
                return self._dict_to_disclosure(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Failed to find disclosure: {e}")
            return None

    async def insert_disclosure(self, disclosure: TradingDisclosure) -> str:
        """Insert new trading disclosure"""
        try:
            disclosure_dict = self._disclosure_to_dict(disclosure)
            if not disclosure_dict.get("id"):
                disclosure_dict["id"] = str(uuid4())

            result = self.client.table("trading_disclosures").insert(disclosure_dict).execute()
            if result.data:
                return result.data[0]["id"]
            return disclosure_dict["id"]
        except Exception as e:
            logger.error(f"Failed to insert disclosure: {e}")
            raise

    async def update_disclosure(self, disclosure: TradingDisclosure) -> bool:
        """Update existing trading disclosure"""
        try:
            disclosure_dict = self._disclosure_to_dict(disclosure)
            disclosure_dict["updated_at"] = datetime.utcnow().isoformat()

            result = (
                self.client.table("trading_disclosures")
                .update(disclosure_dict)
                .eq("id", disclosure.id)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to update disclosure: {e}")
            return False

    async def get_recent_disclosures(self, limit: int = 100) -> List[TradingDisclosure]:
        """Get recent trading disclosures"""
        try:
            result = (
                self.client.table("trading_disclosures")
                .select("*")
                .order("disclosure_date", desc=True)
                .limit(limit)
                .execute()
            )
            return [self._dict_to_disclosure(d) for d in result.data]
        except Exception as e:
            logger.error(f"Failed to get recent disclosures: {e}")
            return []

    # Data pull job management
    async def create_data_pull_job(self, job_type: str, config_snapshot: Dict[str, Any]) -> str:
        """Create new data pull job"""
        try:
            job = DataPullJob(
                id=str(uuid4()),
                job_type=job_type,
                status="pending",
                config_snapshot=config_snapshot,
                started_at=datetime.utcnow(),
            )

            job_dict = self._job_to_dict(job)
            result = self.client.table("data_pull_jobs").insert(job_dict).execute()
            if result.data:
                return result.data[0]["id"]
            return job.id
        except Exception as e:
            logger.error(f"Failed to create data pull job: {e}")
            raise

    async def update_data_pull_job(self, job: DataPullJob) -> bool:
        """Update data pull job"""
        try:
            job_dict = self._job_to_dict(job)
            result = self.client.table("data_pull_jobs").update(job_dict).eq("id", job.id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to update data pull job: {e}")
            return False

    async def get_job_status(self) -> Dict[str, Any]:
        """Get current job status summary"""
        try:
            # Get recent jobs
            result = (
                self.client.table("data_pull_jobs")
                .select("*")
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )

            jobs = result.data

            # Calculate summary statistics
            total_disclosures = (
                self.client.table("trading_disclosures").select("id", count="exact").execute()
            ).count

            recent_disclosures = (
                self.client.table("trading_disclosures")
                .select("id", count="exact")
                .gte(
                    "created_at",
                    (datetime.utcnow().replace(hour=0, minute=0, second=0)).isoformat(),
                )
                .execute()
            ).count

            return {
                "total_disclosures": total_disclosures,
                "recent_disclosures_today": recent_disclosures,
                "recent_jobs": jobs,
                "last_update": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"error": str(e)}

    # Helper methods for data conversion
    def _politician_to_dict(self, politician: Politician) -> Dict[str, Any]:
        """Convert Politician to dictionary"""
        return {
            "id": politician.id,
            "first_name": politician.first_name,
            "last_name": politician.last_name,
            "full_name": politician.full_name,
            "role": politician.role.value if politician.role else None,
            "party": politician.party,
            "state_or_country": politician.state_or_country,
            "district": politician.district,
            "term_start": politician.term_start.isoformat() if politician.term_start else None,
            "term_end": politician.term_end.isoformat() if politician.term_end else None,
            "bioguide_id": politician.bioguide_id,
            "eu_id": politician.eu_id,
            "created_at": politician.created_at.isoformat(),
            "updated_at": politician.updated_at.isoformat(),
        }

    def _dict_to_politician(self, data: Dict[str, Any]) -> Politician:
        """Convert dictionary to Politician"""
        from .models import PoliticianRole

        return Politician(
            id=data.get("id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            full_name=data.get("full_name", ""),
            role=PoliticianRole(data.get("role", "us_house_representative")),
            party=data.get("party", ""),
            state_or_country=data.get("state_or_country", ""),
            district=data.get("district"),
            term_start=(
                datetime.fromisoformat(data["term_start"]) if data.get("term_start") else None
            ),
            term_end=datetime.fromisoformat(data["term_end"]) if data.get("term_end") else None,
            bioguide_id=data.get("bioguide_id"),
            eu_id=data.get("eu_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def _disclosure_to_dict(self, disclosure: TradingDisclosure) -> Dict[str, Any]:
        """Convert TradingDisclosure to dictionary"""
        return {
            "id": disclosure.id,
            "politician_id": disclosure.politician_id,
            "transaction_date": disclosure.transaction_date.isoformat(),
            "disclosure_date": disclosure.disclosure_date.isoformat(),
            "transaction_type": (
                disclosure.transaction_type.value if disclosure.transaction_type else None
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
            "raw_data": disclosure.raw_data,
            "status": disclosure.status.value if disclosure.status else None,
            "processing_notes": disclosure.processing_notes,
            "created_at": disclosure.created_at.isoformat(),
            "updated_at": disclosure.updated_at.isoformat(),
        }

    def _dict_to_disclosure(self, data: Dict[str, Any]) -> TradingDisclosure:
        """Convert dictionary to TradingDisclosure"""
        from decimal import Decimal

        from .models import DisclosureStatus, TransactionType

        return TradingDisclosure(
            id=data.get("id"),
            politician_id=data.get("politician_id", ""),
            transaction_date=datetime.fromisoformat(data["transaction_date"]),
            disclosure_date=datetime.fromisoformat(data["disclosure_date"]),
            transaction_type=TransactionType(data.get("transaction_type", "purchase")),
            asset_name=data.get("asset_name", ""),
            asset_ticker=data.get("asset_ticker"),
            asset_type=data.get("asset_type", ""),
            amount_range_min=(
                Decimal(str(data["amount_range_min"])) if data.get("amount_range_min") else None
            ),
            amount_range_max=(
                Decimal(str(data["amount_range_max"])) if data.get("amount_range_max") else None
            ),
            amount_exact=Decimal(str(data["amount_exact"])) if data.get("amount_exact") else None,
            source_url=data.get("source_url", ""),
            source_document_id=data.get("source_document_id"),
            raw_data=data.get("raw_data", {}),
            status=DisclosureStatus(data.get("status", "pending")),
            processing_notes=data.get("processing_notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def _job_to_dict(self, job: DataPullJob) -> Dict[str, Any]:
        """Convert DataPullJob to dictionary"""
        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "records_found": job.records_found,
            "records_processed": job.records_processed,
            "records_new": job.records_new,
            "records_updated": job.records_updated,
            "records_failed": job.records_failed,
            "error_message": job.error_message,
            "error_details": job.error_details,
            "config_snapshot": job.config_snapshot,
            "created_at": job.created_at.isoformat(),
        }
