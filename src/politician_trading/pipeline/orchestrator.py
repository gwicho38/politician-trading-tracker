"""
Pipeline orchestrator - Coordinates execution of all pipeline stages.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from .base import PipelineContext, PipelineResult, PipelineStatus
from .ingest import IngestionStage, BatchIngestionStage
from .clean import CleaningStage
from .normalize import NormalizationStage
from .publish import PublishingStage

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the full ingestion pipeline.

    Pipeline flow:
    1. Ingest - Fetch raw data from source
    2. Clean - Validate and clean data
    3. Normalize - Transform to standard format
    4. Publish - Store in database

    Each stage can fail independently, and the pipeline tracks
    metrics and errors across all stages.
    """

    def __init__(
        self,
        lookback_days: int = 30,
        batch_ingestion: bool = False,
        batch_size: int = 100,
        strict_cleaning: bool = False,
        skip_duplicates: bool = True,
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            lookback_days: How many days back to fetch data
            batch_ingestion: Use batch ingestion (for rate-limited sources)
            batch_size: Batch size for ingestion and publishing
            strict_cleaning: Strict validation in cleaning stage
            skip_duplicates: Skip duplicate disclosures in publishing
        """
        self.lookback_days = lookback_days
        self.batch_size = batch_size

        # Initialize pipeline stages
        if batch_ingestion:
            self.ingest_stage = BatchIngestionStage(
                lookback_days=lookback_days, batch_size=batch_size, delay_between_batches=1.0
            )
        else:
            self.ingest_stage = IngestionStage(lookback_days=lookback_days)

        self.clean_stage = CleaningStage(remove_duplicates=True, strict_validation=strict_cleaning)

        self.normalize_stage = NormalizationStage(auto_create_politicians=True)

        self.publish_stage = PublishingStage(
            batch_size=batch_size, skip_duplicates=skip_duplicates, update_existing=True
        )

        self.logger = logging.getLogger(__name__)

    async def run(
        self,
        source_name: str,
        source_type: str,
        config: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        db_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline for a single source.

        Args:
            source_name: Name of the source (e.g., "US House")
            source_type: Type of source (e.g., "us_house")
            config: Source-specific configuration
            job_id: Optional job ID for tracking
            db_client: Optional Supabase client for storage operations

        Returns:
            Dictionary with pipeline results and metrics
        """
        start_time = datetime.utcnow()

        self.logger.info(f"Starting pipeline for {source_name} ({source_type})")

        # Create pipeline context
        context = PipelineContext(
            source_name=source_name,
            source_type=source_type,
            job_id=job_id,
            config=config or {},
            started_at=start_time,
            db_client=db_client,  # Pass db_client for storage operations
        )

        # Track results from each stage
        results = {
            "source_name": source_name,
            "source_type": source_type,
            "job_id": job_id,
            "started_at": start_time.isoformat(),
            "stages": {},
            "overall_status": PipelineStatus.PENDING.value,
            "overall_metrics": {},
            "errors": [],
        }

        try:
            # Stage 1: Ingestion
            self.logger.info("Stage 1/4: Ingestion")
            ingest_result = await self.ingest_stage.process([], context)
            results["stages"]["ingestion"] = self._result_to_dict(ingest_result)

            if ingest_result.failed:
                self.logger.error("Ingestion failed, aborting pipeline")
                results["overall_status"] = PipelineStatus.FAILED.value
                results["errors"].extend([str(e) for e in ingest_result.errors])
                return self._finalize_results(results, start_time)

            self.logger.info(f"Ingestion complete: {ingest_result.metrics.records_output} records")

            # Stage 2: Cleaning
            self.logger.info("Stage 2/4: Cleaning")
            clean_result = await self.clean_stage.process(ingest_result.data, context)
            results["stages"]["cleaning"] = self._result_to_dict(clean_result)

            if clean_result.failed:
                self.logger.error("Cleaning failed, aborting pipeline")
                results["overall_status"] = PipelineStatus.FAILED.value
                results["errors"].extend([str(e) for e in clean_result.errors])
                return self._finalize_results(results, start_time)

            self.logger.info(f"Cleaning complete: {clean_result.metrics.records_output} records")

            # Stage 3: Normalization
            self.logger.info("Stage 3/4: Normalization")
            normalize_result = await self.normalize_stage.process(clean_result.data, context)
            results["stages"]["normalization"] = self._result_to_dict(normalize_result)

            if normalize_result.failed:
                self.logger.error("Normalization failed, aborting pipeline")
                results["overall_status"] = PipelineStatus.FAILED.value
                results["errors"].extend([str(e) for e in normalize_result.errors])
                return self._finalize_results(results, start_time)

            self.logger.info(
                f"Normalization complete: {normalize_result.metrics.records_output} records"
            )

            # Stage 4: Publishing
            self.logger.info("Stage 4/4: Publishing")
            publish_result = await self.publish_stage.process(normalize_result.data, context)
            results["stages"]["publishing"] = self._result_to_dict(publish_result)

            if publish_result.failed:
                self.logger.warning("Publishing had failures")
                results["overall_status"] = PipelineStatus.PARTIAL_SUCCESS.value
                results["errors"].extend([str(e) for e in publish_result.errors])
            else:
                results["overall_status"] = PipelineStatus.SUCCESS.value

            self.logger.info(
                f"Publishing complete: {publish_result.metrics.records_output} records"
            )

            # Extract summary from publish results
            if publish_result.data and len(publish_result.data) > 0:
                summary = publish_result.data[0].get("summary", {})
                results["summary"] = summary

        except Exception as e:
            self.logger.error(f"Pipeline failed with exception: {e}", exc_info=True)
            results["overall_status"] = PipelineStatus.FAILED.value
            results["errors"].append(f"Pipeline exception: {str(e)}")

        return self._finalize_results(results, start_time)

    def _result_to_dict(self, result: PipelineResult) -> Dict[str, Any]:
        """Convert PipelineResult to dictionary"""
        return {
            "status": result.status.value,
            "stage_name": result.stage_name,
            "metrics": {
                "records_input": result.metrics.records_input,
                "records_output": result.metrics.records_output,
                "records_skipped": result.metrics.records_skipped,
                "records_failed": result.metrics.records_failed,
                "duration_seconds": result.metrics.duration_seconds,
                "success_rate": result.metrics.success_rate(),
                "errors_count": len(result.metrics.errors),
                "warnings_count": len(result.metrics.warnings),
            },
            "errors": result.metrics.errors[:10],  # Limit error list
            "warnings": result.metrics.warnings[:10],  # Limit warning list
        }

    def _finalize_results(self, results: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """Calculate overall metrics and finalize results"""
        duration = (datetime.utcnow() - start_time).total_seconds()
        results["completed_at"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = duration

        # Calculate overall metrics
        total_input = 0
        total_output = 0
        total_failed = 0
        total_skipped = 0

        for stage_name, stage_result in results["stages"].items():
            metrics = stage_result.get("metrics", {})
            total_input = max(total_input, metrics.get("records_input", 0))
            total_output = metrics.get("records_output", 0)  # Use last stage output
            total_failed += metrics.get("records_failed", 0)
            total_skipped += metrics.get("records_skipped", 0)

        results["overall_metrics"] = {
            "records_input": total_input,
            "records_output": total_output,
            "records_failed": total_failed,
            "records_skipped": total_skipped,
            "success_rate": (total_output / total_input * 100) if total_input > 0 else 0,
            "duration_seconds": duration,
        }

        self.logger.info(
            f"Pipeline complete for {results['source_name']}: "
            f"Status={results['overall_status']}, "
            f"Output={total_output}/{total_input}, "
            f"Duration={duration:.2f}s"
        )

        return results


async def run_pipeline_for_source(
    source_name: str,
    source_type: str,
    config: Optional[Dict[str, Any]] = None,
    **orchestrator_kwargs,
) -> Dict[str, Any]:
    """
    Convenience function to run pipeline for a single source.

    Args:
        source_name: Name of the source
        source_type: Type of source
        config: Source configuration
        **orchestrator_kwargs: Additional arguments for PipelineOrchestrator

    Returns:
        Pipeline results dictionary
    """
    orchestrator = PipelineOrchestrator(**orchestrator_kwargs)
    return await orchestrator.run(source_name, source_type, config)
