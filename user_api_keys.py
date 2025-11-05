"""
User API Keys Manager
Handles storage and retrieval of user-specific Alpaca API keys
"""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
import os
from cryptography.fernet import Fernet
import base64
import hashlib


class UserAPIKeysManager:
    """Manages user-specific API keys with encryption"""

    def __init__(self):
        """Initialize with encryption key from environment"""
        # Get encryption key from environment or generate one
        encryption_key = os.getenv("API_ENCRYPTION_KEY")
        if not encryption_key:
            # For development, use a derived key (in production, use a secure random key)
            # This should be stored in secrets, not generated
            st.warning("⚠️ API_ENCRYPTION_KEY not set - using derived key (not secure for production)")
            # Derive a key from a secret (still not ideal, but better than nothing)
            secret = os.getenv("cookie_secret", "dev-key-not-secure")
            encryption_key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())

        self.cipher = Fernet(encryption_key)

    def _encrypt(self, value: str) -> str:
        """Encrypt a value"""
        if not value:
            return ""
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a value"""
        if not encrypted_value:
            return ""
        try:
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return ""

    def get_user_keys(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Get ALL API keys and credentials for a user from database

        Returns:
            Dictionary with all user credentials (decrypted), or None if not found
        """
        try:
            from politician_trading.database.database import SupabaseClient
            from politician_trading.config import SupabaseConfig

            config = SupabaseConfig.from_env()
            db = SupabaseClient(config)

            # Query user_api_keys table
            response = db.client.table("user_api_keys").select("*").eq("user_email", user_email).execute()

            if response.data and len(response.data) > 0:
                user_data = response.data[0]

                # Decrypt ALL API keys and credentials
                return {
                    # Alpaca Trading
                    "paper_api_key": self._decrypt(user_data.get("paper_api_key", "")),
                    "paper_secret_key": self._decrypt(user_data.get("paper_secret_key", "")),
                    "live_api_key": self._decrypt(user_data.get("live_api_key", "")),
                    "live_secret_key": self._decrypt(user_data.get("live_secret_key", "")),
                    "paper_validated_at": user_data.get("paper_validated_at"),
                    "live_validated_at": user_data.get("live_validated_at"),

                    # Supabase Database
                    "supabase_url": self._decrypt(user_data.get("supabase_url", "")),
                    "supabase_anon_key": self._decrypt(user_data.get("supabase_anon_key", "")),
                    "supabase_service_role_key": self._decrypt(user_data.get("supabase_service_role_key", "")),
                    "supabase_validated_at": user_data.get("supabase_validated_at"),

                    # QuiverQuant
                    "quiverquant_api_key": self._decrypt(user_data.get("quiverquant_api_key", "")),
                    "quiverquant_validated_at": user_data.get("quiverquant_validated_at"),

                    # Subscription
                    "subscription_tier": user_data.get("subscription_tier", "free"),
                    "subscription_status": user_data.get("subscription_status", "active"),
                    "stripe_customer_id": user_data.get("stripe_customer_id", ""),
                }

            return None

        except Exception as e:
            # Table might not exist yet - return empty dict instead of None
            # This allows the UI to render even before migration is run
            import traceback
            print(f"Error fetching user API keys: {str(e)}")
            print(traceback.format_exc())
            # Return empty structure so UI can still render
            return {
                "paper_api_key": "",
                "paper_secret_key": "",
                "live_api_key": "",
                "live_secret_key": "",
                "supabase_url": "",
                "supabase_anon_key": "",
                "supabase_service_role_key": "",
                "quiverquant_api_key": "",
                "subscription_tier": "free",
                "subscription_status": "active",
            }

    def save_user_keys(
        self,
        user_email: str,
        user_name: str,
        # Alpaca Trading
        paper_api_key: Optional[str] = None,
        paper_secret_key: Optional[str] = None,
        live_api_key: Optional[str] = None,
        live_secret_key: Optional[str] = None,
        # Supabase Database
        supabase_url: Optional[str] = None,
        supabase_anon_key: Optional[str] = None,
        supabase_service_role_key: Optional[str] = None,
        # QuiverQuant
        quiverquant_api_key: Optional[str] = None,
        # Subscription
        subscription_tier: Optional[str] = None,
        subscription_status: Optional[str] = None,
    ) -> bool:
        """
        Save or update ALL API keys and credentials for a user

        Args:
            user_email: User's email
            user_name: User's name
            paper_api_key: Alpaca paper trading API key (will be encrypted)
            paper_secret_key: Alpaca paper trading secret key (will be encrypted)
            live_api_key: Alpaca live trading API key (will be encrypted)
            live_secret_key: Alpaca live trading secret key (will be encrypted)
            supabase_url: User's Supabase instance URL (will be encrypted)
            supabase_anon_key: User's Supabase anon key (will be encrypted)
            supabase_service_role_key: User's Supabase service role key (will be encrypted)
            quiverquant_api_key: QuiverQuant API key (will be encrypted)
            subscription_tier: free, basic, or pro
            subscription_status: active, canceled, or past_due

        Returns:
            True if successful, False otherwise
        """
        try:
            from politician_trading.database.database import SupabaseClient
            from politician_trading.config import SupabaseConfig

            config = SupabaseConfig.from_env()
            db = SupabaseClient(config)

            # Prepare update data (only include fields that are provided)
            update_data = {
                "user_email": user_email,
                "user_name": user_name,
                "updated_at": datetime.now().isoformat(),
                "last_used_at": datetime.now().isoformat(),
            }

            # Encrypt and add ALL API keys if provided
            # Alpaca Trading
            if paper_api_key is not None:
                update_data["paper_api_key"] = self._encrypt(paper_api_key)
            if paper_secret_key is not None:
                update_data["paper_secret_key"] = self._encrypt(paper_secret_key)
            if live_api_key is not None:
                update_data["live_api_key"] = self._encrypt(live_api_key)
            if live_secret_key is not None:
                update_data["live_secret_key"] = self._encrypt(live_secret_key)

            # Supabase Database
            if supabase_url is not None:
                update_data["supabase_url"] = self._encrypt(supabase_url)
            if supabase_anon_key is not None:
                update_data["supabase_anon_key"] = self._encrypt(supabase_anon_key)
            if supabase_service_role_key is not None:
                update_data["supabase_service_role_key"] = self._encrypt(supabase_service_role_key)

            # QuiverQuant
            if quiverquant_api_key is not None:
                update_data["quiverquant_api_key"] = self._encrypt(quiverquant_api_key)

            # Subscription
            if subscription_tier is not None:
                update_data["subscription_tier"] = subscription_tier
            if subscription_status is not None:
                update_data["subscription_status"] = subscription_status

            # Upsert (insert or update)
            response = db.client.table("user_api_keys").upsert(
                update_data,
                on_conflict="user_email"
            ).execute()

            return True

        except Exception as e:
            st.error(f"Error saving user API keys: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return False

    def validate_and_save_keys(
        self,
        user_email: str,
        user_name: str,
        api_key: str,
        secret_key: str,
        is_paper: bool = True
    ) -> Dict[str, Any]:
        """
        Validate API keys with Alpaca and save if valid

        Args:
            user_email: User's email
            user_name: User's name
            api_key: API key to validate
            secret_key: Secret key to validate
            is_paper: True for paper trading, False for live

        Returns:
            Dictionary with 'valid' (bool), 'message' (str), and 'account_info' (dict if valid)
        """
        try:
            from politician_trading.trading.alpaca_client import AlpacaTradingClient

            # Test connection
            client = AlpacaTradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=is_paper
            )

            connection_test = client.test_connection()

            if not connection_test["success"]:
                return {
                    "valid": False,
                    "message": connection_test.get("message", "Connection failed"),
                    "error": connection_test.get("error", ""),
                }

            # Get account info
            account = client.get_account()

            # Keys are valid - save them
            if is_paper:
                success = self.save_user_keys(
                    user_email=user_email,
                    user_name=user_name,
                    paper_api_key=api_key,
                    paper_secret_key=secret_key,
                )
            else:
                success = self.save_user_keys(
                    user_email=user_email,
                    user_name=user_name,
                    live_api_key=api_key,
                    live_secret_key=secret_key,
                )

            if success:
                # Update validation timestamp
                from politician_trading.database.database import SupabaseClient
                from politician_trading.config import SupabaseConfig

                config = SupabaseConfig.from_env()
                db = SupabaseClient(config)

                field_name = "paper_validated_at" if is_paper else "live_validated_at"
                db.client.table("user_api_keys").update({
                    field_name: datetime.now().isoformat()
                }).eq("user_email", user_email).execute()

                return {
                    "valid": True,
                    "message": f"✅ {'Paper' if is_paper else 'Live'} trading keys validated and saved!",
                    "account_info": account,
                }
            else:
                return {
                    "valid": False,
                    "message": "Keys validated but failed to save to database",
                }

        except Exception as e:
            return {
                "valid": False,
                "message": f"Validation failed: {str(e)}",
            }

    def get_alpaca_client(self, user_email: str, use_paper: bool = True):
        """
        Get an Alpaca client configured with user's API keys

        Args:
            user_email: User's email
            use_paper: True for paper trading, False for live

        Returns:
            AlpacaTradingClient instance or None if keys not found
        """
        from politician_trading.trading.alpaca_client import AlpacaTradingClient

        user_keys = self.get_user_keys(user_email)

        if not user_keys:
            return None

        if use_paper:
            api_key = user_keys.get("paper_api_key")
            secret_key = user_keys.get("paper_secret_key")
        else:
            api_key = user_keys.get("live_api_key")
            secret_key = user_keys.get("live_secret_key")

        if not api_key or not secret_key:
            return None

        return AlpacaTradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=use_paper
        )

    def has_live_access(self, user_email: str) -> bool:
        """
        Check if user has access to live trading (paid subscription)

        Args:
            user_email: User's email

        Returns:
            True if user has active paid subscription, False otherwise
        """
        user_keys = self.get_user_keys(user_email)

        if not user_keys:
            return False

        # Check subscription tier and status
        tier = user_keys.get("subscription_tier", "free")
        status = user_keys.get("subscription_status", "active")

        return tier in ["basic", "pro"] and status == "active"


# Singleton instance
_manager = None


def get_user_api_keys_manager() -> UserAPIKeysManager:
    """Get or create singleton instance of UserAPIKeysManager"""
    global _manager
    if _manager is None:
        _manager = UserAPIKeysManager()
    return _manager
