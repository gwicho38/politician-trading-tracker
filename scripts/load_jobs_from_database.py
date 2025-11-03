#!/usr/bin/env python3
"""
Load scheduled jobs from database into APScheduler.

This script reads jobs from the scheduled_jobs table and adds them to the
scheduler so they will actually run.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from politician_trading.scheduler import get_scheduler
from politician_trading.scheduler.jobs import data_collection_job, ticker_backfill_job
from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.logger import create_logger

logger = create_logger("load_jobs_from_database")


# Map job function names to actual Python functions
JOB_FUNCTION_MAP = {
    "politician_trading.scheduler.jobs.data_collection_job": data_collection_job,
    "politician_trading.scheduler.jobs.ticker_backfill_job": ticker_backfill_job,
}


def load_jobs_from_database():
    """Load jobs from database and add them to the scheduler"""
    logger.info("Loading jobs from database into scheduler")

    try:
        # Get scheduler instance
        scheduler = get_scheduler()
        logger.info("Got scheduler instance", metadata={
            "running": scheduler.is_running()
        })

        # Connect to database
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)
        logger.info("Connected to database")

        # Get all enabled jobs from database
        response = db.client.table("scheduled_jobs")\
            .select("*")\
            .eq("enabled", True)\
            .execute()

        if not response.data:
            logger.warning("No enabled jobs found in database")
            return

        db_jobs = response.data
        logger.info(f"Found {len(db_jobs)} enabled jobs in database")

        # Get currently scheduled jobs
        current_jobs = scheduler.get_jobs()
        current_job_ids = {job['id'] for job in current_jobs}
        logger.info(f"Currently {len(current_jobs)} jobs in scheduler")

        # Add jobs that aren't already in scheduler
        for db_job in db_jobs:
            job_id = db_job["job_id"]
            job_name = db_job["job_name"]
            job_function_path = db_job["job_function"]
            schedule_type = db_job["schedule_type"]
            schedule_value = db_job["schedule_value"]

            if job_id in current_job_ids:
                logger.info(f"Job '{job_name}' already in scheduler - skipping")
                continue

            # Get the job function
            job_function = JOB_FUNCTION_MAP.get(job_function_path)
            if not job_function:
                logger.error(f"Unknown job function: {job_function_path}")
                continue

            logger.info(f"Adding job to scheduler: {job_name}", metadata={
                "job_id": job_id,
                "schedule_type": schedule_type,
                "schedule_value": schedule_value
            })

            try:
                if schedule_type == "cron":
                    # Parse cron expression (minute hour day month day_of_week)
                    parts = schedule_value.split()
                    if len(parts) == 5:
                        minute, hour, day, month, day_of_week = parts
                        scheduler.add_job(
                            func=job_function,
                            job_id=job_id,
                            name=job_name,
                            schedule_type="cron",
                            minute=minute,
                            hour=hour,
                            day=day,
                            month=month,
                            day_of_week=day_of_week,
                            metadata={
                                "description": db_job.get("metadata", {}).get("description", ""),
                                "auto_created": True
                            }
                        )
                        logger.info(f"✅ Added cron job: {job_name}")
                    else:
                        logger.error(f"Invalid cron expression: {schedule_value}")

                elif schedule_type == "interval":
                    # Interval in seconds
                    seconds = int(schedule_value)
                    scheduler.add_job(
                        func=job_function,
                        job_id=job_id,
                        name=job_name,
                        schedule_type="interval",
                        seconds=seconds,
                        metadata={
                            "description": db_job.get("metadata", {}).get("description", ""),
                            "auto_created": True
                        }
                    )
                    logger.info(f"✅ Added interval job: {job_name} (every {seconds}s)")

                else:
                    logger.error(f"Unknown schedule type: {schedule_type}")

            except Exception as e:
                logger.error(f"Failed to add job {job_name}", error=e)

        # Verify jobs were added
        final_jobs = scheduler.get_jobs()
        logger.info(f"✅ Scheduler now has {len(final_jobs)} jobs")

        for job in final_jobs:
            logger.info(f"  - {job['name']} ({job['id']})", metadata={
                "schedule": job['schedule'],
                "next_run": job['next_run']
            })

        logger.info("Job loading complete!")

    except Exception as e:
        logger.error("Failed to load jobs from database", error=e)
        raise


if __name__ == "__main__":
    load_jobs_from_database()
