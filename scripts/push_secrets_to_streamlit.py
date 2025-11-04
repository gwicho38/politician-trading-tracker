#!/usr/bin/env python3
"""
Push local .streamlit/secrets.toml to Streamlit Cloud.

Usage:
    python scripts/push_secrets_to_streamlit.py

Prerequisites:
    1. Install streamlit-management SDK:
       pip install streamlit-management

    2. Get your Streamlit Cloud API token:
       https://share.streamlit.io/settings/tokens

    3. Set environment variable:
       export STREAMLIT_API_TOKEN="your-token-here"

       Or store it securely with lsh:
       lsh secrets set STREAMLIT_API_TOKEN "your-token-here"

Notes:
    - This will completely replace all secrets in your Streamlit Cloud app
    - Make sure your local secrets.toml is up to date before running
    - The script will show you what will be pushed and ask for confirmation
"""

import os
import sys
from pathlib import Path
import toml
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_local_secrets():
    """Load secrets from .streamlit/secrets.toml"""
    secrets_path = project_root / ".streamlit" / "secrets.toml"

    if not secrets_path.exists():
        print(f"❌ Error: secrets.toml not found at {secrets_path}")
        sys.exit(1)

    with open(secrets_path, 'r') as f:
        secrets = toml.load(f)

    return secrets


def convert_to_streamlit_format(secrets):
    """
    Convert nested TOML structure to flat format for Streamlit Cloud.

    Streamlit Cloud expects flat key-value pairs like:
    auth_enabled = true
    auth_redirect_uri = "..."

    But we can also preserve sections for the [connections.supabase] format.
    """
    # For Streamlit Cloud, we need to preserve the exact TOML format
    # So we'll just return it as a string
    return toml.dumps(secrets)


def push_secrets_via_api(app_url, secrets_str):
    """
    Push secrets to Streamlit Cloud using the management API.

    Args:
        app_url: Your app URL (e.g., "politician-trading-tracker")
        secrets_str: TOML formatted string of secrets
    """
    try:
        import requests
    except ImportError:
        print("❌ Error: requests package not found")
        print("   Install it with: pip install requests")
        sys.exit(1)

    # Get API token from environment
    api_token = os.getenv('STREAMLIT_API_TOKEN')

    if not api_token:
        print("❌ Error: STREAMLIT_API_TOKEN not found in environment")
        print()
        print("Get your token from: https://share.streamlit.io/settings/tokens")
        print()
        print("Then set it with:")
        print("  export STREAMLIT_API_TOKEN='your-token-here'")
        print()
        print("Or store securely with lsh:")
        print("  lsh secrets set STREAMLIT_API_TOKEN 'your-token-here'")
        sys.exit(1)

    # Streamlit Management API endpoint
    # Note: The actual API endpoint may vary - check Streamlit docs
    api_url = f"https://share.streamlit.io/api/v1/apps/{app_url}/secrets"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "secrets": secrets_str
    }

    print(f"📤 Pushing secrets to Streamlit Cloud app: {app_url}")
    print()

    response = requests.put(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        print("✅ Successfully pushed secrets to Streamlit Cloud!")
        return True
    else:
        print(f"❌ Error pushing secrets: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def main():
    print("=" * 70)
    print("Push Secrets to Streamlit Cloud")
    print("=" * 70)
    print()

    # Load local secrets
    print("📂 Loading local secrets from .streamlit/secrets.toml...")
    secrets = load_local_secrets()
    secrets_str = convert_to_streamlit_format(secrets)

    # Show preview
    print()
    print("📋 Preview of secrets to be pushed:")
    print("-" * 70)

    # Show sections but hide sensitive values
    for section, values in secrets.items():
        if isinstance(values, dict):
            print(f"[{section}]")
            for key in values.keys():
                print(f"  {key} = <hidden>")
        else:
            print(f"{section} = <hidden>")

    print("-" * 70)
    print()

    # Get app URL
    app_url = input("Enter your Streamlit Cloud app URL (e.g., 'politician-trading-tracker'): ").strip()

    if not app_url:
        print("❌ Error: App URL is required")
        sys.exit(1)

    # Confirm
    print()
    confirm = input("⚠️  This will replace ALL secrets in your Streamlit Cloud app. Continue? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("❌ Cancelled by user")
        sys.exit(0)

    print()

    # Push secrets
    success = push_secrets_via_api(app_url, secrets_str)

    if success:
        print()
        print("🎉 Done! Your Streamlit Cloud app now has the updated secrets.")
        print("   Note: You may need to restart your app for changes to take effect.")
        print()
        print("   Restart at: https://share.streamlit.io/")
    else:
        print()
        print("Note: If the API method doesn't work, you can use the Streamlit CLI:")
        print()
        print("1. Install Streamlit CLI:")
        print("   pip install streamlit")
        print()
        print("2. Login to Streamlit Cloud:")
        print("   streamlit login")
        print()
        print("3. Push secrets:")
        print(f"   streamlit secrets push {app_url} .streamlit/secrets.toml")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
