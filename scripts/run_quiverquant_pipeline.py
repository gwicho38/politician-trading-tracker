#!/usr/bin/env python3
"""
Run the full pipeline for QuiverQuant data.

Fetches, cleans, normalizes, and publishes congressional trading data.
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig
from politician_trading.pipeline.orchestrator import PipelineOrchestrator
from politician_trading.pipeline.base import PipelineContext


async def main():
    """Run QuiverQuant pipeline"""

    print("=" * 70)
    print("QuiverQuant Congressional Trading Pipeline")
    print("=" * 70)
    print()

    # Get API key from environment
    api_key = os.getenv('QUIVERQUANT_API_KEY')
    if not api_key:
        print("❌ QUIVERQUANT_API_KEY not found in environment")
        print("   Run: export QUIVERQUANT_API_KEY=<your-key>")
        return 1

    print(f"✓ QuiverQuant API key found")
    print()

    # Get database connection
    config = SupabaseConfig.from_env()
    db = create_client(config.url, config.service_role_key)

    print("✓ Connected to Supabase")
    print()

    # Create pipeline orchestrator
    pipeline = PipelineOrchestrator(
        lookback_days=7,  # Fetch last 7 days
        batch_ingestion=False,
        batch_size=50,
        strict_cleaning=False,
        skip_duplicates=True
    )

    print("✓ Pipeline orchestrator initialized")
    print(f"  Lookback: 7 days")
    print(f"  Batch size: 50")
    print(f"  Skip duplicates: Yes")
    print()

    # Create pipeline context
    context = PipelineContext(
        source_name="QuiverQuant",
        source_type="quiverquant",
        job_id=f"quiver_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        config={'api_key': api_key},
        db_client=db  # Pass db_client for storage operations
    )

    print("=" * 70)
    print("Starting Pipeline Execution")
    print("=" * 70)
    print()

    try:
        # Run pipeline
        result = await pipeline.run(
            source_name=context.source_name,
            source_type=context.source_type,
            config=context.config,
            job_id=context.job_id,
            db_client=db  # Pass db_client for storage operations
        )

        print()
        print("=" * 70)
        print("Pipeline Execution Complete")
        print("=" * 70)
        print()

        # Display results
        print("Summary:")
        print("-" * 70)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Duration: {result.get('total_duration_seconds', 0):.2f}s")
        print()

        # Stage results
        stages = result.get('stages', {})
        for stage_name, stage_result in stages.items():
            print(f"{stage_name.upper()}:")
            metrics = stage_result.get('metrics', {})
            print(f"  Input: {metrics.get('records_input', 0)}")
            print(f"  Output: {metrics.get('records_output', 0)}")
            print(f"  Failed: {metrics.get('records_failed', 0)}")
            print(f"  Duration: {metrics.get('duration_seconds', 0):.2f}s")

            errors = stage_result.get('errors', [])
            if errors:
                print(f"  Errors: {len(errors)}")
                for error in errors[:3]:
                    print(f"    - {error}")

            print()

        # Overall metrics
        print("Overall:")
        print("-" * 70)

        # Get detailed stats from top-level summary (set by orchestrator)
        summary = result.get('summary', {})
        if summary:
            new_count = summary.get('disclosures_inserted', 0)
            updated_count = summary.get('disclosures_updated', 0)
            skipped_count = summary.get('disclosures_skipped', 0)
            total_imported = new_count + updated_count

            print(f"✓ Successfully processed {total_imported} trading disclosures")
            if new_count > 0:
                print(f"  - {new_count} new disclosures")
            if updated_count > 0:
                print(f"  - {updated_count} updated disclosures")
            if skipped_count > 0:
                print(f"  - {skipped_count} skipped (duplicates)")
        else:
            # Fallback to metrics if summary not available
            total_imported = stages.get('publishing', {}).get('metrics', {}).get('records_output', 0)
            print(f"✓ Successfully processed {total_imported} trading disclosures")
        print()

        # Check for warnings
        warnings = result.get('warnings', [])
        if warnings:
            print("Warnings:")
            for warning in warnings[:5]:
                print(f"  ⚠️  {warning}")
            print()

        return 0

    except Exception as e:
        print()
        print("=" * 70)
        print("Pipeline Failed")
        print("=" * 70)
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
