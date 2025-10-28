"""
Corporate Registry Scrapers for Financial Disclosure Data

This module contains scrapers for corporate registry and financial disclosure sources:
- UK Companies House REST API (requires free API key)
- Info-Financière API (France) - FREE, no API key
- OpenCorporates API (has free tier)
- XBRL/ESEF/UKSEF via filings.xbrl.org - FREE, no API key
- XBRL US API - FREE API key available

These scrapers fetch corporate financial disclosures that may be relevant to
politician trading patterns, conflicts of interest, and asset declarations.
"""

import logging
import os
import time
from base64 import b64encode
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from .models import Politician, TradingDisclosure

logger = logging.getLogger(__name__)


# =============================================================================
# UK Companies House REST API
# =============================================================================


class UKCompaniesHouseScraper:
    """
    Scraper for UK Companies House REST API
    Source: https://api.companieshouse.gov.uk/

    Requires: Free API key from https://developer.company-information.service.gov.uk/
    """

    BASE_URL = "https://api.companieshouse.gov.uk"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("UK_COMPANIES_HOUSE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "UK Companies House API key required. "
                "Get free key from https://developer.company-information.service.gov.uk/ "
                "and set UK_COMPANIES_HOUSE_API_KEY environment variable."
            )

        self.session = requests.Session()
        # API uses HTTP Basic Auth with API key as username, password empty
        auth_string = f"{self.api_key}:"
        auth_header = b64encode(auth_string.encode()).decode()
        self.session.headers.update(
            {"Authorization": f"Basic {auth_header}", "User-Agent": "PoliticianTradingTracker/1.0"}
        )

    def search_companies(self, query: str, items_per_page: int = 20) -> List[Dict]:
        """
        Search for companies by name

        Args:
            query: Company name search query
            items_per_page: Number of results per page (max 100)

        Returns:
            List of company search results
        """
        try:
            url = f"{self.BASE_URL}/search/companies"
            params = {"q": query, "items_per_page": min(items_per_page, 100)}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            logger.info(f"Found {len(items)} companies matching '{query}'")
            return items

        except Exception as e:
            logger.error(f"Error searching UK companies: {e}")
            return []

    def get_company_profile(self, company_number: str) -> Optional[Dict]:
        """
        Get company profile by company number

        Args:
            company_number: UK company registration number (e.g., "00000006")

        Returns:
            Company profile data or None
        """
        try:
            url = f"{self.BASE_URL}/company/{company_number}"

            # Respect rate limit: 600 requests per 5 minutes = 2 requests/second
            time.sleep(0.5)

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Fetched profile for company {company_number}")

            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Company {company_number} not found")
            else:
                logger.error(f"HTTP error fetching company profile: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching UK company profile: {e}")
            return None

    def get_company_officers(self, company_number: str) -> List[Dict]:
        """
        Get company officers (directors, secretaries) by company number

        Args:
            company_number: UK company registration number

        Returns:
            List of company officers
        """
        try:
            url = f"{self.BASE_URL}/company/{company_number}/officers"

            time.sleep(0.5)  # Rate limiting

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            logger.info(f"Found {len(items)} officers for company {company_number}")
            return items

        except Exception as e:
            logger.error(f"Error fetching UK company officers: {e}")
            return []

    def get_persons_with_significant_control(self, company_number: str) -> List[Dict]:
        """
        Get persons with significant control (PSC) for a company

        Args:
            company_number: UK company registration number

        Returns:
            List of PSC records
        """
        try:
            url = f"{self.BASE_URL}/company/{company_number}/persons-with-significant-control"

            time.sleep(0.5)  # Rate limiting

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            logger.info(f"Found {len(items)} PSC records for company {company_number}")
            return items

        except Exception as e:
            logger.error(f"Error fetching UK company PSC: {e}")
            return []


# =============================================================================
# Info-Financière API (France)
# =============================================================================


class InfoFinanciereAPIScraper:
    """
    Scraper for Info-Financière API (France)
    Source: https://info-financiere.gouv.fr/api/v1/console

    FREE! No API key required. 10,000 calls per IP per day.
    """

    BASE_URL = "https://info-financiere.gouv.fr/api/v1"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "PoliticianTradingTracker/1.0", "Accept": "application/json"}
        )

    def search_publications(
        self,
        query: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> List[Dict]:
        """
        Search financial publications

        Args:
            query: Search query (company name, ISIN, etc.)
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            page: Page number (1-indexed)
            per_page: Results per page (max 100)

        Returns:
            List of publication records
        """
        try:
            url = f"{self.BASE_URL}/publications"
            params = {"page": page, "per_page": min(per_page, 100)}

            if query:
                params["q"] = query
            if from_date:
                params["from_date"] = from_date
            if to_date:
                params["to_date"] = to_date

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", []) or data.get("data", [])

            logger.info(f"Found {len(items)} French financial publications")
            return items

        except Exception as e:
            logger.error(f"Error fetching French financial publications: {e}")
            return []

    def get_publication_details(self, publication_id: str) -> Optional[Dict]:
        """
        Get details for a specific publication

        Args:
            publication_id: Publication ID

        Returns:
            Publication details or None
        """
        try:
            url = f"{self.BASE_URL}/publications/{publication_id}"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Fetched publication {publication_id}")

            return data

        except Exception as e:
            logger.error(f"Error fetching French publication details: {e}")
            return None


# =============================================================================
# OpenCorporates API
# =============================================================================


class OpenCorporatesScraper:
    """
    Scraper for OpenCorporates API
    Source: https://api.opencorporates.com/v0.4/

    Global multi-jurisdiction company registry aggregator.
    Has free tier with rate limits, paid tiers for higher volume.
    """

    BASE_URL = "https://api.opencorporates.com/v0.4"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENCORPORATES_API_KEY")
        # API key is optional for free tier, but recommended

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "PoliticianTradingTracker/1.0", "Accept": "application/json"}
        )

    def search_companies(
        self, query: str, jurisdiction_code: Optional[str] = None, per_page: int = 30, page: int = 1
    ) -> List[Dict]:
        """
        Search for companies across jurisdictions

        Args:
            query: Company name search query
            jurisdiction_code: Filter by jurisdiction (e.g., "us_ca", "gb", "de")
            per_page: Results per page (max 100)
            page: Page number (1-indexed)

        Returns:
            List of company search results
        """
        try:
            url = f"{self.BASE_URL}/companies/search"
            params = {"q": query, "per_page": min(per_page, 100), "page": page}

            if jurisdiction_code:
                params["jurisdiction_code"] = jurisdiction_code

            if self.api_key:
                params["api_token"] = self.api_key

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", {})
            companies = results.get("companies", [])

            logger.info(f"Found {len(companies)} companies matching '{query}'")
            return companies

        except Exception as e:
            logger.error(f"Error searching OpenCorporates: {e}")
            return []

    def get_company(self, jurisdiction_code: str, company_number: str) -> Optional[Dict]:
        """
        Get company details by jurisdiction and company number

        Args:
            jurisdiction_code: Jurisdiction code (e.g., "us_ca", "gb")
            company_number: Company registration number

        Returns:
            Company details or None
        """
        try:
            url = f"{self.BASE_URL}/companies/{jurisdiction_code}/{company_number}"
            params = {}

            if self.api_key:
                params["api_token"] = self.api_key

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            company = data.get("results", {}).get("company", {})

            logger.info(f"Fetched company {jurisdiction_code}/{company_number}")
            return company

        except Exception as e:
            logger.error(f"Error fetching OpenCorporates company: {e}")
            return None

    def get_company_officers(self, jurisdiction_code: str, company_number: str) -> List[Dict]:
        """
        Get officers for a company

        Args:
            jurisdiction_code: Jurisdiction code
            company_number: Company registration number

        Returns:
            List of officers
        """
        try:
            url = f"{self.BASE_URL}/companies/{jurisdiction_code}/{company_number}/officers"
            params = {}

            if self.api_key:
                params["api_token"] = self.api_key

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", {})
            officers = results.get("officers", [])

            logger.info(
                f"Found {len(officers)} officers for company {jurisdiction_code}/{company_number}"
            )
            return officers

        except Exception as e:
            logger.error(f"Error fetching OpenCorporates officers: {e}")
            return []


# =============================================================================
# XBRL Filings API (filings.xbrl.org)
# =============================================================================


class XBRLFilingsScraper:
    """
    Scraper for XBRL Filings API (filings.xbrl.org)
    Source: https://filings.xbrl.org/

    FREE! No API key required. JSON:API compliant.
    Covers EU/UK/Ukraine ESEF/UKSEF filings.
    """

    BASE_URL = "https://filings.xbrl.org/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "PoliticianTradingTracker/1.0", "Accept": "application/vnd.api+json"}
        )

    def get_filings(
        self,
        country: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page_number: int = 1,
        page_size: int = 100,
    ) -> List[Dict]:
        """
        Get XBRL filings with filters

        Args:
            country: Country code filter (e.g., "GB", "FR", "DE")
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            page_number: Page number (1-indexed)
            page_size: Results per page (max 500)

        Returns:
            List of filing records
        """
        try:
            url = f"{self.BASE_URL}/filings"
            params = {"page[number]": page_number, "page[size]": min(page_size, 500)}

            # Add filters using JSON:API filter syntax
            if country:
                params["filter[country]"] = country
            if from_date:
                params["filter[date_added][gte]"] = from_date
            if to_date:
                params["filter[date_added][lte]"] = to_date

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            filings = data.get("data", [])

            logger.info(f"Found {len(filings)} XBRL filings")
            return filings

        except Exception as e:
            logger.error(f"Error fetching XBRL filings: {e}")
            return []

    def get_entities(
        self, country: Optional[str] = None, page_number: int = 1, page_size: int = 100
    ) -> List[Dict]:
        """
        Get filing entities (companies)

        Args:
            country: Country code filter
            page_number: Page number (1-indexed)
            page_size: Results per page (max 500)

        Returns:
            List of entity records
        """
        try:
            url = f"{self.BASE_URL}/entities"
            params = {"page[number]": page_number, "page[size]": min(page_size, 500)}

            if country:
                params["filter[country]"] = country

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            entities = data.get("data", [])

            logger.info(f"Found {len(entities)} XBRL entities")
            return entities

        except Exception as e:
            logger.error(f"Error fetching XBRL entities: {e}")
            return []


# =============================================================================
# XBRL US API
# =============================================================================


class XBRLUSScraper:
    """
    Scraper for XBRL US API
    Source: https://github.com/xbrlus/xbrl-api

    FREE API key available at https://xbrl.us/home/use/xbrl-api/
    ~15 minute latency from SEC filings.
    """

    BASE_URL = "https://api.xbrl.us/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XBRL_US_API_KEY")
        if not self.api_key:
            raise ValueError(
                "XBRL US API key required. "
                "Get free key from https://xbrl.us/home/use/xbrl-api/ "
                "and set XBRL_US_API_KEY environment variable."
            )

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "PoliticianTradingTracker/1.0", "Accept": "application/json"}
        )

    def search_companies(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Search for companies (filers)

        Args:
            query: Company name or ticker search query
            limit: Maximum results (max 2000)

        Returns:
            List of company/filer records
        """
        try:
            url = f"{self.BASE_URL}/entity/search"
            params = {"name": query, "limit": min(limit, 2000), "client_id": self.api_key}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            entities = data.get("data", [])

            logger.info(f"Found {len(entities)} XBRL US entities matching '{query}'")
            return entities

        except Exception as e:
            logger.error(f"Error searching XBRL US companies: {e}")
            return []

    def get_entity_filings(
        self,
        entity_id: int,
        filing_date_from: Optional[str] = None,
        filing_date_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get filings for an entity

        Args:
            entity_id: XBRL US entity ID
            filing_date_from: Start date in YYYY-MM-DD format
            filing_date_to: End date in YYYY-MM-DD format
            limit: Maximum results (max 2000)

        Returns:
            List of filing records
        """
        try:
            url = f"{self.BASE_URL}/filing/search"
            params = {"entity.id": entity_id, "limit": min(limit, 2000), "client_id": self.api_key}

            if filing_date_from:
                params["filing_date.from"] = filing_date_from
            if filing_date_to:
                params["filing_date.to"] = filing_date_to

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            filings = data.get("data", [])

            logger.info(f"Found {len(filings)} filings for entity {entity_id}")
            return filings

        except Exception as e:
            logger.error(f"Error fetching XBRL US filings: {e}")
            return []

    def get_facts(
        self,
        concept_name: str,
        entity_id: Optional[int] = None,
        period_end_from: Optional[str] = None,
        period_end_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get XBRL facts (financial data points)

        Args:
            concept_name: XBRL concept/tag name (e.g., "Assets", "Revenues")
            entity_id: Filter by entity ID
            period_end_from: Start date for period end filter
            period_end_to: End date for period end filter
            limit: Maximum results (max 2000)

        Returns:
            List of fact records
        """
        try:
            url = f"{self.BASE_URL}/fact/search"
            params = {
                "concept.local-name": concept_name,
                "limit": min(limit, 2000),
                "client_id": self.api_key,
            }

            if entity_id:
                params["entity.id"] = entity_id
            if period_end_from:
                params["period.fiscal-period-end.from"] = period_end_from
            if period_end_to:
                params["period.fiscal-period-end.to"] = period_end_to

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            facts = data.get("data", [])

            logger.info(f"Found {len(facts)} facts for concept '{concept_name}'")
            return facts

        except Exception as e:
            logger.error(f"Error fetching XBRL US facts: {e}")
            return []


# =============================================================================
# Unified Corporate Registry Data Fetcher
# =============================================================================


class CorporateRegistryFetcher:
    """
    Unified interface for fetching corporate registry and financial disclosure data
    """

    def __init__(
        self,
        uk_companies_house_key: Optional[str] = None,
        opencorporates_key: Optional[str] = None,
        xbrl_us_key: Optional[str] = None,
    ):
        """
        Initialize fetcher with optional API keys

        Args:
            uk_companies_house_key: UK Companies House API key
            opencorporates_key: OpenCorporates API key
            xbrl_us_key: XBRL US API key
        """
        # Initialize scrapers that don't require keys
        self.info_financiere = InfoFinanciereAPIScraper()
        self.xbrl_filings = XBRLFilingsScraper()

        # Initialize scrapers that require keys (optional)
        self.uk_companies_house = None
        if uk_companies_house_key or os.getenv("UK_COMPANIES_HOUSE_API_KEY"):
            try:
                self.uk_companies_house = UKCompaniesHouseScraper(uk_companies_house_key)
            except ValueError as e:
                logger.warning(f"UK Companies House API not initialized: {e}")

        self.opencorporates = OpenCorporatesScraper(opencorporates_key)

        self.xbrl_us = None
        if xbrl_us_key or os.getenv("XBRL_US_API_KEY"):
            try:
                self.xbrl_us = XBRLUSScraper(xbrl_us_key)
            except ValueError as e:
                logger.warning(f"XBRL US API not initialized: {e}")

    def fetch_uk_company_data(self, company_name: str) -> Dict[str, List]:
        """
        Fetch UK company data by name

        Args:
            company_name: UK company name to search

        Returns:
            Dictionary with companies, officers, and PSC data
        """
        if not self.uk_companies_house:
            logger.error("UK Companies House API not initialized")
            return {"companies": [], "officers": [], "psc": []}

        logger.info(f"Fetching UK company data for: {company_name}")

        # Search for company
        companies = self.uk_companies_house.search_companies(company_name)

        all_officers = []
        all_psc = []

        # Get officers and PSC for each company found
        for company in companies[:5]:  # Limit to first 5 results
            company_number = company.get("company_number")
            if company_number:
                officers = self.uk_companies_house.get_company_officers(company_number)
                psc = self.uk_companies_house.get_persons_with_significant_control(company_number)

                all_officers.extend(officers)
                all_psc.extend(psc)

        logger.info(
            f"Fetched {len(companies)} UK companies, "
            f"{len(all_officers)} officers, {len(all_psc)} PSC records"
        )

        return {"companies": companies, "officers": all_officers, "psc": all_psc}

    def fetch_french_disclosures(
        self, query: Optional[str] = None, days_back: int = 30
    ) -> List[Dict]:
        """
        Fetch French financial disclosures

        Args:
            query: Search query (company name, ISIN, etc.)
            days_back: Number of days to look back

        Returns:
            List of French financial publications
        """
        logger.info(f"Fetching French financial disclosures (last {days_back} days)")

        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        publications = self.info_financiere.search_publications(
            query=query, from_date=from_date, to_date=to_date, per_page=100
        )

        logger.info(f"Fetched {len(publications)} French publications")
        return publications

    def fetch_xbrl_eu_filings(
        self, country: Optional[str] = None, days_back: int = 30
    ) -> List[Dict]:
        """
        Fetch EU/UK XBRL filings

        Args:
            country: Country code (e.g., "GB", "FR")
            days_back: Number of days to look back

        Returns:
            List of XBRL filings
        """
        logger.info(f"Fetching XBRL EU filings (last {days_back} days)")

        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        filings = self.xbrl_filings.get_filings(country=country, from_date=from_date, page_size=100)

        logger.info(f"Fetched {len(filings)} XBRL filings")
        return filings


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "UKCompaniesHouseScraper",
    "InfoFinanciereAPIScraper",
    "OpenCorporatesScraper",
    "XBRLFilingsScraper",
    "XBRLUSScraper",
    "CorporateRegistryFetcher",
]
