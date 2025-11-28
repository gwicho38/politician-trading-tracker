"""
Unit tests for basic authentication utilities (auth_utils.py)
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class TestIsAuthenticated:
    """Tests for is_authenticated function"""

    @patch("auth_utils.st")
    def test_returns_true_when_logged_in(self, mock_st):
        """Test that is_authenticated returns True when user is logged in"""
        mock_st.user.is_logged_in = True

        from auth_utils import is_authenticated

        result = is_authenticated()

        assert result is True

    @patch("auth_utils.st")
    def test_returns_false_when_not_logged_in(self, mock_st):
        """Test that is_authenticated returns False when user is not logged in"""
        mock_st.user.is_logged_in = False

        from auth_utils import is_authenticated

        result = is_authenticated()

        assert result is False


class TestOptionalAuthentication:
    """Tests for optional_authentication function"""

    @patch("auth_utils.st")
    def test_shows_user_info_when_logged_in(self, mock_st):
        """Test that optional_authentication shows user info when logged in"""
        mock_st.user.is_logged_in = True
        mock_st.user.name = "Test User"
        mock_st.user.email = "test@example.com"
        mock_st.sidebar = MagicMock()

        from auth_utils import optional_authentication

        optional_authentication()

        # Should call sidebar context manager for user info
        mock_st.sidebar.__enter__.assert_called()

    @patch("auth_utils.st")
    def test_shows_guest_mode_when_not_logged_in(self, mock_st):
        """Test that optional_authentication shows guest mode when not logged in"""
        mock_st.user.is_logged_in = False
        mock_st.sidebar = MagicMock()

        from auth_utils import optional_authentication

        optional_authentication()

        # Should call sidebar context manager for guest info
        mock_st.sidebar.__enter__.assert_called()

    @patch("auth_utils.st")
    def test_does_not_stop_execution(self, mock_st):
        """Test that optional_authentication does not call st.stop()"""
        mock_st.user.is_logged_in = False
        mock_st.sidebar = MagicMock()

        from auth_utils import optional_authentication

        optional_authentication()

        # Should NOT call stop - this is the key difference from require_authentication
        mock_st.stop.assert_not_called()


class TestRequireAuthentication:
    """Tests for require_authentication function"""

    @patch("auth_utils.st")
    def test_does_not_stop_when_logged_in(self, mock_st):
        """Test that require_authentication does not stop when user is logged in"""
        mock_st.user.is_logged_in = True

        from auth_utils import require_authentication

        require_authentication()

        mock_st.stop.assert_not_called()

    @patch("auth_utils.st")
    def test_stops_execution_when_not_logged_in(self, mock_st):
        """Test that require_authentication stops execution when not logged in"""
        mock_st.user.is_logged_in = False

        from auth_utils import require_authentication

        require_authentication()

        mock_st.stop.assert_called_once()


class TestShowUserInfo:
    """Tests for show_user_info function"""

    @patch("auth_utils.st")
    def test_shows_info_when_logged_in(self, mock_st):
        """Test that show_user_info displays user info when logged in"""
        mock_st.user.is_logged_in = True
        mock_st.user.name = "Test User"
        mock_st.user.email = "test@example.com"
        mock_st.sidebar = MagicMock()

        from auth_utils import show_user_info

        show_user_info()

        # Should call sidebar context manager
        mock_st.sidebar.__enter__.assert_called()

    @patch("auth_utils.st")
    def test_does_nothing_when_not_logged_in(self, mock_st):
        """Test that show_user_info does nothing when not logged in"""
        mock_st.user.is_logged_in = False
        mock_st.sidebar = MagicMock()

        from auth_utils import show_user_info

        show_user_info()

        # Should NOT call sidebar when not logged in
        mock_st.sidebar.__enter__.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
