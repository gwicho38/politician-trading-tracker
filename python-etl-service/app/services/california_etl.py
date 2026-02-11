"""
California Financial Disclosures ETL Service (Stub)

Placeholder service for California Form 700 financial disclosures.
Registers properly in the ETL registry but returns empty results.

California uses Form 700 (Statement of Economic Interests) which has
a fundamentally different format from federal disclosures. A full
implementation would need to:
1. Query the California NetFile system
2. Parse Form 700 PDF documents
3. Map California disclosure categories to our standard schema

This stub replaces the previous Supabase Edge Function that created
placeholder politicians with garbage data.
"""

import logging
from typing import Any, Dict, List, Optional

from app.lib.base_etl import BaseETLService, ETLResult
from app.lib.registry import ETLRegistry

logger = logging.getLogger(__name__)


@ETLRegistry.register
class CaliforniaETLService(BaseETLService):
    """
    California financial disclosures ETL service.

    Currently a stub that registers in the ETL registry and completes
    gracefully without fetching data. This is preferable to the previous
    edge function approach that created garbage placeholder data.
    """

    source_id = "california"
    source_name = "California Financial Disclosures"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """Return empty list - California ETL is not yet implemented."""
        self.logger.info(
            "California ETL is a stub - no disclosures fetched. "
            "A full implementation requires parsing Form 700 from NetFile."
        )
        return []

    async def parse_disclosure(
        self, raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Pass-through parser for future implementation."""
        return raw
