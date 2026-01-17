"""
Shared library utilities for the ETL service.

This module consolidates common functions used across multiple ETL services
to eliminate code duplication.
"""

from app.lib.database import get_supabase, upload_transaction_to_supabase
from app.lib.parser import (
    ASSET_TYPE_CODES,
    VALUE_PATTERNS,
    clean_asset_name,
    extract_ticker_from_text,
    is_header_row,
    normalize_name,
    parse_asset_type,
    parse_value_range,
    sanitize_string,
)
from app.lib.pdf_utils import extract_tables_from_pdf, extract_text_from_pdf
from app.lib.politician import find_or_create_politician

__all__ = [
    # Database
    "get_supabase",
    "upload_transaction_to_supabase",
    # Parser
    "ASSET_TYPE_CODES",
    "VALUE_PATTERNS",
    "clean_asset_name",
    "extract_ticker_from_text",
    "is_header_row",
    "normalize_name",
    "parse_asset_type",
    "parse_value_range",
    "sanitize_string",
    # PDF Utils
    "extract_tables_from_pdf",
    "extract_text_from_pdf",
    # Politician
    "find_or_create_politician",
]
