"""
Publishing stage - Stores normalized data in the database.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .base import (
    PipelineStage,
    PipelineResult,
    PipelineContext,
    PipelineMetrics,
    PipelineStatus,
    NormalizedDisclosure
)

logger = logging.getLogger(__name__)


class PublishingStage(PipelineStage[Dict[str, Any]]):
    """
    Publishing stage - Stores normalized disclosures in the database.

    This stage:
    1. Checks for duplicate disclosures
    2. Creates new politician records if needed
    3. Inserts or updates disclosure records
    4. Handles database errors gracefully
    5. Returns metadata about published records
    """

    def __init__(
        self,
        batch_size: int = 100,
        skip_duplicates: bool = True,
        update_existing: bool = True
    ):
        super().__init__("publishing")
        self.batch_size = batch_size
        self.skip_duplicates = skip_duplicates
        self.update_existing = update_existing

    async def process(
        self,
        data: List[NormalizedDisclosure],
        context: PipelineContext
    ) -> PipelineResult[Dict[str, Any]]:
        """
        Publish normalized disclosures to database.

        Args:
            data: List of NormalizedDisclosure objects from normalization stage
            context: Pipeline context

        Returns:
            PipelineResult containing metadata about published records
        """
        start_time = datetime.utcnow()
        metrics = PipelineMetrics()
        published_records: List[Dict[str, Any]] = []

        metrics.records_input = len(data)
        self.logger.info(f"Starting publishing of {len(data)} normalized disclosures")

        # Get database client
        from ..database.database import SupabaseClient
        from ..config import SupabaseConfig

        try:
            db_config = SupabaseConfig.from_env()
            db = SupabaseClient(db_config)

            # Track statistics
            stats = {
                'politicians_created': 0,
                'politicians_matched': 0,
                'disclosures_inserted': 0,
                'disclosures_updated': 0,
                'disclosures_skipped': 0,
                'errors': []
            }

            # Process in batches
            for batch_start in range(0, len(data), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(data))
                batch = data[batch_start:batch_end]

                self.logger.info(
                    f"Processing batch {batch_start // self.batch_size + 1}: "
                    f"records {batch_start}-{batch_end}"
                )

                for i, disclosure in enumerate(batch):
                    record_num = batch_start + i

                    try:
                        # Handle politician - create or match existing
                        politician_id = await self._ensure_politician(
                            db, disclosure, stats
                        )

                        if not politician_id:
                            self.logger.warning(
                                f"Record {record_num}: Could not find or create politician"
                            )
                            metrics.records_failed += 1
                            stats['errors'].append(
                                f"Record {record_num}: Politician creation/matching failed"
                            )
                            continue

                        # Check for existing disclosure
                        existing = await self._find_existing_disclosure(
                            db, disclosure, politician_id
                        )

                        if existing:
                            if self.skip_duplicates and not self.update_existing:
                                self.logger.debug(
                                    f"Record {record_num}: Duplicate found, skipping"
                                )
                                metrics.records_skipped += 1
                                stats['disclosures_skipped'] += 1
                                continue

                            if self.update_existing:
                                # Update existing record
                                updated = await self._update_disclosure(
                                    db, existing['id'], disclosure
                                )
                                if updated:
                                    self.logger.info(
                                        f"Record {record_num}: Updated disclosure {existing['id']}"
                                    )
                                    metrics.records_output += 1
                                    stats['disclosures_updated'] += 1
                                    published_records.append({
                                        'action': 'updated',
                                        'disclosure_id': existing['id'],
                                        'politician_id': politician_id
                                    })
                                else:
                                    metrics.records_failed += 1
                                    stats['errors'].append(
                                        f"Record {record_num}: Update failed"
                                    )
                        else:
                            # Insert new disclosure
                            disclosure_id = await self._insert_disclosure(
                                db, disclosure, politician_id
                            )

                            if disclosure_id:
                                self.logger.info(
                                    f"Record {record_num}: Inserted new disclosure {disclosure_id}"
                                )
                                metrics.records_output += 1
                                stats['disclosures_inserted'] += 1
                                published_records.append({
                                    'action': 'inserted',
                                    'disclosure_id': disclosure_id,
                                    'politician_id': politician_id
                                })
                            else:
                                metrics.records_failed += 1
                                stats['errors'].append(
                                    f"Record {record_num}: Insert failed"
                                )

                    except Exception as e:
                        self.logger.error(
                            f"Error publishing record {record_num}: {e}",
                            exc_info=True
                        )
                        metrics.records_failed += 1
                        stats['errors'].append(f"Record {record_num}: {str(e)}")

            # Calculate metrics
            metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            metrics.errors.extend(stats['errors'])

            # Add summary to published records
            published_records.insert(0, {
                'summary': stats,
                'total_processed': metrics.records_output + metrics.records_skipped + metrics.records_failed
            })

            # Determine status
            if metrics.records_output > 0 or metrics.records_skipped > 0:
                if metrics.records_failed == 0:
                    status = PipelineStatus.SUCCESS
                else:
                    status = PipelineStatus.PARTIAL_SUCCESS
            else:
                status = PipelineStatus.FAILED
                metrics.errors.append("No records successfully published")

            self.logger.info(
                f"Publishing complete: {metrics.records_output} published "
                f"({stats['disclosures_inserted']} new, {stats['disclosures_updated']} updated), "
                f"{metrics.records_skipped} skipped, "
                f"{metrics.records_failed} failed, "
                f"{metrics.duration_seconds:.2f}s"
            )

            return self._create_result(
                status=status,
                data=published_records,
                context=context,
                metrics=metrics
            )

        except Exception as e:
            self.logger.error(f"Publishing failed: {e}", exc_info=True)
            metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            metrics.errors.append(f"Publishing error: {str(e)}")

            result = self._create_result(
                status=PipelineStatus.FAILED,
                data=[],
                context=context,
                metrics=metrics
            )
            result.errors.append(e)
            return result

    async def _ensure_politician(
        self,
        db,
        disclosure: NormalizedDisclosure,
        stats: Dict[str, int]
    ) -> Optional[str]:
        """
        Ensure politician exists in database.

        Returns politician_id if found/created, None otherwise.
        """
        # If we already have a politician_id, use it
        if disclosure.politician_id:
            stats['politicians_matched'] += 1
            return disclosure.politician_id

        # Try to find existing politician
        from models import Politician

        existing = db.find_politician_by_name(
            first_name=disclosure.politician_first_name,
            last_name=disclosure.politician_last_name,
            role=disclosure.politician_role
        )

        if existing:
            stats['politicians_matched'] += 1
            return existing.id

        # Create new politician
        try:
            new_politician = Politician(
                first_name=disclosure.politician_first_name,
                last_name=disclosure.politician_last_name,
                full_name=disclosure.politician_full_name,
                role=disclosure.politician_role,
                party=disclosure.politician_party,
                state_or_country=disclosure.politician_state,
                source=disclosure.source
            )

            created = db.upsert_politician(new_politician)
            if created:
                stats['politicians_created'] += 1
                return created.id

        except Exception as e:
            self.logger.error(f"Error creating politician: {e}", exc_info=True)

        return None

    async def _find_existing_disclosure(
        self,
        db,
        disclosure: NormalizedDisclosure,
        politician_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find existing disclosure by unique key"""
        try:
            # Look for exact match on key fields
            response = db.client.table("trading_disclosures").select("*").match({
                "politician_id": politician_id,
                "transaction_date": disclosure.transaction_date.isoformat(),
                "asset_name": disclosure.asset_name,
                "transaction_type": disclosure.transaction_type
            }).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

        except Exception as e:
            self.logger.debug(f"Error finding existing disclosure: {e}")

        return None

    async def _insert_disclosure(
        self,
        db,
        disclosure: NormalizedDisclosure,
        politician_id: str
    ) -> Optional[str]:
        """Insert new disclosure record"""
        try:
            data = {
                "politician_id": politician_id,
                "transaction_date": disclosure.transaction_date.isoformat(),
                "disclosure_date": disclosure.disclosure_date.isoformat(),
                "transaction_type": disclosure.transaction_type,
                "asset_name": disclosure.asset_name,
                "asset_ticker": disclosure.asset_ticker,
                "asset_type": disclosure.asset_type,
                "amount_range_min": disclosure.amount_range_min,
                "amount_range_max": disclosure.amount_range_max,
                "amount_exact": disclosure.amount_exact,
                "source": disclosure.source,
                "source_url": disclosure.source_url,
                "source_document_id": disclosure.source_document_id,
                "raw_data": disclosure.raw_data,
                "status": "active"
            }

            response = db.client.table("trading_disclosures").insert(data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]['id']

        except Exception as e:
            self.logger.error(f"Error inserting disclosure: {e}", exc_info=True)

        return None

    async def _update_disclosure(
        self,
        db,
        disclosure_id: str,
        disclosure: NormalizedDisclosure
    ) -> bool:
        """Update existing disclosure record"""
        try:
            data = {
                "asset_ticker": disclosure.asset_ticker,
                "asset_type": disclosure.asset_type,
                "amount_range_min": disclosure.amount_range_min,
                "amount_range_max": disclosure.amount_range_max,
                "amount_exact": disclosure.amount_exact,
                "source_url": disclosure.source_url,
                "raw_data": disclosure.raw_data,
                "updated_at": datetime.utcnow().isoformat()
            }

            response = db.client.table("trading_disclosures")\
                .update(data)\
                .eq("id", disclosure_id)\
                .execute()

            return response.data and len(response.data) > 0

        except Exception as e:
            self.logger.error(f"Error updating disclosure: {e}", exc_info=True)

        return False
