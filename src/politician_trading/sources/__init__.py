"""
Data source implementations for politician trading disclosures.

Each source file implements a specific disclosure source (US House, US Senate, etc.)
"""

from .base_source import BaseSource, SourceConfig
from typing import Optional

__all__ = ['BaseSource', 'SourceConfig', 'get_source']


def get_source(source_type: str) -> Optional[BaseSource]:
    """
    Factory function to get source by type.

    Args:
        source_type: Type of source (e.g., 'us_house', 'us_senate')

    Returns:
        Source instance or None if unknown type
    """
    source_map = {
        'us_house': 'USHouseSource',
        'us_senate': 'USSenateSource',
        'uk_parliament': 'UKParliamentSource',
        'eu_parliament': 'EUParliamentSource',
        'california': 'CaliforniaSource',
        'new_york': 'NewYorkSource',
        'texas': 'TexasSource',
        'quiverquant': 'QuiverQuantSource',
    }

    if source_type not in source_map:
        return None

    # Lazy import to avoid circular dependencies
    class_name = source_map[source_type]

    if source_type == 'us_house':
        from .us_house import USHouseSource
        return USHouseSource()
    elif source_type == 'us_senate':
        from .us_senate import USSenateSource
        return USSenateSource()
    elif source_type == 'uk_parliament':
        from .uk_parliament import UKParliamentSource
        return UKParliamentSource()
    elif source_type == 'eu_parliament':
        from .eu_parliament import EUParliamentSource
        return EUParliamentSource()
    elif source_type == 'california':
        from .california import CaliforniaSource
        return CaliforniaSource()
    elif source_type == 'quiverquant':
        from .quiverquant import QuiverQuantSource
        return QuiverQuantSource()
    # Add more sources as they're implemented

    return None
