# Senate ETL Implementation Guide

## Purpose

This document is a complete reference for any agent or developer working on the Senate financial disclosure ETL pipeline. It consolidates all research on data sources, anti-bot challenges, the legal landscape, and the current codebase — so you can make informed decisions without re-researching from scratch.

---

## Table of Contents

1. [Legal Context: Why Senate Data Is Hard to Get](#1-legal-context)
2. [Official Government Data Sources](#2-official-government-data-sources)
3. [The efdsearch.senate.gov Internal API (Primary Source)](#3-efdsearch-internal-api)
4. [Anti-Bot Protections and How to Handle Them](#4-anti-bot-protections)
5. [Third-Party Data Sources (Alternatives & Supplements)](#5-third-party-data-sources)
6. [Pre-Scraped Open Data Repos](#6-pre-scraped-open-data-repos)
7. [Current Codebase Architecture](#7-current-codebase-architecture)
8. [Database Schema](#8-database-schema)
9. [Implementation Recommendations](#9-implementation-recommendations)
10. [Testing Strategy](#10-testing-strategy)
11. [Known Limitations](#11-known-limitations)
12. [Reference Links](#12-reference-links)

---

## 1. Legal Context

### The STOCK Act and Its Gutting

The **STOCK Act** (S.2038, signed April 4, 2012) originally required Congress to provide a **"searchable, sortable, and downloadable database"** of financial disclosures with **no login required**.

In **April 2013**, Congress passed **S.716** (Public Law 113-7) — with no debate, no recorded vote, in just 4 days — which:

- **Removed** the requirement for a searchable/sortable/downloadable database
- **Removed** the prohibition on requiring a login
- **Removed** electronic filing requirements for most officials (kept it only for Members of Congress and candidates)
- **Allowed** paper filings again

This is why `efdsearch.senate.gov` only offers a basic web search with no API, no bulk download, and no ZIP files — the legal mandate for structured data access was repealed.

**Statutory references:**
- Original STOCK Act: https://www.congress.gov/112/plaws/publ105/PLAW-112publ105.htm
- 2013 Amendment (S.716): https://www.govinfo.gov/content/pkg/PLAW-113publ7/html/PLAW-113publ7.htm

### Usage Restrictions

Per the Ethics in Government Act, it is **unlawful** to use Financial Disclosure Reports for:
- Any **commercial purpose** (except by news/media for public dissemination)
- Determining **credit ratings**
- **Solicitation** purposes

Ensure any use of this data complies with these restrictions.

---

## 2. Official Government Data Sources

### What EXISTS for Senate Trading Data

| Source | URL | Has Trading Data? | Format | API? | Bulk Download? |
|--------|-----|-------------------|--------|------|----------------|
| **efdsearch.senate.gov** | https://efdsearch.senate.gov/search/report/data/ | **YES** | JSON (DataTables) | Undocumented internal | No |
| **Senate.gov Senators XML** | https://www.senate.gov/general/contact_information/senators_cfm.xml | Senator list only | XML | N/A | Yes |

### What Does NOT Have Senate Trading Data

Every other government entity was checked. None carry this data:

| Source | URL | What It Has Instead |
|--------|-----|---------------------|
| GPO GovInfo | https://www.govinfo.gov/bulkdata | Bills, CFR, Federal Register |
| Senate Ethics Committee | https://www.ethics.senate.gov/public/index.cfm/financialdisclosure | Filing instructions and forms only |
| Office of Government Ethics (OGE) | https://www.oge.gov | **Executive branch only** — does not cover Congress |
| GAO | https://www.gao.gov | Audit/oversight reports, not raw data |
| Congress.gov / Library of Congress | https://www.congress.gov | Legislative data (bills, votes) — no financial disclosures |
| Senate LDA API | https://lda.senate.gov/api/redoc/v1/ | **Lobbying** data (completely different system) |
| Senate Bulk Downloads | https://www.senate.gov/legislative/Public_Disclosure/database_download.htm | Lobbying XML only |
| data.gov | https://data.gov | No Senate financial disclosure datasets |
| FEC | https://www.fec.gov | Campaign finance — different from personal finance |

### House vs. Senate: The Asymmetry

The **House** publishes annual ZIP files with XML indexes:
```
https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YEAR}FD.zip
```

The **Senate has no equivalent**. This is the single biggest gap. Senate data is only accessible one report at a time via efdsearch.senate.gov.

### Senate LDA API (Different Data — Do Not Confuse)

The Senate **does** have a proper REST API at `https://lda.senate.gov/api/redoc/v1/` with OpenAPI documentation — but this is for **lobbying disclosure** (who lobbied whom), NOT personal financial disclosures (what senators traded).

> **Warning:** This LDA system will be **decommissioned after 06/30/2026**.

---

## 3. The efdsearch.senate.gov Internal API (Primary Source)

The site is a Django application with a jQuery DataTables-powered interface. There is an **undocumented internal JSON endpoint** that can potentially be accessed without a full browser.

### 3.1 Three-Step Session Flow

#### Step 1: Get CSRF Token

```http
GET https://efdsearch.senate.gov/search/
```

Parse the HTML response for:
```html
<input type="hidden" name="csrfmiddlewaretoken" value="{TOKEN}">
```
Also capture the `csrftoken` cookie from the response headers.

#### Step 2: Accept the Prohibition Agreement

```http
POST https://efdsearch.senate.gov/search/home/
Headers:
  Origin: https://efdsearch.senate.gov
  Referer: https://efdsearch.senate.gov/search/home/
  Cookie: csrftoken={cookie_value}
  Content-Type: application/x-www-form-urlencoded
Body:
  prohibition_agreement=1&csrfmiddlewaretoken={TOKEN}
```

This establishes a session. The server responds with a `sessionid` cookie.

#### Step 3: Query the Data API

```http
POST https://efdsearch.senate.gov/search/report/data/
Headers:
  X-CSRFToken: {csrftoken_from_cookie}
  Referer: https://efdsearch.senate.gov/search/
  Origin: https://efdsearch.senate.gov
  Cookie: csrftoken={value}; sessionid={value}
  Content-Type: application/x-www-form-urlencoded
```

### 3.2 POST Parameters for `/search/report/data/`

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `start` | int | Pagination offset | `0` |
| `length` | int | Records per page (max ~100) | `100` |
| `report_types` | JSON string | Report type filter | `'[11]'` |
| `filter_types` | JSON string | Filer type filter | `'[1]'` |
| `first_name` | string | First name search | `''` |
| `last_name` | string | Last name search | `'booker'` |
| `submitted_start_date` | string | Start date (MM/DD/YYYY HH:MM:SS) | `'01/01/2025 00:00:00'` |
| `submitted_end_date` | string | End date (MM/DD/YYYY HH:MM:SS) | `'12/31/2025 23:59:59'` |

### 3.3 Known `report_types` Values

| Value | Report Type | Confirmed Source |
|-------|-------------|------------------|
| `7` | Annual Report | [Jagermeister/out_of_many_one](https://github.com/Jagermeister/out_of_many_one/blob/master/docs/Process_01_Fetch.md) |
| `11` | Periodic Transaction Report (PTR) | Our deprecated code at `resources/deprecated/python-micro-service/politician_trading/sources/us_senate.py:57` |

Other values likely exist for: Candidate Report, New Filer Report, Termination Report, Blind Trust Report, Amendment variants. These can be enumerated by inspecting the checkbox values on the search form HTML.

### 3.4 Known `filter_types` Values

| Value | Filer Type |
|-------|-----------|
| `1` | Senator |

Other values likely include: Former Senator, Candidate.

### 3.5 JSON Response Format

```json
{
  "draw": 1,
  "recordsTotal": 247,
  "recordsFiltered": 247,
  "result": "ok",
  "data": [
    [
      "Cory",
      "Booker",
      "Senator",
      "<a href='/search/view/ptr/a1b2c3d4-e5f6-7890-abcd-ef1234567890/'>Periodic Transaction Report</a>",
      "01/15/2025"
    ]
  ]
}
```

**Key observations:**
- `data[n][3]` contains HTML with the report link
- Link format for PTRs: `/search/view/ptr/{uuid}/`
- Link format for Annual reports: `/search/view/annual/{uuid}/`
- Link format for Paper filings: `/search/view/paper/{uuid}/`

### 3.6 PTR Detail Pages

Individual PTR pages at `https://efdsearch.senate.gov/search/view/ptr/{uuid}/` contain an HTML table with columns:

| Column Index | Field | Example |
|-------------|-------|---------|
| 0 | Row # | `1` |
| 1 | Transaction Date | `01/05/2025` |
| 2 | Owner | `Self`, `Spouse`, `Joint`, `Dependent` |
| 3 | Ticker | `AAPL` |
| 4 | Asset Name | `Apple Inc.` |
| 5 | Asset Type | `Stock`, `Bond`, `Mutual Fund` |
| 6 | Transaction Type | `Purchase`, `Sale (Full)`, `Sale (Partial)`, `Exchange` |
| 7 | Amount | `$1,001 - $15,000` |
| 8 | Comment | (optional) |

These are standard HTML `<table>` elements parseable with BeautifulSoup. Look for `.table-striped` class or first `<table>` element.

### 3.7 Site Technical Details

- **Framework:** Django (Python)
- **CDN/WAF:** Akamai
- **CSRF:** Django CSRF middleware
- **robots.txt:** Returns 404 (no file exists)
- **sitemap.xml:** Does not exist
- **No XML or JSON feeds are published**

---

## 4. Anti-Bot Protections

### What the Site Uses

1. **Django CSRF tokens** — Must pass `csrfmiddlewaretoken` in form POST and `X-CSRFToken` header matching the cookie
2. **Prohibition agreement checkbox** — Must POST `prohibition_agreement=1` to `/search/home/` before querying
3. **Session cookies** — `csrftoken` + `sessionid` must be maintained across requests
4. **Akamai WAF** — May block requests based on TLS fingerprint, request patterns, or missing browser headers

### What Is NOT Used (as of research date)

- **reCAPTCHA / hCaptcha** — The site does NOT use Google reCAPTCHA or hCaptcha. The "CAPTCHA" issue is likely the Akamai WAF rejecting non-browser TLS fingerprints.
- **JavaScript challenge pages** — No Cloudflare-style JS challenges

### Bypass Strategy: Tiered Approach

#### Tier 1: Plain HTTP with CSRF Flow (Fastest, Least Overhead)

Use `httpx` or `requests` with proper session management:

```python
import httpx
from bs4 import BeautifulSoup

async def create_efd_session() -> httpx.AsyncClient:
    client = httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://efdsearch.senate.gov",
            "Referer": "https://efdsearch.senate.gov/search/",
        },
        follow_redirects=True,
        timeout=30.0,
    )

    # Step 1: Get CSRF token
    resp = await client.get("https://efdsearch.senate.gov/search/")
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    csrf_token = csrf_input["value"]

    # Step 2: Accept prohibition agreement
    await client.post(
        "https://efdsearch.senate.gov/search/home/",
        data={
            "prohibition_agreement": "1",
            "csrfmiddlewaretoken": csrf_token,
        },
        headers={
            "Referer": "https://efdsearch.senate.gov/search/home/",
        },
    )

    # Update CSRF header for subsequent requests
    csrf_cookie = client.cookies.get("csrftoken")
    client.headers["X-CSRFToken"] = csrf_cookie

    return client


async def search_ptrs(client: httpx.AsyncClient, start_date: str, end_date: str):
    resp = await client.post(
        "https://efdsearch.senate.gov/search/report/data/",
        data={
            "start": "0",
            "length": "100",
            "report_types": "[11]",
            "filter_types": "[1]",
            "first_name": "",
            "last_name": "",
            "submitted_start_date": start_date,
            "submitted_end_date": end_date,
        },
    )
    return resp.json()
```

**When this works:** When Akamai is not actively fingerprinting TLS or enforcing strict browser detection.

**When this fails:** When the WAF detects the request as non-browser (usually based on TLS fingerprint mismatch — Python's `httpx`/`requests` uses a different TLS stack than Chrome).

#### Tier 2: Playwright Browser Automation (Current Implementation)

This is what the codebase currently uses (`senate_etl.py:349-526`). It launches a real Chromium browser that passes all WAF checks.

```python
# Key Playwright configuration (from senate_etl.py lines 371-388)
browser = await playwright.chromium.launch(
    headless=True,
    args=[
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--mute-audio",
    ],
)
context = await browser.new_context(
    viewport={"width": 1280, "height": 720},
    user_agent="Mozilla/5.0 ...",
)
```

**Pros:** Always works, passes all bot detection
**Cons:** 200-300MB memory, 10-30s startup, slower than HTTP

#### Tier 3: TLS Fingerprint Matching (Advanced, If Needed)

If Tier 1 fails due to TLS fingerprinting, use libraries that match Chrome's TLS fingerprint:

- **curl_cffi** — Python wrapper around curl-impersonate, matches Chrome/Firefox TLS fingerprints
- **tls-client** — Go-based TLS client with Python bindings
- **Botright** — Built on Playwright with additional anti-detection

```python
# Example with curl_cffi
from curl_cffi import requests as cffi_requests

session = cffi_requests.Session(impersonate="chrome120")
resp = session.get("https://efdsearch.senate.gov/search/")
```

### Recommended Approach

Use a **fallback chain**:
1. Try plain `httpx` with CSRF flow (fast, lightweight)
2. If blocked (403, empty response, redirect to agreement page), fall back to Playwright
3. Log which tier succeeded for monitoring

---

## 5. Third-Party Data Sources (Alternatives & Supplements)

These are structured APIs that aggregate Senate trading data from efdsearch.senate.gov. They solve the scraping problem by doing it for you.

### Tier 1: Free or Low-Cost APIs

| Provider | Endpoint | Free Tier | Pricing | Senate Data? | Notes |
|----------|----------|-----------|---------|-------------|-------|
| **Financial Modeling Prep** | `GET /stable/senate-trading?apikey=KEY` | 250 req/day | Paid plans from ~$15/mo | Yes | Clean REST API, separate Senate & House endpoints |
| **Finnhub** | `GET /api/v1/stock/congressional-trading?symbol=AAPL&token=KEY` | 50 calls/min | Free for most uses | Yes (combined) | Filter by symbol, date range |
| **AInvest** | `GET /open/ownership/congress` | Unknown | Unknown | Yes | Bearer token auth |

**Financial Modeling Prep endpoints:**
- Senate trades: `https://financialmodelingprep.com/stable/senate-trading?apikey=KEY`
- Latest Senate: `https://financialmodelingprep.com/stable/senate-latest?apikey=KEY`
- House trades: `https://financialmodelingprep.com/stable/house-trading?apikey=KEY`

**Finnhub example:**
```python
import finnhub
client = finnhub.Client(api_key="YOUR_KEY")
trades = client.stock_congressional_trading(symbol="AAPL", from_date="2025-01-01", to_date="2025-12-31")
```

### Tier 2: Paid APIs

| Provider | Free Tier | Pricing | Notes |
|----------|-----------|---------|-------|
| **QuiverQuant** | No | $10/mo (Hobbyist), $75/mo (Trader) | Python package available but unmaintained; use REST API directly |
| **Unusual Whales** | Limited | Subscription required | Has MCP server; covers Senate, House, SCOTUS |

**QuiverQuant:**
- API docs: https://api.quiverquant.com/docs/
- Python: `pip install quiverquant` (inactive — prefer direct REST)
- REST: `GET https://api.quiverquant.com/beta/bulk/congresstrading`

**Unusual Whales:**
- Public API: https://unusualwhales.com/public-api
- MCP server available for integration

### Tier 3: Browsable (No Direct API)

| Provider | URL | Notes |
|----------|-----|-------|
| **Capitol Trades** | https://www.capitoltrades.com/trades | No API; Apify scraper exists |
| **Smart Insider** | https://www.smartinsider.com/politicians/ | Free database, searchable by member or stock |
| **InsiderFinance** | https://www.insiderfinance.io/congress-trades | Portfolio views per senator |

### Discontinued APIs (Do Not Use)

| Provider | Status | Notes |
|----------|--------|-------|
| **OpenSecrets API** | Discontinued April 15, 2025 | Had `memPFDprofile` endpoint; bulk data may still be available for educational use |
| **ProPublica Congress API** | Discontinued | Never covered financial disclosures (legislative data only) |
| **GovTrack Bulk Data** | Ended | Legislative activity only |

---

## 6. Pre-Scraped Open Data Repos

These projects scrape efdsearch.senate.gov on a schedule and publish the results as free, structured data.

### Senate Stock Watcher Data (Recommended)

- **GitHub:** https://github.com/timothycarambat/senate-stock-watcher-data
- **Update frequency:** Daily via GitHub Actions
- **Format:** JSON files committed to the repo
- **Available aggregate files:**
  - `all_transactions.json` — Every transaction, merged
  - `all_daily_summaries.json` — Daily aggregates
  - `all_ticker_transactions.json` — Grouped by ticker
  - `all_transactions_for_senators.json` — Grouped by senator

**How to use as a data source:**
```python
import httpx

REPO_BASE = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master"

async def fetch_all_senate_transactions():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{REPO_BASE}/data/all_transactions.json")
        return resp.json()
```

**How they solve the scraping problem:** Uses the exact CSRF + agreement POST flow described in Section 3, running in GitHub Actions (no browser needed). This confirms the plain HTTP approach works from GitHub's infrastructure.

### House Stock Watcher Data

- **S3 endpoint:** `https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json`
- **Format:** JSON

### Other Open Source Scrapers (Reference Implementations)

| Project | Language | Approach | URL |
|---------|----------|----------|-----|
| **senate-stock-watcher-data** | Python | CSRF + POST, GitHub Actions | https://github.com/timothycarambat/senate-stock-watcher-data |
| **out_of_many_one** | Python | Detailed CSRF flow docs | https://github.com/Jagermeister/out_of_many_one |
| **go-efd** | Golang | Library wrapping the API | https://github.com/Individual-1/go-efd |
| **senator-filings** | Python | BeautifulSoup scraping | https://github.com/neelsomani/senator-filings |
| **us-senate-financial-disclosure-scraper** | Python | Handles paper + electronic | https://github.com/jeremiak/us-senate-financial-disclosure-scraper |

### Academic / Historical Datasets

| Source | Coverage | URL |
|--------|----------|-----|
| **Kaggle: US Senate Financial Disclosures** | 2012-2024 | https://www.kaggle.com/datasets/lukekerbs/us-senate-financial-disclosures-stocks-and-options |
| **Kaggle: Congressional Trading** | Inception - March 2023 | https://www.kaggle.com/datasets/shabbarank/congressional-trading-inception-to-march-23 |
| **Harvard Dataverse** | 2012-2021 | https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/XPDSYQ |

---

## 7. Current Codebase Architecture

### File Map

```
python-etl-service/
├── app/
│   ├── main.py                          # FastAPI app, middleware, routers (324 lines)
│   ├── services/
│   │   └── senate_etl.py               # Main Senate ETL service (1,239 lines)
│   ├── routes/
│   │   └── etl.py                      # POST /etl/trigger, GET /etl/status/{id} (~200 lines)
│   └── lib/
│       ├── database.py                  # get_supabase(), upload_transaction_to_supabase() (299 lines)
│       ├── politician.py               # find_or_create_politician() (161 lines)
│       ├── parser.py                   # extract_ticker, parse_value_range, etc. (343 lines)
│       └── http_client.py             # resilient_request(), ResilientClient (295 lines)
├── tests/
│   ├── test_senate_etl_service.py      # 60+ test cases (1,360 lines)
│   └── test_senate_etl_metrics.py      # Field validation tests (513 lines)
└── resources/deprecated/
    └── .../us_senate.py                # Old HTTP-only implementation (reference)
```

### Data Flow

```
1. Senate.gov XML ──────────────> Fetch ~100 senators
                                       │
2. Upsert to `politicians` table <─────┘
                                       │
3. Playwright browser ─────────> efdsearch.senate.gov
   - Accept agreement                 │
   - Search for PTRs                   │
   - Paginate through results          │
                                       │
4. For each PTR:                       │
   - Navigate to PTR detail page <─────┘
   - Parse HTML table
   - Extract transactions
                                       │
5. Upload to `trading_disclosures` <───┘
                                       │
6. Log to `job_executions` <───────────┘
```

### Key Functions in senate_etl.py

| Function | Lines | Purpose |
|----------|-------|---------|
| `fetch_senators_from_xml()` | 73-119 | Fetch senator list from Senate.gov XML |
| `upsert_senator_to_db()` | 122-164 | Upsert senator to `politicians` table (bioguide_id match → name fallback → create) |
| `_upsert_senator_by_name()` | 167-232 | Name-based senator lookup fallback |
| `parse_transaction_from_row()` | 242-341 | Parse a table row into a standardized transaction dict |
| `search_all_ptr_disclosures_playwright()` | 349-526 | Search EFD for all PTRs using Playwright (pagination, filtering) |
| `parse_ptr_page_playwright()` | 529-644 | Extract transactions from a single PTR page via Playwright |
| `process_disclosures_playwright()` | 647-751 | Process multiple disclosures in a single browser session |
| `parse_ptr_page()` | 863-1010 | HTTP/BeautifulSoup fallback for parsing PTR pages |
| `run_senate_etl()` | 1105-1239 | **Main entry point** — orchestrates the full pipeline |

### API Endpoint

```
POST /etl/trigger
Body: {
  "source": "senate",
  "lookback_days": 30,    # How far back to search
  "limit": null,           # Optional test limit
  "update_mode": false     # true = upsert, false = insert
}
Response: {
  "job_id": "uuid",
  "status": "running",
  "message": "Fetching senators..."
}

GET /etl/status/{job_id}
Response: Current job status with progress
```

### Constants (senate_etl.py lines 57-65)

```python
SENATE_BASE_URL = "https://efdsearch.senate.gov"
SENATE_SEARCH_URL = "https://efdsearch.senate.gov/search/"
SENATE_PTR_URL = "https://efdsearch.senate.gov/search/view/ptr/"
SENATORS_XML_URL = "https://www.senate.gov/general/contact_information/senators_cfm.xml"
```

---

## 8. Database Schema

### `politicians` Table

| Column | Type | Senate ETL Value | Notes |
|--------|------|-----------------|-------|
| `id` | UUID | auto-generated | Primary key |
| `first_name` | text | From XML | |
| `last_name` | text | From XML | |
| `full_name` | text | `{first} {last}` | |
| `party` | text | `D`, `R`, `I` | Mapped from XML party names |
| `state_or_country` | text | Two-letter code | |
| `bioguide_id` | text | e.g., `B001288` | **Primary lookup key for Senate** |
| `role` | text | `Senator` | |
| `chamber` | text | `Senate` | |

**Lookup priority:** `bioguide_id` → `first_name + last_name` → fuzzy name match → create new

### `trading_disclosures` Table

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `politician_id` | UUID (FK) | Linked from `politicians` | |
| `transaction_date` | date | PTR HTML col[1] | M/D/YYYY format |
| `disclosure_date` | date | Filing date from PTR header | |
| `transaction_type` | text | PTR HTML col[6] | `purchase`, `sale`, `exchange`, `unknown` |
| `asset_name` | text | PTR HTML col[4] | Truncated to 200 chars |
| `asset_ticker` | text | PTR HTML col[3] | Null if `--` or `N/A` |
| `asset_type` | text | PTR HTML col[5] | `Stock`, `Bond`, `Mutual Fund`, etc. |
| `amount_range_min` | float | Parsed from col[7] | e.g., 1001.0 |
| `amount_range_max` | float | Parsed from col[7] | e.g., 15000.0 |
| `source_url` | text | Full PTR URL | `https://efdsearch.senate.gov/search/view/ptr/{uuid}/` |
| `source_document_id` | text | UUID from URL | |
| `raw_data` | jsonb | Metadata | `{source, filing_type, ...}` |
| `status` | text | `active` | |

**Unique constraint:** `(politician_id, transaction_date, asset_name, transaction_type, disclosure_date)`

### `job_executions` Table

| Column | Type | Notes |
|--------|------|-------|
| `job_id` | text | `politician-trading-senate` |
| `status` | text | `success` or `failed` |
| `started_at` | timestamp | |
| `completed_at` | timestamp | |
| `error_message` | text | If failed |
| `metadata` | jsonb | `{etl_job_id, lookback_days, senators_count, disclosures_processed, transactions_uploaded, errors}` |

---

## 9. Implementation Recommendations

### Strategy A: Hybrid Direct Scraping (Recommended)

Modify the current implementation to try plain HTTP first, falling back to Playwright only when needed.

#### Step 1: Add a Plain HTTP Client for efdsearch.senate.gov

Create a new module (or add to `senate_etl.py`) that implements the 3-step CSRF flow using `httpx`:

1. `GET /search/` → extract CSRF token
2. `POST /search/home/` → accept agreement, get session
3. `POST /search/report/data/` → query PTRs as JSON

This eliminates the Playwright overhead (200-300MB RAM, 10-30s startup) for environments where the WAF doesn't block plain HTTP.

#### Step 2: Implement Fallback Chain

```python
async def search_ptrs(lookback_days: int, limit: int = None):
    try:
        # Tier 1: Plain HTTP (fast)
        return await search_ptrs_http(lookback_days, limit)
    except (HTTPBlockedError, AkamaiWAFError):
        logger.warning("HTTP blocked by WAF, falling back to Playwright")
        # Tier 2: Playwright (reliable)
        return await search_all_ptr_disclosures_playwright(lookback_days, limit)
```

#### Step 3: Add Senate Stock Watcher as Supplementary Source

Use the `senate-stock-watcher-data` GitHub repo as a secondary data source for:
- Historical backfill
- Gap filling when scraping fails
- Validation/cross-referencing

```python
async def backfill_from_stock_watcher():
    url = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/data/all_transactions.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        transactions = resp.json()
        # Map fields to our schema and upsert
```

### Strategy B: Third-Party API Integration

If scraping becomes unreliable, integrate a third-party API as the primary source:

**Recommended: Financial Modeling Prep (FMP)**
- Free tier: 250 requests/day (sufficient for daily ETL)
- Clean REST API with separate Senate and House endpoints
- No scraping needed

```python
async def fetch_senate_trades_fmp(api_key: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://financialmodelingprep.com/stable/senate-trading",
            params={"apikey": api_key},
        )
        return resp.json()
```

**Add env var:**
```bash
FMP_API_KEY=your_key_here
```

### Strategy C: Multi-Source with Deduplication

Use multiple sources simultaneously and deduplicate:

1. **Primary:** Direct scraping of efdsearch.senate.gov (HTTP → Playwright fallback)
2. **Secondary:** Senate Stock Watcher Data (GitHub JSON)
3. **Tertiary:** FMP or Finnhub API (if API key is configured)
4. **Deduplicate** using the existing unique constraint: `(politician_id, transaction_date, asset_name, transaction_type, disclosure_date)`

This gives maximum coverage and resilience.

---

## 10. Testing Strategy

### Existing Tests

- **`tests/test_senate_etl_service.py`** — 60+ tests covering parsing, DB operations, error handling (1,360 lines)
- **`tests/test_senate_etl_metrics.py`** — Field validation and data quality tests (513 lines)

### Running Tests

```bash
cd python-etl-service
uv sync                    # Install dependencies
pytest tests/test_senate_etl_service.py -v
pytest tests/test_senate_etl_metrics.py -v
pytest -v --cov            # Full suite with coverage
```

### What to Test for New Features

If adding the plain HTTP approach:
- Mock the 3-step CSRF flow (GET → POST agreement → POST data)
- Test JSON response parsing
- Test fallback from HTTP to Playwright
- Test rate limiting behavior

If adding a third-party API:
- Mock API responses
- Test field mapping from API schema → our schema
- Test error handling (rate limits, auth failures)
- Test deduplication with existing data

If adding Senate Stock Watcher integration:
- Mock the GitHub raw content response
- Test JSON → our schema mapping
- Test incremental updates (only insert new transactions)

---

## 11. Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **No incremental updates** | Re-processes entire lookback window every run | Use `update_mode=True` for upserts; track last-processed date |
| **Playwright overhead** | 200-300MB RAM, 10-30s startup | Add HTTP-first approach (Strategy A) |
| **Paper filings skipped** | ~10-15% of filings are scanned images | Would require OCR (pytesseract); low priority |
| **Session timeouts** | EFD may timeout during long processing (>30 min) | Restart browser session after N PTRs |
| **No bulk download** | Must fetch one PTR at a time | Batch within single browser session; use pre-scraped repos for backfill |
| **Missing tickers** | Some PTRs have `--` or `N/A` for ticker | Backfilled by `run_ticker_backfill()` using Polygon.io/yfinance |
| **Amount > $50M rejected** | Validation in `upload_transaction_to_supabase()` | Likely OCR errors; safe to skip |
| **100-page pagination limit** | Hard safety limit in Playwright search | Sufficient for 30-day lookback; increase if needed |
| **Date format assumption** | Regex expects `M/D/YYYY` | Consistent for Senate; no known variations |

---

## 12. Reference Links

### Government Sources
- Senate EFD Search: https://efdsearch.senate.gov/search/
- Senate.gov Senators XML: https://www.senate.gov/general/contact_information/senators_cfm.xml
- Senate Ethics Committee: https://www.ethics.senate.gov/public/index.cfm/financialdisclosure
- House Financial Disclosures: https://disclosures-clerk.house.gov/FinancialDisclosure
- STOCK Act full text: https://www.congress.gov/112/plaws/publ105/PLAW-112publ105.htm
- STOCK Act 2013 amendment (S.716): https://www.govinfo.gov/content/pkg/PLAW-113publ7/html/PLAW-113publ7.htm

### Open Source Reference Implementations
- senate-stock-watcher-data: https://github.com/timothycarambat/senate-stock-watcher-data
- out_of_many_one (CSRF flow docs): https://github.com/Jagermeister/out_of_many_one/blob/master/docs/Process_01_Fetch.md
- go-efd (Golang client): https://github.com/Individual-1/go-efd
- us-senate-financial-disclosure-scraper: https://github.com/jeremiak/us-senate-financial-disclosure-scraper

### Third-Party APIs
- Financial Modeling Prep: https://site.financialmodelingprep.com/developer/docs/stable/senate-trading
- QuiverQuant: https://api.quiverquant.com/docs/
- Finnhub: https://finnhub.io/docs/api/congressional-trading
- Unusual Whales: https://unusualwhales.com/public-api
- AInvest: https://docs.ainvest.com/reference/ownership/congress

### Academic Datasets
- Kaggle Senate Disclosures: https://www.kaggle.com/datasets/lukekerbs/us-senate-financial-disclosures-stocks-and-options
- Harvard Dataverse: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/XPDSYQ

---

*Last updated: February 2026*
*Research conducted across all known government portals, third-party APIs, open source projects, and legal sources.*
