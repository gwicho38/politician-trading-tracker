#!/usr/bin/env python3
"""
Scheduled Data Collection Script
Automatically collects politician trading disclosures from all enabled sources.
Designed to be run via cron for regular updates.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables
load_dotenv(project_root / ".env")

from politician_trading.utils.logger import create_logger
from politician_trading.config import SupabaseConfig, WorkflowConfig
from politician_trading.workflow import PoliticianTradingWorkflow

logger = create_logger("scheduled_collection")


async def run_collection():
    """Async function to run data collection."""
    start_time = datetime.now()

    try:
        # Configure data sources
        # Edit these to enable/disable sources for scheduled runs
        enable_us_congress = True
        enable_eu_parliament = False  # Set to True if you want to enable
        enable_uk_parliament = False  # Set to True if you want to enable
        enable_california = False     # Set to True if you want to enable
        enable_us_states = False      # Set to True for other US states

        enabled_sources = []
        if enable_us_congress:
            enabled_sources.append("US Congress")
        if enable_eu_parliament:
            enabled_sources.append("EU Parliament")
        if enable_uk_parliament:
            enabled_sources.append("UK Parliament")
        if enable_california:
            enabled_sources.append("California")
        if enable_us_states:
            enabled_sources.append("US States")

        logger.info("Configured data sources", metadata={
            "enabled_sources": enabled_sources,
            "source_count": len(enabled_sources)
        })

        if not enabled_sources:
            logger.warning("No data sources enabled for collection")
            return 1

        # Create configuration
        supabase_config = SupabaseConfig.from_env()
        logger.info("Database configuration loaded", metadata={
            "url": supabase_config.url[:30] + "..."
        })

        workflow_config = WorkflowConfig(
            supabase=supabase_config,
            enable_us_congress=enable_us_congress,
            enable_uk_parliament=enable_uk_parliament,
            enable_eu_parliament=enable_eu_parliament,
            enable_us_states=enable_us_states,
            enable_california=enable_california,
        )

        # Initialize workflow
        logger.info("Initializing data collection workflow")
        workflow = PoliticianTradingWorkflow(workflow_config)

        # Run collection
        logger.info("Starting full data collection")
        results = await workflow.run_full_collection()

        # Log results
        summary = results.get("summary", {})
        jobs = results.get("jobs", {})

        logger.info("Data collection completed", metadata={
            "total_new_disclosures": summary.get("total_new_disclosures", 0),
            "total_updated_disclosures": summary.get("total_updated_disclosures", 0),
            "job_count": len(jobs),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "status": results.get("status")
        })

        # Log individual job results
        for source, job_result in jobs.items():
            if isinstance(job_result, dict):
                logger.info(f"Job result: {source}", metadata={
                    "status": job_result.get("status"),
                    "new_disclosures": job_result.get("new_disclosures", 0),
                    "updated_disclosures": job_result.get("updated_disclosures", 0),
                    "error": job_result.get("error")
                })

        # Check for errors in summary
        errors = summary.get("errors", [])
        if errors:
            logger.warning("Collection completed with errors", metadata={
                "error_count": len(errors),
                "errors": errors
            })
            return 1  # Non-zero exit code for errors

        logger.info("Scheduled collection job completed successfully")
        return 0

    except Exception as e:
        logger.error("Scheduled collection job failed", error=e, metadata={
            "duration_seconds": (datetime.now() - start_time).total_seconds()
        })
        return 1


def main():
    """Main entry point for scheduled data collection."""
    logger.info("Starting scheduled data collection job")

    try:
        exit_code = asyncio.run(run_collection())
        return exit_code
    except Exception as e:
        logger.error("Fatal error in scheduled collection", error=e)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
