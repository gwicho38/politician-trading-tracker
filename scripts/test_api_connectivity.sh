#!/bin/bash
# Test React App API Connectivity
# Verifies that the React app can successfully call trading signals API

echo "🧪 Testing React App API Connectivity"
echo "====================================="

# Check environment variables
echo "📋 Environment Check:"
echo "VITE_SUPABASE_URL: ${VITE_SUPABASE_URL:-'NOT SET'}"
echo "VITE_SUPABASE_ANON_KEY: ${VITE_SUPABASE_ANON_KEY:+'SET (hidden)' :-'NOT SET'}"

# Test the API endpoint directly
echo ""
echo "🔍 Testing Trading Signals API:"
API_URL="https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/trading-signals/get-signals?limit=1"
echo "URL: $API_URL"

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$API_URL" \
  -H "Authorization: Bearer REDACTED")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "Status: $HTTP_STATUS"
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ API call successful!"
    SIGNAL_COUNT=$(echo "$BODY" | jq '.signals | length' 2>/dev/null || echo "unknown")
    echo "📊 Signals returned: $SIGNAL_COUNT"
else
    echo "❌ API call failed!"
    echo "Response: $BODY"
fi

# Check if React app is running
echo ""
echo "🌐 React App Status:"
if curl -s --max-time 5 http://localhost:9090 > /dev/null 2>&1; then
    echo "✅ React app is running on http://localhost:9090"
    echo "   Visit: http://localhost:9090/trading-signals"
else
    echo "❌ React app is not responding on http://localhost:9090"
    echo "   Make sure to run: make dev"
fi

echo ""
echo "🔧 Troubleshooting:"
echo "• If API fails: Check Supabase Edge Function logs"
echo "• If React fails: Clear browser cache and restart dev server"
echo "• If env vars wrong: Run ./scripts/fix_react_env.sh"