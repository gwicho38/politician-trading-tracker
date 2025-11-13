"""
Database Seeding Script for Politician Trading Data

This script provides functionality to seed the Supabase database with politician
trading data from multiple sources, creating a comprehensive data bank that can
be iteratively updated.

Usage:
    python -m mcli.workflow.politician_trading.seed_database --sources all
    python -m mcli.workflow.politician_trading.seed_database --sources propublica
    python -m mcli.workflow.politician_trading.seed_database --test-run
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from supabase import Client, create_client

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Look for .env in project root
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, try loading from .streamlit/secrets.toml
    pass

from .models import Politician, TradingDisclosure
from .scrapers_free_sources import FreeDataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/tmp/seed_database.log")],
)
logger = logging.getLogger(__name__)


# =============================================================================
# Database Connection
# =============================================================================


def get_supabase_client() -> Client:
    """Get Supabase client from environment variables"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) "
            "environment variables must be set"
        )

    return create_client(url, key)


# =============================================================================
# Data Pull Job Tracking
# =============================================================================


def create_data_pull_job(client: Client, job_type: str, config: Optional[Dict] = None) -> UUID:
    """
    Create a new data pull job record

    Args:
        client: Supabase client
        job_type: Type of job (e.g., "propublica", "stocknear", "seed_all")
        config: Optional configuration snapshot

    Returns:
        Job ID
    """
    logger.info("🚀 Creating data pull job", extra={"job_type": job_type})
    try:
        result = (
            client.table("data_pull_jobs")
            .insert(
                {
                    "job_type": job_type,
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                    "config_snapshot": config or {},
                }
            )
            .execute()
        )
        logger.info("✅ Data pull job created successfully", extra={"job_type": job_type})

        job_id = result.data[0]["id"]
        logger.info(f"Created data pull job: {job_id} (type: {job_type})")
        return UUID(job_id)

    except Exception as e:
        logger.error(f"Error creating data pull job: {e}")
        raise


def update_data_pull_job(
    client: Client,
    job_id: UUID,
    status: str,
    stats: Optional[Dict] = None,
    error: Optional[str] = None,
):
    """
    Update data pull job with results

    Args:
        client: Supabase client
        job_id: Job ID to update
        status: Job status ("completed", "failed", "running")
        stats: Optional statistics (records_found, records_new, etc.)
        error: Optional error message if failed
    """
    logger.info("🔄 Updating data pull job", extra={
        "job_id": str(job_id),
        "status": status,
        "has_stats": bool(stats),
        "has_error": bool(error),
    })

    try:
        update_data = {"status": status, "completed_at": datetime.now().isoformat()}

        if stats:
            update_data.update(stats)
            logger.debug("Job statistics", extra=stats)

        if error:
            update_data["error_message"] = error
            logger.error("Job failed with error", extra={"job_id": str(job_id), "error": error})

        client.table("data_pull_jobs").update(update_data).eq("id", str(job_id)).execute()

        if status == "completed":
            logger.info("✅ Job completed successfully", extra={
                "job_id": str(job_id),
                "records_found": stats.get("records_found", 0) if stats else 0,
                "records_new": stats.get("records_new", 0) if stats else 0,
                "records_updated": stats.get("records_updated", 0) if stats else 0,
            })
        elif status == "failed":
            logger.error(f"❌ Job marked as failed: {job_id}")
        else:
            logger.info(f"Updated job {job_id}: status={status}")

    except Exception as e:
        logger.error(f"❌ Error updating data pull job: {e}", extra={
            "job_id": str(job_id),
            "attempted_status": status,
        })


# =============================================================================
# Politician Upsert Logic
# =============================================================================


def upsert_politicians(client: Client, politicians: List[Politician]) -> Dict[str, UUID]:
    """
    Upsert politicians to database, returning mapping of bioguide_id -> UUID

    Args:
        client: Supabase client
        politicians: List of Politician objects

    Returns:
        Dictionary mapping bioguide_id to politician UUID
    """
    logger.info(f"🔄 Starting politician upsert for {len(politicians)} politicians")
    politician_map = {}
    new_count = 0
    updated_count = 0
    skipped_count = 0
    examples_new = []
    examples_updated = []

    for i, politician in enumerate(politicians, 1):
        try:
            # Convert to database format
            pol_data = {
                "first_name": politician.first_name,
                "last_name": politician.last_name,
                "full_name": politician.full_name,
                "role": politician.role,
                "party": politician.party,
                "state_or_country": politician.state_or_country,
                "district": politician.district,
                "bioguide_id": politician.bioguide_id,
            }

            # Try to find existing politician
            if politician.bioguide_id:
                # Query by bioguide_id if available
                logger.debug(f"Looking up politician by bioguide_id: {politician.bioguide_id}")
                existing = (
                    client.table("politicians")
                    .select("id")
                    .eq("bioguide_id", politician.bioguide_id)
                    .execute()
                )
            else:
                # Query by unique constraint fields (first_name, last_name, role, state_or_country)
                logger.debug(f"Looking up politician by name: {politician.full_name}")
                existing = (
                    client.table("politicians")
                    .select("id")
                    .eq("first_name", politician.first_name)
                    .eq("last_name", politician.last_name)
                    .eq("role", politician.role)
                    .eq("state_or_country", politician.state_or_country)
                    .execute()
                )

            if existing.data:
                # Update existing
                pol_id = UUID(existing.data[0]["id"])
                client.table("politicians").update(pol_data).eq("id", str(pol_id)).execute()
                updated_count += 1

                if len(examples_updated) < 5:
                    examples_updated.append(f"{politician.full_name} ({politician.party}, {politician.state_or_country})")

                logger.debug(f"✅ Updated politician: {politician.full_name}")
            else:
                # Insert new
                result = client.table("politicians").insert(pol_data).execute()
                pol_id = UUID(result.data[0]["id"])
                new_count += 1

                if len(examples_new) < 5:
                    examples_new.append(f"{politician.full_name} ({politician.party}, {politician.state_or_country})")

                logger.debug(f"➕ Inserted new politician: {politician.full_name}")

            # Store mapping - use bioguide_id if available, otherwise use full_name
            if politician.bioguide_id:
                politician_map[politician.bioguide_id] = pol_id
            elif politician.full_name:
                # For sources without bioguide_id (e.g., Senate Stock Watcher), use full_name
                politician_map[politician.full_name] = pol_id

            # Log progress every 100 politicians
            if i % 100 == 0:
                percent_complete = (i / len(politicians)) * 100
                logger.info(f"📊 Politician upsert progress: {percent_complete:.1f}% complete", extra={
                    "processed": i,
                    "total": len(politicians),
                    "new": new_count,
                    "updated": updated_count,
                    "skipped": skipped_count,
                })

        except Exception as e:
            skipped_count += 1
            logger.error(f"❌ Error upserting politician {politician.full_name}: {e}")
            continue

    # Calculate success rate
    success_rate = ((new_count + updated_count) / len(politicians) * 100) if len(politicians) > 0 else 0

    logger.info("✅ Politician upsert completed", extra={
        "total_processed": len(politicians),
        "new_politicians": new_count,
        "updated_politicians": updated_count,
        "skipped": skipped_count,
        "examples_new": examples_new,
        "examples_updated": examples_updated,
        "success_rate": f"{success_rate:.1f}%",
    })

    return politician_map


# =============================================================================
# Trading Disclosure Upsert Logic
# =============================================================================


def upsert_trading_disclosures(
    client: Client, disclosures: List[TradingDisclosure], politician_map: Dict[str, UUID]
) -> Dict[str, int]:
    """
    Upsert trading disclosures to database

    Args:
        client: Supabase client
        disclosures: List of TradingDisclosure objects
        politician_map: Mapping of bioguide_id to politician UUID

    Returns:
        Statistics dictionary with counts
    """
    logger.info(f"🔄 Starting disclosure upsert for {len(disclosures)} disclosures")
    new_count = 0
    updated_count = 0
    skipped_count = 0
    examples_new = []
    examples_updated = []

    for i, disclosure in enumerate(disclosures, 1):
        try:
            # Get politician ID
            pol_id = politician_map.get(disclosure.politician_bioguide_id)
            if not pol_id:
                logger.debug(
                    f"⚠️ Skipping disclosure - politician not found: "
                    f"{disclosure.politician_bioguide_id}"
                )
                skipped_count += 1
                continue

            # Convert to database format
            disclosure_data = {
                "politician_id": str(pol_id),
                "transaction_date": disclosure.transaction_date.isoformat(),
                "disclosure_date": disclosure.disclosure_date.isoformat(),
                "transaction_type": disclosure.transaction_type,
                "asset_name": disclosure.asset_name,
                "asset_ticker": disclosure.asset_ticker,
                "asset_type": disclosure.asset_type,
                "amount_range_min": disclosure.amount_range_min,
                "amount_range_max": disclosure.amount_range_max,
                "amount_exact": disclosure.amount_exact,
                "source_url": disclosure.source_url,
                "raw_data": disclosure.raw_data,
                "status": "processed",
            }

            # Check for existing disclosure (using unique constraint)
            existing = (
                client.table("trading_disclosures")
                .select("id")
                .eq("politician_id", str(pol_id))
                .eq("transaction_date", disclosure.transaction_date.isoformat())
                .eq("asset_name", disclosure.asset_name)
                .eq("transaction_type", disclosure.transaction_type)
                .eq("disclosure_date", disclosure.disclosure_date.isoformat())
                .execute()
            )

            if existing.data:
                # Update existing
                disc_id = existing.data[0]["id"]
                client.table("trading_disclosures").update(disclosure_data).eq(
                    "id", disc_id
                ).execute()
                updated_count += 1

                if len(examples_updated) < 5:
                    examples_updated.append(
                        f"{disclosure.asset_name} ({disclosure.transaction_type}) - "
                        f"{disclosure.transaction_date.strftime('%Y-%m-%d')}"
                    )

                logger.debug(f"✅ Updated disclosure: {disclosure.asset_name}")
            else:
                # Insert new
                client.table("trading_disclosures").insert(disclosure_data).execute()
                new_count += 1

                if len(examples_new) < 5:
                    examples_new.append(
                        f"{disclosure.asset_name} ({disclosure.transaction_type}) - "
                        f"{disclosure.transaction_date.strftime('%Y-%m-%d')}"
                    )

                logger.debug(f"➕ Inserted new disclosure: {disclosure.asset_name}")

            # Log progress every 100 disclosures
            if i % 100 == 0:
                percent_complete = (i / len(disclosures)) * 100
                logger.info(f"📊 Disclosure upsert progress: {percent_complete:.1f}% complete", extra={
                    "processed": i,
                    "total": len(disclosures),
                    "new": new_count,
                    "updated": updated_count,
                    "skipped": skipped_count,
                    "success_rate": f"{((new_count + updated_count) / i * 100):.1f}%" if i > 0 else "0%",
                })

        except Exception as e:
            skipped_count += 1
            logger.error(f"❌ Error upserting disclosure: {e}", extra={
                "asset_name": disclosure.asset_name if hasattr(disclosure, 'asset_name') else 'unknown',
                "transaction_type": disclosure.transaction_type if hasattr(disclosure, 'transaction_type') else 'unknown',
            })
            continue

    # Calculate success rate
    success_rate = ((new_count + updated_count) / len(disclosures) * 100) if len(disclosures) > 0 else 0

    logger.info("✅ Disclosure upsert completed", extra={
        "total_processed": len(disclosures),
        "new_disclosures": new_count,
        "updated_disclosures": updated_count,
        "skipped": skipped_count,
        "examples_new": examples_new,
        "examples_updated": examples_updated,
        "success_rate": f"{success_rate:.1f}%",
    })

    return {
        "records_found": len(disclosures),
        "records_new": new_count,
        "records_updated": updated_count,
        "records_failed": skipped_count,
    }


# =============================================================================
# Source-Specific Seeding Functions
# =============================================================================


def seed_from_senate_watcher(
    client: Client, test_run: bool = False, recent_only: bool = False, days: int = 90
) -> Dict[str, int]:
    """
    Seed database from Senate Stock Watcher GitHub dataset

    Args:
        client: Supabase client
        test_run: If True, only fetch but don't insert to DB
        recent_only: If True, only fetch recent transactions
        days: Number of days to look back if recent_only=True

    Returns:
        Statistics dictionary
    """
    logger.info("=" * 80)
    logger.info("SEEDING FROM SENATE STOCK WATCHER (GitHub)")
    logger.info("=" * 80)

    # Create job record
    job_id = create_data_pull_job(
        client, "senate_watcher_seed", {"recent_only": recent_only, "days": days}
    )

    try:
        # Initialize fetcher
        logger.info("🔄 Initializing FreeDataFetcher")
        fetcher = FreeDataFetcher()

        # Fetch data
        logger.info("📡 Fetching data from Senate Stock Watcher", extra={
            "recent_only": recent_only,
            "days": days if recent_only else "all",
        })
        data = fetcher.fetch_from_senate_watcher(recent_only=recent_only, days=days)

        politicians = data["politicians"]
        disclosures = data["disclosures"]

        logger.info("✅ Fetched data successfully", extra={
            "politicians": len(politicians),
            "disclosures": len(disclosures),
            "total_records": len(politicians) + len(disclosures),
        })

        if test_run:
            logger.info("⚠️ TEST RUN - Not inserting to database")
            if politicians:
                logger.info(f"Sample politician: {politicians[0]}")
            if disclosures:
                logger.info(f"Sample disclosure: {disclosures[0]}")

            update_data_pull_job(
                client,
                job_id,
                "completed",
                {
                    "records_found": len(politicians) + len(disclosures),
                    "records_new": 0,
                    "records_updated": 0,
                },
            )
            return {"records_found": len(politicians) + len(disclosures)}

        # Upsert politicians
        logger.info("👥 Starting politician upsert phase")
        politician_map = upsert_politicians(client, politicians)
        logger.info("✅ Politician upsert phase completed", extra={
            "mapped_politicians": len(politician_map),
        })

        # Upsert disclosures
        logger.info("📊 Starting disclosure upsert phase")
        disclosure_stats = upsert_trading_disclosures(client, disclosures, politician_map)
        logger.info("✅ Disclosure upsert phase completed")

        # Update job record
        update_data_pull_job(client, job_id, "completed", disclosure_stats)

        logger.info("🎉 Senate Stock Watcher seeding completed successfully!", extra=disclosure_stats)

        return disclosure_stats

    except Exception as e:
        logger.error(f"❌ Error seeding from Senate Stock Watcher: {e}")
        update_data_pull_job(client, job_id, "failed", error=str(e))
        raise


def seed_from_all_sources(client: Client, test_run: bool = False) -> Dict[str, Dict[str, int]]:
    """
    Seed database from all available sources

    Args:
        client: Supabase client
        test_run: If True, only fetch but don't insert to DB

    Returns:
        Dictionary mapping source name to statistics
    """
    logger.info("=" * 80)
    logger.info("SEEDING FROM ALL SOURCES")
    logger.info("=" * 80)

    results = {}

    # Senate Stock Watcher (free GitHub dataset - no API key needed!)
    try:
        logger.info("\n📡 Senate Stock Watcher (GitHub)")
        results["senate_watcher"] = seed_from_senate_watcher(client, test_run)
    except Exception as e:
        logger.error(f"Senate Stock Watcher seeding failed: {e}")
        results["senate_watcher"] = {"error": str(e)}

    # TODO: Add other sources as implemented
    # - Finnhub (requires free API key from finnhub.io)
    # - SEC Edgar (free, no API key, but need to implement Form 4 parsing)
    # - StockNear (requires JavaScript rendering)
    # - QuiverQuant (requires premium subscription)

    logger.info("\n" + "=" * 80)
    logger.info("SEEDING SUMMARY")
    logger.info("=" * 80)

    for source, stats in results.items():
        logger.info(f"\n{source}:")
        if "error" in stats:
            logger.error(f"  ❌ Failed: {stats['error']}")
        else:
            logger.info(f"  ✅ Found: {stats.get('records_found', 0)}")
            logger.info(f"  ➕ New: {stats.get('records_new', 0)}")
            logger.info(f"  🔄 Updated: {stats.get('records_updated', 0)}")
            logger.info(f"  ⚠️  Failed: {stats.get('records_failed', 0)}")

    return results


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Seed politician trading database from multiple sources"
    )

    parser.add_argument(
        "--sources",
        choices=["all", "senate", "finnhub", "sec-edgar"],
        default="all",
        help="Which data sources to seed from (default: all)",
    )

    parser.add_argument(
        "--recent-only", action="store_true", help="Only fetch recent transactions (last 90 days)"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days to look back when using --recent-only (default: 90)",
    )

    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Fetch data but don't insert to database (for testing)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get Supabase client
    try:
        client = get_supabase_client()
        logger.info("✅ Connected to Supabase")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)

    # Run seeding
    try:
        if args.sources == "senate":
            seed_from_senate_watcher(
                client, test_run=args.test_run, recent_only=args.recent_only, days=args.days
            )
        elif args.sources == "all":
            seed_from_all_sources(client, args.test_run)
        else:
            logger.error(f"Source '{args.sources}' not yet implemented")
            logger.info("Available sources: all, senate")
            logger.info("Coming soon: finnhub, sec-edgar")
            sys.exit(1)

        logger.info("\n✅ Seeding completed successfully!")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
