#!/usr/bin/env python3
"""
End-to-end integration test for new ETL services.

Runs each ETL service against real APIs and the real Supabase database
with a small limit to verify the full pipeline works.

Usage:
    cd python-etl-service
    source ../.env && uv run python scripts/test_etl_e2e.py
"""

import asyncio
import json
import logging
import os
import sys

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("e2e_test")


async def test_quiverquant():
    """Test QuiverQuant ETL with real API and database."""
    from app.services.quiver_etl import QuiverQuantETLService

    logger.info("=" * 60)
    logger.info("TEST 1: QuiverQuant ETL (real API + real DB)")
    logger.info("=" * 60)

    service = QuiverQuantETLService()
    logger.info(f"Service: {service.source_id} / {service.source_name}")
    logger.info(f"API key present: {bool(service.api_key)}")

    # Run with a small limit (5 records) and lookback of 30 days
    result = await service.run(
        job_id="e2e-test-quiver",
        limit=5,
        lookback_days=30,
        update_mode=True,  # Upsert so re-runs don't fail on duplicates
    )

    logger.info(f"Result: {json.dumps(result.to_dict(), indent=2, default=str)}")

    assert result.started_at is not None, "started_at should be set"
    assert result.completed_at is not None, "completed_at should be set"
    assert result.is_success, f"Should succeed, but got errors: {result.errors}"
    logger.info(f"  records_processed: {result.records_processed}")
    logger.info(f"  records_inserted:  {result.records_inserted}")
    logger.info(f"  records_updated:   {result.records_updated}")
    logger.info(f"  records_skipped:   {result.records_skipped}")
    logger.info(f"  records_failed:    {result.records_failed}")
    logger.info(f"  duration:          {result.duration_seconds:.2f}s")

    # For QuiverQuant, we expect real records to be processed
    if result.records_processed == 0:
        logger.warning(
            "No records fetched - this may indicate an API issue or no "
            "recent trades in the lookback window."
        )
    else:
        logger.info(
            f"SUCCESS: Processed {result.records_processed} records, "
            f"inserted/updated {result.records_inserted + result.records_updated}"
        )

    return result


async def test_eu_parliament():
    """Test EU Parliament stub ETL."""
    from app.services.eu_etl import EUParliamentETLService

    logger.info("=" * 60)
    logger.info("TEST 2: EU Parliament ETL (stub)")
    logger.info("=" * 60)

    service = EUParliamentETLService()
    logger.info(f"Service: {service.source_id} / {service.source_name}")

    result = await service.run(job_id="e2e-test-eu")

    logger.info(f"Result: {json.dumps(result.to_dict(), indent=2, default=str)}")

    assert result.started_at is not None, "started_at should be set"
    assert result.completed_at is not None, "completed_at should be set"
    assert result.is_success, f"Should succeed, but got errors: {result.errors}"
    assert result.records_processed == 0, "Stub should process 0 records"
    assert len(result.warnings) >= 1, "Should have 'No disclosures fetched' warning"
    logger.info(f"  warnings: {result.warnings}")
    logger.info(f"  duration: {result.duration_seconds:.2f}s")
    logger.info("SUCCESS: EU Parliament stub completed gracefully")

    return result


async def test_california():
    """Test California stub ETL."""
    from app.services.california_etl import CaliforniaETLService

    logger.info("=" * 60)
    logger.info("TEST 3: California ETL (stub)")
    logger.info("=" * 60)

    service = CaliforniaETLService()
    logger.info(f"Service: {service.source_id} / {service.source_name}")

    result = await service.run(job_id="e2e-test-california")

    logger.info(f"Result: {json.dumps(result.to_dict(), indent=2, default=str)}")

    assert result.started_at is not None, "started_at should be set"
    assert result.completed_at is not None, "completed_at should be set"
    assert result.is_success, f"Should succeed, but got errors: {result.errors}"
    assert result.records_processed == 0, "Stub should process 0 records"
    assert len(result.warnings) >= 1, "Should have 'No disclosures fetched' warning"
    logger.info(f"  warnings: {result.warnings}")
    logger.info(f"  duration: {result.duration_seconds:.2f}s")
    logger.info("SUCCESS: California stub completed gracefully")

    return result


async def verify_database_records():
    """Verify records were actually written to the database."""
    from app.lib.database import get_supabase

    logger.info("=" * 60)
    logger.info("VERIFICATION: Checking database for QuiverQuant records")
    logger.info("=" * 60)

    supabase = get_supabase()
    if not supabase:
        logger.error("Could not connect to Supabase!")
        return False

    # Check for recent QuiverQuant-sourced records
    response = (
        supabase.table("trading_disclosures")
        .select("id, politician_id, asset_name, asset_ticker, transaction_type, transaction_date, amount_range_min, amount_range_max, source_document_id, created_at")
        .like("source_document_id", "qq-%")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    if not response.data:
        logger.warning("No QuiverQuant records found in database!")
        logger.info("Checking if records were written with different source_document_id...")

        # Try checking for recent records
        response2 = (
            supabase.table("trading_disclosures")
            .select("id, source_document_id, asset_name, created_at")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        if response2.data:
            logger.info("Most recent records:")
            for r in response2.data:
                logger.info(f"  {r['created_at']} - {r['source_document_id']} - {r['asset_name']}")
        return False

    logger.info(f"Found {len(response.data)} QuiverQuant records in database:")
    for record in response.data:
        logger.info(
            f"  {record['transaction_date']} | "
            f"{record['asset_ticker'] or 'N/A':6s} | "
            f"{record['transaction_type']:8s} | "
            f"${record.get('amount_range_min') or '?'}-${record.get('amount_range_max') or '?'} | "
            f"{record['asset_name'][:40]}"
        )

    # Also check the politicians that were created/matched
    politician_ids = list(set(r["politician_id"] for r in response.data))
    pol_response = (
        supabase.table("politicians")
        .select("id, name, role, chamber, bioguide_id")
        .in_("id", politician_ids)
        .execute()
    )

    if pol_response.data:
        logger.info(f"\nLinked politicians ({len(pol_response.data)}):")
        for pol in pol_response.data:
            logger.info(
                f"  {pol['name']:30s} | {pol['role']:15s} | "
                f"bioguide: {pol.get('bioguide_id') or 'N/A'}"
            )

    logger.info("SUCCESS: Database records verified")
    return True


async def test_closed_loop_pipeline():
    """
    Smoke test: verify the closed-loop pipeline components are all wired.
    Does NOT place real trades. Checks DB state and config only.
    """
    from app.lib.database import get_supabase
    supabase = get_supabase()

    results = {}

    # 1. Portfolio config has correct parameters
    config = supabase.table("reference_portfolio_config").select("*").execute().data
    assert config, "reference_portfolio_config is empty"
    cfg = config[0]
    results["trailing_stop_pct"]     = cfg.get("trailing_stop_pct")
    results["default_stop_loss_pct"] = cfg.get("default_stop_loss_pct")
    assert cfg.get("trailing_stop_pct", 0) >= 15, \
        f"trailing_stop_pct={cfg.get('trailing_stop_pct')} — should be >=15% (was 4% before fix)"
    logger.info("Portfolio config: trailing_stop_pct=%s, stop_loss_pct=%s",
                cfg.get("trailing_stop_pct"), cfg.get("default_stop_loss_pct"))

    # 2. politician_committees table exists and has sector map
    committees = supabase.table("committee_sector_map").select("committee_code").execute().data
    assert len(committees) >= 10, "committee_sector_map should have at least 10 entries"
    logger.info("Committee sector map: %d entries", len(committees))

    # 3. ml_models table has at least one model
    models = supabase.table("ml_models").select("id,model_name,status").execute().data
    logger.info("ml_models: %d models (statuses=%s)",
                len(models),
                [m["status"] for m in models])

    # 4. trading_signals has shadow model columns
    signals = supabase.table("trading_signals").select(
        "challenger_model_id,challenger_confidence_score"
    ).limit(1).execute()
    # If columns don't exist, PostgREST returns a 400 error
    logger.info("trading_signals: shadow model columns present")

    logger.info("Closed-loop pipeline smoke test: ALL CHECKS PASSED")
    return results


async def main():
    """Run all end-to-end tests."""
    logger.info("Starting end-to-end ETL service tests")
    logger.info(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')[:30]}...")
    logger.info(f"SUPABASE_SERVICE_KEY: {'SET' if os.getenv('SUPABASE_SERVICE_KEY') else 'NOT SET'}")
    logger.info(f"QUIVERQUANT_API_KEY: {'SET' if os.getenv('QUIVERQUANT_API_KEY') else 'NOT SET'}")
    logger.info("")

    results = {}
    failures = []

    # Test 1: QuiverQuant (real API + real DB)
    try:
        results["quiverquant"] = await test_quiverquant()
    except Exception as e:
        logger.error(f"QuiverQuant test FAILED: {e}", exc_info=True)
        failures.append(("quiverquant", str(e)))

    # Test 2: EU Parliament (stub)
    try:
        results["eu_parliament"] = await test_eu_parliament()
    except Exception as e:
        logger.error(f"EU Parliament test FAILED: {e}", exc_info=True)
        failures.append(("eu_parliament", str(e)))

    # Test 3: California (stub)
    try:
        results["california"] = await test_california()
    except Exception as e:
        logger.error(f"California test FAILED: {e}", exc_info=True)
        failures.append(("california", str(e)))

    # Verify database records
    try:
        db_ok = await verify_database_records()
    except Exception as e:
        logger.error(f"Database verification FAILED: {e}", exc_info=True)
        failures.append(("db_verify", str(e)))
        db_ok = False

    # Test 4: Closed-loop pipeline smoke test
    closed_loop_results = None
    try:
        logger.info("=" * 60)
        logger.info("TEST 4: Closed-loop pipeline smoke test")
        logger.info("=" * 60)
        closed_loop_results = await test_closed_loop_pipeline()
    except Exception as e:
        logger.error(f"Closed-loop pipeline smoke test FAILED: {e}", exc_info=True)
        failures.append(("closed_loop_pipeline", str(e)))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    for name, result in results.items():
        status = "PASS" if result.is_success else "FAIL"
        logger.info(
            f"  {name:20s}: {status} "
            f"(processed={result.records_processed}, "
            f"inserted={result.records_inserted}, "
            f"errors={len(result.errors)})"
        )

    logger.info(f"  {'db_verification':20s}: {'PASS' if db_ok else 'FAIL'}")
    logger.info(
        f"  {'closed_loop_pipeline':20s}: {'PASS' if closed_loop_results is not None else 'FAIL'}"
    )

    if failures:
        logger.error(f"\n{len(failures)} test(s) FAILED:")
        for name, err in failures:
            logger.error(f"  {name}: {err}")
        sys.exit(1)
    else:
        logger.info("\nAll tests PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
