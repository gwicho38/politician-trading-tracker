#!/bin/bash
# Copy .streamlit/secrets.toml contents to clipboard for Streamlit Cloud
#
# This script copies your local secrets to clipboard so you can easily
# paste them into Streamlit Cloud's web interface.
#
# Usage:
#   ./scripts/copy_secrets_for_streamlit.sh
#
# Then:
#   1. Go to: https://share.streamlit.io/
#   2. Open your app settings
#   3. Navigate to "Secrets" section
#   4. Paste (Cmd+V) into the secrets editor
#   5. Save

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "Copy Secrets for Streamlit Cloud"
echo "======================================================================"
echo ""

# Check if secrets.toml exists
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo -e "${RED}❌ Error: .streamlit/secrets.toml not found${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Copying secrets to clipboard...${NC}"
echo ""

# Copy to clipboard (works on macOS)
if command -v pbcopy &> /dev/null; then
    cat .streamlit/secrets.toml | pbcopy
    echo -e "${GREEN}✅ Secrets copied to clipboard!${NC}"
elif command -v xclip &> /dev/null; then
    # Linux with xclip
    cat .streamlit/secrets.toml | xclip -selection clipboard
    echo -e "${GREEN}✅ Secrets copied to clipboard!${NC}"
elif command -v xsel &> /dev/null; then
    # Linux with xsel
    cat .streamlit/secrets.toml | xsel --clipboard
    echo -e "${GREEN}✅ Secrets copied to clipboard!${NC}"
else
    echo -e "${YELLOW}⚠️  Clipboard tool not found${NC}"
    echo ""
    echo "Contents of .streamlit/secrets.toml:"
    echo "======================================================================"
    cat .streamlit/secrets.toml
    echo "======================================================================"
    echo ""
    echo "Please copy the above manually"
    exit 0
fi

echo ""
echo "======================================================================"
echo "Next Steps:"
echo "======================================================================"
echo ""
echo "1. Go to: https://share.streamlit.io/"
echo "2. Find your app in the list"
echo "3. Click the ⚙️  (Settings) button"
echo "4. Navigate to the 'Secrets' tab"
echo "5. Clear existing secrets (if any)"
echo "6. Paste (Cmd+V or Ctrl+V) the clipboard contents"
echo "7. Click 'Save'"
echo "8. Restart your app to apply changes"
echo ""
echo -e "${BLUE}💡 Tip: The secrets are in your clipboard now - just paste!${NC}"
echo ""
