#!/usr/bin/env python3
"""
Repository analyzer CLI entry point.

This module wraps the analyze_repo.py script for use as an installed command.
Run with: ptt-analyze [OPTIONS]

See scripts/analyze_repo.py for full documentation.
"""

import sys
from pathlib import Path


def main() -> None:
    """Entry point for ptt-analyze command."""
    # Import and run the analyzer script
    scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
    analyze_script = scripts_dir / "analyze_repo.py"

    if analyze_script.exists():
        # Execute the script
        import runpy
        sys.argv[0] = str(analyze_script)
        runpy.run_path(str(analyze_script), run_name="__main__")
    else:
        # Fallback: run inline minimal version
        print("Error: analyze_repo.py not found at", analyze_script)
        print("Run directly with: python scripts/analyze_repo.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
