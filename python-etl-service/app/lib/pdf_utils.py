"""
PDF utilities for extracting text and tables from PDF files.

Consolidated from house_etl.py and senate_etl.py
"""

import logging
from io import BytesIO
from typing import List, Optional

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """Extract all text from a PDF file.

    Args:
        pdf_bytes: Raw PDF file content as bytes

    Returns:
        Extracted text as a single string with pages joined by newlines,
        or None if extraction fails
    """
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            text_parts = [
                page.extract_text() for page in pdf.pages if page.extract_text()
            ]
            return "\n".join(text_parts) if text_parts else None
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return None


def extract_tables_from_pdf(pdf_bytes: bytes) -> List[List[List[str]]]:
    """Extract all tables from a PDF file.

    Args:
        pdf_bytes: Raw PDF file content as bytes

    Returns:
        List of tables, where each table is a list of rows,
        and each row is a list of cell strings.
        Returns empty list if extraction fails.
    """
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return [
                table for page in pdf.pages for table in (page.extract_tables() or [])
            ]
    except Exception as e:
        logger.error(f"Failed to extract tables from PDF: {e}")
        return []
