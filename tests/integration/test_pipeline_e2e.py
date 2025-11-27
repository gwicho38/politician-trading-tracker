#!/usr/bin/env python3
"""
End-to-end pipeline test script.

This script tests the full pipeline with the US Senate source.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from politician_trading.pipeline import PipelineOrchestrator


async def test_pipeline():
    """Test the pipeline end-to-end"""

    print("=" * 60)
    print("Testing Pipeline End-to-End with US Senate Source")
    print("=" * 60)
    print()

    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        lookback_days=7  # Only fetch last 7 days for testing
    )

    print("✓ Created PipelineOrchestrator")
    print()

    # Run pipeline
    print("Running pipeline...")
    print("-" * 60)

    try:
        result = await orchestrator.run(
            source_name="US Senate",
            source_type="us_senate"
        )

        print()
        print("=" * 60)
        print("Pipeline Execution Complete!")
        print("=" * 60)
        print()

        # Print results
        print(f"Overall Status: {result.get('overall_status', 'unknown')}")
        print(f"Total Duration: {result.get('duration_seconds', 0):.2f}s")
        print()

        # Print stage results
        for stage_name, stage_result in result.get('stages', {}).items():
            print(f"\n{stage_name.upper()}:")
            print(f"  Status: {stage_result.get('status', 'unknown')}")

            metrics = stage_result.get('metrics', {})
            print(f"  Input: {metrics.get('records_input', 0)}")
            print(f"  Output: {metrics.get('records_output', 0)}")
            print(f"  Failed: {metrics.get('records_failed', 0)}")
            print(f"  Skipped: {metrics.get('records_skipped', 0)}")
            print(f"  Duration: {metrics.get('duration_seconds', 0):.2f}s")

            if stage_result.get('errors'):
                print(f"  Errors: {len(stage_result['errors'])}")
                for error in stage_result['errors'][:3]:  # Show first 3 errors
                    print(f"    - {error}")

            if stage_result.get('warnings'):
                print(f"  Warnings: {len(stage_result['warnings'])}")

        print()
        print("=" * 60)

        # Check if successful
        if result.get('overall_status') in ['success', 'partial_success']:
            print("✅ TEST PASSED: Pipeline executed successfully!")
            return 0
        else:
            print("❌ TEST FAILED: Pipeline did not complete successfully")
            return 1

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ TEST FAILED: Exception occurred")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_pipeline())
    sys.exit(exit_code)
