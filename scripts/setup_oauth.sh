#!/bin/bash
# Quick OAuth Setup Script
# This script helps you set up Google OAuth in just a few steps

set -e

PROJECT_ID="directed-optics-477110-j0"
PROJECT_NUMBER="293495132387"

echo "============================================"
echo "Google OAuth Setup for Politician Trading Tracker"
echo "============================================"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo ""

# Step 1: Open OAuth consent screen
echo "📋 Step 1: Configure OAuth Consent Screen"
echo ""
echo "Opening Google Cloud Console OAuth consent screen..."
echo ""

CONSENT_URL="https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"

if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$CONSENT_URL"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$CONSENT_URL"
else
    echo "Please open this URL in your browser:"
    echo "$CONSENT_URL"
fi

echo ""
echo "In the browser:"
echo "  1. Choose 'External' user type"
echo "  2. Click 'CREATE'"
echo "  3. Fill in:"
echo "     - App name: Politician Trading Tracker"
echo "     - User support email: (your email)"
echo "     - Developer contact: (your email)"
echo "  4. Click 'SAVE AND CONTINUE' (3 times to skip optional sections)"
echo ""
read -p "Press ENTER when you've completed the consent screen setup..."

# Step 2: Create OAuth client
echo ""
echo "🔑 Step 2: Create OAuth Client"
echo ""
echo "Opening OAuth client creation page..."
echo ""

CREDENTIALS_URL="https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"

if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$CREDENTIALS_URL"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$CREDENTIALS_URL"
else
    echo "Please open this URL in your browser:"
    echo "$CREDENTIALS_URL"
fi

echo ""
echo "In the browser:"
echo "  1. Click '+ CREATE CREDENTIALS' at the top"
echo "  2. Select 'OAuth client ID'"
echo "  3. Choose 'Web application'"
echo "  4. Enter:"
echo "     - Name: Politician Trading Tracker"
echo "     - Authorized JavaScript origins:"
echo "         http://localhost:8501"
echo "         https://politician-trading-tracker.streamlit.app"
echo "     - Authorized redirect URIs:"
echo "         http://localhost:8501/oauth2callback"
echo "         https://politician-trading-tracker.streamlit.app/oauth2callback"
echo "  5. Click 'CREATE'"
echo "  6. Copy your Client ID and Client Secret"
echo ""
read -p "Press ENTER when you have your Client ID and Client Secret ready..."

# Step 3: Generate secrets file
echo ""
echo "📝 Step 3: Generate Secrets Configuration"
echo ""

# Generate cookie secret
COOKIE_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

echo "Please enter your OAuth Client ID:"
read -r CLIENT_ID

echo "Please enter your OAuth Client Secret:"
read -r CLIENT_SECRET

# Create LOCAL secrets file
cat > .streamlit/secrets.toml <<EOF
# Google OAuth Configuration (LOCAL)
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "$COOKIE_SECRET"
client_id = "$CLIENT_ID"
client_secret = "$CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF

echo ""
echo "✅ Success! OAuth configuration saved to .streamlit/secrets.toml"
echo ""

# Create STREAMLIT CLOUD secrets file
cat > .streamlit/secrets.toml.cloud <<EOF
# Google OAuth Configuration (STREAMLIT CLOUD)
# Copy this entire content to Streamlit Cloud App Settings > Secrets
[auth]
redirect_uri = "https://politician-trading-tracker.streamlit.app/oauth2callback"
cookie_secret = "$COOKIE_SECRET"
client_id = "$CLIENT_ID"
client_secret = "$CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF

echo "✅ Streamlit Cloud configuration saved to .streamlit/secrets.toml.cloud"
echo ""
echo "🚀 To test locally:"
echo "   streamlit run app.py"
echo ""
echo "☁️  For Streamlit Cloud deployment:"
echo "   1. Go to: https://share.streamlit.io/"
echo "   2. Find your app: politician-trading-tracker"
echo "   3. Click Settings > Secrets"
echo "   4. Copy the entire contents of .streamlit/secrets.toml.cloud"
echo "   5. Paste into the secrets editor"
echo "   6. Click 'Save'"
echo ""
echo "🔗 Your app will be available at:"
echo "   https://politician-trading-tracker.streamlit.app"
echo ""
echo "============================================"
