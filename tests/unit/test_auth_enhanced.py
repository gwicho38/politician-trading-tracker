"""
Unit tests for enhanced authentication system
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class TestAuthenticationManager:
    """Test the AuthenticationManager class"""

    @patch('auth_utils_enhanced.st')
    def test_session_id_generation(self, mock_st):
        """Test that session IDs are unique"""
        from auth_utils_enhanced import AuthenticationManager

        # Setup mock session state
        mock_st.session_state = {
            'auth_sessions': {},
            'auth_login_attempts': {},
            'auth_current_session_id': None
        }

        auth_manager = AuthenticationManager()

        # Generate multiple session IDs
        session_id_1 = auth_manager._generate_session_id("test@example.com")
        session_id_2 = auth_manager._generate_session_id("test@example.com")

        # They should be different
        assert session_id_1 != session_id_2
        assert len(session_id_1) == 16  # SHA256 truncated to 16 chars
        assert len(session_id_2) == 16

    @patch('auth_utils_enhanced.st')
    def test_session_timeout_cleanup(self, mock_st):
        """Test that expired sessions are cleaned up"""
        from auth_utils_enhanced import AuthenticationManager

        # Create sessions with different ages
        now = datetime.now()
        old_time = now - timedelta(hours=9)  # Older than 8 hour timeout
        recent_time = now - timedelta(hours=1)  # Within timeout

        mock_st.session_state = {
            'auth_sessions': {
                'session_1': {
                    'user_email': 'test@example.com',
                    'user_name': 'Test User',
                    'login_time': old_time,
                    'last_activity': old_time
                },
                'session_2': {
                    'user_email': 'test@example.com',
                    'user_name': 'Test User',
                    'login_time': recent_time,
                    'last_activity': recent_time
                }
            },
            'auth_login_attempts': {},
            'auth_current_session_id': None
        }

        auth_manager = AuthenticationManager()

        # Mock the log method to prevent actual logging
        auth_manager._log_auth_event = Mock()

        # Run cleanup
        auth_manager._cleanup_expired_sessions()

        # Old session should be removed, recent one should remain
        assert 'session_1' not in mock_st.session_state['auth_sessions']
        assert 'session_2' in mock_st.session_state['auth_sessions']

        # Should have logged the timeout
        auth_manager._log_auth_event.assert_called_once()
        call_kwargs = auth_manager._log_auth_event.call_args[1]
        assert call_kwargs['action_type'] == 'session_timeout'

    @patch('auth_utils_enhanced.st')
    def test_concurrent_session_limit(self, mock_st):
        """Test that concurrent session limits are enforced"""
        from auth_utils_enhanced import AuthenticationManager

        now = datetime.now()

        # Create 5 existing sessions (at the limit)
        sessions = {}
        for i in range(5):
            session_time = now - timedelta(minutes=i)
            sessions[f'session_{i}'] = {
                'user_email': 'test@example.com',
                'user_name': 'Test User',
                'login_time': session_time,
                'last_activity': session_time
            }

        mock_st.session_state = {
            'auth_sessions': sessions,
            'auth_login_attempts': {},
            'auth_current_session_id': None
        }

        auth_manager = AuthenticationManager(max_concurrent_sessions=5)
        auth_manager._log_auth_event = Mock()

        # Try to add a 6th session
        initial_count = len(mock_st.session_state['auth_sessions'])
        auth_manager._manage_concurrent_sessions('test@example.com')

        # Should have removed the oldest session
        final_count = len(mock_st.session_state['auth_sessions'])
        assert final_count == initial_count - 1

        # Should have logged the termination
        auth_manager._log_auth_event.assert_called_once()
        call_kwargs = auth_manager._log_auth_event.call_args[1]
        assert call_kwargs['action_type'] == 'session_terminated'

    @patch('auth_utils_enhanced.st')
    def test_activity_update(self, mock_st):
        """Test that activity timestamps are updated"""
        from auth_utils_enhanced import AuthenticationManager

        old_time = datetime.now() - timedelta(minutes=10)

        mock_st.session_state = {
            'auth_sessions': {
                'test_session': {
                    'user_email': 'test@example.com',
                    'user_name': 'Test User',
                    'login_time': old_time,
                    'last_activity': old_time
                }
            },
            'auth_login_attempts': {},
            'auth_current_session_id': 'test_session'
        }

        auth_manager = AuthenticationManager()

        # Update activity
        auth_manager._update_session_activity()

        # Last activity should be updated
        updated_activity = mock_st.session_state['auth_sessions']['test_session']['last_activity']
        assert updated_activity > old_time

    @patch('auth_utils_enhanced.st')
    def test_session_stats(self, mock_st):
        """Test that session statistics are calculated correctly"""
        from auth_utils_enhanced import AuthenticationManager

        now = datetime.now()

        mock_st.session_state = {
            'auth_sessions': {
                'session_1': {
                    'user_email': 'user1@example.com',
                    'user_name': 'User 1',
                    'login_time': now,
                    'last_activity': now
                },
                'session_2': {
                    'user_email': 'user1@example.com',
                    'user_name': 'User 1',
                    'login_time': now,
                    'last_activity': now
                },
                'session_3': {
                    'user_email': 'user2@example.com',
                    'user_name': 'User 2',
                    'login_time': now,
                    'last_activity': now
                }
            },
            'auth_login_attempts': {},
            'auth_current_session_id': None
        }

        auth_manager = AuthenticationManager()
        stats = auth_manager.get_session_stats()

        assert stats['total_active_sessions'] == 3
        assert stats['unique_users'] == 2
        assert stats['users']['user1@example.com'] == 2
        assert stats['users']['user2@example.com'] == 1
        assert stats['max_concurrent_sessions'] == 5
        assert stats['session_timeout_minutes'] == 480

    @patch('auth_utils_enhanced.st')
    @patch('auth_utils_enhanced.ACTION_LOGGING_AVAILABLE', True)
    @patch('auth_utils_enhanced.log_action')
    def test_action_logging_integration(self, mock_log_action, mock_st):
        """Test that auth events are logged to action_logs"""
        from auth_utils_enhanced import AuthenticationManager

        mock_st.session_state = {
            'auth_sessions': {},
            'auth_login_attempts': {},
            'auth_current_session_id': None
        }

        auth_manager = AuthenticationManager(enable_action_logging=True)

        # Log an auth event
        auth_manager._log_auth_event(
            action_type='login_success',
            status='completed',
            user_email='test@example.com',
            details={'session_id': 'test123'}
        )

        # Should have called log_action
        mock_log_action.assert_called_once()
        call_kwargs = mock_log_action.call_args[1]
        assert call_kwargs['action_type'] == 'login_success'
        assert call_kwargs['status'] == 'completed'
        assert call_kwargs['user_id'] == 'test@example.com'
        assert call_kwargs['source'] == 'authentication'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
