#!/usr/bin/env python3
"""
Check Production Database Schema

This script queries the production Supabase database to see the actual
schema of the trading_signals table, including:
- All column names
- Data types
- NOT NULL constraints
- Default values

This helps identify any schema mismatches between production and local.

Usage:
    python scripts/check_production_schema.py
"""

import os
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig


def check_table_schema(db: SupabaseClient, table_name: str = "trading_signals"):
    """
    Query the information_schema to get complete table structure.

    Args:
        db: SupabaseClient instance
        table_name: Name of the table to inspect
    """
    print(f"\n{'='*80}")
    print(f"Production Schema for: {table_name}")
    print(f"{'='*80}\n")

    # Query to get column information
    query = f"""
    SELECT
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = '{table_name}'
    ORDER BY ordinal_position;
    """

    try:
        # Execute raw SQL query via Supabase RPC or direct query
        # Note: This requires the query to be executed via the SQL editor
        # or we need to use a different approach

        # Alternative: Try to describe table by attempting inserts with minimal data
        print("Attempting to get schema information...\n")
        print("Note: Supabase client doesn't directly support information_schema queries.")
        print("Instead, we'll try to inspect the table by other means.\n")

        # Try to get a single row to see what columns exist
        response = db.client.table(table_name).select("*").limit(1).execute()

        if response.data and len(response.data) > 0:
            print("Sample row found. Columns in response:")
            print("-" * 80)
            for column_name in response.data[0].keys():
                print(f"  • {column_name}")
            print()

            print("Column values from sample row:")
            print("-" * 80)
            for column_name, value in response.data[0].items():
                value_type = type(value).__name__
                value_repr = repr(value) if value is not None else "NULL"
                if len(value_repr) > 50:
                    value_repr = value_repr[:47] + "..."
                print(f"  {column_name:30} = {value_repr:20} (type: {value_type})")
        else:
            print("No rows found in table. Will attempt empty insert to discover required columns...")
            try:
                # This will fail but the error will tell us what's required
                db.client.table(table_name).insert({}).execute()
            except Exception as e:
                print(f"\nError from attempted insert (this is expected):")
                print(f"  {str(e)}")
                print("\nThis error message should reveal required columns.")

    except Exception as e:
        print(f"Error querying schema: {e}")
        return


def check_all_trading_tables(db: SupabaseClient):
    """Check schema for all trading-related tables."""
    tables = [
        "trading_signals",
        "trading_orders",
        "portfolios",
        "positions"
    ]

    for table in tables:
        try:
            check_table_schema(db, table)
        except Exception as e:
            print(f"\nError checking {table}: {e}\n")


def main():
    """Main function to check production schema."""
    print("\n" + "="*80)
    print("PRODUCTION DATABASE SCHEMA CHECKER")
    print("="*80)

    try:
        # Load configuration from environment
        config = SupabaseConfig.from_env()

        print(f"\nConnecting to Supabase:")
        print(f"  URL: {config.url}")
        print(f"  Key: {config.key[:20]}..." if config.key else "  Key: Not set")

        # Initialize database client
        db = SupabaseClient(config)

        # Check schema
        check_all_trading_tables(db)

        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        print("""
To get the complete schema with NOT NULL constraints, you should:

1. Go to Supabase Dashboard → SQL Editor
2. Run this query:

   SELECT
       column_name,
       data_type,
       is_nullable,
       column_default
   FROM information_schema.columns
   WHERE table_name = 'trading_signals'
   ORDER BY ordinal_position;

3. Look for columns with is_nullable = 'NO' - these are required fields
4. Compare with what the application is sending in the data dictionary

Alternative: Check the Supabase Table Editor UI to see all columns and their constraints.
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure your .env file has:")
        print("  SUPABASE_URL=your-project-url")
        print("  SUPABASE_KEY=your-anon-key")
        sys.exit(1)


if __name__ == "__main__":
    main()
