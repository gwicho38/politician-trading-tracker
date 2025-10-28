"""
Third-Party Data Source Scrapers for Politician Trading Data

This module contains scrapers for third-party aggregator services that track
politician trading activity:
- StockNear
- QuiverQuant
- Barchart
- ProPublica Congress API
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .models import Politician, TradingDisclosure

logger = logging.getLogger(__name__)


# =============================================================================
# StockNear Scraper
# =============================================================================


class StockNearScraper:
    """Scraper for stocknear.com/politicians"""

    BASE_URL = "https://stocknear.com/politicians"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )

    def fetch_politicians_list(self) -> List[Dict]:
        """Fetch list of politicians tracked by StockNear"""
        try:
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # StockNear loads data via JavaScript - would need Selenium or API access
            # For now, return structure for manual data entry or API integration
            logger.warning(
                "StockNear requires JavaScript/API access. "
                "Consider using Selenium or finding their API endpoint."
            )

            return []

        except Exception as e:
            logger.error(f"Error fetching StockNear data: {e}")
            return []

    def fetch_politician_trades(self, politician_id: str) -> List[Dict]:
        """Fetch trading data for a specific politician"""
        # Implementation would require JavaScript rendering or API access
        return []


# =============================================================================
# ProPublica Congress API Client
# =============================================================================


class ProPublicaAPI:
    """Client for ProPublica Congress API"""

    BASE_URL = "https://api.propublica.org/congress/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PROPUBLICA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ProPublica API key required. Set PROPUBLICA_API_KEY environment variable."
            )

        self.session = requests.Session()
        self.session.headers.update(
            {"X-API-Key": self.api_key, "User-Agent": "PoliticianTradingTracker/1.0"}
        )

    def get_member_financial_disclosures(
        self, member_id: str, congress: int = 118  # 118th Congress (2023-2025)
    ) -> List[Dict]:
        """
        Get financial disclosures for a specific member of Congress

        Args:
            member_id: ProPublica member ID
            congress: Congress number (e.g., 118 for 2023-2025)

        Returns:
            List of financial disclosure transactions
        """
        try:
            url = f"{self.BASE_URL}/members/{member_id}/financial-disclosures/{congress}.json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                return []

            disclosures = results[0].get("disclosures", [])
            return disclosures

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No financial disclosures found for member {member_id}")
                return []
            else:
                logger.error(f"HTTP error fetching ProPublica data: {e}")
                return []
        except Exception as e:
            logger.error(f"Error fetching ProPublica financial disclosures: {e}")
            return []

    def get_recent_stock_transactions(self, congress: int = 118, offset: int = 0) -> List[Dict]:
        """
        Get recent stock transactions by members of Congress

        Args:
            congress: Congress number
            offset: Pagination offset

        Returns:
            List of stock transactions
        """
        try:
            url = (
                f"{self.BASE_URL}/{congress}/house/members/financial-disclosures/transactions.json"
            )
            params = {"offset": offset}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            return results

        except Exception as e:
            logger.error(f"Error fetching recent transactions: {e}")
            return []

    def list_current_members(
        self, chamber: str = "house", congress: int = 118  # "house" or "senate"
    ) -> List[Dict]:
        """
        Get list of current members of Congress

        Args:
            chamber: "house" or "senate"
            congress: Congress number

        Returns:
            List of member information
        """
        try:
            url = f"{self.BASE_URL}/{congress}/{chamber}/members.json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                return []

            members = results[0].get("members", [])
            return members

        except Exception as e:
            logger.error(f"Error fetching {chamber} members: {e}")
            return []


# =============================================================================
# Unified Third-Party Data Fetcher
# =============================================================================


class ThirdPartyDataFetcher:
    """
    Unified interface for fetching politician trading data from third-party sources
    """

    def __init__(self, propublica_api_key: Optional[str] = None):
        """
        Initialize fetcher with optional API keys

        Args:
            propublica_api_key: ProPublica API key (or set PROPUBLICA_API_KEY env var)
        """
        self.propublica = None
        if propublica_api_key or os.getenv("PROPUBLICA_API_KEY"):
            try:
                self.propublica = ProPublicaAPI(propublica_api_key)
            except ValueError as e:
                logger.warning(f"ProPublica API not initialized: {e}")

        self.stocknear = StockNearScraper()

    def fetch_from_propublica(
        self, fetch_members: bool = True, fetch_transactions: bool = True
    ) -> Dict[str, List]:
        """
        Fetch data from ProPublica Congress API

        Args:
            fetch_members: Whether to fetch current members
            fetch_transactions: Whether to fetch recent transactions

        Returns:
            Dictionary with 'politicians' and 'disclosures' lists
        """
        if not self.propublica:
            logger.error("ProPublica API not initialized")
            return {"politicians": [], "disclosures": []}

        politicians = []
        disclosures = []

        # Fetch current members
        if fetch_members:
            logger.info("Fetching House members from ProPublica...")
            house_members = self.propublica.list_current_members("house")
            politicians.extend(self._convert_propublica_members(house_members, "House"))

            logger.info("Fetching Senate members from ProPublica...")
            senate_members = self.propublica.list_current_members("senate")
            politicians.extend(self._convert_propublica_members(senate_members, "Senate"))

        # Fetch recent transactions
        if fetch_transactions:
            logger.info("Fetching recent stock transactions from ProPublica...")
            transactions = self.propublica.get_recent_stock_transactions()
            disclosures.extend(self._convert_propublica_transactions(transactions))

        logger.info(
            f"Fetched {len(politicians)} politicians and "
            f"{len(disclosures)} disclosures from ProPublica"
        )

        return {"politicians": politicians, "disclosures": disclosures}

    def _convert_propublica_members(self, members: List[Dict], chamber: str) -> List[Politician]:
        """Convert ProPublica member data to Politician objects"""
        politicians = []

        for member in members:
            try:
                politician = Politician(
                    first_name=member.get("first_name", ""),
                    last_name=member.get("last_name", ""),
                    full_name=f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                    role=chamber,
                    party=member.get("party", ""),
                    state_or_country=member.get("state", ""),
                    district=member.get("district"),
                    bioguide_id=member.get("id"),  # ProPublica uses bioguide IDs
                )
                politicians.append(politician)
            except Exception as e:
                logger.error(f"Error converting ProPublica member: {e}")
                continue

        return politicians

    def _convert_propublica_transactions(self, transactions: List[Dict]) -> List[TradingDisclosure]:
        """Convert ProPublica transaction data to TradingDisclosure objects"""
        disclosures = []

        for txn in transactions:
            try:
                # Parse transaction date
                txn_date_str = txn.get("transaction_date")
                if txn_date_str:
                    try:
                        transaction_date = datetime.strptime(txn_date_str, "%Y-%m-%d")
                    except ValueError:
                        transaction_date = datetime.now()
                else:
                    transaction_date = datetime.now()

                # Parse disclosure date
                disclosure_date_str = txn.get("disclosure_date")
                if disclosure_date_str:
                    try:
                        disclosure_date = datetime.strptime(disclosure_date_str, "%Y-%m-%d")
                    except ValueError:
                        disclosure_date = datetime.now()
                else:
                    disclosure_date = datetime.now()

                # Parse amount range (ProPublica provides ranges like "$1,001 - $15,000")
                amount_str = txn.get("amount", "")
                amount_min, amount_max = self._parse_amount_range(amount_str)

                disclosure = TradingDisclosure(
                    politician_bioguide_id=txn.get("member_id"),
                    transaction_date=transaction_date,
                    disclosure_date=disclosure_date,
                    transaction_type=txn.get("type", "").lower(),
                    asset_name=txn.get("asset_description", ""),
                    asset_ticker=txn.get("ticker"),
                    asset_type="stock",
                    amount_range_min=amount_min,
                    amount_range_max=amount_max,
                    source_url=f"https://www.propublica.org/",
                    raw_data=txn,
                )
                disclosures.append(disclosure)

            except Exception as e:
                logger.error(f"Error converting ProPublica transaction: {e}")
                continue

        return disclosures

    def _parse_amount_range(self, amount_str: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse ProPublica amount range string like "$1,001 - $15,000"

        Returns:
            Tuple of (min_amount, max_amount)
        """
        try:
            if not amount_str or amount_str.lower() in ["n/a", "unknown"]:
                return None, None

            # Remove currency symbols and commas
            amount_str = amount_str.replace("$", "").replace(",", "")

            # Split on dash or hyphen
            parts = [p.strip() for p in amount_str.split("-")]

            if len(parts) == 2:
                min_amt = float(parts[0])
                max_amt = float(parts[1])
                return min_amt, max_amt
            elif len(parts) == 1:
                # Single amount
                amt = float(parts[0])
                return amt, amt
            else:
                return None, None

        except (ValueError, AttributeError):
            return None, None


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "StockNearScraper",
    "ProPublicaAPI",
    "ThirdPartyDataFetcher",
]
