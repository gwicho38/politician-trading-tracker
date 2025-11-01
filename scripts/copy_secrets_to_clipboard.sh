#!/bin/bash
# Copy Streamlit secrets to clipboard for easy pasting to Streamlit Cloud

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_FILE="$PROJECT_ROOT/.streamlit/secrets.toml"

echo "============================================================"
echo "Copy Secrets to Clipboard"
echo "============================================================"
echo ""

# Generate secrets.toml if it doesn't exist or is outdated
if [ ! -f "$SECRETS_FILE" ] || [ "$PROJECT_ROOT/.env" -nt "$SECRETS_FILE" ]; then
    echo "📝 Generating secrets.toml from .env..."
    python3 "$SCRIPT_DIR/sync_secrets_to_streamlit.py" > /dev/null
fi

if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ Error: secrets.toml file not found"
    exit 1
fi

# Copy to clipboard
if command -v pbcopy &> /dev/null; then
    # macOS
    cat "$SECRETS_FILE" | pbcopy
    echo "✅ Secrets copied to clipboard!"
elif command -v xclip &> /dev/null; then
    # Linux with xclip
    cat "$SECRETS_FILE" | xclip -selection clipboard
    echo "✅ Secrets copied to clipboard!"
elif command -v xsel &> /dev/null; then
    # Linux with xsel
    cat "$SECRETS_FILE" | xsel --clipboard
    echo "✅ Secrets copied to clipboard!"
else
    echo "⚠️  Clipboard tool not found. Displaying secrets below:"
    echo ""
    cat "$SECRETS_FILE"
    echo ""
    echo "📋 Please copy the above content manually"
fi

echo ""
echo "📋 Next steps:"
echo "   1. Go to https://share.streamlit.io/"
echo "   2. Select your app: politician-trading-tracker"
echo "   3. Click '⋮' menu → 'Settings'"
echo "   4. Go to 'Secrets' tab"
echo "   5. Paste the secrets (Cmd+V / Ctrl+V)"
echo "   6. Click 'Save'"
echo "   7. App will automatically redeploy"
echo ""
echo "🔒 Security: Secrets are gitignored and never committed"
echo ""
