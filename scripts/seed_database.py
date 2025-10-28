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

from .data_sources import ALL_DATA_SOURCES, AccessMethod, DataSource
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
    try:
        update_data = {"status": status, "completed_at": datetime.now().isoformat()}

        if stats:
            update_data.update(stats)

        if error:
            update_data["error_message"] = error

        client.table("data_pull_jobs").update(update_data).eq("id", str(job_id)).execute()

        logger.info(f"Updated job {job_id}: status={status}")

    except Exception as e:
        logger.error(f"Error updating data pull job: {e}")


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
    politician_map = {}
    new_count = 0
    updated_count = 0

    for politician in politicians:
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
                existing = (
                    client.table("politicians")
                    .select("id")
                    .eq("bioguide_id", politician.bioguide_id)
                    .execute()
                )
            else:
                # Query by unique constraint fields (first_name, last_name, role, state_or_country)
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
            else:
                # Insert new
                result = client.table("politicians").insert(pol_data).execute()
                pol_id = UUID(result.data[0]["id"])
                new_count += 1

            # Store mapping - use bioguide_id if available, otherwise use full_name
            if politician.bioguide_id:
                politician_map[politician.bioguide_id] = pol_id
            elif politician.full_name:
                # For sources without bioguide_id (e.g., Senate Stock Watcher), use full_name
                politician_map[politician.full_name] = pol_id

        except Exception as e:
            logger.error(f"Error upserting politician {politician.full_name}: {e}")
            continue

    logger.info(
        f"Upserted {len(politicians)} politicians ({new_count} new, {updated_count} updated)"
    )

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
    new_count = 0
    updated_count = 0
    skipped_count = 0

    for disclosure in disclosures:
        try:
            # Get politician ID
            pol_id = politician_map.get(disclosure.politician_bioguide_id)
            if not pol_id:
                logger.warning(
                    f"Skipping disclosure - politician not found: "
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
            else:
                # Insert new
                client.table("trading_disclosures").insert(disclosure_data).execute()
                new_count += 1

        except Exception as e:
            logger.error(f"Error upserting disclosure: {e}")
            skipped_count += 1
            continue

    logger.info(
        f"Upserted {len(disclosures)} disclosures "
        f"({new_count} new, {updated_count} updated, {skipped_count} skipped)"
    )

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
        fetcher = FreeDataFetcher()

        # Fetch data
        data = fetcher.fetch_from_senate_watcher(recent_only=recent_only, days=days)

        politicians = data["politicians"]
        disclosures = data["disclosures"]

        logger.info(f"Fetched {len(politicians)} politicians, {len(disclosures)} disclosures")

        if test_run:
            logger.info("TEST RUN - Not inserting to database")
            logger.info(f"Sample politician: {politicians[0] if politicians else 'None'}")
            logger.info(f"Sample disclosure: {disclosures[0] if disclosures else 'None'}")
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
        politician_map = upsert_politicians(client, politicians)

        # Upsert disclosures
        disclosure_stats = upsert_trading_disclosures(client, disclosures, politician_map)

        # Update job record
        update_data_pull_job(client, job_id, "completed", disclosure_stats)

        return disclosure_stats

    except Exception as e:
        logger.error(f"Error seeding from Senate Stock Watcher: {e}")
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
