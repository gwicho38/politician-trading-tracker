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

    def _load_constant_values(self) -> dict:
        """Load all constant values organized by category."""
        constants = {}

        # Database tables
        constants["Tables"] = {
            getattr(Tables, attr): f"Tables.{attr}"
            for attr in dir(Tables)
            if not attr.startswith("_")
        }

        # Database columns (flattened from nested classes)
        constants["Columns"] = {}
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
                    constants["Columns"][value] = f"Columns.{class_name}.{attr}"

        # Job statuses
        constants["JobStatus"] = {
            getattr(JobStatus, attr): f"JobStatus.{attr}"
            for attr in dir(JobStatus)
            if not attr.startswith("_")
        }

        # Order statuses
        constants["OrderStatus"] = {
            getattr(OrderStatus, attr): f"OrderStatus.{attr}"
            for attr in dir(OrderStatus)
            if not attr.startswith("_")
        }

        # Parse statuses
        constants["ParseStatus"] = {
            getattr(ParseStatus, attr): f"ParseStatus.{attr}"
            for attr in dir(ParseStatus)
            if not attr.startswith("_")
        }

        # Transaction types
        constants["TransactionType"] = {
            getattr(TransactionType, attr): f"TransactionType.{attr}"
            for attr in dir(TransactionType)
            if not attr.startswith("_")
        }

        # Signal types
        constants["SignalType"] = {
            getattr(SignalType, attr): f"SignalType.{attr}"
            for attr in dir(SignalType)
            if not attr.startswith("_")
        }

        # Action types
        constants["ActionType"] = {
            getattr(ActionType, attr): f"ActionType.{attr}"
            for attr in dir(ActionType)
            if not attr.startswith("_")
        }

        # Politician roles
        constants["PoliticianRole"] = {
            getattr(PoliticianRole, attr): f"PoliticianRole.{attr}"
            for attr in dir(PoliticianRole)
            if not attr.startswith("_")
        }

        # Environment keys
        constants["EnvKeys"] = {
            getattr(EnvKeys, attr): f"EnvKeys.{attr}"
            for attr in dir(EnvKeys)
            if not attr.startswith("_")
        }

        # Storage buckets
        constants["StorageBuckets"] = {
            getattr(StorageBuckets, attr): f"StorageBuckets.{attr}"
            for attr in dir(StorageBuckets)
            if not attr.startswith("_")
        }

        # Processing statuses
        constants["ProcessingStatus"] = {
            getattr(ProcessingStatus, attr): f"ProcessingStatus.{attr}"
            for attr in dir(ProcessingStatus)
            if not attr.startswith("_")
        }

        # Trading modes
        constants["TradingMode"] = {
            getattr(TradingMode, attr): f"TradingMode.{attr}"
            for attr in dir(TradingMode)
            if not attr.startswith("_")
        }

        # Data source types
        constants["DataSourceType"] = {
            getattr(DataSourceType, attr): f"DataSourceType.{attr}"
            for attr in dir(DataSourceType)
            if not attr.startswith("_")
        }

        # Source types (storage)
        constants["SourceTypes"] = {
            getattr(SourceTypes, attr): f"SourceTypes.{attr}"
            for attr in dir(SourceTypes)
            if not attr.startswith("_")
        }

        # API URLs
        constants["ApiUrls"] = {
            getattr(ApiUrls, attr): f"ApiUrls.{attr}"
            for attr in dir(ApiUrls)
            if not attr.startswith("_")
        }

        # Web URLs
        constants["WebUrls"] = {
            getattr(WebUrls, attr): f"WebUrls.{attr}"
            for attr in dir(WebUrls)
            if not attr.startswith("_")
        }

        # ConfigDefaults (only string-based defaults, not numeric)
        constants["ConfigDefaults"] = {
            value: f"ConfigDefaults.{attr}"
            for attr in dir(ConfigDefaults)
            if not attr.startswith("_")
            for value in [getattr(ConfigDefaults, attr)]
            if isinstance(value, str)
        }

        return constants

    def _check_string_literal(self, node: ast.Str, line: int, col: int):
        """Check if a string literal should use a constant."""
        value = node.s

        # Skip empty strings, single characters, and very short strings
        if not value or len(value) <= 2:
            return

        # Skip strings that look like messages, descriptions, or UI text
        # (they typically contain spaces or punctuation), unless they are in the exception list
        if (
            (" " in value or any(char in value for char in ".!?,;:"))
            and value not in self.EXCEPTION_STRINGS
        ):
            return

        # Skip URLs and file paths
        if value.startswith(("http://", "https://", "/", "./")):
            return

        # Check if this string matches a known constant
        for category, const_map in self.constant_values.items():
            if value in const_map:
                constant_name = const_map[value]
                self.violations.append(
                    (line, col, value, constant_name)
                )
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

    # Filename patterns to skip (for test files)
    skip_name_patterns = {
        "test_",
        "_test.py",
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

    # Check if filename matches skip patterns
    filename = filepath.name
    if any(pattern in filename for pattern in skip_name_patterns):
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
