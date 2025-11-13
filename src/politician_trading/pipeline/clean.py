"""
Cleaning stage - Validates and cleans raw data.
"""

from typing import List, Optional, Set
from datetime import datetime
import logging
import re

from .base import (
    PipelineStage,
    PipelineResult,
    PipelineContext,
    PipelineMetrics,
    PipelineStatus,
    RawDisclosure,
    CleanedDisclosure
)

logger = logging.getLogger(__name__)


class CleaningStage(PipelineStage[CleanedDisclosure]):
    """
    Cleaning stage - Validates and cleans raw disclosure data.

    This stage:
    1. Validates required fields are present
    2. Removes duplicates
    3. Cleans text fields (trim, normalize)
    4. Validates data types and formats
    5. Filters out invalid records
    """

    # Required fields for a valid disclosure
    REQUIRED_FIELDS = {
        "politician_name",
        "transaction_date",
        "disclosure_date",
        "asset_name",
        "transaction_type"
    }

    # Valid transaction types
    VALID_TRANSACTION_TYPES = {
        "purchase", "sale", "exchange",
        "option_purchase", "option_sale", "option_exercise"
    }

    def __init__(
        self,
        remove_duplicates: bool = True,
        strict_validation: bool = False
    ):
        super().__init__("cleaning")
        self.remove_duplicates = remove_duplicates
        self.strict_validation = strict_validation
        self._seen_hashes: Set[str] = set()

    async def process(
        self,
        data: List[RawDisclosure],
        context: PipelineContext
    ) -> PipelineResult[CleanedDisclosure]:
        """
        Clean and validate raw disclosures.

        Args:
            data: List of RawDisclosure objects from ingestion
            context: Pipeline context

        Returns:
            PipelineResult containing CleanedDisclosure objects
        """
        start_time = datetime.utcnow()
        metrics = PipelineMetrics()
        cleaned_disclosures: List[CleanedDisclosure] = []

        metrics.records_input = len(data)
        self.logger.info(f"Starting cleaning of {len(data)} raw disclosures")

        for i, raw in enumerate(data):
            try:
                # Validate required fields
                if not self._has_required_fields(raw.raw_data):
                    missing = self.REQUIRED_FIELDS - set(raw.raw_data.keys())
                    self.logger.warning(
                        f"Record {i} missing required fields: {missing}"
                    )
                    metrics.records_skipped += 1
                    metrics.warnings.append(f"Record {i}: Missing fields {missing}")
                    continue

                # Check for duplicates
                if self.remove_duplicates:
                    record_hash = self._compute_hash(raw.raw_data)
                    if record_hash in self._seen_hashes:
                        self.logger.debug(f"Record {i} is duplicate, skipping")
                        metrics.records_skipped += 1
                        continue
                    self._seen_hashes.add(record_hash)

                # Clean and validate
                cleaned = self._clean_record(raw)

                if cleaned:
                    cleaned_disclosures.append(cleaned)
                    metrics.records_output += 1
                else:
                    metrics.records_failed += 1
                    metrics.errors.append(f"Record {i}: Cleaning failed")

            except Exception as e:
                self.logger.error(f"Error cleaning record {i}: {e}", exc_info=True)
                metrics.records_failed += 1
                metrics.errors.append(f"Record {i}: {str(e)}")

        # Calculate metrics
        metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        # Determine status
        if metrics.records_output > 0:
            if metrics.records_failed == 0 and metrics.records_skipped == 0:
                status = PipelineStatus.SUCCESS
            else:
                status = PipelineStatus.PARTIAL_SUCCESS
        else:
            status = PipelineStatus.FAILED
            metrics.errors.append("No records successfully cleaned")

        self.logger.info(
            f"Cleaning complete: {metrics.records_output} cleaned, "
            f"{metrics.records_skipped} skipped, "
            f"{metrics.records_failed} failed, "
            f"{metrics.duration_seconds:.2f}s"
        )

        return self._create_result(
            status=status,
            data=cleaned_disclosures,
            context=context,
            metrics=metrics
        )

    def _has_required_fields(self, data: dict) -> bool:
        """Check if record has all required fields"""
        return all(
            field in data and data[field] is not None and data[field] != ""
            for field in self.REQUIRED_FIELDS
        )

    def _compute_hash(self, data: dict) -> str:
        """Compute hash for duplicate detection"""
        import hashlib

        # Create a stable hash from key fields
        key_fields = [
            str(data.get("politician_name", "")),
            str(data.get("transaction_date", "")),
            str(data.get("asset_name", "")),
            str(data.get("transaction_type", "")),
            str(data.get("amount", ""))
        ]

        hash_str = "|".join(key_fields)
        return hashlib.md5(hash_str.encode()).hexdigest()

    def _clean_record(self, raw: RawDisclosure) -> Optional[CleanedDisclosure]:
        """
        Clean a single raw disclosure.

        Returns None if record is invalid.
        """
        try:
            data = raw.raw_data

            # Clean politician name
            politician_name = self._clean_text(data["politician_name"])
            if not politician_name:
                self.logger.warning("Empty politician name after cleaning")
                return None

            # Parse and validate dates
            transaction_date = self._parse_date(data["transaction_date"])
            disclosure_date = self._parse_date(data["disclosure_date"])

            if not transaction_date or not disclosure_date:
                self.logger.warning("Invalid dates")
                return None

            # Clean asset name
            asset_name = self._clean_text(data["asset_name"])
            if not asset_name:
                self.logger.warning("Empty asset name after cleaning")
                return None

            # Clean and validate transaction type
            transaction_type = self._clean_transaction_type(data["transaction_type"])
            if not transaction_type:
                self.logger.warning(f"Invalid transaction type: {data['transaction_type']}")
                if self.strict_validation:
                    return None

            # Optional fields - clean but don't fail if missing
            asset_ticker = self._clean_text(data.get("asset_ticker"))
            asset_type = self._clean_text(data.get("asset_type"))
            amount_text = self._clean_text(data.get("amount"))

            return CleanedDisclosure(
                source=raw.source,
                politician_name=politician_name,
                transaction_date=transaction_date,
                disclosure_date=disclosure_date,
                asset_name=asset_name,
                transaction_type=transaction_type,
                asset_ticker=asset_ticker,
                asset_type=asset_type,
                amount_text=amount_text,
                source_url=raw.source_url,
                source_document_id=raw.source_document_id,
                raw_data=data
            )

        except Exception as e:
            self.logger.error(f"Error cleaning record: {e}", exc_info=True)
            return None

    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text field"""
        if not text:
            return None

        # Convert to string if needed
        text = str(text)

        # Strip whitespace
        text = text.strip()

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove null bytes
        text = text.replace('\x00', '')

        return text if text else None

    def _parse_date(self, date_value) -> Optional[datetime]:
        """Parse date from various formats"""
        if isinstance(date_value, datetime):
            return date_value

        if not date_value:
            return None

        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        date_str = str(date_value).strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        self.logger.warning(f"Could not parse date: {date_value}")
        return None

    def _clean_transaction_type(self, trans_type: str) -> Optional[str]:
        """Clean and normalize transaction type"""
        if not trans_type:
            return None

        # Normalize to lowercase
        trans_type = str(trans_type).lower().strip()

        # Map common variants
        type_mapping = {
            "buy": "purchase",
            "bought": "purchase",
            "sell": "sale",
            "sold": "sale",
            "swap": "exchange",
            "trade": "exchange",
            "option buy": "option_purchase",
            "option sell": "option_sale",
        }

        trans_type = type_mapping.get(trans_type, trans_type)

        # Validate against known types
        if self.strict_validation and trans_type not in self.VALID_TRANSACTION_TYPES:
            return None

        return trans_type
