#!/bin/bash
# Backend Monitoring Dashboard
# Shows logs from all backend sources

echo "🔍 Backend Monitoring Dashboard"
echo "================================"
echo ""

# 1. Python Backend Logs (Real-time)
echo "🐍 Python Backend Logs (Real-time):"
echo "tail -f logs/latest.log"
echo "---"
tail -5 logs/latest.log | jq -r '.message' 2>/dev/null || tail -5 logs/latest.log
echo ""

# 2. Action Logs from Database
echo "📊 Recent Action Logs:"
echo "python -c \"from politician_trading.utils.action_logger import get_action_logger; logger = get_action_logger(); [print(f'{a[\"created_at\"][:19]} | {a[\"action_type\"]} | {a[\"action_name\"] or \"N/A\"} | {a[\"status\"]}') for a in logger.get_recent_actions(limit=5)]\""
echo "---"
python -c "
from politician_trading.utils.action_logger import get_action_logger
logger = get_action_logger()
actions = logger.get_recent_actions(limit=5)
for action in actions:
    print(f'{action[\"created_at\"][:19]} | {action[\"action_type\"]} | {action[\"action_name\"] or \"N/A\"} | {action[\"status\"]}')
" 2>/dev/null
echo ""

# 3. Supabase Edge Functions Status
echo "⚡ Supabase Edge Functions Status:"
echo "Check: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/functions"
echo "---"
curl -s "https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/trading-signals/get-signal-stats" \
  -H "Authorization: Bearer REDACTED" \
  | jq '.success' 2>/dev/null && echo "✅ Trading Signals API: OK" || echo "❌ Trading Signals API: ERROR"
echo ""

# 4. Database Connection Status
echo "🗄️ Database Status:"
echo "python -c \"from politician_trading.database.database import SupabaseClient; client = SupabaseClient(); print('✅ Database: Connected' if client.client else '❌ Database: Failed')\""
echo "---"
python -c "
from politician_trading.database.database import SupabaseClient
try:
    client = SupabaseClient()
    print('✅ Database: Connected')
except Exception as e:
    print(f'❌ Database: {e}')
" 2>/dev/null
echo ""

# 5. Log File Sizes
echo "📁 Log Files:"
echo "---"
ls -lh logs/ | tail -5
echo ""

echo "🔧 Quick Commands:"
echo "• View real-time logs: tail -f logs/latest.log"
echo "• Check action logs: make db-logs"
echo "• Supabase dashboard: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/functions"
echo "• Clear old logs: find logs/ -name '*.log' -mtime +30 -delete"