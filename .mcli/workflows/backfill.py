"""Backfill commands for data quality fixes."""

import os
import re
import json
import click
import httpx
from pathlib import Path
from supabase import create_client

# Load .env file from project root
def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)


def get_supabase_client():
    """Create Supabase client."""
    load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")

    return create_client(url, key)


def extract_transaction_type(raw_data: dict) -> str | None:
    """
    Extract transaction type from raw_data.

    House PDFs embed P/S in the row data like:
    "Stock Name [ST] P 01/15/2025 01/20/2025 $1,001 - $15,000"
    """
    if not raw_data:
        return None

    raw_row = raw_data.get("raw_row", [])
    if not raw_row:
        return None

    # Combine all cells into one text, removing null bytes
    full_text = " ".join(str(cell).replace("\x00", "") for cell in raw_row if cell)
    full_lower = full_text.lower()

    # Check for full words first
    if any(kw in full_lower for kw in ["purchase", "bought", "buy"]):
        return "purchase"
    elif any(kw in full_lower for kw in ["sale", "sold", "sell", "exchange"]):
        return "sale"

    # Check for P/S patterns with dates (most common in House PDFs)
    if re.search(r"\bP\s+\d{1,2}/\d{1,2}/\d{4}", full_text):
        return "purchase"
    elif re.search(r"\bS\s+\d{1,2}/\d{1,2}/\d{4}", full_text):
        return "sale"

    # Check for P/S with (partial) notation
    if re.search(r"\bP\s*\(partial\)\s+\d{1,2}/", full_text, re.IGNORECASE):
        return "purchase"
    elif re.search(r"\bS\s*\(partial\)\s+\d{1,2}/", full_text, re.IGNORECASE):
        return "sale"

    return None


def is_metadata_only(asset_name: str) -> bool:
    """Check if an asset_name is just metadata that shouldn't be a record."""
    if not asset_name:
        return True

    # Remove null bytes first - they break regex patterns
    clean_name = asset_name.replace("\x00", "").strip()

    metadata_patterns = [
        r"^F\s*S\s*:",
        r"^S\s*O\s*:",
        r"^Owner\s*:",
        r"^Filing\s*(ID|Date)\s*:",
        r"^Document\s*ID\s*:",
        r"^Filer\s*:",
        r"^Status\s*:",
        r"^Type\s*:",
        r"^Cap.*Gains",
        r"^Div.*Only",
        r"^L\s*:",       # Location
        r"^D\s*:",       # Description
        r"^C\s*:",       # Comment
        r"^TD Ameritrade",
        r"^Charles Schwab",
        r"^Fidelity",
        r"^Vanguard",
        r"^E\*TRADE",
        r"^Merrill",
    ]

    for pattern in metadata_patterns:
        if re.match(pattern, clean_name, re.IGNORECASE):
            return True

    return False


@click.group(name="backfill")
def backfill():
    """Data quality backfill commands."""
    pass


@backfill.command(name="transaction-types")
@click.option("--limit", "-l", type=int, default=None, help="Limit records to process")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("--delete-metadata", is_flag=True, help="Delete metadata-only records")
def transaction_types(limit: int | None, dry_run: bool, delete_metadata: bool):
    """
    Backfill transaction_type for records with 'unknown' type.

    Parses raw_data to extract P (purchase) or S (sale) from House disclosures.
    """
    click.echo("Connecting to Supabase...")
    supabase = get_supabase_client()

    # Query all unknown records
    click.echo("Querying records with unknown transaction_type...")

    # Paginate through all records
    all_records = []
    offset = 0
    batch_size = 1000

    while True:
        query = (
            supabase.table("trading_disclosures")
            .select("id, transaction_type, raw_data, asset_name")
            .eq("transaction_type", "unknown")
            .range(offset, offset + batch_size - 1)
        )

        response = query.execute()
        records = response.data or []

        if not records:
            break

        all_records.extend(records)
        click.echo(f"  Fetched {len(all_records)} records...")

        if len(records) < batch_size:
            break

        offset += batch_size

        if limit and len(all_records) >= limit:
            all_records = all_records[:limit]
            break

    total = len(all_records)
    click.echo(f"Found {total} records with unknown transaction_type")

    if total == 0:
        click.echo("Nothing to do!")
        return

    updated = 0
    deleted = 0
    no_type_found = 0
    errors = 0

    with click.progressbar(all_records, label="Processing") as records:
        for record in records:
            record_id = record["id"]
            raw_data = record.get("raw_data") or {}
            asset_name = record.get("asset_name", "")

            # Check if metadata-only
            if delete_metadata and asset_name and is_metadata_only(asset_name):
                if dry_run:
                    click.echo(f"\n  Would delete metadata: {asset_name[:50]}...")
                    deleted += 1
                else:
                    try:
                        supabase.table("trading_disclosures").delete().eq("id", record_id).execute()
                        deleted += 1
                    except Exception as e:
                        errors += 1
                continue

            # Try to extract transaction type
            tx_type = extract_transaction_type(raw_data)

            if tx_type:
                if dry_run:
                    click.echo(f"\n  Would update {record_id}: {asset_name[:40]}... -> {tx_type}")
                    updated += 1
                else:
                    try:
                        supabase.table("trading_disclosures").update(
                            {"transaction_type": tx_type}
                        ).eq("id", record_id).execute()
                        updated += 1
                    except Exception as e:
                        error_msg = str(e)
                        # If duplicate key constraint, delete the unknown duplicate
                        if "23505" in error_msg or "duplicate key" in error_msg:
                            try:
                                supabase.table("trading_disclosures").delete().eq("id", record_id).execute()
                                deleted += 1
                            except Exception:
                                errors += 1
                        else:
                            if errors < 3:  # Show first few errors
                                click.echo(f"\n  Error updating {record_id}: {e}")
                            errors += 1
            else:
                no_type_found += 1

    click.echo("")
    click.echo("Results:")
    click.echo(f"  Updated: {updated}")
    click.echo(f"  Deleted: {deleted}")
    click.echo(f"  No type found: {no_type_found}")
    click.echo(f"  Errors: {errors}")

    if dry_run:
        click.echo("\n(Dry run - no changes made)")


@backfill.command(name="tickers")
@click.option("--limit", "-l", type=int, default=None, help="Limit records to process")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def tickers(limit: int | None, dry_run: bool):
    """
    Backfill asset_ticker for records with missing tickers.

    Extracts tickers from asset_name using regex patterns and company mappings.
    """
    click.echo("Connecting to Supabase...")
    supabase = get_supabase_client()

    # Query records with null tickers
    click.echo("Querying records with missing tickers...")

    all_records = []
    offset = 0
    batch_size = 1000

    while True:
        query = (
            supabase.table("trading_disclosures")
            .select("id, asset_name, asset_ticker")
            .is_("asset_ticker", "null")
            .range(offset, offset + batch_size - 1)
        )

        response = query.execute()
        records = response.data or []

        if not records:
            break

        all_records.extend(records)
        click.echo(f"  Fetched {len(all_records)} records...")

        if len(records) < batch_size:
            break

        offset += batch_size

        if limit and len(all_records) >= limit:
            all_records = all_records[:limit]
            break

    total = len(all_records)
    click.echo(f"Found {total} records with missing tickers")

    if total == 0:
        click.echo("Nothing to do!")
        return

    updated = 0
    no_ticker_found = 0
    errors = 0

    with click.progressbar(all_records, label="Processing") as records:
        for record in records:
            record_id = record["id"]
            asset_name = record.get("asset_name", "")

            if not asset_name:
                no_ticker_found += 1
                continue

            ticker = extract_ticker_from_name(asset_name)

            if ticker:
                if dry_run:
                    click.echo(f"\n  Would update: {asset_name[:40]}... -> {ticker}")
                    updated += 1
                else:
                    try:
                        supabase.table("trading_disclosures").update(
                            {"asset_ticker": ticker}
                        ).eq("id", record_id).execute()
                        updated += 1
                    except Exception as e:
                        errors += 1
            else:
                no_ticker_found += 1

    click.echo("")
    click.echo("Results:")
    click.echo(f"  Updated: {updated}")
    click.echo(f"  No ticker found: {no_ticker_found}")
    click.echo(f"  Errors: {errors}")

    if dry_run:
        click.echo("\n(Dry run - no changes made)")


def extract_ticker_from_name(asset_name: str) -> str | None:
    """Extract ticker from asset name."""
    if not asset_name:
        return None

    # Pattern 1: Ticker in parentheses (most common)
    match = re.search(r"\(([A-Z]{1,5})\)", asset_name)
    if match:
        return match.group(1)

    # Pattern 2: Ticker after dash
    match = re.search(r"[-–]\s*([A-Z]{1,5})(?:\s|$)", asset_name)
    if match:
        return match.group(1)

    # Pattern 3: Ticker before dash
    match = re.search(r"^([A-Z]{1,5})\s*[-–]", asset_name)
    if match:
        return match.group(1)

    # Pattern 4: Common company name mappings
    asset_lower = asset_name.lower()

    mappings = {
        "apple": "AAPL", "microsoft": "MSFT", "amazon": "AMZN",
        "google": "GOOGL", "alphabet": "GOOGL", "tesla": "TSLA",
        "meta platforms": "META", "facebook": "META", "nvidia": "NVDA",
        "netflix": "NFLX", "disney": "DIS", "intel": "INTC",
        "amd": "AMD", "advanced micro": "AMD", "paypal": "PYPL",
        "salesforce": "CRM", "oracle": "ORCL", "cisco": "CSCO",
        "adobe": "ADBE", "broadcom": "AVGO", "qualcomm": "QCOM",
        "jpmorgan": "JPM", "jp morgan": "JPM", "goldman sachs": "GS",
        "morgan stanley": "MS", "bank of america": "BAC",
        "wells fargo": "WFC", "citigroup": "C", "exxon": "XOM",
        "chevron": "CVX", "pfizer": "PFE", "johnson & johnson": "JNJ",
        "procter & gamble": "PG", "coca-cola": "KO", "pepsi": "PEP",
        "walmart": "WMT", "home depot": "HD", "costco": "COST",
        "target": "TGT", "starbucks": "SBUX", "mcdonald": "MCD",
        "uber": "UBER", "airbnb": "ABNB", "palantir": "PLTR",
        "snowflake": "SNOW", "crowdstrike": "CRWD", "datadog": "DDOG",
        "zoom": "ZM", "shopify": "SHOP", "square": "SQ",
        "roku": "ROKU", "spotify": "SPOT", "coinbase": "COIN",
    }

    for name, ticker in mappings.items():
        if name in asset_lower:
            return ticker

    # Pattern 5: Standalone ticker (2-5 uppercase letters)
    match = re.search(r"\b([A-Z]{2,5})\b", asset_name)
    if match:
        ticker = match.group(1)
        excluded = {
            "INC", "LLC", "LTD", "CORP", "CO", "THE", "AND", "OR",
            "ETF", "FUND", "LP", "NA", "US", "USA", "NEW", "OLD",
            "PLC", "ADR", "ADS", "COMMON", "STOCK", "CLASS",
        }
        if ticker not in excluded:
            return ticker

    return None


def extract_dates_from_raw_row(raw_data: dict) -> tuple[str | None, str | None]:
    """
    Extract transaction date and notification date from raw_data.raw_row.

    Returns:
        Tuple of (transaction_date, disclosure_date) in ISO format, or (None, None)
    """
    if not raw_data:
        return None, None

    raw_row = raw_data.get("raw_row", [])
    if not raw_row:
        return None, None

    # Combine all cells into one text for pattern matching
    row_text = " ".join(str(cell).replace("\x00", "") for cell in raw_row if cell)

    # Pattern: P/S followed by two dates
    # Matches: "P 01/15/2025 01/20/2025" or "S (partial) 12/01/2024 12/05/2024"
    date_pattern = r"[PS]\s*(?:\(partial\))?\s*(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})"
    match = re.search(date_pattern, row_text, re.IGNORECASE)

    if match:
        try:
            from datetime import datetime
            tx_date = datetime.strptime(match.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
            notif_date = datetime.strptime(match.group(2), "%m/%d/%Y").strftime("%Y-%m-%d")
            return tx_date, notif_date
        except ValueError:
            pass

    # Fallback: look for any two consecutive dates
    date_only_pattern = r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})"
    match = re.search(date_only_pattern, row_text)

    if match:
        try:
            from datetime import datetime
            tx_date = datetime.strptime(match.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
            notif_date = datetime.strptime(match.group(2), "%m/%d/%Y").strftime("%Y-%m-%d")
            return tx_date, notif_date
        except ValueError:
            pass

    return None, None


@backfill.command(name="dates")
@click.option("--limit", "-l", type=int, default=None, help="Limit records to process")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def dates(limit: int | None, dry_run: bool):
    """
    Backfill transaction_date and disclosure_date for records where they're identical.

    Extracts actual dates from raw_data.raw_row where P/S patterns include
    transaction date and notification date.
    """
    click.echo("Connecting to Supabase...")
    supabase = get_supabase_client()

    # Query PTR records from us_house source (they have the date pattern in raw_row)
    # PTR = Periodic Transaction Reports (filing_type = "P")
    click.echo("Querying us_house PTR records...")

    all_records = []
    offset = 0
    batch_size = 1000

    while True:
        # Get PTR records where raw_data has filing_type = P (transaction reports)
        query = (
            supabase.table("trading_disclosures")
            .select("id, transaction_date, disclosure_date, raw_data")
            .eq("raw_data->>source", "us_house")
            .eq("raw_data->>filing_type", "P")
            .range(offset, offset + batch_size - 1)
        )

        response = query.execute()
        records = response.data or []

        if not records:
            break

        # Filter to records where dates are identical
        for record in records:
            tx_date = str(record.get("transaction_date") or "")[:10]
            disc_date = str(record.get("disclosure_date") or "")[:10]
            if tx_date == disc_date:
                all_records.append(record)

        click.echo(f"  Checked {offset + len(records)} records, found {len(all_records)} with identical dates...")

        if len(records) < batch_size:
            break

        offset += batch_size

        if limit and len(all_records) >= limit:
            all_records = all_records[:limit]
            break

    total = len(all_records)
    click.echo(f"Found {total} records with identical transaction/disclosure dates")

    if total == 0:
        click.echo("Nothing to do!")
        return

    updated = 0
    deleted = 0
    no_dates_found = 0
    errors = 0

    with click.progressbar(all_records, label="Processing") as records:
        for record in records:
            record_id = record["id"]
            raw_data = record.get("raw_data") or {}

            tx_date, disc_date = extract_dates_from_raw_row(raw_data)

            if tx_date and disc_date and tx_date != disc_date:
                if dry_run:
                    click.echo(f"\n  Would update {record_id}: tx={tx_date}, disc={disc_date}")
                    updated += 1
                else:
                    try:
                        supabase.table("trading_disclosures").update({
                            "transaction_date": tx_date,
                            "disclosure_date": disc_date,
                        }).eq("id", record_id).execute()
                        updated += 1
                    except Exception as e:
                        error_msg = str(e)
                        # If duplicate key constraint, delete the duplicate record
                        if "23505" in error_msg or "duplicate key" in error_msg:
                            try:
                                supabase.table("trading_disclosures").delete().eq("id", record_id).execute()
                                deleted += 1
                            except Exception:
                                errors += 1
                        elif "ConnectionTerminated" in error_msg or "error_code" in error_msg:
                            # Connection error - retry once
                            try:
                                import time
                                time.sleep(1)
                                supabase.table("trading_disclosures").update({
                                    "transaction_date": tx_date,
                                    "disclosure_date": disc_date,
                                }).eq("id", record_id).execute()
                                updated += 1
                            except Exception:
                                errors += 1
                        else:
                            if errors < 3:
                                click.echo(f"\n  Error updating {record_id}: {e}")
                            errors += 1
            else:
                no_dates_found += 1

    click.echo("")
    click.echo("Results:")
    click.echo(f"  Updated: {updated}")
    click.echo(f"  Deleted (duplicates): {deleted}")
    click.echo(f"  No different dates found: {no_dates_found}")
    click.echo(f"  Errors: {errors}")

    if dry_run:
        click.echo("\n(Dry run - no changes made)")


@backfill.command(name="stats")
def stats():
    """Show current data quality statistics."""
    click.echo("Connecting to Supabase...")
    supabase = get_supabase_client()

    click.echo("\nTransaction Type Distribution:")
    click.echo("-" * 40)

    for tx_type in ["purchase", "sale", "holding", "unknown"]:
        response = (
            supabase.table("trading_disclosures")
            .select("id", count="exact")
            .eq("transaction_type", tx_type)
            .execute()
        )
        count = response.count or 0
        click.echo(f"  {tx_type:12}: {count:,}")

    click.echo("\nTicker Status:")
    click.echo("-" * 40)

    # With tickers
    response = (
        supabase.table("trading_disclosures")
        .select("id", count="exact")
        .not_.is_("asset_ticker", "null")
        .execute()
    )
    with_ticker = response.count or 0

    # Without tickers
    response = (
        supabase.table("trading_disclosures")
        .select("id", count="exact")
        .is_("asset_ticker", "null")
        .execute()
    )
    without_ticker = response.count or 0

    total = with_ticker + without_ticker
    pct = (with_ticker / total * 100) if total > 0 else 0

    click.echo(f"  With ticker:    {with_ticker:,} ({pct:.1f}%)")
    click.echo(f"  Without ticker: {without_ticker:,}")
    click.echo(f"  Total:          {total:,}")


# ============================================================================
# Error Report Processing
# ============================================================================


OLLAMA_BASE_URL = "https://ollama.lefv.info"
OLLAMA_MODEL = "llama3.1:8b"  # Can be changed to other models


def get_ollama_api_key():
    """Get Ollama API key from environment or lsh."""
    load_env()
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        # Try to get from lsh
        try:
            import subprocess
            result = subprocess.run(
                ["lsh", "get", "OLLAMA_API_KEY"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                api_key = result.stdout.strip()
        except Exception:
            pass
    return api_key


def get_ollama_client():
    """Create Ollama HTTP client with auth."""
    api_key = get_ollama_api_key()
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return httpx.Client(base_url=OLLAMA_BASE_URL, timeout=120.0, headers=headers)


def interpret_corrections(ollama_client: httpx.Client, report: dict) -> list[dict]:
    """Use Ollama to interpret what correction the user is requesting."""
    prompt = f"""You are analyzing a user-submitted error report for a financial disclosure database record.

ERROR REPORT:
- Error Type: {report['error_type']}
- User Description: "{report['description']}"

CURRENT DISCLOSURE DATA:
{json.dumps(report.get('disclosure_snapshot', {}), indent=2)}

TASK:
Based on the user's description, determine what field(s) need to be corrected and what the new value(s) should be.

FIELD MAPPING:
- wrong_amount → amount_range_min and/or amount_range_max (numeric values in dollars, no commas)
- wrong_date → transaction_date or disclosure_date (ISO 8601 format: YYYY-MM-DD)
- wrong_ticker → asset_ticker (uppercase stock symbol)
- wrong_politician → politician_name or politician_party
- other → any field

RESPONSE FORMAT (JSON only, no markdown):
{{
  "corrections": [
    {{
      "field": "field_name",
      "old_value": <current value from snapshot>,
      "new_value": <corrected value>,
      "confidence": <0.0 to 1.0>,
      "reasoning": "brief explanation"
    }}
  ]
}}

RULES:
1. Parse dollar amounts like "$5,000,001 - $25,000,000" into numeric min/max values
2. Confidence should be 0.9+ only if the user clearly states the correct value
3. Confidence should be 0.5-0.8 if you're inferring the correction
4. Return empty corrections array if you cannot determine what to fix
5. For amount ranges, always provide BOTH amount_range_min and amount_range_max

Respond with ONLY the JSON object, no other text."""

    try:
        response = ollama_client.post(
            "/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }
        )
        response.raise_for_status()

        result_data = response.json()
        response_text = result_data.get("response", "")

        # Parse JSON from response
        result = json.loads(response_text)
        return result.get("corrections", [])

    except json.JSONDecodeError as e:
        click.echo(f"  Failed to parse LLM JSON response: {e}")
        click.echo(f"  Raw response: {response_text[:200]}...")
        return []
    except Exception as e:
        click.echo(f"  LLM interpretation failed: {e}")
        return []


def process_single_report(supabase, ollama_client: httpx.Client, report: dict, dry_run: bool = False) -> dict:
    """Process a single error report."""
    report_id = report["id"]
    disclosure_id = report["disclosure_id"]

    click.echo(f"\n{'='*60}")
    click.echo(f"Report: {report_id[:8]}...")
    click.echo(f"  Type: {report['error_type']}")
    click.echo(f"  Description: {report['description'][:100]}...")

    # Get AI interpretation
    corrections = interpret_corrections(ollama_client, report)

    if not corrections:
        click.echo("  ❌ Could not determine correction from description")
        if not dry_run:
            supabase.table("user_error_reports").update({
                "status": "reviewed",
                "admin_notes": "Auto-processor could not determine correction. Needs human review."
            }).eq("id", report_id).execute()
        return {"status": "needs_review", "corrections": []}

    # Display proposed corrections
    click.echo("\n  Proposed corrections:")
    for c in corrections:
        conf_pct = c['confidence'] * 100
        conf_color = "green" if conf_pct >= 80 else "yellow" if conf_pct >= 50 else "red"
        click.echo(f"    • {c['field']}: {c['old_value']} → {c['new_value']}")
        click.echo(click.style(f"      Confidence: {conf_pct:.0f}% - {c['reasoning']}", fg=conf_color))

    # Check confidence threshold
    all_high_confidence = all(c['confidence'] >= 0.8 for c in corrections)

    if not all_high_confidence:
        click.echo("\n  ⚠️  Low confidence - flagging for human review")
        if not dry_run:
            notes = "; ".join(
                f"{c['field']}: {c['old_value']} → {c['new_value']} ({c['confidence']*100:.0f}%)"
                for c in corrections
            )
            supabase.table("user_error_reports").update({
                "status": "reviewed",
                "admin_notes": f"Low confidence corrections suggested: {notes}"
            }).eq("id", report_id).execute()
        return {"status": "needs_review", "corrections": corrections}

    # Apply corrections
    if dry_run:
        click.echo("\n  ✓ Would apply corrections (dry-run)")
        return {"status": "would_fix", "corrections": corrections}

    # Build update data
    update_data = {}
    for c in corrections:
        update_data[c['field']] = c['new_value']

    try:
        # Update the disclosure
        supabase.table("trading_disclosures").update(update_data).eq("id", disclosure_id).execute()
        click.echo("\n  ✅ Applied corrections to disclosure")

        # Check for related disclosures (same source PDF)
        snapshot = report.get("disclosure_snapshot", {})
        source_url = snapshot.get("source_url")

        if source_url:
            # Find related disclosures with missing amounts
            amount_fields = [c['field'] for c in corrections if 'amount' in c['field']]
            if amount_fields:
                related = supabase.table("trading_disclosures").select("id").eq(
                    "source_url", source_url
                ).neq("id", disclosure_id).is_("amount_range_min", "null").execute()

                if related.data:
                    click.echo(f"  📋 Found {len(related.data)} related disclosures from same PDF")
                    amount_update = {f: update_data[f] for f in amount_fields if f in update_data}
                    for rec in related.data:
                        supabase.table("trading_disclosures").update(amount_update).eq("id", rec["id"]).execute()
                    click.echo(f"  ✅ Applied amount corrections to related disclosures")

        # Mark report as fixed
        correction_summary = "; ".join(f"{c['field']}: {c['old_value']} → {c['new_value']}" for c in corrections)
        supabase.table("user_error_reports").update({
            "status": "fixed",
            "admin_notes": f"Auto-corrected: {correction_summary}"
        }).eq("id", report_id).execute()

        click.echo("  ✅ Marked report as fixed")
        return {"status": "fixed", "corrections": corrections}

    except Exception as e:
        click.echo(f"\n  ❌ Failed to apply corrections: {e}")
        supabase.table("user_error_reports").update({
            "status": "reviewed",
            "admin_notes": f"Auto-correction failed: {e}"
        }).eq("id", report_id).execute()
        return {"status": "error", "corrections": corrections, "error": str(e)}


@backfill.command(name="process-errors")
@click.option("--limit", "-l", type=int, default=10, help="Max reports to process")
@click.option("--dry-run", is_flag=True, help="Preview corrections without applying")
@click.option("--report-id", "-r", type=str, help="Process a specific report by ID")
@click.option("--model", "-m", type=str, default=OLLAMA_MODEL, help=f"Ollama model to use (default: {OLLAMA_MODEL})")
def process_errors(limit: int, dry_run: bool, report_id: str | None, model: str):
    """
    Process pending user error reports using AI.

    Uses Ollama (ollama.lefv.info) to interpret user descriptions and
    automatically apply corrections when confidence is high enough.
    """
    global OLLAMA_MODEL
    OLLAMA_MODEL = model

    click.echo("🔍 Error Report Processor")
    click.echo("=" * 60)
    click.echo(f"Using Ollama model: {model}")

    if dry_run:
        click.echo(click.style("DRY RUN - No changes will be made", fg="yellow"))

    click.echo("\nConnecting to services...")
    supabase = get_supabase_client()
    ollama_client = get_ollama_client()

    # Test Ollama connection
    try:
        test_response = ollama_client.get("/api/tags")
        test_response.raise_for_status()
        click.echo(f"  ✓ Connected to Ollama at {OLLAMA_BASE_URL}")
    except Exception as e:
        click.echo(click.style(f"  ✗ Failed to connect to Ollama: {e}", fg="red"))
        return

    # Fetch reports
    if report_id:
        click.echo(f"Fetching report {report_id}...")
        result = supabase.table("user_error_reports").select("*").eq("id", report_id).execute()
    else:
        click.echo(f"Fetching pending reports (limit: {limit})...")
        result = supabase.table("user_error_reports").select("*").eq(
            "status", "pending"
        ).order("created_at").limit(limit).execute()

    reports = result.data or []

    if not reports:
        click.echo("\n✓ No pending reports to process")
        return

    click.echo(f"Found {len(reports)} report(s) to process")

    # Process each report
    stats = {"fixed": 0, "needs_review": 0, "error": 0}

    for report in reports:
        result = process_single_report(supabase, ollama_client, report, dry_run)
        status = result.get("status", "error")
        if status in ["fixed", "would_fix"]:
            stats["fixed"] += 1
        elif status == "needs_review":
            stats["needs_review"] += 1
        else:
            stats["error"] += 1

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("Summary:")
    click.echo(f"  ✅ Fixed: {stats['fixed']}")
    click.echo(f"  ⚠️  Needs review: {stats['needs_review']}")
    click.echo(f"  ❌ Errors: {stats['error']}")

    if dry_run:
        click.echo(click.style("\n(Dry run - no changes made)", fg="yellow"))


@backfill.command(name="error-stats")
def error_stats():
    """Show user error report statistics."""
    click.echo("Connecting to Supabase...")
    supabase = get_supabase_client()

    click.echo("\nError Report Statistics:")
    click.echo("-" * 40)

    for status in ["pending", "reviewed", "fixed", "invalid"]:
        response = (
            supabase.table("user_error_reports")
            .select("id", count="exact")
            .eq("status", status)
            .execute()
        )
        count = response.count or 0
        icon = {"pending": "⏳", "reviewed": "👀", "fixed": "✅", "invalid": "❌"}.get(status, "•")
        click.echo(f"  {icon} {status:12}: {count:,}")

    click.echo("\nBy Error Type:")
    click.echo("-" * 40)

    for error_type in ["wrong_amount", "wrong_date", "wrong_ticker", "wrong_politician", "other"]:
        response = (
            supabase.table("user_error_reports")
            .select("id", count="exact")
            .eq("error_type", error_type)
            .execute()
        )
        count = response.count or 0
        click.echo(f"  {error_type:18}: {count:,}")
