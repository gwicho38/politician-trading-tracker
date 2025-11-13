"""
Storage bucket and path constants for Supabase storage.

These constants define storage bucket names and path patterns
used throughout the application.
"""


class StorageBuckets:
    """Supabase storage bucket names."""

    RAW_PDFS = "raw-pdfs"
    API_RESPONSES = "api-responses"
    PARSED_DATA = "parsed-data"
    HTML_SNAPSHOTS = "html-snapshots"


class StoragePaths:
    """Storage path patterns and helpers."""

    @staticmethod
    def get_chamber_path(source_type: str) -> str:
        """
        Determine chamber directory based on source type.

        Args:
            source_type: Source type identifier (e.g., "senate_pdf", "house_pdf")

        Returns:
            Chamber directory name ("senate" or "house")
        """
        return "senate" if "senate" in source_type.lower() else "house"

    @staticmethod
    def construct_pdf_path(chamber: str, year: int, month: int, filename: str) -> str:
        """
        Construct a standardized path for PDF storage.

        Args:
            chamber: Chamber name ("senate" or "house")
            year: Year of the disclosure
            month: Month of the disclosure (1-12)
            filename: PDF filename

        Returns:
            Full storage path (e.g., "senate/2024/03/disclosure.pdf")
        """
        return f"{chamber}/{year}/{month:02d}/{filename}"

    @staticmethod
    def construct_api_response_path(source: str, date: str, filename: str) -> str:
        """
        Construct a standardized path for API response storage.

        Args:
            source: API source name (e.g., "quiverquant", "propublica")
            date: Response date (YYYY-MM-DD format)
            filename: Response filename

        Returns:
            Full storage path (e.g., "quiverquant/2024-03-15/response.json")
        """
        return f"{source}/{date}/{filename}"


class SourceTypes:
    """Source type identifiers for storage classification."""

    SENATE_PDF = "senate_pdf"
    HOUSE_PDF = "house_pdf"
    SENATE_API = "senate_api"
    HOUSE_API = "house_api"
    QUIVERQUANT = "quiverquant"
    PROPUBLICA = "propublica"
    EU_PARLIAMENT = "eu_parliament"
    UK_PARLIAMENT = "uk_parliament"
    TEST_SOURCE = "test_source"
