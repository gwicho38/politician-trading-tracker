#!/usr/bin/env python3
"""
Sync Secrets to Streamlit

Converts .env file to .streamlit/secrets.toml format for easy Streamlit Cloud deployment.
The secrets.toml file is gitignored and can be copied to Streamlit Cloud web interface.
"""

import sys
from pathlib import Path
from dotenv import dotenv_values

# Project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
secrets_file = project_root / ".streamlit" / "secrets.toml"

def convert_env_to_toml():
    """Convert .env file to Streamlit secrets.toml format"""

    if not env_file.exists():
        print(f"❌ Error: .env file not found at {env_file}")
        return False

    # Load environment variables
    env_vars = dotenv_values(env_file)

    if not env_vars:
        print(f"⚠️  Warning: No variables found in {env_file}")
        return False

    # Create .streamlit directory if needed
    secrets_file.parent.mkdir(exist_ok=True)

    # Write to secrets.toml
    with open(secrets_file, "w") as f:
        f.write("# Streamlit Secrets\n")
        f.write("# Auto-generated from .env file\n")
        f.write("# DO NOT COMMIT THIS FILE\n\n")

        for key, value in env_vars.items():
            # Skip comments and empty lines
            if not key or key.startswith("#"):
                continue

            # Handle string values that need quotes
            if isinstance(value, str):
                # Escape quotes in value
                value = value.replace('"', '\\"')
                f.write(f'{key} = "{value}"\n')
            else:
                f.write(f'{key} = {value}\n')

    return True

def main():
    print("="*60)
    print("Streamlit Secrets Sync")
    print("="*60)
    print()

    print(f"📄 Reading from: {env_file}")
    print(f"📝 Writing to:   {secrets_file}")
    print()

    success = convert_env_to_toml()

    if success:
        print("✅ Successfully generated .streamlit/secrets.toml")
        print()
        print("📋 Next steps:")
        print("   1. Review the generated secrets.toml file")
        print("   2. Go to your Streamlit Cloud app settings")
        print("   3. Navigate to 'Secrets' section")
        print("   4. Copy the contents of .streamlit/secrets.toml")
        print("   5. Paste into the Streamlit Cloud secrets editor")
        print("   6. Save and redeploy")
        print()
        print("💡 Tip: You can also use this command to view the secrets:")
        print(f"   cat {secrets_file}")
        print()
        print("🔒 Security: secrets.toml is gitignored and won't be committed")
        print()

        # Show preview
        print("="*60)
        print("Preview of secrets.toml:")
        print("="*60)
        with open(secrets_file, "r") as f:
            content = f.read()
            # Mask sensitive values in preview
            lines = content.split("\n")
            for line in lines:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.split("=", 1)
                    value = value.strip().strip('"')
                    if len(value) > 10:
                        masked = value[:4] + "..." + value[-4:]
                    else:
                        masked = "***"
                    print(f"{key}= \"{masked}\"")
                else:
                    print(line)
        print("="*60)

        return 0
    else:
        print("❌ Failed to generate secrets.toml")
        return 1

if __name__ == "__main__":
    sys.exit(main())
