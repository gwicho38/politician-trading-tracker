#!/usr/bin/env python3
"""
Linter to detect hardcoded strings that should use constants.

This linter scans Python files for hardcoded strings that match known
constant values and reports violations.

Exit codes:
    0: No violations found
    1: Violations found
    2: Error during execution
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Tuple

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import constants to check against
try:
    from politician_trading.constants import (
        ActionType,
        ApiUrls,
        Columns,
        ConfigDefaults,
        DataSourceType,
        EnvKeys,
        JobStatus,
        OrderStatus,
        ParseStatus,
        PoliticianRole,
        ProcessingStatus,
        SignalType,
        SourceTypes,
        StorageBuckets,
        Tables,
        TradingMode,
        TransactionType,
        WebUrls,
    )
except ImportError as e:
    print(
        f"Error: Cannot import constants module: {e}\n"
        "Make sure you're running from the project root.",
        file=sys.stderr,
    )
    sys.exit(2)


class HardcodedStringFinder(ast.NodeVisitor):
    """AST visitor to find hardcoded strings that should use constants."""

    # Explicit list of string literals that should not be skipped,
    # even if they contain spaces or punctuation
    EXCEPTION_STRINGS = {
        # Add display names and other UI strings that should use constants
        # (currently none, but can be extended as needed)
    }

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, int, str, str]] = []
        self.constant_values = self._load_constant_values()

    @staticmethod
    def _build_constant_dict(cls, prefix: str) -> dict:
        """Helper to build a constant dictionary from a class.

        Args:
            cls: The class to extract constants from
            prefix: The prefix to use in the constant path (e.g., "Tables")

        Returns:
            Dictionary mapping constant values to their reference paths
        """
        return {
            getattr(cls, attr): f"{prefix}.{attr}" for attr in dir(cls) if not attr.startswith("_")
        }

    def _load_constant_values(self) -> dict:
        """Load all constant values organized by category."""
        # Database columns (flattened from nested classes)
        columns_dict = {}
        for column_class in [
            Columns.Common,
            Columns.Politician,
            Columns.Disclosure,
            Columns.Signal,
            Columns.Order,
            Columns.Job,
            Columns.Storage,
            Columns.ActionLog,
            Columns.User,
        ]:
            for attr in dir(column_class):
                if not attr.startswith("_"):
                    value = getattr(column_class, attr)
                    class_name = column_class.__name__
                    columns_dict[value] = f"Columns.{class_name}.{attr}"

        # ConfigDefaults (only string-based defaults, not numeric)
        config_defaults_dict = {
            value: f"ConfigDefaults.{attr}"
            for attr in dir(ConfigDefaults)
            if not attr.startswith("_")
            for value in [getattr(ConfigDefaults, attr)]
            if isinstance(value, str)
        }

        # Build the constants dictionary with all mappings
        return {
            "Tables": self._build_constant_dict(Tables, "Tables"),
            "Columns": columns_dict,
            "JobStatus": self._build_constant_dict(JobStatus, "JobStatus"),
            "OrderStatus": self._build_constant_dict(OrderStatus, "OrderStatus"),
            "ParseStatus": self._build_constant_dict(ParseStatus, "ParseStatus"),
            "TransactionType": self._build_constant_dict(TransactionType, "TransactionType"),
            "SignalType": self._build_constant_dict(SignalType, "SignalType"),
            "ActionType": self._build_constant_dict(ActionType, "ActionType"),
            "PoliticianRole": self._build_constant_dict(PoliticianRole, "PoliticianRole"),
            "EnvKeys": self._build_constant_dict(EnvKeys, "EnvKeys"),
            "StorageBuckets": self._build_constant_dict(StorageBuckets, "StorageBuckets"),
            "ProcessingStatus": self._build_constant_dict(ProcessingStatus, "ProcessingStatus"),
            "TradingMode": self._build_constant_dict(TradingMode, "TradingMode"),
            "DataSourceType": self._build_constant_dict(DataSourceType, "DataSourceType"),
            "SourceTypes": self._build_constant_dict(SourceTypes, "SourceTypes"),
            "ApiUrls": self._build_constant_dict(ApiUrls, "ApiUrls"),
            "WebUrls": self._build_constant_dict(WebUrls, "WebUrls"),
            "ConfigDefaults": config_defaults_dict,
        }

    def _check_string_literal(self, node: ast.Str, line: int, col: int):
        """Check if a string literal should use a constant."""
        value = node.s

        # Skip empty strings, single characters, and very short strings
        if not value or len(value) <= 2:
            return

        # Skip strings that look like messages, descriptions, or UI text
        # (they typically contain spaces or punctuation), unless they are in the exception list
        if (
            " " in value or any(char in value for char in ".!?,;:")
        ) and value not in self.EXCEPTION_STRINGS:
            return

        # Skip URLs and file paths
        if value.startswith(("http://", "https://", "/", "./")):
            return

        # Check if this string matches a known constant
        for category, const_map in self.constant_values.items():
            if value in const_map:
                constant_name = const_map[value]
                self.violations.append((line, col, value, constant_name))
                return

    def visit_Str(self, node: ast.Str):
        """Visit string literals (Python < 3.8)."""
        self._check_string_literal(node, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        """Visit constant nodes including strings (Python >= 3.8)."""
        if isinstance(node.value, str):
            self._check_string_literal(node, node.lineno, node.col_offset)
        self.generic_visit(node)


def lint_file(filepath: Path) -> List[Tuple[int, int, str, str]]:
    """
    Lint a single Python file for hardcoded strings.

    Args:
        filepath: Path to the Python file

    Returns:
        List of violations (line, col, hardcoded_value, constant_name)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        finder = HardcodedStringFinder(str(filepath))
        finder.visit(tree)
        return finder.violations

    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def should_skip_file(filepath: Path) -> bool:
    """
    Determine if a file should be skipped during linting.

    Args:
        filepath: Path to check

    Returns:
        True if the file should be skipped
    """
    # Exact file path matches (relative to project root)
    skip_files = {
        "src/politician_trading/constants/__init__.py",
        "src/politician_trading/constants/database.py",
        "src/politician_trading/constants/statuses.py",
        "src/politician_trading/constants/env_keys.py",
        "src/politician_trading/constants/storage.py",
        "src/politician_trading/constants/urls.py",
        "scripts/lint_hardcoded_strings.py",
    }

    # Directory patterns to skip
    skip_dirs = {
        "__pycache__",
        "migrations",
        ".git",
        ".venv",
        "venv",
        ".pytest_cache",
    }

    # File patterns to skip (suffix matching)
    skip_suffixes = {
        ".pyc",
        ".pyo",
        ".so",
    }

    filepath_str = str(filepath)
    filepath_parts = filepath.parts

    # Check if file is in skip_files (exact match on relative path)
    for skip_file in skip_files:
        if filepath_str.endswith(skip_file):
            return True

    # Check if any parent directory is in skip_dirs
    if any(dir_name in skip_dirs for dir_name in filepath_parts):
        return True

    # Check if file has a skip suffix
    if any(filepath_str.endswith(suffix) for suffix in skip_suffixes):
        return True

    # Check if filename is a test file (strict pattern matching)
    filename = filepath.name
    # Only skip if filename starts with "test_" or ends with "_test.py"
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True

    # Also skip conftest.py and other pytest files
    if filename in {"conftest.py", "pytest.ini", "setup.py"}:
        return True

    return False


def main():
    """Main entry point for the linter."""
    parser = argparse.ArgumentParser(
        description="Lint Python files for hardcoded strings that should use constants"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to lint (default: all Python files in src/)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code even for warnings",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix violations (not implemented)",
    )

    args = parser.parse_args()

    # Determine files to lint
    if args.files:
        files_to_lint = [Path(f) for f in args.files if f.endswith(".py")]
    else:
        # Default to all Python files in src/
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src"
        files_to_lint = list(src_dir.rglob("*.py"))

    # Filter out files that should be skipped
    files_to_lint = [f for f in files_to_lint if not should_skip_file(f)]

    if not files_to_lint:
        print("No files to lint")
        return 0

    print(f"Linting {len(files_to_lint)} files for hardcoded strings...")
    print()

    total_violations = 0
    files_with_violations = 0

    for filepath in sorted(files_to_lint):
        violations = lint_file(filepath)

        if violations:
            files_with_violations += 1
            total_violations += len(violations)

            print(f"\n{filepath}:")
            for line, col, value, constant_name in violations:
                print(f"  Line {line}:{col}: Use {constant_name} instead of '{value}'")

    print()
    print("=" * 70)
    print(f"Summary: {total_violations} violations in {files_with_violations} files")
    print("=" * 70)

    if total_violations > 0:
        print()
        print("To fix these violations:")
        print("1. Import the appropriate constant:")
        print("   from politician_trading.constants import Tables, Columns, ...")
        print("2. Replace the hardcoded string with the constant")
        print()
        print("Example:")
        print('   Before: db.table("politicians").select("*")')
        print("   After:  db.table(Tables.POLITICIANS).select('*')")
        print()
        return 1

    print("✓ No hardcoded string violations found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
