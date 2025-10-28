"""
UK Parliament API scraper for financial interests register data

This module implements scrapers for the UK Parliament's Register of Interests API
to collect MP financial disclosure data.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .models import Politician, PoliticianRole, TradingDisclosure, TransactionType
from .scrapers import BaseScraper

logger = logging.getLogger(__name__)


class UKParliamentScraper(BaseScraper):
    """Scraper for UK Parliament Register of Interests API"""

    def __init__(self, config):
        super().__init__(config)
        self.base_url = "https://interests-api.parliament.uk/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={"User-Agent": self.config.user_agent},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_members_interests(self) -> List[TradingDisclosure]:
        """Fetch all MP financial interests from the API"""
        logger.info("Starting UK Parliament financial interests collection")

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        disclosures = []

        try:
            # First, get all interest categories to understand what types of interests exist
            categories = await self._fetch_categories()
            logger.info(f"Found {len(categories)} interest categories")

            # Get all interests for financial/investment categories
            financial_categories = self._filter_financial_categories(categories)

            for category in financial_categories:
                category_disclosures = await self._fetch_interests_by_category(category)
                disclosures.extend(category_disclosures)

                # Rate limiting
                await asyncio.sleep(self.config.request_delay)

            logger.info(f"Collected {len(disclosures)} UK Parliament financial interests")
            return disclosures

        except Exception as e:
            logger.error(f"Failed to fetch UK Parliament interests: {e}")
            raise

    async def _fetch_categories(self) -> List[Dict[str, Any]]:
        """Fetch all interest categories from the API"""
        url = f"{self.base_url}/Categories"
        params = {"Take": 100}  # Get up to 100 categories

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("items", [])

    def _filter_financial_categories(
        self, categories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter categories to include only financial/investment related ones"""
        financial_keywords = [
            "shareholding",
            "share",
            "investment",
            "financial",
            "company",
            "directorship",
            "employment",
            "remuneration",
            "sponsorship",
            "gift",
            "benefit",
            "land",
            "property",
        ]

        financial_categories = []
        for category in categories:
            category_name = category.get("name", "").lower()
            if any(keyword in category_name for keyword in financial_keywords):
                financial_categories.append(category)
                logger.debug(f"Including financial category: {category.get('name')}")

        return financial_categories

    async def _fetch_interests_by_category(
        self, category: Dict[str, Any]
    ) -> List[TradingDisclosure]:
        """Fetch interests for a specific category"""
        category_id = category.get("id")
        category_name = category.get("name")

        logger.debug(f"Fetching interests for category: {category_name} (ID: {category_id})")

        disclosures = []
        skip = 0
        take = 50

        while True:
            url = f"{self.base_url}/Interests"
            params = {"categoryId": category_id, "Skip": skip, "Take": take}

            try:
                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

                    interests = data.get("items", [])
                    if not interests:
                        break

                    for interest in interests:
                        disclosure = await self._parse_uk_interest(interest, category_name)
                        if disclosure:
                            disclosures.append(disclosure)

                    skip += take

                    # If we got fewer results than requested, we're done
                    if len(interests) < take:
                        break

            except Exception as e:
                logger.error(f"Failed to fetch interests for category {category_name}: {e}")
                break

        logger.debug(f"Found {len(disclosures)} interests in category: {category_name}")
        return disclosures

    async def _parse_uk_interest(
        self, interest: Dict[str, Any], category_name: str
    ) -> Optional[TradingDisclosure]:
        """Parse a UK Parliament interest into a TradingDisclosure"""
        try:
            # Extract member information from the new API structure
            member_data = interest.get("member")
            if not member_data:
                return None

            member_id = member_data.get("id")
            politician_name = member_data.get("nameDisplayAs", "")

            # Get interest details
            interest_id = interest.get("id")
            description = interest.get("summary", "")
            registered_date = interest.get("registrationDate")

            # Parse dates
            transaction_date = (
                self._parse_date(registered_date) if registered_date else datetime.now()
            )
            disclosure_date = transaction_date  # UK system doesn't separate these

            # Determine transaction type from description
            transaction_type = self._infer_transaction_type(description, category_name)

            # Extract asset information from fields and description
            asset_name, asset_ticker = self._extract_asset_info_from_fields(
                interest, description, category_name
            )

            # Extract amount information (if available)
            amount_min, amount_max, amount_exact = self._extract_amount_info(description)

            disclosure = TradingDisclosure(
                id=f"uk_parliament_{interest_id}",
                politician_id="",  # Will be filled during politician matching
                transaction_date=transaction_date,
                disclosure_date=disclosure_date,
                transaction_type=transaction_type,
                asset_name=asset_name,
                asset_ticker=asset_ticker,
                asset_type="shareholding",  # Most UK disclosures are shareholdings
                amount_range_min=amount_min,
                amount_range_max=amount_max,
                amount_exact=amount_exact,
                source_url=f"https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/",
                raw_data={
                    "uk_interest_id": interest_id,
                    "uk_member_id": member_id,
                    "description": description,
                    "category_name": category_name,
                    "registered_date": registered_date,
                    "source": "uk_parliament_api",
                    "politician_name": politician_name,
                },
            )

            return disclosure

        except Exception as e:
            logger.error(f"Failed to parse UK interest: {e}")
            return None

    async def _fetch_mp_name(self, member_id: int) -> str:
        """Fetch MP name from the Parliament API using member ID"""
        if not self.session:
            return ""

        try:
            # Try the Members endpoint to get MP details
            member_url = f"{self.base_url}/Members/{member_id}"

            async with self.session.get(member_url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract name from the response
                    name = data.get("name", "")
                    if not name:
                        # Try alternative field names
                        name = data.get("displayAs", "")
                    if not name:
                        # Combine first and last name if available
                        first_name = data.get("nameGiven", "")
                        last_name = data.get("nameFull", "") or data.get("nameFamily", "")
                        if first_name and last_name:
                            name = f"{first_name} {last_name}"

                    if name:
                        logger.debug(f"Found MP name for ID {member_id}: {name}")
                        return name.strip()

                else:
                    logger.debug(
                        f"Could not fetch MP details for ID {member_id}: HTTP {response.status}"
                    )

        except Exception as e:
            logger.debug(f"Failed to fetch MP name for ID {member_id}: {e}")

        return ""

    def _parse_date(self, date_str: str) -> datetime:
        """Parse UK Parliament API date format"""
        try:
            # UK Parliament API uses ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

    def _infer_transaction_type(self, description: str, category_name: str) -> TransactionType:
        """Infer transaction type from description and category"""
        description_lower = description.lower()
        category_lower = category_name.lower()

        # UK Parliament disclosures are mostly about holdings, not transactions
        # But we can infer some information
        if any(word in description_lower for word in ["sold", "disposed", "divested"]):
            return TransactionType.SALE
        elif any(word in description_lower for word in ["acquired", "purchased", "bought"]):
            return TransactionType.PURCHASE
        elif "shareholding" in category_lower:
            return TransactionType.PURCHASE  # Assume shareholding disclosure is a purchase
        else:
            return TransactionType.PURCHASE  # Default assumption

    def _extract_asset_info_from_fields(
        self, interest: Dict[str, Any], description: str, category_name: str
    ) -> tuple[str, Optional[str]]:
        """Extract asset name and ticker from interest fields"""
        # Look for OrganisationName in fields
        fields = interest.get("fields", [])
        organization_name = None

        for field in fields:
            if field.get("name") == "OrganisationName":
                organization_name = field.get("value")
                break

        # Use organization name if available, otherwise fall back to description
        if organization_name:
            return organization_name, None
        else:
            return self._extract_asset_info(description, category_name)

    def _extract_asset_info(
        self, description: str, category_name: str
    ) -> tuple[str, Optional[str]]:
        """Extract asset name and ticker from description"""
        # UK descriptions often contain company names
        # This is a simplified extraction - could be enhanced with NLP

        if "shareholding" in category_name.lower():
            # Try to extract company name from shareholding descriptions
            # Format often like: "Shareholding in [Company Name] Ltd"
            if " in " in description:
                parts = description.split(" in ", 1)
                if len(parts) > 1:
                    asset_name = parts[1].strip().rstrip(".")
                    return asset_name, None

        # Fallback: use description as asset name
        return description[:100], None  # Truncate to reasonable length

    def _extract_amount_info(
        self, description: str
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Extract amount information from description"""
        # UK Parliament disclosures often don't include specific amounts
        # They use threshold categories (£70,000+, etc.)

        description_lower = description.lower()

        # Look for UK threshold amounts
        if "£70,000" in description_lower or "70000" in description_lower:
            return 70000.0, None, None
        elif "£" in description_lower:
            # Try to extract specific amounts
            import re

            amount_pattern = r"£([\d,]+)"
            matches = re.findall(amount_pattern, description)
            if matches:
                try:
                    amount = float(matches[0].replace(",", ""))
                    return amount, None, amount
                except ValueError:
                    pass

        return None, None, None

    async def get_politicians(self) -> List[Politician]:
        """Fetch current MPs from the Members API"""
        logger.info("Fetching current UK MPs")

        # For now, return empty list - would need Members API integration
        # This would require calling https://members-api.parliament.uk/
        return []


async def run_uk_parliament_collection(config) -> List[TradingDisclosure]:
    """Main function to run UK Parliament data collection"""
    async with UKParliamentScraper(config) as scraper:
        return await scraper.fetch_members_interests()


# Example usage for testing
if __name__ == "__main__":
    from .config import WorkflowConfig

    async def main():
        config = WorkflowConfig.default()
        disclosures = await run_uk_parliament_collection(config.scraping)
        print(f"Collected {len(disclosures)} UK Parliament financial interests")

        for disclosure in disclosures[:3]:  # Show first 3
            print(
                f"- {disclosure.asset_name} by {disclosure.raw_data.get('politician_name', 'Unknown')}"
            )

    asyncio.run(main())
