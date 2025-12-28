"""
Normalization stage - Transforms cleaned data into standard database format.
"""

from typing import List, Optional, Tuple
from datetime import datetime
import logging
import re

from .base import (
    PipelineStage,
    PipelineResult,
    PipelineContext,
    PipelineMetrics,
    PipelineStatus,
    CleanedDisclosure,
    NormalizedDisclosure,
)

logger = logging.getLogger(__name__)


class NormalizationStage(PipelineStage[NormalizedDisclosure]):
    """
    Normalization stage - Transforms cleaned data into database-ready format.

    This stage:
    1. Parses politician names into components
    2. Matches politicians to existing database records
    3. Extracts ticker symbols from asset names
    4. Parses amount ranges
    5. Normalizes transaction types
    6. Enriches with metadata
    """

    def __init__(self, auto_create_politicians: bool = True):
        super().__init__("normalization")
        self.auto_create_politicians = auto_create_politicians
        self._politician_cache = {}  # Cache for politician lookups

    async def process(
        self, data: List[CleanedDisclosure], context: PipelineContext
    ) -> PipelineResult[NormalizedDisclosure]:
        """
        Normalize cleaned disclosures.

        Args:
            data: List of CleanedDisclosure objects from cleaning stage
            context: Pipeline context

        Returns:
            PipelineResult containing NormalizedDisclosure objects
        """
        start_time = datetime.utcnow()
        metrics = PipelineMetrics()
        normalized_disclosures: List[NormalizedDisclosure] = []

        metrics.records_input = len(data)
        self.logger.info(f"Starting normalization of {len(data)} cleaned disclosures")

        # Load transformers
        from ..transformers import TickerExtractor, AmountParser, PoliticianMatcher

        ticker_extractor = TickerExtractor()
        amount_parser = AmountParser()
        politician_matcher = PoliticianMatcher()

        # Load existing politicians for matching
        await politician_matcher.load_politicians()

        for i, cleaned in enumerate(data):
            try:
                # Parse politician name
                first_name, last_name, full_name = self._parse_politician_name(
                    cleaned.politician_name
                )

                # Match to existing politician or prepare for creation
                politician_id, role, party, state = await politician_matcher.match(
                    first_name=first_name, last_name=last_name, source=cleaned.source
                )

                # Extract ticker if not already present
                asset_ticker = cleaned.asset_ticker
                if not asset_ticker:
                    asset_ticker = ticker_extractor.extract(cleaned.asset_name)

                # Determine asset type
                asset_type = cleaned.asset_type or self._infer_asset_type(
                    cleaned.asset_name, asset_ticker
                )

                # Parse amount range
                amount_min, amount_max, amount_exact = amount_parser.parse(cleaned.amount_text)

                # Normalize transaction type
                transaction_type = self._normalize_transaction_type(cleaned.transaction_type)

                # Create normalized disclosure
                normalized = NormalizedDisclosure(
                    politician_id=politician_id,
                    politician_first_name=first_name,
                    politician_last_name=last_name,
                    politician_full_name=full_name,
                    politician_role=role,
                    politician_party=party,
                    politician_state=state,
                    transaction_date=cleaned.transaction_date,
                    disclosure_date=cleaned.disclosure_date,
                    transaction_type=transaction_type,
                    asset_name=cleaned.asset_name,
                    asset_ticker=asset_ticker,
                    asset_type=asset_type,
                    amount_range_min=amount_min,
                    amount_range_max=amount_max,
                    amount_exact=amount_exact,
                    source=cleaned.source,
                    source_url=cleaned.source_url,
                    source_document_id=cleaned.source_document_id,
                    raw_data=cleaned.raw_data,
                )

                normalized_disclosures.append(normalized)
                metrics.records_output += 1

            except Exception as e:
                self.logger.error(f"Error normalizing record {i}: {e}", exc_info=True)
                metrics.records_failed += 1
                metrics.errors.append(f"Record {i}: {str(e)}")

        # Calculate metrics
        metrics.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        # Determine status
        if metrics.records_output > 0:
            if metrics.records_failed == 0:
                status = PipelineStatus.SUCCESS
            else:
                status = PipelineStatus.PARTIAL_SUCCESS
        else:
            status = PipelineStatus.FAILED
            metrics.errors.append("No records successfully normalized")

        self.logger.info(
            f"Normalization complete: {metrics.records_output} normalized, "
            f"{metrics.records_failed} failed, "
            f"{metrics.duration_seconds:.2f}s"
        )

        return self._create_result(
            status=status, data=normalized_disclosures, context=context, metrics=metrics
        )

    def _parse_politician_name(self, full_name: str) -> Tuple[str, str, str]:
        """
        Parse politician name into components.

        Returns: (first_name, last_name, full_name)
        """
        # Remove titles and prefixes
        clean_name = full_name
        titles = [
            r"^(Sen\.|Senator|Rep\.|Representative|Hon\.|Honorable|Mr\.|Mrs\.|Ms\.|Dr\.)\s+",
            r"^(The\s+)?(Right\s+)?(Honourable|Honorable)\s+",
        ]

        for title_pattern in titles:
            clean_name = re.sub(title_pattern, "", clean_name, flags=re.IGNORECASE)

        clean_name = clean_name.strip()

        # Split name
        parts = clean_name.split()

        if len(parts) == 0:
            return "", "", full_name
        elif len(parts) == 1:
            return parts[0], "", full_name
        elif len(parts) == 2:
            return parts[0], parts[1], full_name
        else:
            # Handle middle names/initials - take first and last
            return parts[0], parts[-1], full_name

    def _infer_asset_type(self, asset_name: str, asset_ticker: Optional[str]) -> str:
        """Infer asset type from asset name and ticker"""
        asset_lower = asset_name.lower()

        # Check for specific indicators
        if any(word in asset_lower for word in ["fund", "mutual", "etf", "index"]):
            if "etf" in asset_lower or "exchange traded" in asset_lower:
                return "etf"
            return "mutual_fund"

        if any(word in asset_lower for word in ["bond", "treasury", "note", "bill"]):
            return "bond"

        if any(word in asset_lower for word in ["option", "call", "put"]):
            return "option"

        if any(word in asset_lower for word in ["crypto", "bitcoin", "ethereum"]):
            return "cryptocurrency"

        # If has ticker, likely a stock
        if asset_ticker:
            return "stock"

        # Default to stock if can't determine
        return "stock"

    def _normalize_transaction_type(self, trans_type: str) -> str:
        """Normalize transaction type to standard values"""
        # These should already be normalized from cleaning stage
        # Just ensure consistency
        type_map = {
            "purchase": "purchase",
            "sale": "sale",
            "exchange": "exchange",
            "option_purchase": "option_purchase",
            "option_sale": "option_sale",
            "option_exercise": "option_exercise",
        }

        return type_map.get(trans_type.lower(), trans_type)
