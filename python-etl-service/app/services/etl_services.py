"""
ETL Service Implementations

Wrapper services that extend BaseETLService and delegate to existing
ETL functions. This provides the registry pattern while maintaining
backward compatibility with the existing well-tested code.

Usage:
    from app.lib import ETLRegistry

    # Get registered service
    service = ETLRegistry.create_instance("house")
    result = await service.run(job_id="...", year=2025)

    # Or list all sources
    sources = ETLRegistry.list_sources()  # ["house", "senate"]
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.lib.base_etl import BaseETLService, ETLResult
from app.lib.registry import ETLRegistry


@ETLRegistry.register
class HouseETLService(BaseETLService):
    """
    US House of Representatives financial disclosure ETL service.

    Wraps the existing run_house_etl function to provide the
    BaseETLService interface while maintaining backward compatibility.
    """

    source_id = "house"
    source_name = "US House of Representatives"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch disclosures from House disclosure index.

        Note: The actual fetching is handled by run_house_etl internally.
        This method returns an empty list as the existing implementation
        handles the full pipeline.
        """
        # The existing run_house_etl handles fetching internally
        # This is a pass-through for the interface
        return []

    async def parse_disclosure(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single disclosure.

        Note: The existing implementation handles parsing internally.
        """
        # The existing run_house_etl handles parsing internally
        return raw

    async def run(
        self,
        job_id: str,
        year: int = 2025,
        limit: Optional[int] = None,
        update_mode: bool = False,
        **kwargs,
    ) -> ETLResult:
        """
        Run the House ETL pipeline.

        Delegates to the existing run_house_etl function while providing
        standardized result tracking.

        Args:
            job_id: Unique job identifier
            year: Year to process (default: 2025)
            limit: Optional limit on PDFs to process
            update_mode: If True, upsert instead of insert
        """
        result = ETLResult(started_at=datetime.now(timezone.utc))

        try:
            # Import here to avoid circular imports
            from app.services.house_etl import run_house_etl, JOB_STATUS

            # Run the existing ETL function
            await run_house_etl(
                job_id=job_id,
                year=year,
                limit=limit,
                update_mode=update_mode,
            )

            # Extract results from job status
            status = JOB_STATUS.get(job_id, {})
            result.completed_at = datetime.now(timezone.utc)

            # Parse message for counts (e.g., "Completed: 50 transactions from 10 PDFs")
            message = status.get("message", "")
            if "transactions" in message.lower():
                try:
                    # Extract transaction count from message
                    import re
                    match = re.search(r"(\d+)\s+transactions", message)
                    if match:
                        result.records_inserted = int(match.group(1))
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Failed to parse transaction count from message '{message}': {e}")

            result.records_processed = status.get("total", 0)

            if status.get("status") == "failed":
                result.add_error(status.get("message", "Unknown error"))

            result.metadata = {
                "year": year,
                "source_status": status,
                "rate_limiter_stats": status.get("rate_limiter_stats"),
            }

        except Exception as e:
            result.add_error(str(e))
            result.completed_at = datetime.now(timezone.utc)
            self.logger.exception(f"House ETL failed: {e}")

        return result


@ETLRegistry.register
class SenateETLService(BaseETLService):
    """
    US Senate financial disclosure ETL service.

    Wraps the existing run_senate_etl function to provide the
    BaseETLService interface while maintaining backward compatibility.
    """

    source_id = "senate"
    source_name = "US Senate"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch disclosures from Senate EFD database.

        Note: The actual fetching is handled by run_senate_etl internally.
        """
        return []

    async def parse_disclosure(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single disclosure.

        Note: The existing implementation handles parsing internally.
        """
        return raw

    async def run(
        self,
        job_id: str,
        lookback_days: int = 30,
        limit: Optional[int] = None,
        update_mode: bool = False,
        **kwargs,
    ) -> ETLResult:
        """
        Run the Senate ETL pipeline.

        Delegates to the existing run_senate_etl function while providing
        standardized result tracking.

        Args:
            job_id: Unique job identifier
            lookback_days: How many days back to search (default: 30)
            limit: Optional limit on records to process
            update_mode: If True, upsert instead of insert
        """
        result = ETLResult(started_at=datetime.now(timezone.utc))

        try:
            # Import here to avoid circular imports
            from app.services.senate_etl import run_senate_etl
            from app.services.house_etl import JOB_STATUS  # Shared status dict

            # Run the existing ETL function
            await run_senate_etl(
                job_id=job_id,
                lookback_days=lookback_days,
                limit=limit,
                update_mode=update_mode,
            )

            # Extract results from job status
            status = JOB_STATUS.get(job_id, {})
            result.completed_at = datetime.now(timezone.utc)

            # Parse message for counts
            message = status.get("message", "")
            if "transactions" in message.lower():
                try:
                    import re
                    match = re.search(r"(\d+)\s+transactions", message)
                    if match:
                        result.records_inserted = int(match.group(1))
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Failed to parse transaction count from message '{message}': {e}")

            result.records_processed = status.get("total", 0)

            if status.get("status") == "failed":
                result.add_error(status.get("message", "Unknown error"))

            result.metadata = {
                "lookback_days": lookback_days,
                "source_status": status,
            }

        except Exception as e:
            result.add_error(str(e))
            result.completed_at = datetime.now(timezone.utc)
            self.logger.exception(f"Senate ETL failed: {e}")

        return result


# Register any additional ETL services here
# Example for future services:
#
# @ETLRegistry.register
# class QuiverQuantETLService(BaseETLService):
#     source_id = "quiverquant"
#     source_name = "QuiverQuant"
#     ...


def init_services():
    """
    Initialize and register all ETL services.

    This function is called on module import to ensure all services
    are registered with the ETLRegistry.
    """
    # Services are auto-registered via @ETLRegistry.register decorator
    # This function can be used for any additional initialization
    pass


# Auto-initialize on import
init_services()
