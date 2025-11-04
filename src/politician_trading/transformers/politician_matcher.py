"""
Politician matcher transformer.
"""

from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)


class PoliticianMatcher:
    """
    Matches politician names to existing database records.

    Handles fuzzy matching and title/prefix removal.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._politicians_cache: Dict[str, Dict] = {}
        self._loaded = False

    async def load_politicians(self):
        """Load existing politicians from database into cache"""
        if self._loaded:
            return

        try:
            from supabase import create_client
            from ..config import SupabaseConfig

            config = SupabaseConfig.from_env()
            # Create Supabase client directly
            db_client = create_client(config.url, config.key)

            # Query politicians from database
            response = db_client.table("politicians").select("*").execute()

            if response.data:
                for politician in response.data:
                    # Create cache key from name
                    key = self._make_cache_key(
                        politician.get('first_name', ''),
                        politician.get('last_name', '')
                    )
                    self._politicians_cache[key] = politician

                self.logger.info(f"Loaded {len(self._politicians_cache)} politicians into cache")
                self._loaded = True
            else:
                self.logger.warning("No politicians found in database")

        except Exception as e:
            self.logger.error(f"Failed to load politicians: {e}", exc_info=True)

    async def match(
        self,
        first_name: str,
        last_name: str,
        source: str
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str]]:
        """
        Match politician by name.

        Args:
            first_name: First name
            last_name: Last name
            source: Source of the disclosure (helps determine role)

        Returns:
            Tuple of (politician_id, role, party, state)
        """
        # Ensure politicians are loaded
        if not self._loaded:
            await self.load_politicians()

        # Look for exact match in cache
        cache_key = self._make_cache_key(first_name, last_name)

        if cache_key in self._politicians_cache:
            politician = self._politicians_cache[cache_key]
            self.logger.debug(f"Found cached politician: {first_name} {last_name}")
            return (
                politician.get('id'),
                politician.get('role', self._infer_role_from_source(source)),
                politician.get('party'),
                politician.get('state_or_country')
            )

        # Try fuzzy match (last name only)
        for key, politician in self._politicians_cache.items():
            if last_name.lower() in key.lower():
                self.logger.debug(f"Fuzzy matched politician: {first_name} {last_name} -> {politician.get('full_name')}")
                return (
                    politician.get('id'),
                    politician.get('role', self._infer_role_from_source(source)),
                    politician.get('party'),
                    politician.get('state_or_country')
                )

        # No match found - will need to create new politician
        self.logger.info(f"No match found for: {first_name} {last_name}")
        role = self._infer_role_from_source(source)
        return None, role, None, None

    def _make_cache_key(self, first_name: str, last_name: str) -> str:
        """Create cache key from names"""
        return f"{first_name.lower()}_{last_name.lower()}"

    def _infer_role_from_source(self, source: str) -> str:
        """Infer politician role from data source"""
        source_lower = source.lower()

        if 'house' in source_lower or 'representative' in source_lower:
            return 'US_HOUSE_REP'
        elif 'senate' in source_lower or 'senator' in source_lower:
            return 'US_SENATOR'
        elif 'uk' in source_lower or 'parliament' in source_lower:
            if 'lords' in source_lower:
                return 'UK_LORD'
            return 'UK_MP'
        elif 'eu' in source_lower or 'european' in source_lower:
            return 'EU_MEP'
        elif 'california' in source_lower:
            return 'CA_STATE_LEGISLATOR'
        elif 'new york' in source_lower or 'ny' in source_lower:
            return 'NY_STATE_LEGISLATOR'
        elif 'texas' in source_lower or 'tx' in source_lower:
            return 'TX_STATE_LEGISLATOR'
        else:
            return 'UNKNOWN'
