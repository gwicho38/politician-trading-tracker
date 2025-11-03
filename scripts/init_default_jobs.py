#!/usr/bin/env python3
"""
Initialize default scheduled jobs in the database.

This script creates the default daily data collection and ticker backfill jobs
if they don't already exist in the scheduled_jobs table.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.logger import create_logger

logger = create_logger("init_default_jobs")


def init_default_jobs():
    """Initialize default scheduled jobs in the database"""
    logger.info("Initializing default scheduled jobs")

    try:
        # Connect to database
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)
        logger.info("Connected to database")

        # Define default jobs
        default_jobs = [
            {
                "job_id": "data_collection_daily",
                "job_name": "Daily Data Collection",
                "job_function": "politician_trading.scheduler.jobs.data_collection_job",
                "schedule_type": "cron",
                "schedule_value": "0 2 * * *",  # Daily at 2 AM UTC
                "enabled": True,
                "next_scheduled_run": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "description": "Automatically collect politician trading data from all enabled sources once per day",
                    "sources": ["US Congress", "QuiverQuant"],
                    "auto_created": True
                }
            },
            {
                "job_id": "ticker_backfill_daily",
                "job_name": "Daily Ticker Backfill",
                "job_function": "politician_trading.scheduler.jobs.ticker_backfill_job",
                "schedule_type": "cron",
                "schedule_value": "0 3 * * *",  # Daily at 3 AM UTC (1 hour after data collection)
                "enabled": True,
                "next_scheduled_run": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "metadata": {
                    "description": "Extract and populate missing ticker symbols from asset names for all disclosures",
                    "auto_created": True
                }
            }
        ]

        # Insert each job (using upsert to avoid duplicates)
        for job in default_jobs:
            logger.info(f"Creating job: {job['job_name']}", metadata={
                "job_id": job["job_id"],
                "schedule": f"{job['schedule_type']}: {job['schedule_value']}"
            })

            try:
                # Check if job already exists
                response = db.client.table("scheduled_jobs")\
                    .select("id, job_id, job_name")\
                    .eq("job_id", job["job_id"])\
                    .execute()

                if response.data:
                    logger.info(f"Job '{job['job_name']}' already exists - skipping", metadata={
                        "job_id": job["job_id"]
                    })
                    continue

                # Insert new job
                insert_response = db.client.table("scheduled_jobs")\
                    .insert(job)\
                    .execute()

                if insert_response.data:
                    logger.info(f"✅ Created job: {job['job_name']}", metadata={
                        "job_id": job["job_id"],
                        "db_id": insert_response.data[0]["id"]
                    })
                else:
                    logger.error(f"Failed to create job: {job['job_name']}")

            except Exception as e:
                logger.error(f"Error creating job: {job['job_name']}", error=e, metadata={
                    "job_id": job["job_id"]
                })

        # Verify jobs were created
        logger.info("Verifying scheduled jobs...")
        all_jobs_response = db.client.table("scheduled_jobs")\
            .select("job_id, job_name, schedule_type, schedule_value, enabled")\
            .execute()

        if all_jobs_response.data:
            logger.info(f"✅ Found {len(all_jobs_response.data)} scheduled jobs in database:")
            for job in all_jobs_response.data:
                status = "✅ ENABLED" if job.get("enabled") else "⏸️ DISABLED"
                logger.info(f"  {status} - {job['job_name']} ({job['job_id']})", metadata={
                    "schedule": f"{job['schedule_type']}: {job['schedule_value']}"
                })
        else:
            logger.warning("No scheduled jobs found in database after initialization")

        logger.info("Default jobs initialization complete!")

    except Exception as e:
        logger.error("Failed to initialize default jobs", error=e)
        raise


if __name__ == "__main__":
    init_default_jobs()
