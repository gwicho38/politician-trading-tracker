#!/usr/bin/env python3
"""
Generate hashed passwords for streamlit-authenticator

Usage:
    python scripts/generate_password_hash.py <password>
    python scripts/generate_password_hash.py  # Will prompt for password
"""

import sys
import getpass
import streamlit_authenticator as stauth


def main():
    """Generate password hash"""
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Enter password to hash: ")

    # Generate hash using bcrypt directly (streamlit-authenticator uses bcrypt)
    import bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    print("\n" + "=" * 80)
    print("Password Hash Generated")
    print("=" * 80)
    print(f"\nOriginal: {password}")
    print(f"Hashed:   {hashed}")
    print("\nAdd this to your .streamlit/secrets.toml:")
    print("\n[auth.credentials.usernames.your_username]")
    print(f'password = "{hashed}"')
    print('name = "Your Name"')
    print('email = "your.email@example.com"')
    print()


if __name__ == "__main__":
    main()
