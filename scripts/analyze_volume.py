#!/usr/bin/env python3
"""Analyze trade volume spike."""
import os
from supabase import create_client

SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjgwMjI0NCwiZXhwIjoyMDcyMzc4MjQ0fQ.4364sQbTJQd4IcxEQG6mPiOUw1iJ2bdKfV6W4oRqHvs"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== Top 20 Highest Amount Trades ===")
result = supabase.table('trading_disclosures').select(
    'id,politician_id,asset_ticker,asset_name,amount_range_min,amount_range_max,amount_exact,transaction_date,transaction_type'
).order('amount_range_max', desc=True, nullsfirst=False).limit(20).execute()

for d in result.data:
    max_amt = d.get('amount_range_max') or 0
    min_amt = d.get('amount_range_min') or 0
    exact = d.get('amount_exact') or 0
    ticker = d.get('asset_ticker') or 'N/A'
    date = d.get('transaction_date') or 'N/A'
    tx_type = d.get('transaction_type') or 'N/A'
    print(f"  {date} | {ticker:10} | max: ${max_amt:>15,.0f} | min: ${min_amt:>15,.0f} | {tx_type}")

print("\n=== Trades in Aug-Sep 2025 with amount > $1B ===")
result2 = supabase.table('trading_disclosures').select(
    'id,politician_id,asset_ticker,asset_name,amount_range_min,amount_range_max,transaction_date,transaction_type'
).gte('transaction_date', '2025-08-01').lte('transaction_date', '2025-09-30').gt('amount_range_max', 1000000000).execute()

print(f"Found {len(result2.data)} trades > $1B in Aug-Sep 2025")
for d in result2.data[:10]:
    max_amt = d.get('amount_range_max') or 0
    ticker = d.get('asset_ticker') or 'N/A'
    name = d.get('asset_name') or 'N/A'
    date = d.get('transaction_date') or 'N/A'
    print(f"  {date} | {ticker:10} | ${max_amt:>15,.0f} | {name[:40]}")

print("\n=== Volume by Month (using amount_range_max) ===")
# Get all trades and aggregate by month
all_trades = supabase.table('trading_disclosures').select(
    'transaction_date,amount_range_max'
).gte('transaction_date', '2025-01-01').execute()

from collections import defaultdict
monthly_volume = defaultdict(float)
monthly_count = defaultdict(int)

for d in all_trades.data:
    date = d.get('transaction_date')
    amt = d.get('amount_range_max') or 0
    if date:
        month = date[:7]  # YYYY-MM
        monthly_volume[month] += amt
        monthly_count[month] += 1

for month in sorted(monthly_volume.keys()):
    vol = monthly_volume[month]
    count = monthly_count[month]
    print(f"  {month}: ${vol:>15,.0f} ({count} trades, avg: ${vol/count if count > 0 else 0:,.0f})")
