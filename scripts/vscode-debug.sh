#!/bin/bash
# Quick launcher script for VS Code debugging
# Usage: ./scripts/vscode-debug.sh [run|debug|test]

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$REPO_ROOT/.venv/bin/activate"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -f "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi

# Activate virtual environment
source "$VENV_PATH"

# Default command
COMMAND="${1:-run}"

case "$COMMAND" in
    run)
        echo -e "${GREEN}Starting Streamlit app...${NC}"
        echo "App will be available at http://localhost:8501"
        streamlit run app.py
        ;;
    debug)
        echo -e "${GREEN}Starting Streamlit app in debug mode...${NC}"
        streamlit run --logger.level=debug app.py
        ;;
    test)
        echo -e "${GREEN}Running pytest suite...${NC}"
        python -m pytest tests/ -v
        ;;
    setup)
        echo -e "${GREEN}Running database setup...${NC}"
        python scripts/init_default_jobs.py
        ;;
    lint)
        echo -e "${GREEN}Running pylint...${NC}"
        pylint src/ --exit-zero
        ;;
    format)
        echo -e "${GREEN}Formatting code with black...${NC}"
        black src/ --line-length 100
        ;;
    verify)
        echo -e "${GREEN}Verifying debug setup...${NC}"
        python verify_debug_setup.py
        ;;
    *)
        echo -e "${YELLOW}Available commands:${NC}"
        echo "  run       - Start Streamlit app (default)"
        echo "  debug     - Start Streamlit with debug logging"
        echo "  test      - Run pytest suite"
        echo "  setup     - Initialize database"
        echo "  lint      - Run code quality checks"
        echo "  format    - Format code with black"
        echo "  verify    - Verify debug setup"
        exit 1
        ;;
esac
