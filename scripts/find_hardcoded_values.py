#!/usr/bin/env python3
"""
Script to find hardcoded values that should be moved to constants.

This script scans Python files for:
- Hardcoded URLs (http://, https://) not in constants
- Environment variable names used with os.getenv/os.environ
- Database table names
- Configuration values that should be constants

Usage:
    python scripts/find_hardcoded_values.py
    python scripts/find_hardcoded_values.py --verbose  # Show all details
"""

import ast
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Directories to scan
SCAN_DIRS = ["src"]

# Files/directories to exclude
EXCLUDE_PATTERNS = [
    "**/constants/**",
    "**/__pycache__/**",
    "**/migrations/**",
    "**/.venv/**",
    "**/venv/**",
    "**/test_*.py",
    "**/*_test.py",
    "**/conftest.py",
    "**/notebooks/**",
]

# Known URLs from constants (loaded from urls.py)
KNOWN_URLS = {
    # ApiUrls
    "https://paper-api.alpaca.markets",
    "https://api.alpaca.markets",
    "https://data.alpaca.markets",
    "https://disclosures-clerk.house.gov/FinancialDisclosure",
    "https://efdsearch.senate.gov/search/",
    "https://efd.senate.gov",
    "https://api.quiverquant.com/beta/live/congresstrading",
    "https://api.propublica.org/congress/v1",
    "https://api.companieshouse.gov.uk",
    "https://members-api.parliament.uk",
    "https://interests-api.parliament.uk/api/v1",
    "https://info-financiere.gouv.fr/api/v1",
    "https://api.opencorporates.com",
    "https://api.opencorporates.com/v0.4",
    "https://api.xbrl.us/api/v1",
    "https://filings.xbrl.org/api",
    "https://finnhub.io/api/v1",
    "https://data.sec.gov",
    "https://netfile.com/Connect2/api/public/list/ANC",
    # WebUrls
    "https://github.com/gwicho38/politician-trading-tracker",
    "https://supabase.com/dashboard",
    "https://app.alpaca.markets/",
    "https://app.alpaca.markets/paper/dashboard/overview",
    "https://app.alpaca.markets/live/dashboard/overview",
    "https://quiverquant.com/",
    "https://www.quiverquant.com",
    "https://www.quiverquant.com/congresstrading/",
    "https://www.propublica.org/",
    "https://disclosures-clerk.house.gov",
    "https://efdsearch.senate.gov",
    "https://www.oge.gov/web/OGE.nsf/Officials Individual Disclosures Search Collection Form",
    "https://www.sos.ca.gov/campaign-lobbying/cal-access-resources",
    "https://www.fppc.ca.gov/",
    "https://www.ethics.state.tx.us",
    "https://www.ethics.state.tx.us/search/cf/",
    "https://ethics.ny.gov/financial-disclosure-statements-elected-officials",
    "https://www.jcope.ny.gov",
    "https://ethics.state.fl.us/FinancialDisclosure/",
    "https://www.ethics.state.fl.us",
    "https://ethics.illinois.gov",
    "https://www.ethics.pa.gov",
    "https://www.michigan.gov/sos/elections/disclosure/personal-financial-disclosure",
    "https://www.mass.gov/orgs/state-ethics-commission",
    "https://www.europarl.europa.eu",
    "https://www.europarl.europa.eu/meps/en/home",
    "https://www.europarl.europa.eu/meps/en/declarations",
    "https://www.integritywatch.eu/mepincomes",
    "https://www.bundestag.de",
    "https://www.bundestag.de/abgeordnete",
    "https://www2.assemblee-nationale.fr",
    "https://www.senat.fr",
    "https://www.hatvp.fr",
    "https://www.camera.it",
    "https://www.senato.it",
    "https://www.congreso.es",
    "https://www.senado.es",
    "https://www.tweedekamer.nl",
    "https://www.eerstekamer.nl",
    "https://www.parliament.uk",
    "https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/",
    "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master",
    "https://stocknear.com/politicians",
    "http://localhost:9090",  # React dev server
    # "https://share.streamlit.io",  # Removed - now using React UI
    "https://test.example.com",
    "https://xxxxx.supabase.co",
    "https://xxxxx.supabase.co (enter to update)",
    # ApiUrls - additional
    "https://api.companieshouse.gov.uk/",
    "https://stream.companieshouse.gov.uk/",
    "https://finnhub.io/docs/api/congressional-trading",
    "https://info-financiere.gouv.fr/api/v1/console",
    "https://api.opencorporates.com/v0.4/",
    "https://apidoc.transparentdata.pl/company_registers_api.html",
    "https://getedge.com.au/docs/api",
    "https://www.cr.gov.hk/en/electronic/e-servicesportal/",
    # WebUrls - additional
    "https://www.opensecrets.org/personal-finances",
    "https://www.legistorm.com/financial_disclosure.html",
    "https://www.barchart.com/investing-ideas/politician-insider-trading",
    "https://www.finddynamics.com/",
    "https://github.com/timothycarambat/senate-stock-watcher-data",
    "https://github.com/xbrlus/xbrl-api",
    "https://filings.xbrl.org/",
    "https://members.parliament.uk/members/lords/interests/register-of-lords-interests",
    "https://www.congreso.es/transparencia",
    "https://www.camera.it/leg19/1",
    "https://uljsqvwkomdrlnofmlad.supabase.co",
    # OGE URL with full path
    "https://www.oge.gov/web/OGE.nsf/Officials Individual Disclosures Search Collection",
    # UK Parliament full path
    "https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/parliamentary-commissioner-for-standards/registers-of-interests/register-of-members-financial-interests/",
}

# Known env keys from constants
KNOWN_ENV_KEYS = {
    "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_KEY",
    "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_PAPER_API_KEY",
    "ALPACA_PAPER_SECRET_KEY", "ALPACA_PAPER", "ALPACA_BASE_URL",
    "QUIVER_API_KEY", "QUIVERQUANT_API_KEY", "PROPUBLICA_API_KEY",
    "FINNHUB_API_KEY", "UK_COMPANIES_HOUSE_API_KEY", "OPENCORPORATES_API_KEY",
    "XBRL_US_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "API_ENCRYPTION_KEY", "LOG_LEVEL", "ENVIRONMENT", "DEBUG",
    "SIGNAL_LOOKBACK_DAYS", "TRADING_MIN_CONFIDENCE",
    "RISK_MAX_POSITION_SIZE_PCT", "RISK_MAX_PORTFOLIO_RISK_PCT",
    "RISK_MAX_TOTAL_EXPOSURE_PCT", "RISK_MAX_POSITIONS",
    "SCRAPING_DELAY", "MAX_RETRIES", "TIMEOUT",
    "STREAMLIT_API_TOKEN", "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    # Admin and alerting (newly added)
    "ADMIN_EMAILS", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "ALERT_FROM_EMAIL", "ALERT_TO_EMAILS", "SLACK_WEBHOOK_URL", "SLACK_CHANNEL",
    "DISCORD_WEBHOOK_URL", "ALERT_WEBHOOK_URL", "cookie_secret", "PYTHONPATH",
}

# Known table names from constants
KNOWN_TABLES = {
    "politicians", "trading_disclosures", "trading_signals", "trading_orders",
    "portfolios", "positions", "data_pull_jobs", "scheduled_jobs",
    "job_executions", "scheduled_jobs_status", "job_execution_summary",
    "action_logs", "action_logs_summary", "stored_files", "data_sources",
    "user_api_keys", "user_sessions", "storage_statistics",
}

# Strings to always ignore
IGNORE_STRINGS = {
    # Common values
    "*", "id", "name", "value", "data", "error", "message", "result", "status",
    "true", "false", "yes", "no", "on", "off", "none", "null", "undefined",
    # Encodings
    "utf-8", "utf8", "ascii", "latin-1",
    # HTTP methods
    "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS",
    # Content types
    "application/json", "text/html", "text/plain", "multipart/form-data",
    # File extensions
    "json", "csv", "pdf", "html", "xml", "txt", "py", "md",
    # Date formats
    "%Y-%m-%d", "%Y%m%d", "%H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
    # Python
    "__name__", "__main__", "__file__", "__doc__", "__all__", "__init__",
    # Common SQL
    "SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "AND", "OR",
    # Pandas
    "index", "columns", "values", "dtype", "float64", "int64", "object", "datetime64",
    # Common params
    "default", "type", "help", "required", "action", "dest", "nargs", "choices",
    # UI strings
    "submit", "cancel", "save", "delete", "edit", "view", "create", "update",
    # Common status values (already in constants)
    "pending", "running", "completed", "failed", "success", "error", "active",
    "inactive", "processed", "buy", "sell", "hold",
    # Date/time
    "days", "hours", "minutes", "seconds", "milliseconds",
    # Misc
    "left", "right", "center", "top", "bottom", "all", "any", "some",
    "asc", "desc", "ASC", "DESC",
}


@dataclass
class HardcodedValue:
    """Represents a found hardcoded value."""
    file_path: str
    line_number: int
    value: str
    value_type: str
    context: str
    suggested_constant: Optional[str] = None


class HardcodedValueFinder(ast.NodeVisitor):
    """AST visitor to find hardcoded values in Python code."""

    def __init__(self, file_path: str, source_lines: list):
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: list[HardcodedValue] = []

    def get_context(self, lineno: int) -> str:
        """Get the source line for context."""
        if 0 < lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def visit_Call(self, node):
        """Visit function calls to find os.getenv patterns."""
        # Check for os.getenv("ENV_VAR") or os.environ.get("ENV_VAR")
        if self._is_getenv_call(node):
            if node.args and isinstance(node.args[0], ast.Constant):
                env_var = node.args[0].value
                if isinstance(env_var, str) and env_var not in KNOWN_ENV_KEYS:
                    context = self.get_context(node.lineno)
                    self.issues.append(HardcodedValue(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        value=env_var,
                        value_type="env_var_not_in_constants",
                        context=context,
                        suggested_constant=f"EnvKeys.{env_var}"
                    ))

        # Check for .table("table_name") calls
        if self._is_table_call(node):
            if node.args and isinstance(node.args[0], ast.Constant):
                table_name = node.args[0].value
                if isinstance(table_name, str) and table_name not in KNOWN_TABLES:
                    context = self.get_context(node.lineno)
                    self.issues.append(HardcodedValue(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        value=table_name,
                        value_type="table_name_not_in_constants",
                        context=context,
                        suggested_constant=f"Tables.{table_name.upper()}"
                    ))

        self.generic_visit(node)

    def visit_Assign(self, node):
        """Visit assignments to find URL patterns."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_name = target.id.lower()
                # Check for URL assignments
                if any(x in target_name for x in ["url", "base_url", "api_url", "endpoint"]):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        url = node.value.value
                        if url.startswith(("http://", "https://")) and url not in KNOWN_URLS:
                            context = self.get_context(node.lineno)
                            self.issues.append(HardcodedValue(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                value=url,
                                value_type="url_not_in_constants",
                                context=context,
                                suggested_constant=self._suggest_url_constant(url)
                            ))

        self.generic_visit(node)

    def visit_Constant(self, node):
        """Visit constant nodes for standalone URLs."""
        value = node.value
        if isinstance(value, str):
            # Check for URLs in general (not just in assignments)
            if value.startswith(("http://", "https://")) and len(value) > 15:
                # Skip known URLs and already-in-constants URLs
                if value not in KNOWN_URLS and not self._is_in_constants_context(node):
                    context = self.get_context(node.lineno)
                    # Skip if this is in a docstring, comment-like context, or format string
                    if not (context.startswith('"""') or context.startswith("'''") or
                            "# " in context or "{" in value):
                        # Check if already reported
                        if not any(i.value == value and i.line_number == node.lineno for i in self.issues):
                            self.issues.append(HardcodedValue(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                value=value,
                                value_type="url_not_in_constants",
                                context=context,
                                suggested_constant=self._suggest_url_constant(value)
                            ))

        self.generic_visit(node)

    def _is_getenv_call(self, node) -> bool:
        """Check if this is an os.getenv or os.environ.get call."""
        if isinstance(node.func, ast.Attribute):
            # os.getenv
            if node.func.attr == "getenv":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    return True
            # os.environ.get
            if node.func.attr == "get":
                if isinstance(node.func.value, ast.Attribute):
                    if node.func.value.attr == "environ":
                        return True
        return False

    def _is_table_call(self, node) -> bool:
        """Check if this is a .table() call."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "table":
            return True
        return False

    def _is_in_constants_context(self, node) -> bool:
        """Check if node is inside a constants definition."""
        # Simplified check
        return False

    def _suggest_url_constant(self, url: str) -> str:
        """Suggest a constant name for a URL."""
        match = re.search(r"https?://([^/]+)", url)
        if match:
            domain = match.group(1)
            # Clean up domain for constant name
            name = domain.replace(".", "_").replace("-", "_").upper()
            if "/api" in url.lower():
                return f"ApiUrls.{name}"
            return f"WebUrls.{name}"
        return "URL_UNKNOWN"


def find_python_files(base_dir: Path) -> list[Path]:
    """Find all Python files to scan."""
    files = []
    for file_path in base_dir.rglob("*.py"):
        # Check if file should be excluded
        should_exclude = False
        str_path = str(file_path)
        for exclude in EXCLUDE_PATTERNS:
            # Simple pattern matching
            pattern = exclude.replace("**", ".*").replace("*", "[^/]*")
            if re.search(pattern, str_path):
                should_exclude = True
                break
        if not should_exclude:
            files.append(file_path)
    return files


def scan_file(file_path: Path) -> list[HardcodedValue]:
    """Scan a single file for hardcoded values."""
    try:
        source = file_path.read_text(encoding="utf-8")
        source_lines = source.split("\n")
        tree = ast.parse(source, filename=str(file_path))

        finder = HardcodedValueFinder(str(file_path), source_lines)
        finder.visit(tree)

        return finder.issues
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error scanning {file_path}: {e}", file=sys.stderr)
        return []


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    verbose = "--verbose" in sys.argv

    all_issues: list[HardcodedValue] = []
    files_scanned = 0

    for scan_dir in SCAN_DIRS:
        dir_path = project_root / scan_dir
        if not dir_path.exists():
            print(f"Warning: Directory {dir_path} does not exist", file=sys.stderr)
            continue

        python_files = find_python_files(dir_path)

        for file_path in python_files:
            issues = scan_file(file_path)
            all_issues.extend(issues)
            files_scanned += 1

    # Deduplicate issues (same file, line, value)
    seen = set()
    unique_issues = []
    for issue in all_issues:
        key = (issue.file_path, issue.line_number, issue.value)
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)
    all_issues = unique_issues

    # Group by type
    by_type = defaultdict(list)
    for issue in all_issues:
        by_type[issue.value_type].append(issue)

    # Print report
    print("=" * 70)
    print("HARDCODED VALUES REPORT")
    print("=" * 70)
    print(f"\nFiles scanned: {files_scanned}")
    print(f"Total issues found: {len(all_issues)}")
    print()

    if not all_issues:
        print("No hardcoded values found!")
        return 0

    # Print summary first
    print("Summary by type:")
    for value_type in sorted(by_type.keys()):
        print(f"  - {value_type}: {len(by_type[value_type])}")
    print()

    # Print details by type
    for value_type, issues in sorted(by_type.items()):
        print(f"\n{'=' * 70}")
        print(f"{value_type.upper().replace('_', ' ')} ({len(issues)} issues)")
        print("=" * 70)

        for issue in sorted(issues, key=lambda x: (x.file_path, x.line_number)):
            rel_path = Path(issue.file_path).relative_to(project_root)
            print(f"\n  {rel_path}:{issue.line_number}")
            print(f"    Value: {issue.value[:80]}{'...' if len(issue.value) > 80 else ''}")
            if verbose:
                print(f"    Context: {issue.context[:80]}{'...' if len(issue.context) > 80 else ''}")
            if issue.suggested_constant:
                print(f"    Suggested: {issue.suggested_constant}")

    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {len(all_issues)} hardcoded values need attention")
    print("=" * 70)

    return len(all_issues)


if __name__ == "__main__":
    sys.exit(main())
