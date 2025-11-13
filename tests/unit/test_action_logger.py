"""
Unit tests for action logging functionality
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from politician_trading.utils.action_logger import (
    ActionLogger,
    log_action,
    start_action,
    complete_action,
    fail_action,
)


class TestActionLogger:
    """Test the ActionLogger class"""

    @pytest.fixture
    def mock_db_client(self):
        """Create a mock database client"""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.client.table.return_value = mock_table
        return mock_client, mock_table

    @pytest.fixture
    def action_logger(self, mock_db_client):
        """Create an ActionLogger instance with mocked database"""
        mock_client, _ = mock_db_client
        with patch(
            "politician_trading.utils.action_logger.SupabaseClient", return_value=mock_client
        ):
            logger = ActionLogger()
            return logger

    def test_log_action_success(self, action_logger, mock_db_client):
        """Test logging an action successfully"""
        _, mock_table = mock_db_client

        # Mock successful insert
        mock_response = Mock()
        mock_response.data = [{"id": "test-action-id-123"}]
        mock_table.insert.return_value.execute.return_value = mock_response

        action_id = action_logger.log_action(
            action_type="test_action",
            status="completed",
            action_name="Test Action",
            user_id="test_user",
            source="ui_button",
        )

        assert action_id == "test-action-id-123"
        mock_table.insert.assert_called_once()

        # Verify the inserted data structure
        call_args = mock_table.insert.call_args[0][0]
        assert call_args["action_type"] == "test_action"
        assert call_args["status"] == "completed"
        assert call_args["action_name"] == "Test Action"
        assert call_args["user_id"] == "test_user"
        assert call_args["source"] == "ui_button"
        assert "action_timestamp" in call_args

    def test_log_action_with_details(self, action_logger, mock_db_client):
        """Test logging an action with additional details"""
        _, mock_table = mock_db_client

        mock_response = Mock()
        mock_response.data = [{"id": "test-id"}]
        mock_table.insert.return_value.execute.return_value = mock_response

        action_details = {"param1": "value1", "param2": 42, "nested": {"key": "value"}}

        action_id = action_logger.log_action(
            action_type="test_action",
            status="initiated",
            action_details=action_details,
            job_id="test-job-123",
        )

        assert action_id == "test-id"

        call_args = mock_table.insert.call_args[0][0]
        assert call_args["action_details"] == action_details
        assert call_args["job_id"] == "test-job-123"

    def test_log_action_failure(self, action_logger, mock_db_client):
        """Test handling of logging failure"""
        _, mock_table = mock_db_client

        # Mock database error
        mock_table.insert.return_value.execute.side_effect = Exception("Database error")

        # Should not raise, but return None
        action_id = action_logger.log_action(
            action_type="test_action",
            status="completed",
        )

        assert action_id is None

    def test_start_action(self, action_logger, mock_db_client):
        """Test starting an action tracking"""
        _, mock_table = mock_db_client

        mock_response = Mock()
        mock_response.data = [{"id": "action-123"}]
        mock_table.insert.return_value.execute.return_value = mock_response

        action_id = action_logger.start_action(
            action_type="data_collection",
            action_name="Data Collection Job",
            user_id="user@example.com",
            action_details={"sources": ["us_congress"]},
        )

        assert action_id == "action-123"
        assert action_id in action_logger._current_actions
        assert "start_time" in action_logger._current_actions[action_id]
        assert "action_type" in action_logger._current_actions[action_id]

    def test_update_action_status(self, action_logger, mock_db_client):
        """Test updating an action's status"""
        _, mock_table = mock_db_client

        # Start action
        mock_insert_response = Mock()
        mock_insert_response.data = [{"id": "action-123"}]
        mock_table.insert.return_value.execute.return_value = mock_insert_response

        action_id = action_logger.start_action(
            action_type="test_action",
            action_name="Test Action",
        )

        # Simulate some time passing
        time.sleep(0.1)

        # Update action
        mock_update_response = Mock()
        mock_update_response.data = [{"id": action_id}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_response

        success = action_logger.update_action(
            action_id=action_id,
            status="in_progress",
            result_message="Processing data",
        )

        assert success is True
        mock_table.update.assert_called_once()

        # Verify update data
        call_args = mock_table.update.call_args[0][0]
        assert call_args["status"] == "in_progress"
        assert call_args["result_message"] == "Processing data"
        assert "duration_seconds" in call_args
        assert call_args["duration_seconds"] >= 0.1

    def test_complete_action(self, action_logger, mock_db_client):
        """Test completing an action"""
        _, mock_table = mock_db_client

        # Start action
        mock_insert_response = Mock()
        mock_insert_response.data = [{"id": "action-123"}]
        mock_table.insert.return_value.execute.return_value = mock_insert_response

        action_id = action_logger.start_action(action_type="test_action")

        # Complete action
        mock_update_response = Mock()
        mock_update_response.data = [{"id": action_id}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_response

        success = action_logger.complete_action(
            action_id=action_id,
            result_message="Action completed successfully",
            action_details={"records_processed": 100},
        )

        assert success is True

        call_args = mock_table.update.call_args[0][0]
        assert call_args["status"] == "completed"
        assert call_args["result_message"] == "Action completed successfully"
        assert "completed_at" in call_args

        # Should be removed from tracking
        assert action_id not in action_logger._current_actions

    def test_fail_action(self, action_logger, mock_db_client):
        """Test failing an action"""
        _, mock_table = mock_db_client

        # Start action
        mock_insert_response = Mock()
        mock_insert_response.data = [{"id": "action-123"}]
        mock_table.insert.return_value.execute.return_value = mock_insert_response

        action_id = action_logger.start_action(action_type="test_action")

        # Fail action
        mock_update_response = Mock()
        mock_update_response.data = [{"id": action_id}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_response

        success = action_logger.fail_action(
            action_id=action_id,
            error_message="Test error occurred",
            action_details={"error_code": 500},
        )

        assert success is True

        call_args = mock_table.update.call_args[0][0]
        assert call_args["status"] == "failed"
        assert call_args["error_message"] == "Test error occurred"
        assert "completed_at" in call_args

        # Should be removed from tracking
        assert action_id not in action_logger._current_actions

    def test_get_recent_actions(self, action_logger, mock_db_client):
        """Test retrieving recent actions"""
        _, mock_table = mock_db_client

        mock_actions = [
            {
                "id": "action-1",
                "action_type": "data_collection",
                "status": "completed",
                "action_timestamp": "2025-11-03T10:00:00",
            },
            {
                "id": "action-2",
                "action_type": "ticker_backfill",
                "status": "failed",
                "action_timestamp": "2025-11-03T11:00:00",
            },
        ]

        mock_response = Mock()
        mock_response.data = mock_actions
        mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_response
        )

        actions = action_logger.get_recent_actions(limit=10)

        assert len(actions) == 2
        assert actions[0]["action_type"] == "data_collection"
        assert actions[1]["status"] == "failed"

    def test_get_recent_actions_with_filters(self, action_logger, mock_db_client):
        """Test retrieving recent actions with filters"""
        _, mock_table = mock_db_client

        mock_response = Mock()
        mock_response.data = []

        # Create a mock chain
        mock_chain = Mock()
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = mock_response

        mock_table.select.return_value = mock_chain

        action_logger.get_recent_actions(
            action_type="data_collection",
            user_id="test@example.com",
            source="ui_button",
            status="completed",
            limit=50,
        )

        # Verify filters were applied
        assert mock_chain.eq.call_count == 4  # Four filters applied
        mock_chain.order.assert_called_once()
        mock_chain.limit.assert_called_once_with(50)

    def test_get_action_summary(self, action_logger, mock_db_client):
        """Test retrieving action summary statistics"""
        _, mock_table = mock_db_client

        mock_summary = [
            {
                "action_type": "data_collection",
                "source": "ui_button",
                "status": "completed",
                "total_count": 10,
                "completed_count": 9,
                "failed_count": 1,
                "avg_duration_seconds": 45.5,
            }
        ]

        mock_response = Mock()
        mock_response.data = mock_summary
        mock_table.select.return_value.execute.return_value = mock_response

        summary = action_logger.get_action_summary(days=7)

        assert "summary" in summary
        assert "period_days" in summary
        assert summary["period_days"] == 7
        assert len(summary["summary"]) == 1
        assert summary["summary"][0]["total_count"] == 10


class TestConvenienceFunctions:
    """Test the convenience wrapper functions"""

    def test_log_action_convenience(self):
        """Test the log_action convenience function"""
        with patch("politician_trading.utils.action_logger.get_action_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.log_action.return_value = "action-id-123"
            mock_get_logger.return_value = mock_logger

            result = log_action(
                action_type="test_action",
                status="completed",
                user_id="test_user",
            )

            assert result == "action-id-123"
            mock_logger.log_action.assert_called_once_with(
                action_type="test_action",
                status="completed",
                user_id="test_user",
            )

    def test_start_action_convenience(self):
        """Test the start_action convenience function"""
        with patch("politician_trading.utils.action_logger.get_action_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.start_action.return_value = "action-id-456"
            mock_get_logger.return_value = mock_logger

            result = start_action(action_type="test_action", user_id="test_user")

            assert result == "action-id-456"
            mock_logger.start_action.assert_called_once()

    def test_complete_action_convenience(self):
        """Test the complete_action convenience function"""
        with patch("politician_trading.utils.action_logger.get_action_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.complete_action.return_value = True
            mock_get_logger.return_value = mock_logger

            result = complete_action(action_id="action-123", result_message="Success")

            assert result is True
            mock_logger.complete_action.assert_called_once()

    def test_fail_action_convenience(self):
        """Test the fail_action convenience function"""
        with patch("politician_trading.utils.action_logger.get_action_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.fail_action.return_value = True
            mock_get_logger.return_value = mock_logger

            result = fail_action(action_id="action-123", error_message="Test error")

            assert result is True
            mock_logger.fail_action.assert_called_once()


class TestActionLoggerIntegration:
    """Integration-style tests (still mocked, but testing more complex workflows)"""

    @pytest.fixture
    def mock_db_client(self):
        """Create a mock database client"""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.client.table.return_value = mock_table
        return mock_client, mock_table

    def test_complete_action_workflow(self, mock_db_client):
        """Test complete action workflow from start to completion"""
        mock_client, mock_table = mock_db_client

        # Mock responses
        mock_insert_response = Mock()
        mock_insert_response.data = [{"id": "action-789"}]
        mock_table.insert.return_value.execute.return_value = mock_insert_response

        mock_update_response = Mock()
        mock_update_response.data = [{"id": "action-789"}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_response

        with patch(
            "politician_trading.utils.action_logger.SupabaseClient", return_value=mock_client
        ):
            logger = ActionLogger()

            # Start action
            action_id = logger.start_action(
                action_type="data_collection",
                action_name="Test Collection",
                user_id="test@example.com",
                action_details={"sources": ["us_congress"]},
            )

            assert action_id == "action-789"

            # Simulate some work
            time.sleep(0.1)

            # Update status
            logger.update_action(
                action_id=action_id,
                status="in_progress",
                action_details={"records_processed": 50},
            )

            # Complete action
            success = logger.complete_action(
                action_id=action_id,
                result_message="Collection completed successfully",
                action_details={"total_records": 100},
            )

            assert success is True
            assert mock_table.insert.call_count == 1
            assert mock_table.update.call_count == 2  # Once for in_progress, once for completed

    def test_failed_action_workflow(self, mock_db_client):
        """Test failed action workflow"""
        mock_client, mock_table = mock_db_client

        # Mock responses
        mock_insert_response = Mock()
        mock_insert_response.data = [{"id": "action-error"}]
        mock_table.insert.return_value.execute.return_value = mock_insert_response

        mock_update_response = Mock()
        mock_update_response.data = [{"id": "action-error"}]
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_update_response

        with patch(
            "politician_trading.utils.action_logger.SupabaseClient", return_value=mock_client
        ):
            logger = ActionLogger()

            # Start action
            action_id = logger.start_action(
                action_type="data_collection",
                action_name="Test Collection",
            )

            # Simulate failure
            logger.fail_action(
                action_id=action_id,
                error_message="Connection timeout",
                action_details={"error_code": "TIMEOUT", "retry_count": 3},
            )

            # Verify failure was logged
            call_args = mock_table.update.call_args[0][0]
            assert call_args["status"] == "failed"
            assert call_args["error_message"] == "Connection timeout"
            assert call_args["action_details"]["error_code"] == "TIMEOUT"
