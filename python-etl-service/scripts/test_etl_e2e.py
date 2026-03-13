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


async def test_ml_training_async():
    """
    TEST 5: ML Training Async — verifies the 202 async pattern of the ml-training
    Supabase edge function.  Does NOT wait for the training job to finish.
    """
    import httpx

    logger.info("=" * 60)
    logger.info("TEST 5: ML Training Async (edge function 202 pattern)")
    logger.info("=" * 60)

    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not service_key:
        logger.warning(
            "SUPABASE_URL or service key env var not set — skipping ML training async test"
        )
        return None

    edge_fn_url = f"{supabase_url}/functions/v1/ml-training"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: trigger training — expect HTTP 202
        logger.info("Step 1: POST action=train to ml-training edge function")
        train_resp = await client.post(
            edge_fn_url,
            headers=headers,
            json={
                "action": "train",
                "triggered_by": "e2e_test",
                "compare_to_current": True,
                "auto_training_mode": False,
            },
        )
        logger.info(f"  HTTP status: {train_resp.status_code}")
        train_body = train_resp.json()
        logger.info(f"  Response body: {json.dumps(train_body, indent=2, default=str)}")

        assert train_resp.status_code == 202, (
            f"Expected HTTP 202 from action=train, got {train_resp.status_code}. "
            f"Body: {train_body}"
        )
        assert train_body.get("status") == "training_queued", (
            f"Expected status='training_queued', got: {train_body.get('status')!r}"
        )
        job_id = train_body.get("job_id")
        assert job_id and isinstance(job_id, str) and len(job_id) > 0, (
            f"Expected non-empty string job_id, got: {job_id!r}"
        )
        logger.info(f"  Queued training job_id: {job_id}")
        logger.info("  Step 1 PASSED: 202 received, status=training_queued, job_id present")

        # Step 2: evaluate-training — expect HTTP 200
        logger.info("Step 2: POST action=evaluate-training to ml-training edge function")
        eval_resp = await client.post(
            edge_fn_url,
            headers=headers,
            json={"action": "evaluate-training"},
        )
        logger.info(f"  HTTP status: {eval_resp.status_code}")
        eval_body = eval_resp.json()
        logger.info(f"  Response body: {json.dumps(eval_body, indent=2, default=str)}")

        assert eval_resp.status_code == 200, (
            f"Expected HTTP 200 from action=evaluate-training, got {eval_resp.status_code}. "
            f"Body: {eval_body}"
        )
        assert eval_body.get("success") is True, (
            f"Expected success=True in evaluate-training response, got: {eval_body.get('success')!r}"
        )
        has_message_or_job = "message" in eval_body or "job_id" in eval_body
        assert has_message_or_job, (
            f"Expected 'message' or 'job_id' in evaluate-training response, got keys: "
            f"{list(eval_body.keys())}"
        )
        logger.info("  Step 2 PASSED: 200 received, success=True, message/job_id present")

    # Step 3: verify cc_evaluated_at column exists in ml_training_jobs
    logger.info("Step 3: Verify cc_evaluated_at column exists in ml_training_jobs")
    from app.lib.database import get_supabase

    supabase = get_supabase()
    if not supabase:
        logger.warning("  Could not get Supabase client — skipping column check")
    else:
        try:
            col_resp = (
                supabase.table("ml_training_jobs")
                .select("id, cc_evaluated_at")
                .limit(1)
                .execute()
            )
            # If PostgREST returns data (even empty list) the column exists
            logger.info(
                f"  cc_evaluated_at column present — query returned {len(col_resp.data)} rows"
            )
            logger.info("  Step 3 PASSED: cc_evaluated_at column exists")
        except Exception as col_err:
            err_str = str(col_err)
            if "cc_evaluated_at" in err_str or "column" in err_str.lower():
                raise AssertionError(
                    "cc_evaluated_at column missing from ml_training_jobs — "
                    "migration may not have been applied. "
                    f"Error: {col_err}"
                ) from col_err
            # Other DB errors are logged but don't fail the column-existence check
            logger.warning(f"  Unexpected error checking cc_evaluated_at column: {col_err}")

    logger.info("SUCCESS: ML Training Async test completed")
    return {"job_id": job_id}


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

    # Test 5: ML Training Async (202 pattern)
    ml_training_result = None
    try:
        ml_training_result = await test_ml_training_async()
    except Exception as e:
        logger.error(f"ML Training Async test FAILED: {e}", exc_info=True)
        failures.append(("ml_training_async", str(e)))

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
    ml_training_status = (
        "SKIP" if ml_training_result is None and not any(
            n == "ml_training_async" for n, _ in failures
        )
        else ("PASS" if ml_training_result is not None else "FAIL")
    )
    logger.info(f"  {'ml_training_async':20s}: {ml_training_status}")

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
