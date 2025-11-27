#!/usr/bin/env python3
"""
Test configuration for Politician Trading Tracker
"""

import os
import sys

def test_config():
    """Test if environment variables are properly configured"""

    print("=" * 70)
    print("POLITICIAN TRADING TRACKER - CONFIGURATION TEST")
    print("=" * 70)
    print()

    # Test Supabase
    print("📊 SUPABASE DATABASE")
    print("-" * 70)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon = os.getenv("SUPABASE_ANON_KEY")
    supabase_service = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if supabase_url:
        print(f"✅ SUPABASE_URL: {supabase_url}")
    else:
        print("❌ SUPABASE_URL: Not set")

    if supabase_anon:
        print(f"✅ SUPABASE_ANON_KEY: {supabase_anon[:20]}...")
    else:
        print("❌ SUPABASE_ANON_KEY: Not set")

    if supabase_service:
        print(f"✅ SUPABASE_SERVICE_KEY: {supabase_service[:20]}...")
    else:
        print("⚠️  SUPABASE_SERVICE_KEY: Not set (optional)")

    # Test Supabase connection
    if supabase_url and supabase_anon:
        try:
            from politician_trading.database.database import SupabaseClient
            from politician_trading.config import SupabaseConfig

            config = SupabaseConfig.from_env()
            db = SupabaseClient(config)

            # Test query
            response = db.client.table("politicians").select("id", count="exact").limit(1).execute()
            print(f"✅ Database connection successful!")
            print(f"   Politicians table accessible: {response.count if response.count else 0} records")
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")

    print()

    # Test Alpaca
    print("💼 ALPACA TRADING API")
    print("-" * 70)

    alpaca_key = os.getenv("ALPACA_API_KEY")
    alpaca_secret = os.getenv("ALPACA_SECRET_KEY")
    alpaca_paper = os.getenv("ALPACA_PAPER", "true")

    if alpaca_key:
        print(f"✅ ALPACA_API_KEY: {alpaca_key[:10]}...")
    else:
        print("⚠️  ALPACA_API_KEY: Not set (trading disabled)")

    if alpaca_secret:
        print(f"✅ ALPACA_SECRET_KEY: {alpaca_secret[:10]}...")
    else:
        print("⚠️  ALPACA_SECRET_KEY: Not set (trading disabled)")

    print(f"ℹ️  Trading Mode: {'Paper Trading' if alpaca_paper == 'true' else 'LIVE TRADING'}")

    # Test Alpaca connection
    if alpaca_key and alpaca_secret:
        try:
            from politician_trading.trading.alpaca_client import AlpacaTradingClient

            client = AlpacaTradingClient(
                api_key=alpaca_key,
                secret_key=alpaca_secret,
                paper=(alpaca_paper == "true")
            )

            account = client.get_account()
            print(f"✅ Alpaca connection successful!")
            print(f"   Account Status: {account['status']}")
            print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
            print(f"   Cash: ${account['cash']:,.2f}")
        except Exception as e:
            print(f"❌ Alpaca connection failed: {str(e)}")

    print()

    # Other APIs
    print("🔌 OPTIONAL APIS")
    print("-" * 70)

    uk_api = os.getenv("UK_COMPANIES_HOUSE_API_KEY")
    if uk_api:
        print(f"✅ UK_COMPANIES_HOUSE_API_KEY: {uk_api[:10]}...")
    else:
        print("ℹ️  UK_COMPANIES_HOUSE_API_KEY: Not set (optional)")

    quiver_api = os.getenv("QUIVER_API_KEY")
    if quiver_api:
        print(f"✅ QUIVER_API_KEY: {quiver_api[:10]}...")
    else:
        print("ℹ️  QUIVER_API_KEY: Not set (optional)")

    print()
    print("=" * 70)
    print("CONFIGURATION TEST COMPLETE")
    print("=" * 70)
    print()

    # Summary
    required_vars = [supabase_url, supabase_anon]
    if all(required_vars):
        print("✅ All required configuration is set!")
        print()
        print("🚀 Ready to run:")
        print("   streamlit run app.py")
        print()
        if alpaca_key and alpaca_secret:
            print("💼 Trading enabled in PAPER mode (safe!)")
        else:
            print("ℹ️  Trading disabled (set ALPACA keys to enable)")
        return 0
    else:
        print("❌ Missing required configuration!")
        print()
        print("Please set the following environment variables:")
        if not supabase_url:
            print("   - SUPABASE_URL")
        if not supabase_anon:
            print("   - SUPABASE_ANON_KEY")
        return 1

if __name__ == "__main__":
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded .env file")
        print()
    except:
        print("ℹ️  No .env file found (using system environment variables)")
        print()

    sys.exit(test_config())
