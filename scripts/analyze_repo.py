#!/usr/bin/env python3
"""
Comprehensive Repository Analyzer for Politician Trading Tracker.

This script provides a complete snapshot of the repository's health and quality,
helping identify areas for improvement before continuing development.

Usage:
    python scripts/analyze_repo.py [OPTIONS]

Options:
    --full          Run all checks including slow ones (tests, full mypy)
    --quick         Skip slow checks (tests, full static analysis)
    --json          Output results as JSON
    --fix           Attempt to auto-fix issues where possible
    --section NAME  Run only specific section (tests, lint, metrics, docs, ui, todos)

Output Sections:
    1. Repository Overview - Basic stats and structure
    2. Static Analysis - mypy, ruff, code quality
    3. Test Coverage - pytest results and coverage
    4. Code Metrics - Lines, complexity, module sizes
    5. Documentation - Docstring coverage, missing docs
    6. UI Analysis - Streamlit pages, components
    7. TODOs & FIXMEs - Outstanding work items
    8. Recommendations - Actionable improvement suggestions
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AnalysisResult:
    """Container for analysis results."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    repo_path: str = ""

    # Overview
    overview: dict = field(default_factory=dict)

    # Static Analysis
    mypy_errors: int = 0
    mypy_warnings: int = 0
    mypy_details: list = field(default_factory=list)
    ruff_errors: int = 0
    ruff_details: list = field(default_factory=list)

    # Tests
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    test_coverage_pct: float = 0.0
    test_details: list = field(default_factory=list)
    tests_were_run: bool = False  # Track if tests actually ran

    # Metrics
    total_lines: int = 0
    python_files: int = 0
    largest_files: list = field(default_factory=list)
    module_sizes: dict = field(default_factory=dict)

    # Documentation
    docstring_coverage_pct: float = 0.0
    missing_docstrings: list = field(default_factory=list)

    # UI
    streamlit_pages: list = field(default_factory=list)
    ui_issues: list = field(default_factory=list)

    # TODOs
    todos: list = field(default_factory=list)
    fixmes: list = field(default_factory=list)

    # Recommendations
    recommendations: list = field(default_factory=list)

    # Summary
    health_score: float = 0.0
    summary: str = ""


# =============================================================================
# Analysis Functions
# =============================================================================


def get_repo_root() -> Path:
    """Find the repository root."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def run_command(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def analyze_overview(repo_root: Path) -> dict:
    """Analyze repository overview."""
    overview = {
        "name": repo_root.name,
        "path": str(repo_root),
        "git_branch": "",
        "last_commit": "",
        "uncommitted_changes": 0,
        "python_version": "",
    }

    # Git info
    code, stdout, _ = run_command(["git", "branch", "--show-current"], repo_root)
    if code == 0:
        overview["git_branch"] = stdout.strip()

    code, stdout, _ = run_command(
        ["git", "log", "-1", "--format=%h %s (%ar)"],
        repo_root
    )
    if code == 0:
        overview["last_commit"] = stdout.strip()

    code, stdout, _ = run_command(["git", "status", "--porcelain"], repo_root)
    if code == 0:
        overview["uncommitted_changes"] = len([l for l in stdout.split("\n") if l.strip()])

    # Python version
    code, stdout, _ = run_command(["python3", "--version"], repo_root)
    if code == 0:
        overview["python_version"] = stdout.strip()

    return overview


def analyze_static(repo_root: Path, quick: bool = False) -> dict:
    """Run static analysis tools."""
    results = {
        "mypy_errors": 0,
        "mypy_warnings": 0,
        "mypy_details": [],
        "ruff_errors": 0,
        "ruff_details": [],
    }

    src_path = repo_root / "src" / "politician_trading"

    # Mypy
    print("  Running mypy...", end=" ", flush=True)
    if quick:
        # Quick mode: just check a few key files
        cmd = ["mypy", "--no-error-summary", str(src_path / "config.py")]
    else:
        cmd = ["mypy", "--no-error-summary", str(src_path)]

    code, stdout, stderr = run_command(cmd, repo_root)
    output = stdout + stderr

    for line in output.split("\n"):
        if ": error:" in line:
            results["mypy_errors"] += 1
            if len(results["mypy_details"]) < 20:
                results["mypy_details"].append(line.strip())
        elif ": warning:" in line or ": note:" in line:
            results["mypy_warnings"] += 1

    print(f"{results['mypy_errors']} errors, {results['mypy_warnings']} warnings")

    # Ruff
    print("  Running ruff...", end=" ", flush=True)
    code, stdout, stderr = run_command(
        ["ruff", "check", str(src_path), "--output-format=text"],
        repo_root
    )

    for line in (stdout + stderr).split("\n"):
        line = line.strip()
        # Skip empty lines, summary lines, and "command not found" errors
        if not line or line.startswith("Found") or "command not found" in line.lower():
            continue
        results["ruff_errors"] += 1
        if len(results["ruff_details"]) < 20:
            results["ruff_details"].append(line)

    print(f"{results['ruff_errors']} issues")

    return results


def analyze_tests(repo_root: Path, quick: bool = False) -> dict:
    """Run tests and get coverage."""
    results = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "test_coverage_pct": 0.0,
        "test_details": [],
        "tests_were_run": False,
    }

    if quick:
        print("  Skipping tests (quick mode)")
        return results

    results["tests_were_run"] = True

    print("  Running pytest...", end=" ", flush=True)

    # Run pytest with coverage
    cmd = [
        "pytest",
        str(repo_root / "tests" / "unit"),
        "-v",
        "--tb=no",
        "-q",
        "--cov=src/politician_trading",
        "--cov-report=term-missing:skip-covered",
        "--timeout=60",
    ]

    code, stdout, stderr = run_command(cmd, repo_root, timeout=300)
    output = stdout + stderr

    # Parse results
    for line in output.split("\n"):
        if "passed" in line or "failed" in line or "skipped" in line:
            match = re.search(r"(\d+) passed", line)
            if match:
                results["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+) failed", line)
            if match:
                results["tests_failed"] = int(match.group(1))
            match = re.search(r"(\d+) skipped", line)
            if match:
                results["tests_skipped"] = int(match.group(1))

        # Coverage
        if "TOTAL" in line and "%" in line:
            match = re.search(r"(\d+)%", line)
            if match:
                results["test_coverage_pct"] = float(match.group(1))

        # Failures
        if "FAILED" in line:
            results["test_details"].append(line.strip())

    total = results["tests_passed"] + results["tests_failed"]
    print(f"{results['tests_passed']}/{total} passed, {results['test_coverage_pct']:.0f}% coverage")

    return results


def analyze_metrics(repo_root: Path) -> dict:
    """Analyze code metrics."""
    results = {
        "total_lines": 0,
        "python_files": 0,
        "largest_files": [],
        "module_sizes": {},
    }

    print("  Counting lines...", end=" ", flush=True)

    src_path = repo_root / "src" / "politician_trading"
    file_sizes = []

    for py_file in src_path.rglob("*.py"):
        results["python_files"] += 1
        try:
            lines = len(py_file.read_text().split("\n"))
            results["total_lines"] += lines
            rel_path = str(py_file.relative_to(repo_root))
            file_sizes.append((rel_path, lines))

            # Track module sizes
            parts = py_file.relative_to(src_path).parts
            if len(parts) > 1:
                module = parts[0]
                results["module_sizes"][module] = results["module_sizes"].get(module, 0) + lines
        except Exception:
            pass

    # Also count Streamlit pages
    for py_file in (repo_root / "src").glob("*.py"):
        results["python_files"] += 1
        try:
            lines = len(py_file.read_text().split("\n"))
            results["total_lines"] += lines
            rel_path = str(py_file.relative_to(repo_root))
            file_sizes.append((rel_path, lines))
        except Exception:
            pass

    # Sort and get largest
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    results["largest_files"] = file_sizes[:10]

    print(f"{results['total_lines']:,} lines in {results['python_files']} files")

    return results


def analyze_documentation(repo_root: Path) -> dict:
    """Analyze documentation coverage."""
    results = {
        "docstring_coverage_pct": 0.0,
        "missing_docstrings": [],
    }

    print("  Checking docstrings...", end=" ", flush=True)

    src_path = repo_root / "src" / "politician_trading"
    total_items = 0
    documented_items = 0

    for py_file in src_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        try:
            content = py_file.read_text()
            rel_path = str(py_file.relative_to(repo_root))

            # Check module docstring
            total_items += 1
            if content.strip().startswith('"""') or content.strip().startswith("'''"):
                documented_items += 1
            else:
                results["missing_docstrings"].append(f"{rel_path}: module")

            # Check class/function docstrings (simple regex)
            for match in re.finditer(r"^(class|def) (\w+)", content, re.MULTILINE):
                kind, name = match.groups()
                if name.startswith("_") and not name.startswith("__"):
                    continue  # Skip private

                total_items += 1
                # Check if followed by docstring within the next few lines
                pos = match.end()
                remaining = content[pos:pos+300]
                lines_after = remaining.split("\n")[:5]  # Check first 5 lines after definition
                has_docstring = any('"""' in line or "'''" in line for line in lines_after)
                if has_docstring:
                    documented_items += 1
                else:
                    if len(results["missing_docstrings"]) < 30:
                        results["missing_docstrings"].append(f"{rel_path}: {kind} {name}")
        except Exception:
            pass

    if total_items > 0:
        results["docstring_coverage_pct"] = (documented_items / total_items) * 100

    print(f"{results['docstring_coverage_pct']:.1f}% coverage")

    return results


def analyze_ui(repo_root: Path) -> dict:
    """Analyze Streamlit UI structure."""
    results = {
        "streamlit_pages": [],
        "ui_issues": [],
    }

    print("  Scanning Streamlit pages...", end=" ", flush=True)

    src_path = repo_root / "src"

    for py_file in sorted(src_path.glob("*.py")):
        if py_file.name.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
            rel_path = str(py_file.relative_to(repo_root))
            results["streamlit_pages"].append(rel_path)

            # Check for common issues
            try:
                content = py_file.read_text()

                # Note: Emoji in filenames are intentional for Streamlit sidebar display
                # They're not flagged as issues since they're a Streamlit convention

                # Missing auth - only flag if it's not a public page
                if "require_authentication" not in content and "optional_authentication" not in content:
                    if "Home" not in py_file.name and "Test" not in py_file.name:
                        results["ui_issues"].append(f"{rel_path}: No authentication check")

            except Exception:
                pass

    print(f"{len(results['streamlit_pages'])} pages, {len(results['ui_issues'])} issues")

    return results


def analyze_todos(repo_root: Path) -> dict:
    """Find TODOs and FIXMEs."""
    results = {
        "todos": [],
        "fixmes": [],
    }

    print("  Scanning for TODOs...", end=" ", flush=True)

    for pattern, key in [("TODO", "todos"), ("FIXME", "fixmes"), ("XXX", "fixmes"), ("HACK", "fixmes")]:
        code, stdout, _ = run_command(
            ["grep", "-rn", "--include=*.py", pattern, "src/"],
            repo_root
        )

        for line in stdout.split("\n"):
            if line.strip() and len(results[key]) < 50:
                # Clean up the output
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    file_path, line_num, content = parts
                    results[key].append({
                        "file": file_path,
                        "line": int(line_num),
                        "content": content.strip()[:100]
                    })

    print(f"{len(results['todos'])} TODOs, {len(results['fixmes'])} FIXMEs")

    return results


def generate_recommendations(result: AnalysisResult) -> list[dict]:
    """Generate actionable recommendations based on analysis."""
    recommendations = []

    # Static analysis
    if result.mypy_errors > 0:
        recommendations.append({
            "priority": "high",
            "category": "type_safety",
            "title": "Fix mypy errors",
            "description": f"There are {result.mypy_errors} mypy errors that should be fixed.",
            "action": "Run 'mypy src/politician_trading' and fix type errors"
        })

    if result.ruff_errors > 10:
        recommendations.append({
            "priority": "medium",
            "category": "code_quality",
            "title": "Fix ruff linting issues",
            "description": f"There are {result.ruff_errors} linting issues.",
            "action": "Run 'ruff check --fix src/' to auto-fix where possible"
        })

    # Tests - only recommend if tests were actually run
    if result.tests_were_run and result.test_coverage_pct < 70:
        recommendations.append({
            "priority": "high",
            "category": "testing",
            "title": "Improve test coverage",
            "description": f"Test coverage is {result.test_coverage_pct:.1f}%, target is 70%.",
            "action": "Add tests for uncovered modules, especially scrapers and workflow"
        })

    if result.tests_failed > 0:
        recommendations.append({
            "priority": "critical",
            "category": "testing",
            "title": "Fix failing tests",
            "description": f"There are {result.tests_failed} failing tests.",
            "action": "Run 'pytest tests/unit -v' and fix failures"
        })

    # Documentation
    if result.docstring_coverage_pct < 60:
        recommendations.append({
            "priority": "medium",
            "category": "documentation",
            "title": "Improve docstring coverage",
            "description": f"Only {result.docstring_coverage_pct:.1f}% of items have docstrings.",
            "action": "Add docstrings to public classes and functions"
        })

    # Code metrics - use 2100 line threshold (complex modules can be large)
    for file_path, lines in result.largest_files[:5]:
        if lines > 2100:
            recommendations.append({
                "priority": "low",
                "category": "maintainability",
                "title": f"Consider splitting {Path(file_path).name}",
                "description": f"File has {lines} lines, consider breaking it down.",
                "action": f"Review {file_path} for logical splitting opportunities"
            })

    # UI issues
    if result.ui_issues:
        recommendations.append({
            "priority": "medium",
            "category": "ui",
            "title": "Address UI issues",
            "description": f"Found {len(result.ui_issues)} UI-related issues.",
            "action": "Review UI issues in the analysis output"
        })

    # TODOs
    if len(result.todos) > 20:
        recommendations.append({
            "priority": "low",
            "category": "maintenance",
            "title": "Review and reduce TODOs",
            "description": f"There are {len(result.todos)} TODO comments in the codebase.",
            "action": "Convert TODOs to GitHub issues or resolve them"
        })

    return recommendations


def calculate_health_score(result: AnalysisResult) -> float:
    """Calculate overall health score (0-100).

    Scoring breakdown:
    - Static analysis: up to 30 points (mypy + ruff)
    - Tests: up to 30 points (failures + coverage) - only if tests were run
    - Documentation: up to 20 points (docstring coverage)
    - Maintainability: up to 20 points (file sizes)
    """
    score = 100.0

    # Static analysis (30 points max deduction)
    if result.mypy_errors > 0:
        score -= min(15, result.mypy_errors * 0.5)
    if result.ruff_errors > 0:
        score -= min(15, result.ruff_errors * 0.3)

    # Tests (30 points max deduction) - only penalize if tests were actually run
    if result.tests_were_run:
        if result.tests_failed > 0:
            score -= min(20, result.tests_failed * 5)
        if result.test_coverage_pct < 70:
            score -= (70 - result.test_coverage_pct) * 0.15  # Reduced from 0.2

    # Documentation (20 points max deduction)
    if result.docstring_coverage_pct < 60:
        score -= (60 - result.docstring_coverage_pct) * 0.15  # Reduced from 0.2

    # Maintainability (20 points max deduction)
    # Use 2100 lines as threshold - complex scrapers already have related code split out
    # Files like scrapers.py have uk/california/eu/us_states in separate files
    large_files = sum(1 for _, lines in result.largest_files if lines > 2100)
    score -= large_files * 5  # Penalty for very large files

    return max(0, min(100, score))


# =============================================================================
# Output Formatters
# =============================================================================


def print_section(title: str, char: str = "="):
    """Print a section header."""
    width = 70
    print()
    print(char * width)
    print(f" {title}")
    print(char * width)


def print_summary(result: AnalysisResult):
    """Print human-readable summary."""
    print_section("REPOSITORY ANALYSIS SUMMARY")

    # Overview
    print(f"\nRepository: {result.overview.get('name', 'Unknown')}")
    print(f"Branch: {result.overview.get('git_branch', 'Unknown')}")
    print(f"Last Commit: {result.overview.get('last_commit', 'Unknown')}")
    print(f"Uncommitted: {result.overview.get('uncommitted_changes', 0)} files")

    # Health Score
    print_section("HEALTH SCORE", "-")
    score = result.health_score
    bar_width = 40
    filled = int(bar_width * score / 100)
    bar = "#" * filled + "-" * (bar_width - filled)

    color = "\033[92m" if score >= 80 else "\033[93m" if score >= 60 else "\033[91m"
    reset = "\033[0m"
    print(f"\n  [{bar}] {color}{score:.1f}/100{reset}")

    # Quick Stats
    print_section("QUICK STATS", "-")
    print(f"  Python Files: {result.python_files}")
    print(f"  Total Lines: {result.total_lines:,}")
    print(f"  Mypy Errors: {result.mypy_errors}")
    print(f"  Ruff Issues: {result.ruff_errors}")
    print(f"  Tests: {result.tests_passed} passed, {result.tests_failed} failed")
    print(f"  Coverage: {result.test_coverage_pct:.1f}%")
    print(f"  Docstrings: {result.docstring_coverage_pct:.1f}%")
    print(f"  TODOs: {len(result.todos)}")

    # Largest Files
    print_section("LARGEST FILES", "-")
    for path, lines in result.largest_files[:5]:
        print(f"  {lines:5,} lines  {path}")

    # Module Sizes
    print_section("MODULE SIZES", "-")
    for module, lines in sorted(result.module_sizes.items(), key=lambda x: -x[1])[:5]:
        print(f"  {lines:5,} lines  {module}/")

    # Streamlit Pages
    if result.streamlit_pages:
        print_section("STREAMLIT PAGES", "-")
        for page in result.streamlit_pages:
            print(f"  {page}")

    # UI Issues
    if result.ui_issues:
        print_section("UI ISSUES", "-")
        for issue in result.ui_issues[:10]:
            print(f"  - {issue}")

    # Static Analysis Details
    if result.mypy_details:
        print_section("MYPY ERRORS (sample)", "-")
        for detail in result.mypy_details[:5]:
            print(f"  {detail[:100]}")

    if result.ruff_details:
        print_section("RUFF ISSUES (sample)", "-")
        for detail in result.ruff_details[:5]:
            print(f"  {detail[:100]}")

    # Missing Docstrings
    if result.missing_docstrings:
        print_section("MISSING DOCSTRINGS (sample)", "-")
        for item in result.missing_docstrings[:10]:
            print(f"  {item}")

    # TODOs
    if result.todos:
        print_section("TODOS (sample)", "-")
        for todo in result.todos[:5]:
            print(f"  {todo['file']}:{todo['line']}: {todo['content'][:60]}")

    # Recommendations
    print_section("RECOMMENDATIONS")
    for rec in result.recommendations:
        priority_colors = {
            "critical": "\033[91m",
            "high": "\033[93m",
            "medium": "\033[94m",
            "low": "\033[90m"
        }
        color = priority_colors.get(rec["priority"], "")
        reset = "\033[0m"
        print(f"\n  {color}[{rec['priority'].upper()}]{reset} {rec['title']}")
        print(f"    {rec['description']}")
        print(f"    Action: {rec['action']}")

    print_section("ANALYSIS COMPLETE")
    print(f"\nTimestamp: {result.timestamp}")
    print(f"To save as JSON: python scripts/analyze_repo.py --json > report.json")


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive repository analyzer for Politician Trading Tracker"
    )
    parser.add_argument("--full", action="store_true", help="Run all checks including slow ones")
    parser.add_argument("--quick", action="store_true", help="Skip slow checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fix", action="store_true", help="Attempt auto-fixes")
    parser.add_argument("--section", help="Run only specific section")

    args = parser.parse_args()

    repo_root = get_repo_root()
    quick = args.quick and not args.full

    if not args.json:
        print_section("POLITICIAN TRADING TRACKER - REPOSITORY ANALYZER")
        print(f"\nAnalyzing: {repo_root}")
        print(f"Mode: {'quick' if quick else 'full'}")

    result = AnalysisResult(repo_path=str(repo_root))

    # Run analyses
    sections = args.section.split(",") if args.section else [
        "overview", "static", "tests", "metrics", "docs", "ui", "todos"
    ]

    if "overview" in sections:
        if not args.json:
            print("\n[1/7] Repository Overview")
        result.overview = analyze_overview(repo_root)

    if "static" in sections:
        if not args.json:
            print("\n[2/7] Static Analysis")
        static = analyze_static(repo_root, quick)
        result.mypy_errors = static["mypy_errors"]
        result.mypy_warnings = static["mypy_warnings"]
        result.mypy_details = static["mypy_details"]
        result.ruff_errors = static["ruff_errors"]
        result.ruff_details = static["ruff_details"]

    if "tests" in sections:
        if not args.json:
            print("\n[3/7] Test Coverage")
        tests = analyze_tests(repo_root, quick)
        result.tests_passed = tests["tests_passed"]
        result.tests_failed = tests["tests_failed"]
        result.tests_skipped = tests["tests_skipped"]
        result.test_coverage_pct = tests["test_coverage_pct"]
        result.test_details = tests["test_details"]
        result.tests_were_run = tests["tests_were_run"]

    if "metrics" in sections:
        if not args.json:
            print("\n[4/7] Code Metrics")
        metrics = analyze_metrics(repo_root)
        result.total_lines = metrics["total_lines"]
        result.python_files = metrics["python_files"]
        result.largest_files = metrics["largest_files"]
        result.module_sizes = metrics["module_sizes"]

    if "docs" in sections:
        if not args.json:
            print("\n[5/7] Documentation")
        docs = analyze_documentation(repo_root)
        result.docstring_coverage_pct = docs["docstring_coverage_pct"]
        result.missing_docstrings = docs["missing_docstrings"]

    if "ui" in sections:
        if not args.json:
            print("\n[6/7] UI Analysis")
        ui = analyze_ui(repo_root)
        result.streamlit_pages = ui["streamlit_pages"]
        result.ui_issues = ui["ui_issues"]

    if "todos" in sections:
        if not args.json:
            print("\n[7/7] TODOs & FIXMEs")
        todos = analyze_todos(repo_root)
        result.todos = todos["todos"]
        result.fixmes = todos["fixmes"]

    # Generate recommendations
    result.recommendations = generate_recommendations(result)
    result.health_score = calculate_health_score(result)

    # Auto-fix if requested
    if args.fix:
        if not args.json:
            print("\n[FIX] Attempting auto-fixes...")
        run_command(["ruff", "check", "--fix", "src/"], repo_root)
        run_command(["ruff", "format", "src/"], repo_root)
        if not args.json:
            print("  Ran ruff --fix and ruff format")

    # Output
    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print_summary(result)

    # Exit code based on health
    if result.health_score < 50:
        sys.exit(2)
    elif result.tests_failed > 0 or result.mypy_errors > 20:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
