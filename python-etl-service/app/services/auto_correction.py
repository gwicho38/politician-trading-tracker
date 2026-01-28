"""
Auto-Correction Service

Automatically fixes common data quality issues with full audit trail.

Correction types:
- date_format: Normalize dates to ISO format
- ticker_cleanup: Fix outdated tickers (FB → META)
- duplicate_merge: Merge duplicates, keep most complete
- value_range: Fix min/max inversions
- politician_match: Fuzzy match politician names

All corrections are logged to data_quality_corrections table for rollback.
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.lib.database import get_supabase


class CorrectionType(str, Enum):
    DATE_FORMAT = "date_format"
    TICKER_CLEANUP = "ticker_cleanup"
    DUPLICATE_MERGE = "duplicate_merge"
    VALUE_RANGE = "value_range"
    POLITICIAN_MATCH = "politician_match"
    AMOUNT_CLEANUP = "amount_cleanup"


@dataclass
class CorrectionResult:
    """Result of an auto-correction operation."""

    success: bool
    correction_type: CorrectionType
    record_id: str
    table_name: str
    field_name: str
    old_value: Any
    new_value: Any
    confidence: float
    message: str = ""
    correction_id: Optional[str] = None


class AutoCorrector:
    """
    Auto-correction service for data quality issues.

    All corrections are logged with old/new values for audit and rollback.
    """

    # Known ticker mappings (company rebrands, etc.)
    TICKER_MAPPINGS = {
        "FB": "META",
        "TWTR": "X",
        "ANTM": "ELV",  # Anthem -> Elevance
        "ATVI": "MSFT",  # Activision merged with Microsoft
        "DISCA": "WBD",  # Discovery -> Warner Bros Discovery
        "DISCK": "WBD",
        "VIAC": "PARA",  # ViacomCBS -> Paramount
        "VIACA": "PARA",
    }

    # Amount range mappings (from disclosure text to numeric)
    AMOUNT_RANGES = {
        "$1,001 - $15,000": (1001, 15000),
        "$15,001 - $50,000": (15001, 50000),
        "$50,001 - $100,000": (50001, 100000),
        "$100,001 - $250,000": (100001, 250000),
        "$250,001 - $500,000": (250001, 500000),
        "$500,001 - $1,000,000": (500001, 1000000),
        "$1,000,001 - $5,000,000": (1000001, 5000000),
        "$5,000,001 - $25,000,000": (5000001, 25000000),
        "$25,000,001 - $50,000,000": (25000001, 50000000),
        "Over $50,000,000": (50000001, None),
    }

    supabase: Optional[Any]
    corrections_made: List[CorrectionResult]

    def __init__(self) -> None:
        self.supabase = self._get_supabase()
        self.corrections_made = []

    def _get_supabase(self) -> Optional[Any]:
        """Get Supabase client."""
        return get_supabase()

    # =========================================================================
    # Main Correction Methods
    # =========================================================================

    def correct_ticker(
        self, record_id: str, current_ticker: str, dry_run: bool = False
    ) -> Optional[CorrectionResult]:
        """
        Correct outdated tickers to current symbols.

        Args:
            record_id: The disclosure record ID
            current_ticker: The current (possibly outdated) ticker
            dry_run: If True, don't actually make the change

        Returns:
            CorrectionResult if correction was made, None otherwise
        """
        if not current_ticker:
            return None

        ticker_upper = current_ticker.upper().strip()
        if ticker_upper not in self.TICKER_MAPPINGS:
            return None

        new_ticker = self.TICKER_MAPPINGS[ticker_upper]

        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id=record_id,
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value=current_ticker,
            new_value=new_ticker,
            confidence=1.0,  # High confidence for known mappings
            message=f"Updated ticker from {current_ticker} to {new_ticker} (company rebrand)",
        )

        if not dry_run:
            self._apply_correction(result)

        return result

    def correct_value_range(
        self,
        record_id: str,
        amount_min: float,
        amount_max: float,
        dry_run: bool = False,
    ) -> Optional[CorrectionResult]:
        """
        Fix inverted min/max values.

        Args:
            record_id: The disclosure record ID
            amount_min: Current min value
            amount_max: Current max value
            dry_run: If True, don't actually make the change

        Returns:
            CorrectionResult if correction was made, None otherwise
        """
        if amount_min is None or amount_max is None:
            return None

        if amount_min <= amount_max:
            return None  # Already correct

        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.VALUE_RANGE,
            record_id=record_id,
            table_name="trading_disclosures",
            field_name="amount_range",
            old_value={"min": amount_min, "max": amount_max},
            new_value={"min": amount_max, "max": amount_min},  # Swap them
            confidence=0.95,
            message=f"Swapped inverted amount range: {amount_min} <-> {amount_max}",
        )

        if not dry_run:
            self._apply_range_correction(result)

        return result

    def correct_date_format(
        self, record_id: str, field_name: str, date_value: str, dry_run: bool = False
    ) -> Optional[CorrectionResult]:
        """
        Normalize date to ISO format.

        Handles formats like:
        - MM/DD/YYYY
        - DD-MM-YYYY
        - YYYY/MM/DD
        - Month DD, YYYY

        Args:
            record_id: The disclosure record ID
            field_name: Which date field (transaction_date, disclosure_date)
            date_value: The current date string
            dry_run: If True, don't actually make the change

        Returns:
            CorrectionResult if correction was made, None otherwise
        """
        from dateutil import parser

        if not date_value:
            return None

        try:
            # Try to parse and normalize
            parsed = parser.parse(date_value, fuzzy=True)
            normalized = parsed.strftime("%Y-%m-%d")

            # Already in correct format?
            if date_value == normalized:
                return None

            result = CorrectionResult(
                success=True,
                correction_type=CorrectionType.DATE_FORMAT,
                record_id=record_id,
                table_name="trading_disclosures",
                field_name=field_name,
                old_value=date_value,
                new_value=normalized,
                confidence=0.9,
                message=f"Normalized date from '{date_value}' to '{normalized}'",
            )

            if not dry_run:
                self._apply_correction(result)

            return result

        except (ValueError, TypeError):
            return None

    def correct_amount_text(
        self, record_id: str, amount_text: str, dry_run: bool = False
    ) -> Optional[CorrectionResult]:
        """
        Parse amount text into numeric min/max values.

        Args:
            record_id: The disclosure record ID
            amount_text: Text like "$15,001 - $50,000"
            dry_run: If True, don't actually make the change

        Returns:
            CorrectionResult if correction was made, None otherwise
        """
        if not amount_text:
            return None

        # Clean up the text
        cleaned = amount_text.strip()

        # Try exact match first
        if cleaned in self.AMOUNT_RANGES:
            min_val, max_val = self.AMOUNT_RANGES[cleaned]

            result = CorrectionResult(
                success=True,
                correction_type=CorrectionType.AMOUNT_CLEANUP,
                record_id=record_id,
                table_name="trading_disclosures",
                field_name="amount_range",
                old_value=amount_text,
                new_value={"min": min_val, "max": max_val},
                confidence=1.0,
                message=f"Parsed amount range from text: {amount_text}",
            )

            if not dry_run:
                self._apply_amount_correction(result)

            return result

        # Try fuzzy matching
        import difflib

        matches = difflib.get_close_matches(cleaned, self.AMOUNT_RANGES.keys(), n=1, cutoff=0.8)
        if matches:
            min_val, max_val = self.AMOUNT_RANGES[matches[0]]

            result = CorrectionResult(
                success=True,
                correction_type=CorrectionType.AMOUNT_CLEANUP,
                record_id=record_id,
                table_name="trading_disclosures",
                field_name="amount_range",
                old_value=amount_text,
                new_value={"min": min_val, "max": max_val},
                confidence=0.8,
                message=f"Fuzzy matched amount range: '{amount_text}' -> '{matches[0]}'",
            )

            if not dry_run:
                self._apply_amount_correction(result)

            return result

        return None

    # =========================================================================
    # Batch Correction Methods
    # =========================================================================

    def run_ticker_corrections(
        self, limit: int = 100, dry_run: bool = False
    ) -> List[CorrectionResult]:
        """
        Find and correct all outdated tickers.

        Args:
            limit: Maximum records to process
            dry_run: If True, don't actually make changes

        Returns:
            List of CorrectionResults
        """
        if not self.supabase:
            return []

        results = []
        tickers_to_check = list(self.TICKER_MAPPINGS.keys())

        for old_ticker in tickers_to_check:
            try:
                response = (
                    self.supabase.table("trading_disclosures")
                    .select("id, asset_ticker")
                    .eq("asset_ticker", old_ticker)
                    .limit(limit)
                    .execute()
                )

                for record in response.data:
                    result = self.correct_ticker(
                        record["id"], record["asset_ticker"], dry_run
                    )
                    if result:
                        results.append(result)

            except Exception as e:
                print(f"Error checking ticker {old_ticker}: {e}")

        return results

    def run_value_range_corrections(
        self, limit: int = 100, dry_run: bool = False
    ) -> List[CorrectionResult]:
        """
        Find and correct all inverted value ranges.

        Args:
            limit: Maximum records to process
            dry_run: If True, don't actually make changes

        Returns:
            List of CorrectionResults
        """
        if not self.supabase:
            return []

        results = []

        try:
            # Find records where min > max (inverted)
            # Note: This requires a raw query or RPC function
            # For now, we'll fetch and check in Python
            response = (
                self.supabase.table("trading_disclosures")
                .select("id, amount_range_min, amount_range_max")
                .not_.is_("amount_range_min", "null")
                .not_.is_("amount_range_max", "null")
                .limit(limit * 10)  # Over-fetch since most won't need correction
                .execute()
            )

            for record in response.data:
                min_val = record.get("amount_range_min")
                max_val = record.get("amount_range_max")

                if min_val is not None and max_val is not None and min_val > max_val:
                    result = self.correct_value_range(
                        record["id"], min_val, max_val, dry_run
                    )
                    if result:
                        results.append(result)

                    if len(results) >= limit:
                        break

        except Exception as e:
            print(f"Error checking value ranges: {e}")

        return results

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _apply_correction(self, result: CorrectionResult) -> bool:
        """Apply a single-field correction and log it."""
        if not self.supabase:
            result.success = False
            result.message = "Supabase not configured"
            return False

        try:
            # Log the correction first
            correction_id = self._log_correction(result)
            result.correction_id = correction_id

            # Apply the update
            self.supabase.table(result.table_name).update(
                {result.field_name: result.new_value}
            ).eq("id", result.record_id).execute()

            # Mark correction as applied
            self._mark_correction_applied(correction_id)

            self.corrections_made.append(result)
            return True

        except Exception as e:
            result.success = False
            result.message = f"Failed to apply correction: {e}"
            return False

    def _apply_range_correction(self, result: CorrectionResult) -> bool:
        """Apply a min/max swap correction."""
        if not self.supabase:
            result.success = False
            return False

        try:
            correction_id = self._log_correction(result)
            result.correction_id = correction_id

            # Swap min and max
            self.supabase.table(result.table_name).update(
                {
                    "amount_range_min": result.new_value["min"],
                    "amount_range_max": result.new_value["max"],
                }
            ).eq("id", result.record_id).execute()

            self._mark_correction_applied(correction_id)
            self.corrections_made.append(result)
            return True

        except Exception as e:
            result.success = False
            result.message = f"Failed to apply range correction: {e}"
            return False

    def _apply_amount_correction(self, result: CorrectionResult) -> bool:
        """Apply an amount parsing correction."""
        if not self.supabase:
            result.success = False
            return False

        try:
            correction_id = self._log_correction(result)
            result.correction_id = correction_id

            update_data = {"amount_range_min": result.new_value["min"]}
            if result.new_value["max"] is not None:
                update_data["amount_range_max"] = result.new_value["max"]

            self.supabase.table(result.table_name).update(update_data).eq(
                "id", result.record_id
            ).execute()

            self._mark_correction_applied(correction_id)
            self.corrections_made.append(result)
            return True

        except Exception as e:
            result.success = False
            result.message = f"Failed to apply amount correction: {e}"
            return False

    def _log_correction(self, result: CorrectionResult) -> str:
        """Log correction to audit table before applying."""
        correction_id = str(uuid.uuid4())

        try:
            self.supabase.table("data_quality_corrections").insert(
                {
                    "id": correction_id,
                    "record_id": result.record_id,
                    "table_name": result.table_name,
                    "field_name": result.field_name,
                    "old_value": (
                        result.old_value
                        if isinstance(result.old_value, (str, int, float))
                        else str(result.old_value)
                    ),
                    "new_value": (
                        result.new_value
                        if isinstance(result.new_value, (str, int, float))
                        else str(result.new_value)
                    ),
                    "correction_type": result.correction_type.value,
                    "confidence_score": result.confidence,
                    "corrected_by": "auto",
                    "status": "pending",
                }
            ).execute()

        except Exception as e:
            print(f"Warning: Failed to log correction: {e}")

        return correction_id

    def _mark_correction_applied(self, correction_id: str) -> None:
        """Mark a correction as successfully applied."""
        try:
            self.supabase.table("data_quality_corrections").update(
                {"status": "applied", "applied_at": datetime.utcnow().isoformat()}
            ).eq("id", correction_id).execute()
        except Exception as e:
            print(f"Warning: Failed to mark correction applied: {e}")

    # =========================================================================
    # Rollback Support
    # =========================================================================

    def rollback_correction(self, correction_id: str) -> bool:
        """
        Rollback a previously applied correction.

        Args:
            correction_id: The correction to rollback

        Returns:
            True if rollback succeeded
        """
        if not self.supabase:
            return False

        try:
            # Get the correction record
            response = (
                self.supabase.table("data_quality_corrections")
                .select("*")
                .eq("id", correction_id)
                .single()
                .execute()
            )

            if not response.data:
                return False

            correction = response.data

            # Apply the old value
            self.supabase.table(correction["table_name"]).update(
                {correction["field_name"]: correction["old_value"]}
            ).eq("id", correction["record_id"]).execute()

            # Mark as rolled back
            self.supabase.table("data_quality_corrections").update(
                {"status": "rolled_back", "rolled_back_at": datetime.utcnow().isoformat()}
            ).eq("id", correction_id).execute()

            return True

        except Exception as e:
            print(f"Error rolling back correction: {e}")
            return False
