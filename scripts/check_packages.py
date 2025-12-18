#!/usr/bin/env python3
"""
Check if required packages are installed in the current environment.
Useful for debugging Streamlit Cloud deployment issues.
"""

import sys

# Packages to check (Streamlit packages removed - now using React UI)
REQUIRED_PACKAGES = {
    # "streamlit-hotkeys": "streamlit_hotkeys",
    # "streamlit-autorefresh": "streamlit_autorefresh",
    # "streamlit-analytics": "streamlit_analytics",
    # "streamlit-antd-components": "streamlit_antd_components",
    # "st-supabase-connection": "st_supabase_connection",
}

def check_package(package_name, import_name):
    """Check if a package is installed"""
    try:
        __import__(import_name)
        return True, "✅ Installed"
    except ImportError as e:
        return False, f"❌ Not installed: {str(e)}"

def main():
    print("=" * 70)
    print("Package Installation Check")
    print("=" * 70)
    print()

    all_installed = True

    for package_name, import_name in REQUIRED_PACKAGES.items():
        installed, status = check_package(package_name, import_name)
        print(f"{package_name:30} {status}")
        if not installed:
            all_installed = False

    print()
    print("=" * 70)

    if all_installed:
        print("✅ All packages installed successfully!")
    else:
        print("❌ Some packages are missing")
        print()
        print("If running on Streamlit Cloud:")
        print("  1. Check requirements.txt includes all packages")
        print("  2. Clear cache: Settings → Reboot app")
        print("  3. Check build logs for errors")

    print("=" * 70)

    return 0 if all_installed else 1

if __name__ == "__main__":
    sys.exit(main())
