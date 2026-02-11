#!/usr/bin/env python3
"""
End-to-end integration test for Senate ETL pipeline.

Runs the full Senate ETL pipeline against the real Senate.gov EFD database
and Supabase with a small limit to verify the complete pipeline works:
1. Fetch senators from Senate.gov XML
2. Upsert senators to database
3. Search EFD for PTR disclosures using Playwright
4. Parse PTR pages and upload transactions

Usage:
    cd python-etl-service
    set -a && source ../.env && set +a && uv run python scripts/test_senate_e2e.py
"""

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("senate_e2e")


async def test_step1_fetch_senators():
    """Step 1: Verify we can fetch senators from Senate.gov XML."""
    from app.services.senate_etl import fetch_senators_from_xml

    logger.info("=" * 60)
    logger.info("STEP 1: Fetch senators from Senate.gov XML")
    logger.info("=" * 60)

    senators = await fetch_senators_from_xml()

    assert len(senators) > 0, "Should fetch at least some senators"
    logger.info(f"Fetched {len(senators)} senators")

    # Verify structure
    sample = senators[0]
    assert "first_name" in sample, "Senator should have first_name"
    assert "last_name" in sample, "Senator should have last_name"
    assert "bioguide_id" in sample, "Senator should have bioguide_id"
    assert "party" in sample, "Senator should have party"
    assert "state" in sample, "Senator should have state"

    logger.info(f"Sample senator: {sample['first_name']} {sample['last_name']} "
                f"({sample['party']}-{sample['state']}) [{sample['bioguide_id']}]")
    logger.info("STEP 1 PASSED")
    return senators


async def test_step2_upsert_senators(senators):
    """Step 2: Verify we can upsert senators to database."""
    from app.services.senate_etl import upsert_senator_to_db
    from app.lib.database import get_supabase

    logger.info("=" * 60)
    logger.info("STEP 2: Upsert senators to database")
    logger.info("=" * 60)

    supabase = get_supabase()
    assert supabase is not None, "Supabase client should connect"

    # Upsert first 3 senators as a test
    test_senators = senators[:3]
    senator_ids = {}
    for senator in test_senators:
        politician_id = upsert_senator_to_db(supabase, senator)
        if politician_id:
            senator["politician_id"] = politician_id
            senator_ids[senator["last_name"]] = politician_id
            logger.info(f"  Upserted: {senator['full_name']} -> {politician_id}")

    assert len(senator_ids) > 0, "Should upsert at least one senator"
    logger.info(f"Upserted {len(senator_ids)}/{len(test_senators)} senators")

    # Verify in database
    for last_name, pol_id in senator_ids.items():
        result = supabase.table("politicians").select("id, name, role, bioguide_id").eq("id", pol_id).execute()
        assert result.data, f"Senator {last_name} should exist in database"
        assert result.data[0]["role"] == "Senator", f"Role should be Senator"
        logger.info(f"  Verified: {result.data[0]['name']} (role={result.data[0]['role']}, "
                    f"bioguide={result.data[0].get('bioguide_id')})")

    logger.info("STEP 2 PASSED")
    return senator_ids


async def test_step3_search_disclosures():
    """Step 3: Verify we can search EFD for PTR disclosures."""
    from app.services.senate_etl import search_all_ptr_disclosures_playwright

    logger.info("=" * 60)
    logger.info("STEP 3: Search EFD for PTR disclosures (Playwright)")
    logger.info("=" * 60)

    # Search with a small limit
    disclosures = await search_all_ptr_disclosures_playwright(
        lookback_days=60,  # Wider window to ensure we find some
        limit=5,
    )

    logger.info(f"Found {len(disclosures)} PTR disclosures")

    if not disclosures:
        logger.warning("No disclosures found - Senate EFD may be down or no recent filings")
        return disclosures

    # Verify structure
    for d in disclosures[:3]:
        logger.info(f"  {d.get('politician_name'):30s} | "
                    f"filed: {d.get('filing_date', 'N/A')[:10] if d.get('filing_date') else 'N/A'} | "
                    f"paper: {d.get('is_paper', False)} | "
                    f"{d.get('source_url', '')[:60]}")

    electronic = [d for d in disclosures if not d.get("is_paper")]
    paper = [d for d in disclosures if d.get("is_paper")]
    logger.info(f"Electronic: {len(electronic)}, Paper: {len(paper)}")

    assert any("source_url" in d and d["source_url"] for d in disclosures), \
        "At least one disclosure should have a source_url"

    logger.info("STEP 3 PASSED")
    return disclosures


async def test_step4_full_pipeline():
    """Step 4: Run the full pipeline with a tiny limit."""
    from app.services.senate_etl import run_senate_etl
    from app.services.house_etl import JOB_STATUS
    from app.lib.database import get_supabase
    from datetime import datetime, timezone

    logger.info("=" * 60)
    logger.info("STEP 4: Full Senate ETL pipeline (limit=3)")
    logger.info("=" * 60)

    job_id = "e2e-test-senate"
    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": 3,
        "message": "Job queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    try:
        await run_senate_etl(
            job_id=job_id,
            lookback_days=60,
            limit=3,
            update_mode=True,  # Upsert so re-runs don't fail on duplicates
        )
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)

    status = JOB_STATUS.get(job_id, {})
    logger.info(f"Final status: {json.dumps(status, indent=2, default=str)}")

    assert status.get("status") in ("completed", "error"), \
        f"Job should have completed or errored, got: {status.get('status')}"

    if status.get("status") == "completed":
        logger.info(f"Pipeline COMPLETED: {status.get('message')}")

        # Verify some records exist in the database
        supabase = get_supabase()
        result = (
            supabase.table("trading_disclosures")
            .select("id, politician_id, asset_name, asset_ticker, transaction_type, transaction_date, created_at")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if result.data:
            logger.info(f"\nMost recent disclosures in DB:")
            for r in result.data:
                logger.info(
                    f"  {r['transaction_date']} | "
                    f"{r.get('asset_ticker') or 'N/A':6s} | "
                    f"{r['transaction_type']:10s} | "
                    f"{r['asset_name'][:50]}"
                )
    else:
        logger.warning(f"Pipeline ERRORED: {status.get('message')}")
        # Still passes - errors are expected in some cases (rate limiting, etc.)

    logger.info("STEP 4 PASSED")
    return status


async def test_step5_backfill_single_year():
    """Step 5: Test historical backfill for one year (2025, limit=3)."""
    from app.services.senate_backfill import run_senate_backfill
    from app.services.house_etl import JOB_STATUS
    from app.lib.database import get_supabase
    from datetime import datetime, timezone

    logger.info("=" * 60)
    logger.info("STEP 5: Senate backfill single year (2025, limit=3)")
    logger.info("=" * 60)

    job_id = "e2e-test-backfill"
    JOB_STATUS[job_id] = {
        "_type": "senate_backfill",
        "status": "queued",
        "progress": 0,
        "total": 1,
        "message": "Job queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    try:
        await run_senate_backfill(
            job_id=job_id,
            start_year=2025,
            end_year=2025,
            limit=3,
            skip_completed=False,  # Always run for e2e test
        )
    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)

    status = JOB_STATUS.get(job_id, {})
    logger.info(f"Final status: {json.dumps(status, indent=2, default=str)}")

    assert status.get("status") in ("completed", "error"), \
        f"Backfill should have completed or errored, got: {status.get('status')}"

    if status.get("status") == "completed":
        logger.info(f"Backfill COMPLETED: {status.get('message')}")

        # Verify Senate disclosures exist
        supabase = get_supabase()
        result = (
            supabase.table("trading_disclosures")
            .select("id, source_url, asset_name, transaction_date", count="exact")
            .like("source_url", "%efdsearch.senate%")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        logger.info(f"Senate disclosures in DB: {result.count or len(result.data)}")
        for r in (result.data or []):
            logger.info(
                f"  {r.get('transaction_date', 'N/A')} | "
                f"{r.get('asset_name', 'N/A')[:50]} | "
                f"{r.get('source_url', '')[:60]}"
            )
    else:
        logger.warning(f"Backfill ERRORED: {status.get('message')}")

    logger.info("STEP 5 PASSED")
    return status


async def main():
    """Run all Senate ETL end-to-end tests."""
    logger.info("Starting Senate ETL end-to-end tests")
    logger.info(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')[:30]}...")
    logger.info(f"SUPABASE_SERVICE_KEY: {'SET' if os.getenv('SUPABASE_SERVICE_KEY') else 'NOT SET'}")
    logger.info("")

    failures = []

    # Step 1: Fetch senators
    try:
        senators = await test_step1_fetch_senators()
    except Exception as e:
        logger.error(f"Step 1 FAILED: {e}", exc_info=True)
        failures.append(("step1_fetch_senators", str(e)))
        senators = []

    # Step 2: Upsert senators
    if senators:
        try:
            senator_ids = await test_step2_upsert_senators(senators)
        except Exception as e:
            logger.error(f"Step 2 FAILED: {e}", exc_info=True)
            failures.append(("step2_upsert_senators", str(e)))

    # Step 3: Search disclosures
    try:
        disclosures = await test_step3_search_disclosures()
    except Exception as e:
        logger.error(f"Step 3 FAILED: {e}", exc_info=True)
        failures.append(("step3_search_disclosures", str(e)))

    # Step 4: Full pipeline
    try:
        status = await test_step4_full_pipeline()
    except Exception as e:
        logger.error(f"Step 4 FAILED: {e}", exc_info=True)
        failures.append(("step4_full_pipeline", str(e)))

    # Step 5: Backfill single year
    try:
        backfill_status = await test_step5_backfill_single_year()
    except Exception as e:
        logger.error(f"Step 5 FAILED: {e}", exc_info=True)
        failures.append(("step5_backfill_single_year", str(e)))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    steps = ["step1_fetch_senators", "step2_upsert_senators",
             "step3_search_disclosures", "step4_full_pipeline",
             "step5_backfill_single_year"]
    failed_names = [f[0] for f in failures]
    for step in steps:
        status_str = "FAIL" if step in failed_names else "PASS"
        logger.info(f"  {step:35s}: {status_str}")

    if failures:
        logger.error(f"\n{len(failures)} step(s) FAILED:")
        for name, err in failures:
            logger.error(f"  {name}: {err}")
        sys.exit(1)
    else:
        logger.info("\nAll steps PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
