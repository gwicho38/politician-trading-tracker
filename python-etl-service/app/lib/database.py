import os
import logging
from typing import Any, Dict, List, Optional, Tuple

from supabase import create_client, Client

from app.lib.parser import sanitize_string, validate_and_sanitize_amounts

logger = logging.getLogger(__name__)

def get_supabase() -> Optional[Client]:
    """Get Supabase client."""
    supabase_url = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_key or not supabase_url:
        return None
    return create_client(supabase_url, supabase_key)

def refresh_materialized_views(supabase_client: Optional[Client] = None) -> bool:
    """Refresh materialized views after ETL data imports.

    Calls the refresh_top_tickers() database function to update the
    pre-computed top_tickers materialized view with fresh data.
    """
    try:
        client = supabase_client or get_supabase()
        if not client:
            logger.warning("No Supabase client available for materialized view refresh")
            return False
        client.rpc("refresh_top_tickers").execute()
        logger.info("Refreshed top_tickers materialized view")
        return True
    except Exception as e:
        logger.warning(f"Failed to refresh materialized views: {e}")
        return False


def upload_transaction_to_supabase(
    supabase_client: Client,
    politician_id: str,
    transaction: Dict[str, Any],
    disclosure: Dict[str, Any],
    update_mode: bool = False,
) -> Optional[str]:
    """Upload a single transaction to Supabase trading_disclosures table.

    Args:
        supabase_client: Supabase client instance
        politician_id: UUID of the politician
        transaction: Parsed transaction data
        disclosure: Disclosure metadata
        update_mode: If True, use upsert to update existing records
    """
    try:
        # Get dates: prefer extracted dates from row, fall back to filing_date
        filing_date = transaction.get("filing_date") or disclosure.get("filing_date")
        if filing_date and "T" in str(filing_date):
            filing_date = str(filing_date).replace("T", " ")[:19]

        # Transaction date = when the buy/sell occurred
        transaction_date = transaction.get("transaction_date")
        if transaction_date and "T" in str(transaction_date):
            transaction_date = str(transaction_date).replace("T", " ")[:19]
        # Fall back to filing_date if not extracted
        if not transaction_date:
            transaction_date = filing_date

        # Disclosure date = when it was reported/notified
        disclosure_date = transaction.get("notification_date")
        if disclosure_date and "T" in str(disclosure_date):
            disclosure_date = str(disclosure_date).replace("T", " ")[:19]
        # Fall back to filing_date if not extracted
        if not disclosure_date:
            disclosure_date = filing_date

        asset_name = sanitize_string(transaction.get("asset_name", ""))
        if not asset_name:
            return None
        asset_name = asset_name[:200]

        raw_row = transaction.get("raw_row", [])
        sanitized_raw_row = [sanitize_string(cell) for cell in raw_row]

        # Validate and sanitize trade amounts to prevent corrupted data
        amount_min, amount_max = validate_and_sanitize_amounts(
            transaction.get("value_low"), transaction.get("value_high")
        )
        if amount_min is None and amount_max is None:
            # Both were None originally, or validation failed
            orig_low = transaction.get("value_low")
            orig_high = transaction.get("value_high")
            if orig_low is not None or orig_high is not None:
                logger.warning(
                    f"Rejected invalid trade amounts for '{asset_name[:50]}': "
                    f"low=${orig_low}, high=${orig_high} (exceeds $50M threshold)"
                )

        disclosure_data = {
            "politician_id": politician_id,
            "transaction_date": transaction_date,
            "disclosure_date": disclosure_date,
            "transaction_type": transaction.get("transaction_type") or "unknown",
            "asset_name": asset_name,
            "asset_ticker": (sanitize_string(transaction.get("asset_ticker")) or "")[:20] or None,
            "asset_type": sanitize_string(
                transaction.get("asset_type") or transaction.get("asset_type_code")
            ),
            "amount_range_min": amount_min,
            "amount_range_max": amount_max,
            "source_url": disclosure.get("pdf_url") or disclosure.get("source_url"),
            "source_document_id": disclosure.get("doc_id"),
            "raw_data": {
                "source": disclosure.get("source", "us_house"),
                "year": disclosure.get("year"),
                "filing_type": disclosure.get("filing_type"),
                "state_district": disclosure.get("state_district"),
                "raw_row": sanitized_raw_row,
            },
            "status": "active",
        }

        if update_mode:
            # Upsert: update if exists (based on unique constraint), insert if not
            # The unique constraint idx_disclosures_unique is on:
            # (politician_id, transaction_date, asset_name, transaction_type, disclosure_date)
            response = (
                supabase_client.table("trading_disclosures")
                .upsert(
                    disclosure_data,
                    on_conflict="politician_id,transaction_date,asset_name,transaction_type,disclosure_date"
                )
                .execute()
            )
        else:
            # Normal insert (fails on duplicate)
            response = (
                supabase_client.table("trading_disclosures").insert(disclosure_data).execute()
            )

        if response.data and len(response.data) > 0:
            return response.data[0]["id"]

    except Exception as e:
        error_str = str(e)
        if "duplicate key" in error_str or "23505" in error_str:
            logger.debug(f"Duplicate transaction skipped: {asset_name[:50]}")
        else:
            logger.error(f"Error uploading transaction: {e}")

    return None


def prepare_transaction_for_batch(
    politician_id: str,
    transaction: Dict[str, Any],
    disclosure: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Prepare a transaction record for batch upload.

    Args:
        politician_id: UUID of the politician
        transaction: Parsed transaction data
        disclosure: Disclosure metadata

    Returns:
        Dict ready for batch insert, or None if invalid
    """
    # Get dates: prefer extracted dates from row, fall back to filing_date
    filing_date = transaction.get("filing_date") or disclosure.get("filing_date")
    if filing_date and "T" in str(filing_date):
        filing_date = str(filing_date).replace("T", " ")[:19]

    # Transaction date = when the buy/sell occurred
    transaction_date = transaction.get("transaction_date")
    if transaction_date and "T" in str(transaction_date):
        transaction_date = str(transaction_date).replace("T", " ")[:19]
    if not transaction_date:
        transaction_date = filing_date

    # Disclosure date = when it was reported/notified
    disclosure_date = transaction.get("notification_date")
    if disclosure_date and "T" in str(disclosure_date):
        disclosure_date = str(disclosure_date).replace("T", " ")[:19]
    if not disclosure_date:
        disclosure_date = filing_date

    asset_name = sanitize_string(transaction.get("asset_name", ""))
    if not asset_name:
        return None
    asset_name = asset_name[:200]

    raw_row = transaction.get("raw_row", [])
    sanitized_raw_row = [sanitize_string(cell) for cell in raw_row]

    # Validate and sanitize trade amounts to prevent corrupted data
    amount_min, amount_max = validate_and_sanitize_amounts(
        transaction.get("value_low"), transaction.get("value_high")
    )
    if amount_min is None and amount_max is None:
        orig_low = transaction.get("value_low")
        orig_high = transaction.get("value_high")
        if orig_low is not None or orig_high is not None:
            logger.warning(
                f"Rejected invalid trade amounts for '{asset_name[:50]}': "
                f"low=${orig_low}, high=${orig_high} (exceeds $50M threshold)"
            )

    return {
        "politician_id": politician_id,
        "transaction_date": transaction_date,
        "disclosure_date": disclosure_date,
        "transaction_type": transaction.get("transaction_type") or "unknown",
        "asset_name": asset_name,
        "asset_ticker": (sanitize_string(transaction.get("asset_ticker")) or "")[:20] or None,
        "asset_type": sanitize_string(
            transaction.get("asset_type") or transaction.get("asset_type_code")
        ),
        "amount_range_min": amount_min,
        "amount_range_max": amount_max,
        "source_url": disclosure.get("pdf_url") or disclosure.get("source_url"),
        "source_document_id": disclosure.get("doc_id"),
        "raw_data": {
            "source": disclosure.get("source", "us_house"),
            "year": disclosure.get("year"),
            "filing_type": disclosure.get("filing_type"),
            "state_district": disclosure.get("state_district"),
            "raw_row": sanitized_raw_row,
        },
        "status": "active",
    }


def batch_upload_transactions(
    supabase_client: Client,
    transactions: List[Dict[str, Any]],
    update_mode: bool = False,
    batch_size: int = 50,
) -> Tuple[int, int]:
    """Upload multiple transactions to Supabase in batches.

    This is more efficient than uploading one at a time for ETL jobs
    that process many transactions.

    Args:
        supabase_client: Supabase client instance
        transactions: List of prepared transaction dicts (from prepare_transaction_for_batch)
        update_mode: If True, use upsert to update existing records
        batch_size: Number of records per batch (default 50)

    Returns:
        Tuple of (successful_count, failed_count)
    """
    if not transactions:
        return 0, 0

    successful = 0
    failed = 0

    # Process in batches
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]

        try:
            if update_mode:
                response = (
                    supabase_client.table("trading_disclosures")
                    .upsert(
                        batch,
                        on_conflict="politician_id,transaction_date,asset_name,transaction_type,disclosure_date"
                    )
                    .execute()
                )
            else:
                response = (
                    supabase_client.table("trading_disclosures")
                    .insert(batch)
                    .execute()
                )

            if response.data:
                successful += len(response.data)
            else:
                failed += len(batch)

        except Exception as e:
            error_str = str(e)
            if "duplicate key" in error_str or "23505" in error_str:
                # Some duplicates in batch - fall back to individual inserts
                logger.debug(f"Batch had duplicates, falling back to individual inserts")
                for txn in batch:
                    try:
                        if update_mode:
                            resp = (
                                supabase_client.table("trading_disclosures")
                                .upsert(
                                    txn,
                                    on_conflict="politician_id,transaction_date,asset_name,transaction_type,disclosure_date"
                                )
                                .execute()
                            )
                        else:
                            resp = (
                                supabase_client.table("trading_disclosures")
                                .insert(txn)
                                .execute()
                            )
                        if resp.data:
                            successful += 1
                        else:
                            failed += 1
                    except Exception as txn_error:
                        failed += 1
                        asset_name = txn.get("asset_name", "unknown")[:50]
                        logger.debug(f"Individual insert failed for '{asset_name}': {txn_error}")
            else:
                logger.error(f"Batch upload failed: {e}")
                failed += len(batch)

    return successful, failed