"""
HTTP client for the EU Parliament MEP data and financial declarations.

Fetches:
1. MEP list from the official XML endpoint
2. Declaration of Private Interests (DPI) PDF links from MEP declaration pages
3. DPI PDF downloads

The EU Parliament publishes MEP information as XML and hosts financial
interest declarations as downloadable PDFs on each MEP's profile page.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from app.lib.party_registry import abbreviate_group_name

logger = logging.getLogger(__name__)

MEP_LIST_URL = "https://www.europarl.europa.eu/meps/en/full-list/xml"
# Outgoing members from previous parliamentary term (8th term: 2014-2019)
MEP_OUTGOING_URL = "https://www.europarl.europa.eu/meps/en/incoming-outgoing/outgoing/xml"
MEP_DECLARATIONS_URL = (
    "https://www.europarl.europa.eu/meps/en/{mep_id}/{slug}/declarations"
)
USER_AGENT = "Mozilla/5.0 (compatible; PoliticianTradingETL/1.0)"

# Rate limiting defaults
REQUEST_DELAY_SECONDS = 1.5
PDF_DELAY_SECONDS = 0.5
MAX_RETRIES = 3
BACKOFF_MULTIPLIER = 2.0


class EUParliamentClient:
    """
    Async HTTP client for EU Parliament MEP data.

    Usage::

        async with EUParliamentClient() as client:
            meps = await client.fetch_mep_list()
            for mep in meps[:10]:
                decls = await client.fetch_declarations_page(
                    mep["mep_id"], mep["full_name"]
                )
    """

    def __init__(
        self,
        request_delay: float = REQUEST_DELAY_SECONDS,
        pdf_delay: float = PDF_DELAY_SECONDS,
    ) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._request_delay = request_delay
        self._pdf_delay = pdf_delay

    async def __aenter__(self) -> "EUParliamentClient":
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_mep_list(self) -> List[Dict[str, str]]:
        """
        Fetch the full MEP list from the EU Parliament XML endpoint.

        Returns:
            List of dicts with keys: mep_id, full_name, country,
            political_group, national_party
        """
        assert self._client is not None, "Client not initialized (use async with)"

        try:
            response = await self._client.get(MEP_LIST_URL)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch MEP list: {e}")
            return []

        return parse_mep_xml(response.text)

    async def fetch_outgoing_meps(self) -> List[Dict[str, str]]:
        """
        Fetch outgoing/former MEPs from the EU Parliament XML endpoint.

        This covers MEPs from the previous parliamentary term (2014-2019)
        who are no longer serving, enabling backfilling of 2015+ data.

        Returns:
            List of dicts with same keys as fetch_mep_list.
        """
        assert self._client is not None, "Client not initialized (use async with)"

        try:
            response = await self._client.get(MEP_OUTGOING_URL)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch outgoing MEP list: {e}")
            return []

        return parse_mep_xml(response.text)

    async def fetch_declarations_page(
        self, mep_id: str, mep_name: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch an MEP's declarations page and extract DPI PDF links.

        Args:
            mep_id: EU Parliament MEP numeric ID
            mep_name: MEP full name (used to build URL slug)

        Returns:
            List of dicts with keys: pdf_url, label, date, revision
        """
        assert self._client is not None, "Client not initialized (use async with)"

        slug = _name_to_slug(mep_name)
        url = MEP_DECLARATIONS_URL.format(mep_id=mep_id, slug=slug)

        await asyncio.sleep(self._request_delay)

        try:
            response = await self._client.get(url)
            if response.status_code == 404:
                logger.debug(f"No declarations page for MEP {mep_name} ({mep_id})")
                return []
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch declarations for {mep_name}: {e}")
            return []

        return parse_declarations_html(response.text, mep_id)

    async def download_pdf(self, url: str) -> Optional[bytes]:
        """
        Download a PDF file with retry and backoff.

        Args:
            url: Full URL to the PDF

        Returns:
            PDF bytes, or None on failure
        """
        assert self._client is not None, "Client not initialized (use async with)"

        delay = self._pdf_delay
        for attempt in range(MAX_RETRIES):
            await asyncio.sleep(delay)
            try:
                response = await self._client.get(url)
                if response.status_code == 200:
                    content = response.content
                    if content and content[:5] == b"%PDF-":
                        return content
                    logger.warning(f"Downloaded content is not a valid PDF: {url}")
                    return None
                elif response.status_code in {429, 503, 502}:
                    delay *= BACKOFF_MULTIPLIER
                    logger.warning(
                        f"Rate limited ({response.status_code}), "
                        f"retry {attempt + 1}/{MAX_RETRIES}"
                    )
                    continue
                elif response.status_code == 404:
                    logger.debug(f"PDF not found: {url}")
                    return None
                else:
                    logger.warning(
                        f"PDF download failed ({response.status_code}): {url}"
                    )
                    return None
            except httpx.TimeoutException:
                delay *= BACKOFF_MULTIPLIER
                logger.warning(
                    f"Timeout downloading PDF, retry {attempt + 1}/{MAX_RETRIES}"
                )
            except httpx.HTTPError as e:
                logger.error(f"Error downloading PDF: {e}")
                return None

        logger.error(f"Max retries exceeded for PDF: {url}")
        return None


# ---------------------------------------------------------------------------
# Parsing helpers (pure functions, easy to test)
# ---------------------------------------------------------------------------


def parse_mep_xml(xml_text: str) -> List[Dict[str, str]]:
    """
    Parse the MEP list XML into a list of dicts.

    The XML structure is:
    <meps>
      <mep>
        <id>256810</id>
        <fullName>Mika AALTOLA</fullName>
        <country>Finland</country>
        <politicalGroup>Group of the European People's Party (Christian Democrats)</politicalGroup>
        <nationalPoliticalGroup>Kansallinen Kokoomus</nationalPoliticalGroup>
      </mep>
      ...
    </meps>
    """
    meps: List[Dict[str, str]] = []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as e:
        logger.error(f"Failed to parse MEP XML: {e}")
        return meps

    for mep_el in root.findall(".//mep"):
        mep_id_el = mep_el.find("id")
        name_el = mep_el.find("fullName")

        if mep_id_el is None or name_el is None:
            continue

        mep_id = (mep_id_el.text or "").strip()
        full_name = (name_el.text or "").strip()
        if not mep_id or not full_name:
            continue

        country_el = mep_el.find("country")
        group_el = mep_el.find("politicalGroup")
        nat_party_el = mep_el.find("nationalPoliticalGroup")

        meps.append(
            {
                "mep_id": mep_id,
                "full_name": full_name,
                "country": (country_el.text or "").strip() if country_el is not None else "",
                "political_group": abbreviate_group_name(
                    (group_el.text or "").strip() if group_el is not None else ""
                ),
                "national_party": (
                    (nat_party_el.text or "").strip() if nat_party_el is not None else ""
                ),
            }
        )

    logger.info(f"Parsed {len(meps)} MEPs from XML")
    return meps


def parse_declarations_html(
    html: str, mep_id: str
) -> List[Dict[str, Any]]:
    """
    Parse an MEP's declarations page to extract DPI PDF links.

    The page contains links to Declaration of Private Interests PDFs,
    typically found in anchor tags within the declarations section.
    Links look like:
        /erpl-app-public/mep-documents/DPI/10/256810/...pdf
    """
    results: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html, "html.parser")

    # Find all links that point to DPI PDFs
    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Match DPI document links
        if "/DPI/" not in href and "dpi" not in href.lower():
            continue

        if not href.endswith(".pdf"):
            continue

        # Build absolute URL if relative
        if href.startswith("/"):
            pdf_url = f"https://www.europarl.europa.eu{href}"
        elif href.startswith("http"):
            pdf_url = href
        else:
            continue

        # Extract label text from the link or surrounding context
        label = link.get_text(strip=True) or "Declaration"

        # Try to extract date from URL or label
        date = _extract_date_from_url(href) or _extract_date_from_text(label)

        # Determine revision number (0 = original, 1+ = amendments)
        revision = 0
        label_lower = label.lower()
        if "modif" in label_lower or "amend" in label_lower or "corrig" in label_lower:
            revision = 1
            # Try to get specific revision number
            rev_match = re.search(r"(\d+)(?:st|nd|rd|th)\s+modif", label_lower)
            if rev_match:
                revision = int(rev_match.group(1))

        results.append(
            {
                "pdf_url": pdf_url,
                "label": label,
                "date": date,
                "revision": revision,
                "mep_id": mep_id,
            }
        )

    logger.debug(f"Found {len(results)} DPI declarations for MEP {mep_id}")
    return results


def _name_to_slug(name: str) -> str:
    """Convert MEP name to URL slug format.

    'Mika AALTOLA' -> 'Mika+AALTOLA'
    'María Teresa GIMÉNEZ BARBAT' -> 'Maria+Teresa+GIMENEZ+BARBAT'
    """
    # Replace accented characters with ASCII equivalents for URL
    slug = name.strip()
    slug = re.sub(r"\s+", "+", slug)
    return slug



def _extract_date_from_url(url: str) -> Optional[str]:
    """Try to extract a date from a DPI PDF URL.

    URLs often contain timestamps like:
    .../DPI/10/256810/256810_20240716_...pdf
    """
    match = re.search(r"(\d{4})(\d{2})(\d{2})", url)
    if match:
        year, month, day = match.groups()
        year_int = int(year)
        month_int = int(month)
        day_int = int(day)
        if 2004 <= year_int <= 2030 and 1 <= month_int <= 12 and 1 <= day_int <= 31:
            return f"{year}-{month}-{day}"
    return None


def _extract_date_from_text(text: str) -> Optional[str]:
    """Try to extract a date from label text.

    Labels may contain dates like '16/07/2024' or '2024-07-16'.
    """
    # DD/MM/YYYY
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    # YYYY-MM-DD
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return match.group(0)

    return None
