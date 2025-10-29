#!/bin/bash
#
# Setup Politician Trading Tracker with LSH Framework
# This script sets up the environment using lsh-framework for secrets management
#

set -e

echo "=================================================="
echo "Politician Trading Tracker - LSH Setup"
echo "=================================================="
echo ""

# Check if lsh is installed
if ! command -v lsh &> /dev/null; then
    echo "❌ lsh-framework not found"
    echo ""
    echo "Installing lsh-framework..."
    npm install -g lsh-framework
    echo "✅ lsh-framework installed"
    echo ""
fi

# Check lsh version
LSH_VERSION=$(lsh --version 2>/dev/null | head -1)
echo "✅ Using lsh-framework: $LSH_VERSION"
echo ""

# Initialize lsh if needed
if [ ! -f ~/.lsh/config.json ]; then
    echo "⚙️  Initializing lsh configuration..."
    lsh config --init
    echo ""
fi

# Push secrets to lsh
echo "📤 Pushing secrets to lsh-framework..."
echo ""
echo "This will encrypt and store your secrets in Supabase."
echo "You can then pull them on any machine with: lsh secrets pull --environment politician-trading"
echo ""

lsh secrets push --environment politician-trading --file .env.politician-trading

echo ""
echo "✅ Secrets pushed successfully!"
echo ""

# Pull secrets to create .env
echo "📥 Pulling secrets to create .env file..."
lsh secrets pull --environment politician-trading --output .env

echo ""
echo "✅ .env file created from lsh secrets"
echo ""

# Test configuration
echo "🧪 Testing configuration..."
python test_config.py

echo ""
echo "=================================================="
echo "Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Your secrets are now managed by lsh-framework and stored encrypted in Supabase."
echo ""
echo "Next steps:"
echo "  1. Run: streamlit run app.py"
echo "  2. On other machines: lsh secrets pull --environment politician-trading"
echo "  3. Deploy to Streamlit Cloud with the secrets"
echo ""
echo "For more information, see: LSH_SECRETS_GUIDE.md"
echo ""
