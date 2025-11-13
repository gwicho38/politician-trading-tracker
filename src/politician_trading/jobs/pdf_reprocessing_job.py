"""
PDF Reprocessing Background Job.

Processes PDF-only disclosure records in batches with rate limiting,
error handling, and progress tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from supabase import create_client
from ..config import SupabaseConfig
from ..transformers.pdf_parser import SenatePDFParser

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Track processing statistics"""
    total_records: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    errors: int = 0
    transactions_extracted: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return 0.0

    def records_per_second(self) -> float:
        """Calculate processing rate"""
        duration = self.duration_seconds()
        if duration > 0:
            return self.processed / duration
        return 0.0

    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.processed > 0:
            return (self.successful / self.processed) * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_records': self.total_records,
            'processed': self.processed,
            'successful': self.successful,
            'failed': self.failed,
            'errors': self.errors,
            'transactions_extracted': self.transactions_extracted,
            'duration_seconds': self.duration_seconds(),
            'records_per_second': self.records_per_second(),
            'success_rate': self.success_rate()
        }


class PDFReprocessingJob:
    """
    Background job to reprocess PDF-only disclosure records.

    Features:
    - Batch processing with configurable size
    - Rate limiting to avoid overwhelming Senate website
    - Automatic retry on transient errors
    - Progress tracking and logging
    - Database updates with proper error handling
    """

    def __init__(
        self,
        batch_size: int = 50,
        delay_between_records: float = 3.0,
        delay_between_batches: float = 30.0,
        max_retries: int = 2
    ):
        self.batch_size = batch_size
        self.delay_between_records = delay_between_records
        self.delay_between_batches = delay_between_batches
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.stats = ProcessingStats()

    async def run(self, max_records: Optional[int] = None) -> ProcessingStats:
        """
        Run the PDF reprocessing job.

        Args:
            max_records: Maximum number of records to process (None = all)

        Returns:
            ProcessingStats with results
        """
        self.stats = ProcessingStats()
        self.stats.start_time = datetime.utcnow()

        self.logger.info("Starting PDF reprocessing job")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Delay between records: {self.delay_between_records}s")
        self.logger.info(f"Delay between batches: {self.delay_between_batches}s")

        # Get database connection
        config = SupabaseConfig.from_env()
        db = create_client(config.url, config.key)

        # Create PDF parser
        async with SenatePDFParser() as parser:
            batch_num = 0

            while True:
                batch_num += 1

                # Get next batch of records
                records = self._get_next_batch(db, max_records)

                if not records:
                    self.logger.info("No more records to process")
                    break

                self.stats.total_records += len(records)

                self.logger.info(
                    f"Processing batch {batch_num}: {len(records)} records "
                    f"(Total: {self.stats.processed}/{self.stats.total_records})"
                )

                # Process batch
                await self._process_batch(db, parser, records)

                # Check if we've hit max_records limit
                if max_records and self.stats.processed >= max_records:
                    self.logger.info(f"Reached max_records limit: {max_records}")
                    break

                # Delay between batches
                if records:  # More records might be available
                    self.logger.info(f"Waiting {self.delay_between_batches}s before next batch...")
                    await asyncio.sleep(self.delay_between_batches)

        self.stats.end_time = datetime.utcnow()

        self.logger.info("PDF reprocessing job complete")
        self.logger.info(f"Processed: {self.stats.processed} records")
        self.logger.info(f"Successful: {self.stats.successful}")
        self.logger.info(f"Failed: {self.stats.failed}")
        self.logger.info(f"Errors: {self.stats.errors}")
        self.logger.info(f"Transactions extracted: {self.stats.transactions_extracted}")
        self.logger.info(f"Duration: {self.stats.duration_seconds():.2f}s")
        self.logger.info(f"Rate: {self.stats.records_per_second():.2f} records/sec")
        self.logger.info(f"Success rate: {self.stats.success_rate():.1f}%")

        return self.stats

    def _get_next_batch(self, db, max_records: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get next batch of records to process"""
        try:
            limit = self.batch_size
            if max_records:
                remaining = max_records - self.stats.processed
                limit = min(self.batch_size, remaining)

            if limit <= 0:
                return []

            response = db.table("trading_disclosures").select("*").eq(
                "status", "needs_pdf_parsing"
            ).order("transaction_date", desc=True).limit(limit).execute()

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error fetching batch: {e}", exc_info=True)
            return []

    async def _process_batch(
        self,
        db,
        parser: SenatePDFParser,
        records: List[Dict[str, Any]]
    ):
        """Process a batch of records"""
        for i, record in enumerate(records):
            record_id = record['id']
            politician_id = record.get('politician_id')

            self.logger.info(
                f"Processing record {i+1}/{len(records)}: {record_id}"
            )

            try:
                # Update status to 'processing'
                db.table("trading_disclosures").update({
                    "status": "pdf_parsing"
                }).eq("id", record_id).execute()

                # Extract PDF URL
                pdf_url = self._extract_pdf_url(record)

                if not pdf_url:
                    self.logger.warning(f"No PDF URL found for record {record_id}")
                    db.table("trading_disclosures").update({
                        "status": "pdf_parse_failed"
                    }).eq("id", record_id).execute()
                    self.stats.failed += 1
                    self.stats.processed += 1
                    continue

                # Get politician name
                politician_name = await self._get_politician_name(db, politician_id)

                # Parse PDF with retries
                transactions = await self._parse_with_retry(
                    parser,
                    pdf_url,
                    politician_name
                )

                # Process results
                if transactions:
                    await self._handle_successful_parse(
                        db, record_id, politician_id, transactions
                    )
                    self.stats.successful += 1
                    self.stats.transactions_extracted += len(transactions)
                else:
                    await self._handle_failed_parse(db, record_id)
                    self.stats.failed += 1

                self.stats.processed += 1

                # Log progress
                if self.stats.processed % 10 == 0:
                    self.logger.info(
                        f"Progress: {self.stats.processed} records, "
                        f"{self.stats.successful} successful, "
                        f"{self.stats.transactions_extracted} transactions, "
                        f"{self.stats.records_per_second():.2f} rec/sec"
                    )

            except Exception as e:
                self.logger.error(
                    f"Error processing record {record_id}: {e}",
                    exc_info=True
                )
                db.table("trading_disclosures").update({
                    "status": "pdf_parse_error"
                }).eq("id", record_id).execute()
                self.stats.errors += 1
                self.stats.processed += 1

            # Delay between records
            if i < len(records) - 1:  # Don't delay after last record
                await asyncio.sleep(self.delay_between_records)

    def _extract_pdf_url(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract PDF URL from record"""
        # Try raw_data field
        raw_data = record.get('raw_data', {})

        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except (json.JSONDecodeError, ValueError):
                raw_data = {}

        pdf_url = raw_data.get('ptr_link') or raw_data.get('pdf_url')

        # Fallback to source_url
        if not pdf_url:
            pdf_url = record.get('source_url')

        return pdf_url

    async def _get_politician_name(self, db, politician_id: str) -> str:
        """Get politician name from database"""
        try:
            response = db.table("politicians").select("full_name,first_name,last_name").eq(
                "id", politician_id
            ).execute()

            if response.data and len(response.data) > 0:
                politician = response.data[0]
                return politician.get('full_name') or f"{politician.get('first_name')} {politician.get('last_name')}"

        except Exception as e:
            self.logger.warning(f"Could not fetch politician name: {e}")

        return "Unknown"

    async def _parse_with_retry(
        self,
        parser: SenatePDFParser,
        pdf_url: str,
        politician_name: str
    ) -> List[Dict[str, Any]]:
        """Parse PDF with retry logic"""

        for attempt in range(self.max_retries + 1):
            try:
                transactions = await parser.parse_pdf_url(pdf_url, politician_name)
                return transactions

            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"PDF parsing attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"PDF parsing failed after {self.max_retries + 1} attempts: {e}"
                    )

        return []

    async def _handle_successful_parse(
        self,
        db,
        record_id: str,
        politician_id: str,
        transactions: List[Dict[str, Any]]
    ):
        """Handle successful PDF parse - create new disclosure records"""
        self.logger.info(f"Successfully extracted {len(transactions)} transactions")

        # Delete the placeholder record
        db.table("trading_disclosures").delete().eq("id", record_id).execute()

        # Insert new records for each transaction
        for transaction in transactions:
            try:
                # Convert transaction to disclosure record
                disclosure_data = {
                    "politician_id": politician_id,
                    "transaction_date": transaction.get('transaction_date'),
                    "disclosure_date": transaction.get('disclosure_date') or transaction.get('transaction_date'),
                    "asset_name": transaction.get('asset_name'),
                    "asset_ticker": transaction.get('asset_ticker'),
                    "asset_type": transaction.get('asset_type', 'stock'),
                    "transaction_type": transaction.get('transaction_type'),
                    "amount": transaction.get('amount'),
                    "source": "us_senate_pdf",
                    "source_url": transaction.get('source_url'),
                    "raw_data": transaction,
                    "status": "processed"
                }

                db.table("trading_disclosures").insert(disclosure_data).execute()

            except Exception as e:
                self.logger.error(f"Error inserting transaction: {e}")

    async def _handle_failed_parse(self, db, record_id: str):
        """Handle failed PDF parse"""
        self.logger.warning("No transactions extracted from PDF")

        db.table("trading_disclosures").update({
            "status": "pdf_parse_failed"
        }).eq("id", record_id).execute()
