#!/bin/bash
# Sync local .streamlit/secrets.toml to Streamlit Cloud
#
# This script uses the official Streamlit CLI to push secrets to Streamlit Cloud.
#
# Prerequisites:
#   1. Install Streamlit CLI (if not already installed):
#      pip install streamlit
#
#   2. Login to Streamlit Cloud:
#      streamlit login
#
# Usage:
#   ./scripts/sync_secrets_to_streamlit.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "Sync Local Secrets to Streamlit Cloud"
echo "======================================================================"
echo ""

# Check if secrets.toml exists
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo -e "${RED}❌ Error: .streamlit/secrets.toml not found${NC}"
    echo "   Make sure you're running this from the project root directory"
    exit 1
fi

echo -e "${BLUE}📂 Found local secrets file: .streamlit/secrets.toml${NC}"
echo ""

# Check if streamlit CLI is installed
if ! command -v streamlit &> /dev/null; then
    echo -e "${YELLOW}⚠️  Streamlit CLI not found${NC}"
    echo ""
    echo "Installing Streamlit CLI..."
    pip install streamlit
    echo ""
fi

# Check if user is logged in (try to list apps)
echo -e "${BLUE}🔑 Checking Streamlit Cloud authentication...${NC}"
if streamlit list &> /dev/null; then
    echo -e "${GREEN}✓ Already logged in to Streamlit Cloud${NC}"
else
    echo -e "${YELLOW}⚠️  Not logged in to Streamlit Cloud${NC}"
    echo ""
    echo "Please login with:"
    echo "  streamlit login"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo ""

# Get app URL/name
echo "Enter your Streamlit Cloud app name/URL:"
echo "  Example: politician-trading-tracker"
echo "  Or full URL: https://politician-trading-tracker.streamlit.app"
echo ""
read -p "App name: " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo -e "${RED}❌ Error: App name is required${NC}"
    exit 1
fi

# Remove https:// and .streamlit.app if provided
APP_NAME=$(echo "$APP_NAME" | sed 's|https://||' | sed 's|.streamlit.app||')

echo ""
echo "======================================================================"
echo -e "${YELLOW}⚠️  WARNING: This will REPLACE all secrets in Streamlit Cloud${NC}"
echo "======================================================================"
echo ""
echo "App: $APP_NAME"
echo "Source: .streamlit/secrets.toml"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}❌ Cancelled by user${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}📤 Pushing secrets to Streamlit Cloud...${NC}"
echo ""

# Push secrets using Streamlit CLI
# Note: The exact command may vary based on Streamlit CLI version
# Check with: streamlit --help

if streamlit secrets push "$APP_NAME" .streamlit/secrets.toml; then
    echo ""
    echo "======================================================================"
    echo -e "${GREEN}✅ Successfully pushed secrets to Streamlit Cloud!${NC}"
    echo "======================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Go to https://share.streamlit.io/"
    echo "  2. Find your app: $APP_NAME"
    echo "  3. Restart the app to apply new secrets"
    echo ""
else
    echo ""
    echo "======================================================================"
    echo -e "${RED}❌ Failed to push secrets${NC}"
    echo "======================================================================"
    echo ""
    echo "Alternative method:"
    echo ""
    echo "1. Go to: https://share.streamlit.io/"
    echo "2. Open your app settings"
    echo "3. Navigate to the 'Secrets' section"
    echo "4. Copy the contents of .streamlit/secrets.toml"
    echo "5. Paste into the secrets editor"
    echo "6. Save and restart your app"
    echo ""
    exit 1
fi
