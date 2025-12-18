"""
Backward compatibility module for auth_utils_enhanced.

This module re-exports all enhanced authentication functionality from the
consolidated auth_utils module. New code should import directly from auth_utils.

Deprecated: Import from auth_utils instead.
    # Old way (still works):
    from auth_utils_enhanced import get_auth_manager

    # New way (preferred):
    from auth_utils import get_auth_manager
"""

from auth_utils import (
    AuthenticationManager,
    get_auth_manager,
    is_authenticated,
    optional_authentication,
    require_authentication,
    show_user_info,
)

__all__ = [
    "require_authentication",
    "show_user_info",
    "is_authenticated",
    "optional_authentication",
    "AuthenticationManager",
    "get_auth_manager",
]
