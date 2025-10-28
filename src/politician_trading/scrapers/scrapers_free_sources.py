"""
Free Data Source Scrapers for Politician Trading Data

This module contains scrapers for free, publicly available politician trading data sources:
- Senate Stock Watcher (GitHub JSON dataset)
- Finnhub Congressional Trading API
- SEC Edgar Insider Trading API
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from .models import Politician, TradingDisclosure

logger = logging.getLogger(__name__)


# =============================================================================
# Senate Stock Watcher (GitHub Dataset)
# =============================================================================


class SenateStockWatcherScraper:
    """
    Scraper for Senate Stock Watcher GitHub dataset
    Source: https://github.com/timothycarambat/senate-stock-watcher-data
    """

    BASE_URL = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PoliticianTradingTracker/1.0"})

    def fetch_all_transactions(self) -> List[Dict]:
        """
        Fetch all historical Senate transactions from GitHub

        Returns:
            List of transaction dictionaries
        """
        try:
            # File is in aggregate/ folder
            url = f"{self.BASE_URL}/aggregate/all_transactions.json"
            logger.info(f"Fetching Senate transactions from: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Fetched {len(data)} Senate transactions")

            return data

        except Exception as e:
            logger.error(f"Error fetching Senate Stock Watcher data: {e}")
            return []

    def fetch_recent_transactions(self, days: int = 30) -> List[Dict]:
        """
        Fetch recent transactions from the last N days

        Args:
            days: Number of days to look back

        Returns:
            List of recent transaction dictionaries
        """
        all_transactions = self.fetch_all_transactions()

        if not all_transactions:
            return []

        # Filter for recent transactions
        cutoff_date = datetime.now() - timedelta(days=days)
        recent = []

        for txn in all_transactions:
            try:
                # Parse transaction date
                txn_date_str = txn.get("transaction_date")
                if not txn_date_str:
                    continue

                txn_date = datetime.strptime(txn_date_str, "%m/%d/%Y")

                if txn_date >= cutoff_date:
                    recent.append(txn)

            except (ValueError, AttributeError):
                continue

        logger.info(f"Found {len(recent)} transactions in last {days} days")
        return recent

    def convert_to_politicians(self, transactions: List[Dict]) -> List[Politician]:
        """
        Extract unique politicians from transaction data

        Args:
            transactions: List of transaction dictionaries

        Returns:
            List of Politician objects
        """
        politicians_map = {}

        for txn in transactions:
            try:
                # Parse senator name (format: "FirstName MiddleInitial LastName")
                senator_name = txn.get("senator", "").strip()
                if not senator_name:
                    continue

                # Split name into parts
                name_parts = senator_name.split()
                if len(name_parts) >= 2:
                    # Handle middle names/initials
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    full_name = senator_name
                else:
                    first_name = senator_name
                    last_name = ""
                    full_name = senator_name

                # Create unique key
                key = senator_name

                if key not in politicians_map:
                    politicians_map[key] = Politician(
                        first_name=first_name,
                        last_name=last_name,
                        full_name=full_name,
                        role="Senate",
                        party="",  # Not included in dataset
                        state_or_country="US",
                        bioguide_id=None,  # Not included in dataset
                    )

            except Exception as e:
                logger.error(f"Error converting politician: {e}")
                continue

        politicians = list(politicians_map.values())
        logger.info(f"Extracted {len(politicians)} unique senators")

        return politicians

    def convert_to_disclosures(
        self, transactions: List[Dict], politician_lookup: Optional[Dict[str, str]] = None
    ) -> List[TradingDisclosure]:
        """
        Convert transaction data to TradingDisclosure objects

        Args:
            transactions: List of transaction dictionaries
            politician_lookup: Optional mapping of "FirstName_LastName" to politician_id

        Returns:
            List of TradingDisclosure objects
        """
        disclosures = []

        for txn in transactions:
            try:
                # Parse dates
                txn_date_str = txn.get("transaction_date")
                disclosure_date_str = txn.get("date_received")

                if not txn_date_str:
                    continue

                try:
                    transaction_date = datetime.strptime(txn_date_str, "%m/%d/%Y")
                except ValueError:
                    transaction_date = datetime.now()

                try:
                    disclosure_date = (
                        datetime.strptime(disclosure_date_str, "%m/%d/%Y")
                        if disclosure_date_str
                        else transaction_date
                    )
                except ValueError:
                    disclosure_date = transaction_date

                # Parse amount range
                amount_str = txn.get("amount", "")
                amount_min, amount_max = self._parse_amount_range(amount_str)

                # Get senator name for bioguide_id (use same format as convert_to_politicians)
                senator_name = txn.get("senator", "").strip()

                # Create disclosure
                disclosure = TradingDisclosure(
                    politician_bioguide_id=senator_name,  # Use senator name as bioguide_id
                    transaction_date=transaction_date,
                    disclosure_date=disclosure_date,
                    transaction_type=txn.get("type", "").lower() or "purchase",
                    asset_name=txn.get("asset_description", ""),
                    asset_ticker=txn.get("ticker"),
                    asset_type=txn.get("asset_type", "stock"),
                    amount_range_min=amount_min,
                    amount_range_max=amount_max,
                    source_url=txn.get("ptr_link", "https://efdsearch.senate.gov"),
                    raw_data=txn,
                )

                disclosures.append(disclosure)

            except Exception as e:
                logger.error(f"Error converting disclosure: {e}")
                continue

        logger.info(f"Converted {len(disclosures)} disclosures")
        return disclosures

    def _parse_amount_range(self, amount_str: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse Senate amount range format: "$1,001 - $15,000"

        Returns:
            Tuple of (min_amount, max_amount)
        """
        try:
            if not amount_str or amount_str.lower() in ["n/a", "unknown"]:
                return None, None

            # Handle special cases
            if "over" in amount_str.lower():
                # "$50,000,001 - Over"
                parts = amount_str.split("-")
                if parts:
                    min_str = parts[0].strip().replace("$", "").replace(",", "")
                    try:
                        return float(min_str), None
                    except ValueError:
                        return None, None

            # Remove currency symbols and commas
            amount_str = amount_str.replace("$", "").replace(",", "")

            # Split on dash
            parts = [p.strip() for p in amount_str.split("-")]

            if len(parts) == 2:
                min_amt = float(parts[0])
                max_amt = float(parts[1]) if parts[1] and parts[1].lower() != "over" else None
                return min_amt, max_amt
            elif len(parts) == 1:
                amt = float(parts[0])
                return amt, amt
            else:
                return None, None

        except (ValueError, AttributeError):
            return None, None


# =============================================================================
# Finnhub Congressional Trading API
# =============================================================================


class FinnhubCongressionalAPI:
    """
    Client for Finnhub Congressional Trading API
    Free tier available at https://finnhub.io
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("Finnhub API key required. Set FINNHUB_API_KEY environment variable.")

        self.session = requests.Session()

    def get_congressional_trading(
        self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Get congressional trading for a specific stock symbol

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format

        Returns:
            List of trading transactions
        """
        try:
            url = f"{self.BASE_URL}/stock/congressional-trading"
            params = {"symbol": symbol, "token": self.api_key}

            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            transactions = data.get("data", [])

            logger.info(f"Fetched {len(transactions)} transactions for {symbol}")
            return transactions

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Finnhub rate limit exceeded (30 requests/second)")
            else:
                logger.error(f"HTTP error fetching Finnhub data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Finnhub congressional trading: {e}")
            return []


# =============================================================================
# SEC Edgar Insider Trading API
# =============================================================================


class SECEdgarInsiderAPI:
    """
    Client for SEC Edgar Insider Trading data
    Source: https://data.sec.gov
    """

    BASE_URL = "https://data.sec.gov"

    def __init__(self):
        self.session = requests.Session()
        # SEC requires a User-Agent header
        self.session.headers.update(
            {
                "User-Agent": "PoliticianTradingTracker/1.0 (contact@example.com)",
                "Accept-Encoding": "gzip, deflate",
                "Host": "data.sec.gov",
            }
        )

    def get_company_submissions(self, cik: str) -> Dict:
        """
        Get submission history for a company by CIK number

        Args:
            cik: 10-digit Central Index Key (with leading zeros)

        Returns:
            Submissions data dictionary
        """
        try:
            # Ensure CIK is 10 digits with leading zeros
            cik_padded = cik.zfill(10)

            url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"
            logger.info(f"Fetching submissions for CIK {cik_padded}")

            # Respect SEC rate limit: 10 requests per second
            time.sleep(0.11)  # ~9 requests/second to be safe

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Fetched submissions for {data.get('name', 'Unknown')}")

            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"CIK {cik} not found")
            else:
                logger.error(f"HTTP error fetching SEC data: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching SEC Edgar data: {e}")
            return {}

    def get_insider_transactions(self, cik: str) -> List[Dict]:
        """
        Get Form 4 insider transaction filings for a company

        Args:
            cik: Company CIK number

        Returns:
            List of Form 4 filings
        """
        submissions = self.get_company_submissions(cik)

        if not submissions:
            return []

        # Extract Form 4 filings
        filings = submissions.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        primary_documents = filings.get("primaryDocument", [])

        form4_transactions = []

        for i, form in enumerate(forms):
            if form == "4":  # Form 4 is insider transaction report
                form4_transactions.append(
                    {
                        "accessionNumber": (
                            accession_numbers[i] if i < len(accession_numbers) else None
                        ),
                        "filingDate": filing_dates[i] if i < len(filing_dates) else None,
                        "primaryDocument": (
                            primary_documents[i] if i < len(primary_documents) else None
                        ),
                        "cik": cik,
                    }
                )

        logger.info(f"Found {len(form4_transactions)} Form 4 filings for CIK {cik}")
        return form4_transactions


# =============================================================================
# Unified Free Data Fetcher
# =============================================================================


class FreeDataFetcher:
    """
    Unified interface for fetching politician trading data from free sources
    """

    def __init__(self, finnhub_api_key: Optional[str] = None):
        """
        Initialize fetcher with optional API keys

        Args:
            finnhub_api_key: Finnhub API key (or set FINNHUB_API_KEY env var)
        """
        self.senate_watcher = SenateStockWatcherScraper()
        self.sec_edgar = SECEdgarInsiderAPI()

        self.finnhub = None
        if finnhub_api_key or os.getenv("FINNHUB_API_KEY"):
            try:
                self.finnhub = FinnhubCongressionalAPI(finnhub_api_key)
            except ValueError as e:
                logger.warning(f"Finnhub API not initialized: {e}")

    def fetch_from_senate_watcher(
        self, recent_only: bool = False, days: int = 90
    ) -> Dict[str, List]:
        """
        Fetch data from Senate Stock Watcher GitHub dataset

        Args:
            recent_only: If True, only fetch recent transactions
            days: Number of days to look back if recent_only=True

        Returns:
            Dictionary with 'politicians' and 'disclosures' lists
        """
        logger.info("=" * 80)
        logger.info("FETCHING FROM SENATE STOCK WATCHER (GitHub)")
        logger.info("=" * 80)

        # Fetch transactions
        if recent_only:
            transactions = self.senate_watcher.fetch_recent_transactions(days)
        else:
            transactions = self.senate_watcher.fetch_all_transactions()

        if not transactions:
            logger.warning("No transactions fetched from Senate Stock Watcher")
            return {"politicians": [], "disclosures": []}

        # Convert to models
        politicians = self.senate_watcher.convert_to_politicians(transactions)
        disclosures = self.senate_watcher.convert_to_disclosures(transactions)

        logger.info(
            f"Fetched {len(politicians)} politicians and "
            f"{len(disclosures)} disclosures from Senate Stock Watcher"
        )

        return {"politicians": politicians, "disclosures": disclosures}


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "SenateStockWatcherScraper",
    "FinnhubCongressionalAPI",
    "SECEdgarInsiderAPI",
    "FreeDataFetcher",
]
