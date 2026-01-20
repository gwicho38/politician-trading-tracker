"""
Tests for PDF utilities (app/lib/pdf_utils.py).

Tests:
- extract_text_from_pdf() - Text extraction from PDFs
- extract_tables_from_pdf() - Table extraction from PDFs
"""

import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO


# =============================================================================
# extract_text_from_pdf() Tests
# =============================================================================

class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf() function."""

    def test_extracts_text_from_single_page(self):
        """extract_text_from_pdf() extracts text from single page PDF."""
        from app.lib.pdf_utils import extract_text_from_pdf

        # Mock pdfplumber
        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Sample text content"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_text_from_pdf(b"%PDF-1.4 fake content")

            assert result == "Sample text content"

    def test_extracts_text_from_multiple_pages(self):
        """extract_text_from_pdf() joins text from multiple pages."""
        from app.lib.pdf_utils import extract_text_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Page 1 content"

            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = "Page 2 content"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_text_from_pdf(b"%PDF-1.4 fake content")

            assert result == "Page 1 content\nPage 2 content"

    def test_skips_empty_pages(self):
        """extract_text_from_pdf() skips pages with no text."""
        from app.lib.pdf_utils import extract_text_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Page 1 content"

            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = None  # Empty page

            mock_page3 = MagicMock()
            mock_page3.extract_text.return_value = ""  # Empty string

            mock_page4 = MagicMock()
            mock_page4.extract_text.return_value = "Page 4 content"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2, mock_page3, mock_page4]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_text_from_pdf(b"%PDF-1.4 fake content")

            assert "Page 1 content" in result
            assert "Page 4 content" in result

    def test_returns_none_for_pdf_with_no_text(self):
        """extract_text_from_pdf() returns None if no text in PDF."""
        from app.lib.pdf_utils import extract_text_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = None

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_text_from_pdf(b"%PDF-1.4 fake content")

            assert result is None

    def test_returns_none_on_exception(self):
        """extract_text_from_pdf() returns None on exception."""
        from app.lib.pdf_utils import extract_text_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_open.side_effect = Exception("Invalid PDF")

            result = extract_text_from_pdf(b"not a pdf")

            assert result is None

    def test_handles_bytes_input(self):
        """extract_text_from_pdf() handles bytes input correctly."""
        from app.lib.pdf_utils import extract_text_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Content"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            # Verify it's called with BytesIO
            result = extract_text_from_pdf(b"%PDF-1.4 content")

            assert result == "Content"
            # Verify the call was made (pdfplumber.open was called)
            mock_open.assert_called_once()


# =============================================================================
# extract_tables_from_pdf() Tests
# =============================================================================

class TestExtractTablesFromPdf:
    """Tests for extract_tables_from_pdf() function."""

    def test_extracts_table_from_single_page(self):
        """extract_tables_from_pdf() extracts table from single page."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_table = [
                ["Header1", "Header2"],
                ["Value1", "Value2"],
            ]

            mock_page = MagicMock()
            mock_page.extract_tables.return_value = [mock_table]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert len(result) == 1
            assert result[0] == mock_table

    def test_extracts_tables_from_multiple_pages(self):
        """extract_tables_from_pdf() extracts tables from all pages."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            table1 = [["A1", "B1"], ["A2", "B2"]]
            table2 = [["C1", "D1"], ["C2", "D2"]]

            mock_page1 = MagicMock()
            mock_page1.extract_tables.return_value = [table1]

            mock_page2 = MagicMock()
            mock_page2.extract_tables.return_value = [table2]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert len(result) == 2
            assert result[0] == table1
            assert result[1] == table2

    def test_handles_multiple_tables_per_page(self):
        """extract_tables_from_pdf() handles multiple tables on one page."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            table1 = [["A1", "B1"]]
            table2 = [["C1", "D1"]]

            mock_page = MagicMock()
            mock_page.extract_tables.return_value = [table1, table2]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert len(result) == 2

    def test_returns_empty_list_for_no_tables(self):
        """extract_tables_from_pdf() returns empty list if no tables."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_tables.return_value = []

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert result == []

    def test_handles_none_tables_return(self):
        """extract_tables_from_pdf() handles None from extract_tables."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_page = MagicMock()
            mock_page.extract_tables.return_value = None

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert result == []

    def test_returns_empty_list_on_exception(self):
        """extract_tables_from_pdf() returns empty list on exception."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_open.side_effect = Exception("Invalid PDF")

            result = extract_tables_from_pdf(b"not a pdf")

            assert result == []

    def test_skips_pages_with_no_tables(self):
        """extract_tables_from_pdf() skips pages without tables."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            table1 = [["A1", "B1"]]

            mock_page1 = MagicMock()
            mock_page1.extract_tables.return_value = [table1]

            mock_page2 = MagicMock()
            mock_page2.extract_tables.return_value = None

            mock_page3 = MagicMock()
            mock_page3.extract_tables.return_value = []

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert len(result) == 1
            assert result[0] == table1

    def test_preserves_table_structure(self):
        """extract_tables_from_pdf() preserves table row/column structure."""
        from app.lib.pdf_utils import extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            # House disclosure style table
            mock_table = [
                ["Transaction Date", "Notification Date", "Owner", "Asset", "Amount"],
                ["01/15/2024", "01/25/2024", "SP", "Apple Inc.", "$1,001 - $15,000"],
                ["01/16/2024", "01/25/2024", "JT", "Microsoft", "$15,001 - $50,000"],
            ]

            mock_page = MagicMock()
            mock_page.extract_tables.return_value = [mock_table]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            result = extract_tables_from_pdf(b"%PDF-1.4 fake content")

            assert len(result) == 1
            assert len(result[0]) == 3  # 3 rows
            assert len(result[0][0]) == 5  # 5 columns
            assert result[0][0][0] == "Transaction Date"
            assert result[0][1][3] == "Apple Inc."


# =============================================================================
# Integration-Style Tests (without real PDFs)
# =============================================================================

class TestPdfUtilsIntegration:
    """Integration tests for PDF utilities using mock data."""

    def test_text_and_tables_can_be_extracted_together(self):
        """Both text and tables can be extracted from the same PDF bytes."""
        from app.lib.pdf_utils import extract_text_from_pdf, extract_tables_from_pdf

        pdf_bytes = b"%PDF-1.4 fake content"

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            mock_table = [["Col1", "Col2"], ["Val1", "Val2"]]

            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Some text content"
            mock_page.extract_tables.return_value = [mock_table]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            text = extract_text_from_pdf(pdf_bytes)

            # Reset mock for tables call
            mock_open.reset_mock()
            mock_open.return_value = mock_pdf

            tables = extract_tables_from_pdf(pdf_bytes)

            assert text == "Some text content"
            assert len(tables) == 1

    def test_handles_house_disclosure_format(self):
        """Handles typical House disclosure PDF structure."""
        from app.lib.pdf_utils import extract_text_from_pdf, extract_tables_from_pdf

        with patch("app.lib.pdf_utils.pdfplumber.open") as mock_open:
            # Simulate House disclosure structure
            mock_table = [
                ["ID", "Transaction Date", "Notification Date", "Owner", "Asset",
                 "Type", "Transaction", "Amount", "Cap. Gains > $200?"],
                ["1", "01/15/2024", "01/25/2024", "SP", "Apple Inc. (AAPL)",
                 "ST", "P", "$1,001 - $15,000", "N"],
            ]

            mock_page = MagicMock()
            mock_page.extract_text.return_value = "FINANCIAL DISCLOSURE REPORT"
            mock_page.extract_tables.return_value = [mock_table]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_pdf

            tables = extract_tables_from_pdf(b"fake pdf")

            assert len(tables) == 1
            assert "Transaction Date" in tables[0][0]
            assert "Apple Inc." in tables[0][1][4]
