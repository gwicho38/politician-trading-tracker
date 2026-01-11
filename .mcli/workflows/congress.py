#!/usr/bin/env python3
# @description: Congress.gov API commands
# @version: 1.0.0
# @group: workflows

"""
Congress.gov command group for mcli.

Commands for fetching data from the official Congress.gov API.
"""
import click
import httpx
import subprocess
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table

console = Console()

# API Configuration
CONGRESS_API_URL = "https://api.congress.gov/v3"
CURRENT_CONGRESS = 119  # 119th Congress (2025-2027)


def get_api_key() -> Optional[str]:
    """Get Congress.gov API key from lsh."""
    try:
        result = subprocess.run(
            ["lsh", "get", "CONGRESS_API_KEY"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def make_request(endpoint: str, params: Dict[str, Any] = None) -> Dict:
    """Make authenticated request to Congress.gov API."""
    api_key = get_api_key()
    if not api_key:
        raise click.ClickException("CONGRESS_API_KEY not found. Set with: lsh set CONGRESS_API_KEY <key>")

    url = f"{CONGRESS_API_URL}{endpoint}"
    params = params or {}
    params["api_key"] = api_key
    params["format"] = "json"

    response = httpx.get(url, params=params, timeout=30.0)

    if response.status_code != 200:
        raise click.ClickException(f"API error: HTTP {response.status_code} - {response.text[:200]}")

    return response.json()


@click.group(name="congress")
def app():
    """
    Congress.gov API commands.

    Fetch member data, bills, and voting records from Congress.gov.
    """
    pass


@app.command("test")
def test_connection():
    """
    Test connection to Congress.gov API.

    Example: mcli run congress test
    """
    api_key = get_api_key()

    if not api_key:
        console.print("[red]Error: CONGRESS_API_KEY not found[/red]")
        console.print("Get a free API key at: https://api.congress.gov/sign-up/")
        console.print("Then set it with: lsh set CONGRESS_API_KEY <your_key>")
        raise SystemExit(1)

    console.print("[cyan]Testing Congress.gov API connection...[/cyan]")
    console.print(f"[dim]API Key: {api_key[:8]}...{api_key[-4:]}[/dim]")

    try:
        data = make_request("/member", {"limit": 1})

        if "members" in data:
            console.print("[green]Success: API connection works[/green]")
            total = data.get("pagination", {}).get("count", "unknown")
            console.print(f"  Total members in database: {total}")
        else:
            console.print("[yellow]Warning: Unexpected response format[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("members")
@click.option("--congress", "-c", default=CURRENT_CONGRESS, help=f"Congress number (default: {CURRENT_CONGRESS})")
@click.option("--chamber", type=click.Choice(["house", "senate", "all"]), default="all", help="Chamber filter")
@click.option("--state", "-s", help="Filter by state (e.g., CA, TX, NY)")
@click.option("--party", "-p", type=click.Choice(["D", "R", "I", "all"]), default="all", help="Party filter")
@click.option("--limit", "-l", default=50, help="Number of members to show")
@click.option("--output", "-o", type=click.Choice(["table", "json", "csv"]), default="table")
@click.option("--current/--all-time", default=True, help="Only current members")
def list_members(congress: int, chamber: str, state: str, party: str, limit: int, output: str, current: bool):
    """
    List members of Congress.

    Examples:
        mcli run congress members
        mcli run congress members --chamber senate --state CA
        mcli run congress members --party D --limit 100
    """
    console.print(f"[cyan]Fetching members of the {congress}th Congress...[/cyan]")

    try:
        all_members = []
        offset = 0
        page_size = 250  # Max allowed by API

        # Fetch all members (paginated)
        while True:
            params = {
                "limit": page_size,
                "offset": offset,
                "currentMember": "true" if current else None
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            data = make_request("/member", params)
            members = data.get("members", [])

            if not members:
                break

            all_members.extend(members)
            offset += page_size

            # Check if we've fetched enough or reached the end
            total = data.get("pagination", {}).get("count", 0)
            if offset >= total or len(all_members) >= 1000:  # Safety limit
                break

        console.print(f"[dim]Fetched {len(all_members)} total members[/dim]")

        # Filter members
        filtered = []
        for member in all_members:
            # Get current term info
            terms = member.get("terms", {}).get("item", [])
            current_term = terms[0] if terms else {}

            member_chamber = current_term.get("chamber", "").lower()
            member_state = member.get("state", "")
            member_party = member.get("partyName", "")

            # Apply filters
            if chamber != "all" and member_chamber != chamber:
                continue
            if state and member_state.upper() != state.upper():
                continue
            if party != "all":
                party_letter = member_party[0].upper() if member_party else ""
                if party_letter != party:
                    continue

            filtered.append({
                "name": member.get("name", ""),
                "bioguideId": member.get("bioguideId", ""),
                "state": member_state,
                "district": member.get("district"),
                "party": member_party,
                "chamber": member_chamber.title() if member_chamber else "",
                "url": member.get("url", ""),
            })

        # Sort by state, then name
        filtered.sort(key=lambda x: (x["state"], x["name"]))

        # Apply limit
        display_members = filtered[:limit]

        if output == "json":
            import json
            console.print(json.dumps(display_members, indent=2))

        elif output == "csv":
            console.print("name,bioguideId,state,district,party,chamber")
            for m in display_members:
                console.print(f'"{m["name"]}",{m["bioguideId"]},{m["state"]},{m["district"] or ""},"{m["party"]}",{m["chamber"]}')

        else:
            # Table output
            title = f"Members of {congress}th Congress"
            if chamber != "all":
                title += f" ({chamber.title()})"
            if state:
                title += f" - {state.upper()}"

            table = Table(title=title)
            table.add_column("Name", style="green", width=25)
            table.add_column("State", width=6)
            table.add_column("Dist", width=5)
            table.add_column("Party", width=12)
            table.add_column("Chamber", width=8)
            table.add_column("BioGuide ID", style="dim", width=12)

            for m in display_members:
                party_style = "blue" if m["party"].startswith("Democrat") else "red" if m["party"].startswith("Republican") else "yellow"
                table.add_row(
                    m["name"][:24],
                    m["state"],
                    str(m["district"]) if m["district"] else "-",
                    f"[{party_style}]{m['party'][:10]}[/{party_style}]",
                    m["chamber"][:7],
                    m["bioguideId"]
                )

            console.print(table)
            console.print(f"\n[dim]Showing {len(display_members)} of {len(filtered)} filtered members[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("member")
@click.argument("bioguide_id")
def get_member(bioguide_id: str):
    """
    Get details for a specific member by BioGuide ID.

    Example: mcli run congress member P000197
    """
    console.print(f"[cyan]Fetching member {bioguide_id}...[/cyan]")

    try:
        data = make_request(f"/member/{bioguide_id}")
        member = data.get("member", {})

        if not member:
            console.print(f"[red]Member not found: {bioguide_id}[/red]")
            raise SystemExit(1)

        console.print(f"\n[bold]{member.get('directOrderName', member.get('name', 'Unknown'))}[/bold]")
        console.print("-" * 50)
        console.print(f"BioGuide ID: {member.get('bioguideId', '-')}")
        console.print(f"Party: {member.get('partyHistory', [{}])[0].get('partyName', '-')}")
        console.print(f"State: {member.get('state', '-')}")
        console.print(f"District: {member.get('district', '-')}")
        console.print(f"Birth Year: {member.get('birthYear', '-')}")

        # Terms
        terms = member.get("terms", [])
        if terms:
            console.print(f"\n[bold]Terms ({len(terms)}):[/bold]")
            for term in terms[:5]:  # Show last 5 terms
                chamber = term.get("chamber", "-")
                start = term.get("startYear", "-")
                end = term.get("endYear", "present")
                congress = term.get("congress", "-")
                console.print(f"  {congress}th Congress: {chamber} ({start}-{end})")

        # Sponsored legislation count
        sponsored = member.get("sponsoredLegislation", {}).get("count", 0)
        cosponsored = member.get("cosponsoredLegislation", {}).get("count", 0)
        console.print(f"\n[bold]Legislation:[/bold]")
        console.print(f"  Sponsored: {sponsored}")
        console.print(f"  Co-sponsored: {cosponsored}")

        # Official URL
        if member.get("officialWebsiteUrl"):
            console.print(f"\nWebsite: {member.get('officialWebsiteUrl')}")

    except click.ClickException:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("stats")
@click.option("--congress", "-c", default=CURRENT_CONGRESS, help=f"Congress number")
def show_stats(congress: int):
    """
    Show statistics about current Congress members.

    Example: mcli run congress stats
    """
    console.print(f"[cyan]Fetching stats for {congress}th Congress...[/cyan]")

    try:
        all_members = []
        offset = 0

        # Fetch all current members
        while True:
            params = {"limit": 250, "offset": offset, "currentMember": "true"}
            data = make_request("/member", params)
            members = data.get("members", [])

            if not members:
                break

            all_members.extend(members)
            offset += 250

            if offset >= data.get("pagination", {}).get("count", 0):
                break

        # Calculate stats
        house = {"D": 0, "R": 0, "I": 0, "Other": 0}
        senate = {"D": 0, "R": 0, "I": 0, "Other": 0}
        states = {}

        for member in all_members:
            terms = member.get("terms", {}).get("item", [])
            if not terms:
                continue

            current_term = terms[0]
            chamber = current_term.get("chamber", "").lower()
            party = member.get("partyName", "")
            state = member.get("state", "Unknown")

            party_key = party[0].upper() if party else "Other"
            if party_key not in ["D", "R", "I"]:
                party_key = "Other"

            if chamber == "house of representatives":
                house[party_key] += 1
            elif chamber == "senate":
                senate[party_key] += 1

            states[state] = states.get(state, 0) + 1

        console.print(f"\n[bold]{congress}th Congress Statistics[/bold]")
        console.print("=" * 50)

        # House
        house_total = sum(house.values())
        console.print(f"\n[bold]House of Representatives ({house_total} members):[/bold]")
        console.print(f"  [blue]Democrats: {house['D']}[/blue]")
        console.print(f"  [red]Republicans: {house['R']}[/red]")
        if house["I"]:
            console.print(f"  [yellow]Independents: {house['I']}[/yellow]")

        # Senate
        senate_total = sum(senate.values())
        console.print(f"\n[bold]Senate ({senate_total} members):[/bold]")
        console.print(f"  [blue]Democrats: {senate['D']}[/blue]")
        console.print(f"  [red]Republicans: {senate['R']}[/red]")
        if senate["I"]:
            console.print(f"  [yellow]Independents: {senate['I']}[/yellow]")

        # Top states
        console.print(f"\n[bold]Top 10 States by Representation:[/bold]")
        for state, count in sorted(states.items(), key=lambda x: -x[1])[:10]:
            console.print(f"  {state}: {count}")

        console.print(f"\n[dim]Total members: {len(all_members)}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command("health")
def health_check():
    """
    Quick health check of Congress.gov API.

    Example: mcli run congress health
    """
    api_key = get_api_key()

    console.print("\n[bold]Congress.gov API Health Check[/bold]")
    console.print("-" * 40)

    # Check API key
    if api_key:
        console.print(f"[green]OK[/green] API Key: configured")
    else:
        console.print("[red]FAIL[/red] API Key: missing")
        console.print("Get one at: https://api.congress.gov/sign-up/")
        raise SystemExit(1)

    # Check connectivity
    try:
        data = make_request("/member", {"limit": 1})
        if "members" in data:
            console.print("[green]OK[/green] API Connection: healthy")
        else:
            console.print("[red]FAIL[/red] API Connection: unexpected response")
            raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]FAIL[/red] API Connection: {str(e)[:40]}")
        raise SystemExit(1)

    console.print("\n[green]All checks passed[/green]")


def get_supabase_config() -> Dict[str, str]:
    """Get Supabase configuration from lsh."""
    config = {}
    for key in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
        try:
            result = subprocess.run(
                ["lsh", "get", key],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                config[key] = result.stdout.strip()
        except Exception:
            pass
    return config


def normalize_name(name: str) -> str:
    """Normalize a name for matching."""
    if not name:
        return ""
    # Handle "Last, First" format
    if ", " in name:
        parts = name.split(", ", 1)
        name = f"{parts[1]} {parts[0]}"
    # Remove common suffixes/prefixes
    for suffix in [" Jr.", " Jr", " Sr.", " Sr", " III", " II", " IV"]:
        name = name.replace(suffix, "")
    return name.lower().strip()


def fetch_all_congress_members() -> List[Dict]:
    """Fetch all current Congress members from Congress.gov API."""
    all_members = []
    offset = 0
    page_size = 250

    while True:
        params = {
            "limit": page_size,
            "offset": offset,
            "currentMember": "true"
        }
        data = make_request("/member", params)
        members = data.get("members", [])

        if not members:
            break

        for member in members:
            terms = member.get("terms", {}).get("item", [])
            current_term = terms[0] if terms else {}

            all_members.append({
                "bioguide_id": member.get("bioguideId", ""),
                "name": member.get("name", ""),
                "direct_name": member.get("directOrderName", ""),
                "state": member.get("state", ""),
                "district": member.get("district"),
                "party": member.get("partyName", ""),
                "chamber": current_term.get("chamber", ""),
            })

        offset += page_size
        total = data.get("pagination", {}).get("count", 0)
        if offset >= total:
            break

    return all_members


def fetch_app_politicians(config: Dict[str, str]) -> List[Dict]:
    """Fetch politicians from app database."""
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        return []

    response = httpx.get(
        f"{url}/rest/v1/politicians",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        params={
            "select": "id,full_name,first_name,last_name,bioguide_id,party,state_or_country,chamber",
            "limit": 2000
        },
        timeout=30.0
    )

    if response.status_code == 200:
        return response.json()
    return []


def update_politician_bioguide(config: Dict[str, str], politician_id: str, bioguide_id: str) -> bool:
    """Update a politician's bioguide_id in the database."""
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        return False

    response = httpx.patch(
        f"{url}/rest/v1/politicians",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        params={"id": f"eq.{politician_id}"},
        json={"bioguide_id": bioguide_id},
        timeout=10.0
    )

    return response.status_code in [200, 204]


@app.command("backfill-bioguide")
@click.option("--dry-run", is_flag=True, help="Show matches without updating database")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed matching info")
def backfill_bioguide(dry_run: bool, verbose: bool):
    """
    Backfill bioguide_id for politicians by matching with Congress.gov data.

    Example: mcli run congress backfill-bioguide --dry-run
    Example: mcli run congress backfill-bioguide
    """
    config = get_supabase_config()
    if not config.get("SUPABASE_URL"):
        console.print("[red]Error: SUPABASE_URL not found in lsh[/red]")
        raise SystemExit(1)

    console.print("[cyan]Fetching Congress members from Congress.gov...[/cyan]")
    congress_members = fetch_all_congress_members()
    console.print(f"  Found {len(congress_members)} current members")

    console.print("[cyan]Fetching politicians from app database...[/cyan]")
    app_politicians = fetch_app_politicians(config)
    console.print(f"  Found {len(app_politicians)} politicians")

    # Filter to those without bioguide_id
    missing_bioguide = [p for p in app_politicians if not p.get("bioguide_id")]
    already_have = len(app_politicians) - len(missing_bioguide)
    console.print(f"  Already have bioguide_id: {already_have}")
    console.print(f"  Missing bioguide_id: {len(missing_bioguide)}")

    # Build lookup tables for Congress members
    congress_by_name = {}
    congress_by_direct_name = {}
    for m in congress_members:
        norm_name = normalize_name(m["name"])
        norm_direct = normalize_name(m["direct_name"])
        if norm_name:
            congress_by_name[norm_name] = m
        if norm_direct:
            congress_by_direct_name[norm_direct] = m

    # Match politicians
    matches = []
    no_match = []

    for pol in missing_bioguide:
        full_name = pol.get("full_name", "")
        first_name = pol.get("first_name", "")
        last_name = pol.get("last_name", "")

        # Try different name formats
        names_to_try = [
            normalize_name(full_name),
            normalize_name(f"{first_name} {last_name}"),
            normalize_name(f"{last_name}, {first_name}"),
        ]

        match = None
        matched_name = None
        for name in names_to_try:
            if name in congress_by_name:
                match = congress_by_name[name]
                matched_name = name
                break
            if name in congress_by_direct_name:
                match = congress_by_direct_name[name]
                matched_name = name
                break

        if match:
            matches.append({
                "politician": pol,
                "congress_member": match,
                "matched_on": matched_name
            })
        else:
            no_match.append(pol)

    console.print(f"\n[bold]Matching Results[/bold]")
    console.print("-" * 60)
    console.print(f"[green]Matched: {len(matches)}[/green]")
    console.print(f"[yellow]No match: {len(no_match)}[/yellow]")

    if verbose and matches:
        console.print(f"\n[bold]Matches:[/bold]")
        for m in matches[:20]:
            pol = m["politician"]
            cong = m["congress_member"]
            console.print(f"  {pol['full_name']} -> {cong['bioguide_id']} ({cong['name']})")
        if len(matches) > 20:
            console.print(f"  ... and {len(matches) - 20} more")

    if verbose and no_match:
        console.print(f"\n[bold]No Match Found:[/bold]")
        for pol in no_match[:10]:
            console.print(f"  {pol['full_name']} ({pol.get('state_or_country', '?')})")
        if len(no_match) > 10:
            console.print(f"  ... and {len(no_match) - 10} more")

    if dry_run:
        console.print(f"\n[yellow]Dry run - no changes made[/yellow]")
        return

    if not matches:
        console.print("[yellow]No matches to update[/yellow]")
        return

    # Update database
    console.print(f"\n[cyan]Updating {len(matches)} politicians...[/cyan]")
    updated = 0
    failed = 0

    for m in matches:
        pol_id = m["politician"]["id"]
        bioguide_id = m["congress_member"]["bioguide_id"]

        if update_politician_bioguide(config, pol_id, bioguide_id):
            updated += 1
        else:
            failed += 1
            if verbose:
                console.print(f"  [red]Failed to update {m['politician']['full_name']}[/red]")

    console.print(f"\n[bold]Update Results[/bold]")
    console.print(f"  [green]Updated: {updated}[/green]")
    if failed:
        console.print(f"  [red]Failed: {failed}[/red]")


@app.command("lookup")
@click.argument("name")
def lookup_member(name: str):
    """
    Look up a Congress member by name and show their BioGuide ID.

    Example: mcli run congress lookup "Nancy Pelosi"
    Example: mcli run congress lookup "Pelosi"
    """
    console.print(f"[cyan]Searching for '{name}'...[/cyan]")

    try:
        # Fetch all current members
        all_members = fetch_all_congress_members()

        # Search by name (case-insensitive partial match)
        search_lower = name.lower()
        matches = []

        for member in all_members:
            if (search_lower in member["name"].lower() or
                search_lower in member.get("direct_name", "").lower()):
                matches.append(member)

        if not matches:
            console.print(f"[yellow]No members found matching '{name}'[/yellow]")
            return

        console.print(f"\n[bold]Found {len(matches)} match(es):[/bold]")
        table = Table()
        table.add_column("Name", style="green", width=30)
        table.add_column("BioGuide ID", style="cyan", width=12)
        table.add_column("State", width=6)
        table.add_column("Party", width=12)
        table.add_column("Chamber", width=10)

        for m in matches[:20]:
            party_style = "blue" if "Democrat" in m["party"] else "red" if "Republican" in m["party"] else "yellow"
            table.add_row(
                m["direct_name"] or m["name"],
                m["bioguide_id"],
                m["state"],
                f"[{party_style}]{m['party'][:10]}[/{party_style}]",
                m["chamber"][:10] if m["chamber"] else "-"
            )

        console.print(table)

        if len(matches) > 20:
            console.print(f"\n[dim]Showing first 20 of {len(matches)} matches[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)
