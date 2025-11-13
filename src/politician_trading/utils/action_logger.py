"""
Action Logger for Politician Trading Tracker
Provides centralized logging for all user actions and system events
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.logger import create_logger

logger = create_logger("action_logger")


class ActionLogger:
    """
    Centralized action logging system.

    Logs all user actions, scheduled jobs, and system events to the action_logs table.
    Provides context tracking and correlation with job executions.
    """

    def __init__(self, config: Optional[SupabaseConfig] = None):
        """
        Initialize action logger.

        Args:
            config: Supabase configuration. If None, loads from environment.
        """
        self.config = config or SupabaseConfig.from_env()
        self.db = SupabaseClient(self.config)
        self._current_actions: Dict[str, Dict[str, Any]] = {}

    def log_action(
        self,
        action_type: str,
        status: str,
        action_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        job_execution_id: Optional[str] = None,
        error_message: Optional[str] = None,
        result_message: Optional[str] = None,
        source: str = "ui_button",
        user_id: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log an action to the action_logs table.

        Args:
            action_type: Type of action (e.g., 'data_collection_start', 'job_execution')
            status: Action status ('initiated', 'in_progress', 'completed', 'failed', 'cancelled')
            action_name: Human-readable action name
            action_details: Dict of action-specific data
            job_id: Job ID if related to a scheduled job
            job_execution_id: Job execution ID if related to job execution
            error_message: Error message if action failed
            result_message: Result/success message
            source: Source of action ('ui_button', 'scheduled_job', 'api', 'recovery', 'system')
            user_id: Username or user ID
            duration_seconds: Duration of action
            ip_address: IP address of requester
            user_agent: User agent string
            session_id: Session identifier

        Returns:
            action_log_id (UUID as string) if successful, None if failed
        """
        try:
            action_record = {
                "action_type": action_type,
                "action_name": action_name,
                "status": status,
                "action_details": action_details or {},
                "job_id": job_id,
                "job_execution_id": job_execution_id,
                "error_message": error_message,
                "result_message": result_message,
                "source": source,
                "user_id": user_id,
                "action_timestamp": datetime.now().isoformat(),
                "duration_seconds": duration_seconds,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
            }

            response = self.db.client.table("action_logs").insert(action_record).execute()

            if response.data and len(response.data) > 0:
                action_id = response.data[0]["id"]
                logger.debug(
                    f"Logged action: {action_type}",
                    metadata={
                        "action_id": action_id,
                        "status": status,
                        "user_id": user_id,
                        "source": source,
                    },
                )
                return action_id

            logger.warning(f"No data returned when logging action: {action_type}")
            return None

        except Exception as e:
            logger.error(
                f"Failed to log action {action_type}: {e}",
                metadata={"action_type": action_type, "status": status, "source": source},
            )
            # Don't fail main operation if logging fails
            return None

    def start_action(
        self,
        action_type: str,
        action_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        source: str = "ui_button",
        user_id: Optional[str] = None,
        job_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Start tracking an action. Returns an action_id that can be used to update the action later.

        Args:
            action_type: Type of action being started
            action_name: Human-readable name
            action_details: Initial action details
            source: Source of action
            user_id: User identifier
            job_id: Related job ID
            session_id: Session identifier

        Returns:
            action_id if successful, None if failed
        """
        action_id = self.log_action(
            action_type=action_type,
            action_name=action_name,
            status="initiated",
            action_details=action_details,
            source=source,
            user_id=user_id,
            job_id=job_id,
            session_id=session_id,
        )

        if action_id:
            # Store action context for later updates
            self._current_actions[action_id] = {
                "action_type": action_type,
                "start_time": time.time(),
                "action_details": action_details or {},
            }

        return action_id

    def update_action(
        self,
        action_id: str,
        status: str,
        result_message: Optional[str] = None,
        error_message: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing action with new status or details.

        Args:
            action_id: ID of the action to update
            status: New status
            result_message: Result message
            error_message: Error message if failed
            action_details: Updated action details (will be merged with existing)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate duration if we have start time
            duration_seconds = None
            if action_id in self._current_actions:
                start_time = self._current_actions[action_id]["start_time"]
                duration_seconds = time.time() - start_time

                # Merge action details
                if action_details:
                    existing_details = self._current_actions[action_id].get("action_details", {})
                    action_details = {**existing_details, **action_details}

            update_data = {
                "status": status,
                "result_message": result_message,
                "error_message": error_message,
                "updated_at": datetime.now().isoformat(),
            }

            if duration_seconds is not None:
                update_data["duration_seconds"] = round(duration_seconds, 3)

            if action_details:
                update_data["action_details"] = action_details

            if status in ("completed", "failed", "cancelled"):
                update_data["completed_at"] = datetime.now().isoformat()

            response = self.db.client.table("action_logs").update(update_data).eq("id", action_id).execute()

            if response.data and len(response.data) > 0:
                logger.debug(
                    f"Updated action {action_id}",
                    metadata={"action_id": action_id, "status": status, "duration": duration_seconds},
                )

                # Clean up tracking if action is complete
                if status in ("completed", "failed", "cancelled"):
                    self._current_actions.pop(action_id, None)

                return True

            logger.warning(f"No data returned when updating action: {action_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to update action {action_id}: {e}", metadata={"action_id": action_id})
            return False

    def complete_action(
        self,
        action_id: str,
        result_message: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark an action as completed.

        Args:
            action_id: ID of the action
            result_message: Success message
            action_details: Final action details

        Returns:
            True if successful, False otherwise
        """
        return self.update_action(
            action_id=action_id, status="completed", result_message=result_message, action_details=action_details
        )

    def fail_action(
        self,
        action_id: str,
        error_message: str,
        action_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark an action as failed.

        Args:
            action_id: ID of the action
            error_message: Error description
            action_details: Additional error details

        Returns:
            True if successful, False otherwise
        """
        return self.update_action(
            action_id=action_id, status="failed", error_message=error_message, action_details=action_details
        )

    def get_recent_actions(
        self,
        action_type: Optional[str] = None,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """
        Get recent actions with optional filtering.

        Args:
            action_type: Filter by action type
            user_id: Filter by user
            source: Filter by source
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of action log records
        """
        try:
            query = self.db.client.table("action_logs").select("*")

            if action_type:
                query = query.eq("action_type", action_type)
            if user_id:
                query = query.eq("user_id", user_id)
            if source:
                query = query.eq("source", source)
            if status:
                query = query.eq("status", status)

            query = query.order("action_timestamp", desc=True).limit(limit)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(
                f"Failed to get recent actions: {e}",
                metadata={
                    "action_type": action_type,
                    "user_id": user_id,
                    "source": source,
                    "status": status,
                },
            )
            return []

    def get_action_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get summary statistics for actions over the specified time period.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Use the pre-built view for efficiency
            response = self.db.client.table("action_logs_summary").select("*").execute()

            if response.data:
                return {
                    "summary": response.data,
                    "period_days": days,
                    "generated_at": datetime.now().isoformat(),
                }

            return {
                "summary": [],
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get action summary: {e}")
            return {"error": str(e)}


# Global singleton instance
_action_logger: Optional[ActionLogger] = None


def get_action_logger(config: Optional[SupabaseConfig] = None) -> ActionLogger:
    """
    Get or create the global action logger instance.

    Args:
        config: Optional Supabase configuration

    Returns:
        ActionLogger instance
    """
    global _action_logger

    if _action_logger is None:
        _action_logger = ActionLogger(config=config)

    return _action_logger


# Convenience functions for quick logging
def log_action(
    action_type: str,
    status: str,
    **kwargs,
) -> Optional[str]:
    """
    Convenience function to log an action using the global logger.

    See ActionLogger.log_action for parameter documentation.
    """
    logger_instance = get_action_logger()
    return logger_instance.log_action(action_type=action_type, status=status, **kwargs)


def start_action(
    action_type: str,
    **kwargs,
) -> Optional[str]:
    """
    Convenience function to start tracking an action.

    See ActionLogger.start_action for parameter documentation.
    """
    logger_instance = get_action_logger()
    return logger_instance.start_action(action_type=action_type, **kwargs)


def complete_action(action_id: str, **kwargs) -> bool:
    """
    Convenience function to complete an action.

    See ActionLogger.complete_action for parameter documentation.
    """
    logger_instance = get_action_logger()
    return logger_instance.complete_action(action_id=action_id, **kwargs)


def fail_action(action_id: str, error_message: str, **kwargs) -> bool:
    """
    Convenience function to fail an action.

    See ActionLogger.fail_action for parameter documentation.
    """
    logger_instance = get_action_logger()
    return logger_instance.fail_action(action_id=action_id, error_message=error_message, **kwargs)
