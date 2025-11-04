"""
Ingestion stage - Fetches raw data from sources.
"""

import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .base import (
    PipelineStage,
    PipelineResult,
    PipelineContext,
    PipelineMetrics,
    PipelineStatus,
    RawDisclosure
)
from ..storage import StorageManager

logger = logging.getLogger(__name__)


class IngestionStage(PipelineStage[RawDisclosure]):
    """
    Ingestion stage - Responsible for fetching raw data from sources.

    This stage:
    1. Connects to data sources
    2. Fetches raw disclosure data
    3. Minimal processing (just ensure we have valid raw data)
    4. Returns RawDisclosure objects
    """

    def __init__(self, lookback_days: int = 30, max_retries: int = 3, enable_storage: bool = True):
        super().__init__("ingestion")
        self.lookback_days = lookback_days
        self.max_retries = max_retries
        self.enable_storage = enable_storage

    async def process(
        self,
        data: List[any],  # Typically empty for ingestion stage
        context: PipelineContext
    ) -> PipelineResult[RawDisclosure]:
        """
        Fetch raw data from the source.

        Args:
            data: Not used in ingestion (we fetch from source)
            context: Pipeline context with source information

        Returns:
            PipelineResult containing RawDisclosure objects
        """
        start_time = datetime.utcnow()
        metrics = PipelineMetrics()
        raw_disclosures: List[RawDisclosure] = []

        try:
            self.logger.info(
                f"Starting ingestion for source: {context.source_name} "
                f"(type: {context.source_type})"
            )

            # Get the source-specific scraper
            from ..sources import get_source
            source = get_source(context.source_type)

            if source is None:
                raise ValueError(f"Unknown source type: {context.source_type}")

            # Configure source
            source.configure(context.config)

            # Attach storage manager if enabled and db_client available
            if self.enable_storage and hasattr(context, 'db_client') and context.db_client:
                storage_manager = StorageManager(context.db_client)
                if hasattr(source, 'storage_manager'):
                    source.storage_manager = storage_manager
                    self.logger.info("Storage manager attached to source for raw data archival")
            else:
                self.logger.debug("Storage disabled or db_client not available")

            # Fetch data from source
            self.logger.info(f"Fetching data with {self.lookback_days} day lookback")
            # Pass config as kwargs to source (e.g., api_key for QuiverQuant)
            raw_data = await source.fetch(lookback_days=self.lookback_days, **context.config)

            self.logger.info(f"Fetched {len(raw_data)} raw records from {context.source_name}")
            metrics.records_input = len(raw_data)

            # Convert to RawDisclosure objects
            for item in raw_data:
                try:
                    disclosure = RawDisclosure(
                        source=context.source_name,
                        source_type=context.source_type,
                        raw_data=item,
                        source_url=item.get("source_url"),
                        source_document_id=item.get("document_id")
                    )
                    raw_disclosures.append(disclosure)
                    metrics.records_output += 1

                except Exception as e:
                    self.logger.warning(
                        f"Failed to create RawDisclosure from item: {e}",
                        exc_info=True
                    )
                    metrics.records_failed += 1
                    metrics.errors.append(f"Item conversion failed: {str(e)}")

            # Calculate metrics
            metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            # Determine status
            if metrics.records_output > 0:
                if metrics.records_failed == 0:
                    status = PipelineStatus.SUCCESS
                else:
                    status = PipelineStatus.PARTIAL_SUCCESS
            else:
                status = PipelineStatus.FAILED
                metrics.errors.append("No records successfully ingested")

            self.logger.info(
                f"Ingestion complete: {metrics.records_output} records, "
                f"{metrics.records_failed} failed, "
                f"{metrics.duration_seconds:.2f}s"
            )

            return self._create_result(
                status=status,
                data=raw_disclosures,
                context=context,
                metrics=metrics
            )

        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            metrics.errors.append(f"Ingestion error: {str(e)}")

            result = self._create_result(
                status=PipelineStatus.FAILED,
                data=[],
                context=context,
                metrics=metrics
            )
            result.errors.append(e)
            return result


class BatchIngestionStage(IngestionStage):
    """
    Batch ingestion stage - Ingests data in batches with rate limiting.

    Useful for sources with rate limits or large datasets.
    """

    def __init__(
        self,
        lookback_days: int = 30,
        max_retries: int = 3,
        batch_size: int = 100,
        delay_between_batches: float = 1.0
    ):
        super().__init__(lookback_days, max_retries)
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches

    async def process(
        self,
        data: List[any],
        context: PipelineContext
    ) -> PipelineResult[RawDisclosure]:
        """
        Fetch raw data in batches with rate limiting.
        """
        start_time = datetime.utcnow()
        metrics = PipelineMetrics()
        raw_disclosures: List[RawDisclosure] = []

        try:
            self.logger.info(
                f"Starting batch ingestion for source: {context.source_name} "
                f"(batch_size={self.batch_size}, delay={self.delay_between_batches}s)"
            )

            # Get the source-specific scraper
            from ..sources import get_source
            source = get_source(context.source_type)

            if source is None:
                raise ValueError(f"Unknown source type: {context.source_type}")

            source.configure(context.config)

            # Fetch data in batches
            batch_num = 0
            total_fetched = 0

            while True:
                offset = batch_num * self.batch_size

                self.logger.info(f"Fetching batch {batch_num + 1} (offset={offset})")

                batch_data = await source.fetch_batch(
                    offset=offset,
                    limit=self.batch_size,
                    lookback_days=self.lookback_days
                )

                if not batch_data:
                    self.logger.info(f"No more data to fetch (batch {batch_num + 1})")
                    break

                total_fetched += len(batch_data)
                self.logger.info(f"Fetched {len(batch_data)} records in batch {batch_num + 1}")

                # Convert batch to RawDisclosure objects
                for item in batch_data:
                    try:
                        disclosure = RawDisclosure(
                            source=context.source_name,
                            source_type=context.source_type,
                            raw_data=item,
                            source_url=item.get("source_url"),
                            source_document_id=item.get("document_id")
                        )
                        raw_disclosures.append(disclosure)
                        metrics.records_output += 1

                    except Exception as e:
                        self.logger.warning(f"Failed to create RawDisclosure: {e}")
                        metrics.records_failed += 1
                        metrics.errors.append(f"Item conversion failed: {str(e)}")

                batch_num += 1

                # Rate limiting delay
                if self.delay_between_batches > 0:
                    await asyncio.sleep(self.delay_between_batches)

            metrics.records_input = total_fetched
            metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            # Determine status
            if metrics.records_output > 0:
                if metrics.records_failed == 0:
                    status = PipelineStatus.SUCCESS
                else:
                    status = PipelineStatus.PARTIAL_SUCCESS
            else:
                status = PipelineStatus.FAILED
                metrics.errors.append("No records successfully ingested")

            self.logger.info(
                f"Batch ingestion complete: {metrics.records_output} records from {batch_num} batches, "
                f"{metrics.records_failed} failed, "
                f"{metrics.duration_seconds:.2f}s"
            )

            return self._create_result(
                status=status,
                data=raw_disclosures,
                context=context,
                metrics=metrics
            )

        except Exception as e:
            self.logger.error(f"Batch ingestion failed: {e}", exc_info=True)
            metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            metrics.errors.append(f"Batch ingestion error: {str(e)}")

            result = self._create_result(
                status=PipelineStatus.FAILED,
                data=[],
                context=context,
                metrics=metrics
            )
            result.errors.append(e)
            return result
