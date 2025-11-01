#!/bin/bash
# Test Scheduled Jobs
# Helper script to test scheduled jobs before adding to cron

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=================================================="
echo "Testing Politician Trading Tracker Scheduled Jobs"
echo "=================================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Check environment
echo "Checking environment variables..."
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found"
    exit 1
fi

# Load .env and check key variables
if ! grep -q "SUPABASE_URL" .env; then
    echo "❌ ERROR: SUPABASE_URL not found in .env"
    exit 1
fi

if ! grep -q "SUPABASE_ANON_KEY" .env; then
    echo "❌ ERROR: SUPABASE_ANON_KEY not found in .env"
    exit 1
fi

echo "✅ Environment variables configured"
echo ""

# Test 1: Data Collection
echo "=================================================="
echo "Test 1: Data Collection Script"
echo "=================================================="
echo ""

echo "Running: python3 scripts/scheduled_data_collection.py"
echo ""

if python3 scripts/scheduled_data_collection.py; then
    echo ""
    echo "✅ Data collection script completed successfully"
else
    EXIT_CODE=$?
    echo ""
    echo "❌ Data collection script failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
fi

echo ""
echo "Recent data collection logs:"
cat logs/latest.log | jq 'select(.logger == "politician_trading:scheduled_collection")' | tail -5
echo ""

# Test 2: Ticker Backfill
echo "=================================================="
echo "Test 2: Ticker Backfill Script"
echo "=================================================="
echo ""

echo "Running: python3 scripts/backfill_tickers.py"
echo ""

if python3 scripts/backfill_tickers.py; then
    echo ""
    echo "✅ Ticker backfill script completed successfully"
else
    EXIT_CODE=$?
    echo ""
    echo "❌ Ticker backfill script failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
fi

echo ""
echo "Recent backfill logs:"
cat logs/latest.log | jq 'select(.logger == "politician_trading:scheduled_backfill")' | tail -5
echo ""

# Summary
echo "=================================================="
echo "All Tests Passed!"
echo "=================================================="
echo ""
echo "The scheduled jobs are working correctly and can be added to cron."
echo ""
echo "Next steps:"
echo "  1. Review docs/scheduled-jobs.md for cron configuration"
echo "  2. Choose your schedule (daily, weekly, etc.)"
echo "  3. Add jobs to crontab: crontab -e"
echo ""
echo "Suggested cron configuration:"
echo "  # Daily data collection at 2 AM"
echo "  0 2 * * * cd $PROJECT_ROOT && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1"
echo ""
echo "  # Weekly ticker backfill on Sunday at 3 AM"
echo "  0 3 * * 0 cd $PROJECT_ROOT && /usr/bin/python3 scripts/backfill_tickers.py >> logs/cron.log 2>&1"
echo ""
