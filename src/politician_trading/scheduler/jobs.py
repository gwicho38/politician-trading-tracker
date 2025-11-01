"""
Scheduled job functions for in-app scheduling.

These functions wrap the existing scheduled scripts and are designed
to be called by APScheduler.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from politician_trading.utils.logger import create_logger
from politician_trading.config import SupabaseConfig, WorkflowConfig
from politician_trading.workflow import PoliticianTradingWorkflow
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.ticker_utils import extract_ticker_from_asset_name

logger = create_logger("scheduled_jobs")


def data_collection_job():
    """
    Run data collection from all enabled sources.

    This job is designed to be called by APScheduler.
    """
    logger.info("Starting scheduled data collection job (in-app)")
    start_time = datetime.now()

    try:
        # Import here to avoid circular imports with streamlit
        import streamlit as st

        # Check if we can access session state (might not be available in background thread)
        # Get configuration from session state or use defaults
        try:
            enable_us_congress = st.session_state.get("scheduled_us_congress", True)
            enable_eu_parliament = st.session_state.get("scheduled_eu_parliament", False)
            enable_uk_parliament = st.session_state.get("scheduled_uk_parliament", False)
            enable_california = st.session_state.get("scheduled_california", False)
            enable_us_states = st.session_state.get("scheduled_us_states", False)
        except RuntimeError:
            # Session state not available (background thread), use defaults
            enable_us_congress = True
            enable_eu_parliament = False
            enable_uk_parliament = False
            enable_california = False
            enable_us_states = False

    except ImportError:
        # Streamlit not available, use defaults
        enable_us_congress = True
        enable_eu_parliament = False
        enable_uk_parliament = False
        enable_california = False
        enable_us_states = False

    async def run_collection():
        """Async wrapper for collection workflow"""
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

        logger.info("Running data collection", metadata={
            "enabled_sources": enabled_sources,
            "source_count": len(enabled_sources)
        })

        if not enabled_sources:
            logger.warning("No data sources enabled for collection")
            return

        # Create configuration
        supabase_config = SupabaseConfig.from_env()

        workflow_config = WorkflowConfig(
            supabase=supabase_config,
            enable_us_congress=enable_us_congress,
            enable_uk_parliament=enable_uk_parliament,
            enable_eu_parliament=enable_eu_parliament,
            enable_us_states=enable_us_states,
            enable_california=enable_california,
        )

        # Initialize workflow
        workflow = PoliticianTradingWorkflow(workflow_config)

        # Run collection
        results = await workflow.run_full_collection()

        # Log results
        summary = results.get("summary", {})
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("Data collection completed", metadata={
            "total_new_disclosures": summary.get("total_new_disclosures", 0),
            "total_updated_disclosures": summary.get("total_updated_disclosures", 0),
            "duration_seconds": duration,
            "status": results.get("status")
        })

    try:
        # Run the async function
        asyncio.run(run_collection())
        logger.info("Scheduled data collection job completed successfully")

    except Exception as e:
        logger.error("Scheduled data collection job failed", error=e, metadata={
            "duration_seconds": (datetime.now() - start_time).total_seconds()
        })
        raise  # Re-raise so APScheduler marks it as failed


def ticker_backfill_job():
    """
    Run ticker backfill for disclosures with missing tickers.

    This job is designed to be called by APScheduler.
    """
    logger.info("Starting scheduled ticker backfill job (in-app)")
    start_time = datetime.now()

    try:
        # Initialize database
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)

        logger.info("Querying disclosures with missing tickers")

        # Get all disclosures where ticker is null or empty
        response = db.client.table("trading_disclosures").select(
            "id, asset_name, asset_ticker"
        ).is_("asset_ticker", "null").execute()

        disclosures_no_ticker = response.data or []

        # Also get disclosures where ticker is empty string
        response2 = db.client.table("trading_disclosures").select(
            "id, asset_name, asset_ticker"
        ).eq("asset_ticker", "").execute()

        disclosures_empty_ticker = response2.data or []

        # Combine both lists
        all_disclosures = disclosures_no_ticker + disclosures_empty_ticker

        logger.info("Found disclosures with missing tickers", metadata={
            "count": len(all_disclosures)
        })

        if not all_disclosures:
            logger.info("No disclosures need ticker backfill")
            return

        updated = 0
        failed = 0
        no_ticker_found = 0

        for i, disclosure in enumerate(all_disclosures, 1):
            disclosure_id = disclosure["id"]
            asset_name = disclosure.get("asset_name")

            if not asset_name:
                no_ticker_found += 1
                continue

            # Extract ticker
            ticker = extract_ticker_from_asset_name(asset_name)

            if ticker:
                try:
                    # Update the record
                    db.client.table("trading_disclosures").update(
                        {"asset_ticker": ticker}
                    ).eq("id", disclosure_id).execute()

                    updated += 1
                    logger.debug("Updated disclosure with ticker", metadata={
                        "disclosure_id": disclosure_id,
                        "asset_name": asset_name,
                        "ticker": ticker
                    })
                except Exception as e:
                    failed += 1
                    logger.error("Failed to update disclosure", error=e, metadata={
                        "disclosure_id": disclosure_id,
                        "asset_name": asset_name,
                        "ticker": ticker
                    })
            else:
                no_ticker_found += 1
                logger.debug("No ticker found", metadata={
                    "disclosure_id": disclosure_id,
                    "asset_name": asset_name
                })

            # Log progress every 100 items
            if i % 100 == 0:
                logger.info("Backfill progress", metadata={
                    "processed": i,
                    "updated": updated,
                    "no_ticker_found": no_ticker_found,
                    "failed": failed
                })

        duration = (datetime.now() - start_time).total_seconds()

        logger.info("Ticker backfill completed", metadata={
            "total_processed": len(all_disclosures),
            "total_updated": updated,
            "total_no_ticker_found": no_ticker_found,
            "total_failed": failed,
            "duration_seconds": duration
        })

        if failed > 0:
            raise Exception(f"Ticker backfill completed with {failed} failures")

    except Exception as e:
        logger.error("Scheduled ticker backfill job failed", error=e, metadata={
            "duration_seconds": (datetime.now() - start_time).total_seconds()
        })
        raise  # Re-raise so APScheduler marks it as failed
