"""
EU Parliament Financial Declarations ETL Service (Stub)

Placeholder service for EU Parliament financial interest declarations.
Registers properly in the ETL registry but returns empty results.

EU Parliament declarations have a fundamentally different format from
US congressional disclosures (financial interest declarations vs.
periodic transaction reports). A full implementation would need to:
1. Scrape the EU Parliament transparency register
2. Parse multi-language PDF declarations
3. Map EU financial categories to our standard schema

This stub replaces the previous Supabase Edge Function that created
placeholder politicians with garbage data.
"""

import logging
from typing import Any, Dict, List, Optional

from app.lib.base_etl import BaseETLService, ETLResult
from app.lib.registry import ETLRegistry

logger = logging.getLogger(__name__)


@ETLRegistry.register
class EUParliamentETLService(BaseETLService):
    """
    EU Parliament financial declarations ETL service.

    Currently a stub that registers in the ETL registry and completes
    gracefully without fetching data. This is preferable to the previous
    edge function approach that created garbage placeholder data.
    """

    source_id = "eu_parliament"
    source_name = "EU Parliament Declarations"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """Return empty list - EU Parliament ETL is not yet implemented."""
        self.logger.info(
            "EU Parliament ETL is a stub - no disclosures fetched. "
            "A full implementation requires parsing the EU transparency register."
        )
        return []

    async def parse_disclosure(
        self, raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Pass-through parser for future implementation."""
        return raw
