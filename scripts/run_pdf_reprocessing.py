#!/usr/bin/env python3
"""
Run PDF reprocessing job.

This script processes PDF-only disclosure records in the background.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from politician_trading.jobs.pdf_reprocessing_job import PDFReprocessingJob


async def main():
    """Run PDF reprocessing job"""

    parser = argparse.ArgumentParser(description='Run PDF reprocessing job')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size')
    parser.add_argument('--max-records', type=int, help='Maximum records to process')
    parser.add_argument('--delay', type=float, default=3.0, help='Delay between records (seconds)')
    parser.add_argument('--batch-delay', type=float, default=30.0, help='Delay between batches (seconds)')
    args = parser.parse_args()

    print("=" * 60)
    print("PDF Reprocessing Job")
    print("=" * 60)
    print()
    print(f"Configuration:")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Max records: {args.max_records or 'unlimited'}")
    print(f"  Delay between records: {args.delay}s")
    print(f"  Delay between batches: {args.batch_delay}s")
    print()
    print("=" * 60)
    print()

    # Create and run job
    job = PDFReprocessingJob(
        batch_size=args.batch_size,
        delay_between_records=args.delay,
        delay_between_batches=args.batch_delay
    )

    stats = await job.run(max_records=args.max_records)

    # Print final statistics
    print()
    print("=" * 60)
    print("Job Complete!")
    print("=" * 60)
    print()
    print(f"Total records: {stats.total_records}")
    print(f"Processed: {stats.processed}")
    print(f"Successful: {stats.successful}")
    print(f"Failed: {stats.failed}")
    print(f"Errors: {stats.errors}")
    print(f"Transactions extracted: {stats.transactions_extracted}")
    print()
    print(f"Duration: {stats.duration_seconds():.2f} seconds")
    print(f"Rate: {stats.records_per_second():.2f} records/second")
    print(f"Success rate: {stats.success_rate():.1f}%")
    print()
    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nJob cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
