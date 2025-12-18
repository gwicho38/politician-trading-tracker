#!/bin/bash
# Fix React App Environment Variables
# Sets up correct Supabase URL and WalletConnect configuration

echo "🔧 Fixing React App Environment Configuration"
echo "=============================================="

# Navigate to React app
cd submodules/capital-trades

# Check current .env files
echo "📋 Current environment files:"
ls -la .env*

# Create proper .env.production if it doesn't exist or is wrong
echo ""
echo "🔄 Setting up .env.production..."

cat > .env.production << 'EOF'
# Supabase Configuration
VITE_SUPABASE_URL=https://uljsqvwkomdrlnofmlad.supabase.co
VITE_SUPABASE_ANON_KEY=REDACTED

# Application Configuration
VITE_APP_TITLE="Politician Trading Tracker"
VITE_APP_VERSION="1.0.0"
VITE_APP_ENVIRONMENT="production"

# WalletConnect Configuration (Demo - Replace with real project ID)
VITE_WALLETCONNECT_PROJECT_ID=demo-project-id

# Feature Flags
VITE_ENABLE_LIVE_TRADING=false
VITE_ENABLE_DEBUG_MODE=false
EOF

echo "✅ Created .env.production with correct Supabase URL"

# Check if there's a .env.local that might be overriding
if [ -f ".env.local" ]; then
    echo ""
    echo "⚠️  Found .env.local - this might override .env.production"
    echo "   If you're in development, rename it or check its contents"
fi

# Test the configuration
echo ""
echo "🧪 Testing configuration..."
echo "VITE_SUPABASE_URL should be: https://uljsqvwkomdrlnofmlad.supabase.co"
grep "VITE_SUPABASE_URL" .env.production

echo ""
echo "🔄 Restarting development server..."
echo "If running, stop it with Ctrl+C and run: make dev"

echo ""
echo "📝 Next steps:"
echo "1. Stop any running dev server (Ctrl+C)"
echo "2. Run: make dev"
echo "3. Check browser console - Supabase errors should be gone"
echo "4. For production wallet features, get real WalletConnect project ID"

echo ""
echo "🎯 The main Supabase 404 error should now be fixed!"