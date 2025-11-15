"""
Data validation utilities for House financial disclosures.

This module provides validation rules for ensuring data quality and
identifying potential issues in parsed disclosure data.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DisclosureValidator:
    """Validates disclosure data for completeness and accuracy"""

    # Mandatory fields for transactions
    REQUIRED_TRANSACTION_FIELDS = [
        "transaction_type",
        "asset_name",
    ]

    # Reasonable value thresholds
    MAX_REASONABLE_TRANSACTION_VALUE = Decimal("50000000")  # $50M
    MIN_REASONABLE_TRANSACTION_VALUE = Decimal("1")

    def __init__(self):
        self.validation_stats = {
            "total_validated": 0,
            "passed": 0,
            "warnings": 0,
            "errors": 0,
        }

    def validate_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single transaction disclosure.

        Args:
            transaction: Transaction dictionary

        Returns:
            Dict with validation results:
            {
                "is_valid": bool,
                "warnings": List[str],
                "errors": List[str],
                "quality_score": float (0.0-1.0)
            }
        """
        warnings = []
        errors = []

        # Check mandatory fields
        missing_fields = self._check_mandatory_fields(transaction, self.REQUIRED_TRANSACTION_FIELDS)
        if missing_fields:
            errors.extend([f"Missing required field: {field}" for field in missing_fields])

        # Validate date sequence
        date_warnings = self._validate_date_sequence(transaction)
        warnings.extend(date_warnings)

        # Validate value ranges
        value_warnings, value_errors = self._validate_value_range(transaction)
        warnings.extend(value_warnings)
        errors.extend(value_errors)

        # Check ticker confidence
        ticker_warnings = self._check_ticker_confidence(transaction)
        warnings.extend(ticker_warnings)

        # Calculate quality score
        quality_score = self._calculate_quality_score(transaction, warnings, errors)

        # Update stats
        self.validation_stats["total_validated"] += 1
        if errors:
            self.validation_stats["errors"] += 1
        elif warnings:
            self.validation_stats["warnings"] += 1
        else:
            self.validation_stats["passed"] += 1

        return {
            "is_valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
            "quality_score": quality_score,
        }

    def validate_capital_gain(self, capital_gain: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a capital gain entry.

        Args:
            capital_gain: Capital gain dictionary

        Returns:
            Validation results dictionary
        """
        warnings = []
        errors = []

        # Check required fields
        if not capital_gain.get("asset_name"):
            errors.append("Missing asset_name")

        if not capital_gain.get("date_sold"):
            errors.append("Missing date_sold")

        # Validate date sequence (sold must be after acquired)
        date_acquired = capital_gain.get("date_acquired")
        date_sold = capital_gain.get("date_sold")

        if date_acquired and date_sold:
            if isinstance(date_acquired, datetime) and isinstance(date_sold, datetime):
                if date_sold < date_acquired:
                    errors.append(f"date_sold ({date_sold}) is before date_acquired ({date_acquired})")

        # Validate gain type matches holding period
        if date_acquired and date_sold and capital_gain.get("gain_type"):
            if isinstance(date_acquired, datetime) and isinstance(date_sold, datetime):
                holding_period = (date_sold - date_acquired).days
                gain_type = capital_gain.get("gain_type")

                if gain_type == "LONG_TERM" and holding_period <= 365:
                    warnings.append(f"Marked LONG_TERM but holding period is {holding_period} days (<= 365)")
                elif gain_type == "SHORT_TERM" and holding_period > 365:
                    warnings.append(f"Marked SHORT_TERM but holding period is {holding_period} days (> 365)")

        quality_score = self._calculate_quality_score(capital_gain, warnings, errors)

        return {
            "is_valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
            "quality_score": quality_score,
        }

    def validate_asset_holding(self, holding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an asset holding entry.

        Args:
            holding: Asset holding dictionary

        Returns:
            Validation results dictionary
        """
        warnings = []
        errors = []

        # Check required fields
        if not holding.get("asset_name"):
            errors.append("Missing asset_name")

        if not holding.get("filing_date"):
            warnings.append("Missing filing_date")

        # Validate value range
        value_low = holding.get("value_low")
        value_high = holding.get("value_high")

        if value_low and value_high:
            if isinstance(value_low, Decimal) and isinstance(value_high, Decimal):
                if value_high < value_low:
                    errors.append(f"value_high ({value_high}) is less than value_low ({value_low})")

        # Check for unreasonably high values
        if value_high and isinstance(value_high, Decimal):
            if value_high > self.MAX_REASONABLE_TRANSACTION_VALUE:
                warnings.append(f"Very high value_high: ${value_high:,}")

        quality_score = self._calculate_quality_score(holding, warnings, errors)

        return {
            "is_valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
            "quality_score": quality_score,
        }

    def check_duplicate_transactions(
        self, transactions: List[Dict[str, Any]], threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """
        Identify potential duplicate transactions.

        Args:
            transactions: List of transaction dictionaries
            threshold: Similarity threshold (0.0-1.0) for flagging duplicates

        Returns:
            List of potential duplicate pairs with similarity scores
        """
        duplicates = []

        for i, trans1 in enumerate(transactions):
            for j, trans2 in enumerate(transactions[i + 1 :], start=i + 1):
                similarity = self._calculate_similarity(trans1, trans2)
                if similarity >= threshold:
                    duplicates.append(
                        {
                            "index1": i,
                            "index2": j,
                            "transaction1": trans1,
                            "transaction2": trans2,
                            "similarity": similarity,
                        }
                    )

        if duplicates:
            logger.warning(f"Found {len(duplicates)} potential duplicate transaction pairs")

        return duplicates

    def flag_outliers(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flag transactions with unusual characteristics.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            List of flagged transactions with reasons
        """
        outliers = []

        for i, trans in enumerate(transactions):
            flags = []

            # Flag very large transactions
            value_high = trans.get("value_high")
            if value_high and isinstance(value_high, Decimal):
                if value_high > Decimal("1000000"):  # $1M+
                    flags.append(f"Large transaction: ${value_high:,}")

            # Flag very low confidence ticker resolutions
            ticker_confidence = trans.get("ticker_confidence_score")
            if ticker_confidence is not None and ticker_confidence < 0.5:
                flags.append(f"Low ticker confidence: {ticker_confidence:.2f}")

            # Flag missing critical data
            if not trans.get("transaction_date"):
                flags.append("Missing transaction_date")

            if not trans.get("ticker") and not trans.get("asset_name"):
                flags.append("Missing both ticker and asset_name")

            if flags:
                outliers.append(
                    {
                        "index": i,
                        "transaction": trans,
                        "flags": flags,
                    }
                )

        if outliers:
            logger.info(f"Flagged {len(outliers)} outlier transactions")

        return outliers

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all validations performed"""
        total = self.validation_stats["total_validated"]
        if total == 0:
            return self.validation_stats

        return {
            **self.validation_stats,
            "pass_rate": self.validation_stats["passed"] / total,
            "warning_rate": self.validation_stats["warnings"] / total,
            "error_rate": self.validation_stats["errors"] / total,
        }

    # Private helper methods

    def _check_mandatory_fields(
        self, data: Dict[str, Any], required_fields: List[str]
    ) -> List[str]:
        """Check which required fields are missing"""
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing.append(field)
        return missing

    def _validate_date_sequence(self, transaction: Dict[str, Any]) -> List[str]:
        """Validate that dates are in logical sequence"""
        warnings = []

        transaction_date = transaction.get("transaction_date")
        filing_date = transaction.get("filing_date")

        if transaction_date and filing_date:
            if isinstance(transaction_date, datetime) and isinstance(filing_date, datetime):
                # Transaction should be before filing
                if transaction_date > filing_date:
                    warnings.append(
                        f"transaction_date ({transaction_date.date()}) is after filing_date ({filing_date.date()})"
                    )

                # Filing should be within reasonable time (e.g., 45 days)
                days_diff = (filing_date - transaction_date).days
                if days_diff > 60:
                    warnings.append(
                        f"Filing is {days_diff} days after transaction (>60 days)"
                    )

        # Check if dates are not in the future
        now = datetime.now()
        if transaction_date and isinstance(transaction_date, datetime):
            if transaction_date > now:
                warnings.append(f"transaction_date ({transaction_date.date()}) is in the future")

        if filing_date and isinstance(filing_date, datetime):
            if filing_date > now:
                warnings.append(f"filing_date ({filing_date.date()}) is in the future")

        return warnings

    def _validate_value_range(
        self, transaction: Dict[str, Any]
    ) -> tuple[List[str], List[str]]:
        """Validate value ranges are reasonable"""
        warnings = []
        errors = []

        value_low = transaction.get("value_low")
        value_high = transaction.get("value_high")

        if value_low and value_high:
            if isinstance(value_low, Decimal) and isinstance(value_high, Decimal):
                # Check that high >= low
                if value_high < value_low:
                    errors.append(
                        f"value_high ({value_high}) is less than value_low ({value_low})"
                    )

                # Check for unreasonably high values
                if value_high > self.MAX_REASONABLE_TRANSACTION_VALUE:
                    warnings.append(f"Very high transaction value: ${value_high:,}")

                # Check for unreasonably low values
                if value_low < self.MIN_REASONABLE_TRANSACTION_VALUE:
                    warnings.append(f"Very low transaction value: ${value_low:,}")

        return warnings, errors

    def _check_ticker_confidence(self, transaction: Dict[str, Any]) -> List[str]:
        """Check ticker resolution confidence"""
        warnings = []

        ticker = transaction.get("ticker")
        ticker_confidence = transaction.get("ticker_confidence_score")

        if ticker and ticker_confidence is not None:
            if ticker_confidence < 0.6:
                warnings.append(
                    f"Low confidence ticker resolution for '{ticker}': {ticker_confidence:.2f}"
                )

        return warnings

    def _calculate_quality_score(
        self, data: Dict[str, Any], warnings: List[str], errors: List[str]
    ) -> float:
        """
        Calculate overall quality score for a data entry.

        Returns score from 0.0 to 1.0 based on:
        - Presence of optional fields
        - Number of warnings/errors
        - Ticker confidence
        """
        score = 1.0

        # Penalize for errors (more severe)
        score -= len(errors) * 0.2

        # Penalize for warnings (less severe)
        score -= len(warnings) * 0.05

        # Bonus for having ticker
        if data.get("ticker"):
            score += 0.1

        # Bonus for high ticker confidence
        ticker_confidence = data.get("ticker_confidence_score")
        if ticker_confidence is not None:
            score += ticker_confidence * 0.1

        # Bonus for having date
        if data.get("transaction_date") or data.get("filing_date"):
            score += 0.05

        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, score))

    def _calculate_similarity(self, trans1: Dict[str, Any], trans2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two transactions.

        Returns score from 0.0 to 1.0.
        """
        similarity = 0.0
        checks = 0

        # Check ticker match
        if trans1.get("ticker") and trans2.get("ticker"):
            checks += 1
            if trans1["ticker"] == trans2["ticker"]:
                similarity += 0.4

        # Check asset name similarity
        if trans1.get("asset_name") and trans2.get("asset_name"):
            checks += 1
            if trans1["asset_name"].lower() == trans2["asset_name"].lower():
                similarity += 0.3

        # Check transaction type
        if trans1.get("transaction_type") and trans2.get("transaction_type"):
            checks += 1
            if trans1["transaction_type"] == trans2["transaction_type"]:
                similarity += 0.15

        # Check dates (same day)
        date1 = trans1.get("transaction_date")
        date2 = trans2.get("transaction_date")
        if date1 and date2:
            checks += 1
            if isinstance(date1, datetime) and isinstance(date2, datetime):
                if date1.date() == date2.date():
                    similarity += 0.15

        if checks == 0:
            return 0.0

        return similarity
