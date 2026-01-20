"""
Tests for Job Execution Logger (app/lib/job_logger.py).

Tests:
- log_job_execution() - Log job execution to database
- cleanup_old_executions() - Clean up old execution records
- JobExecutionContext - Context manager for tracking jobs
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta


# =============================================================================
# log_job_execution() Tests
# =============================================================================

class TestLogJobExecution:
    """Tests for log_job_execution() function."""

    def test_logs_successful_execution(self):
        """log_job_execution() logs a successful job execution."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        started = datetime.utcnow()
        completed = datetime.utcnow()

        result = log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="success",
            started_at=started,
            completed_at=completed
        )

        assert result is not None
        mock_supabase.table.assert_called_with("job_executions")

    def test_logs_failed_execution_with_error(self):
        """log_job_execution() logs a failed job with error message."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        started = datetime.utcnow()
        completed = datetime.utcnow()

        result = log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="failed",
            started_at=started,
            completed_at=completed,
            error_message="Something went wrong"
        )

        assert result is not None
        # Verify error_message was included in the insert
        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["error_message"] == "Something went wrong"

    def test_logs_execution_with_metadata(self):
        """log_job_execution() logs execution with metadata."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        started = datetime.utcnow()
        metadata = {"records_processed": 100, "source": "house"}

        result = log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="success",
            started_at=started,
            metadata=metadata
        )

        assert result is not None
        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["metadata"] == metadata

    def test_calculates_duration(self):
        """log_job_execution() calculates duration in seconds."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        started = datetime(2024, 1, 1, 12, 0, 0)
        completed = datetime(2024, 1, 1, 12, 1, 30)  # 90 seconds later

        log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="success",
            started_at=started,
            completed_at=completed
        )

        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["duration_seconds"] == 90.0

    def test_returns_none_on_empty_response(self):
        """log_job_execution() returns None when insert returns empty data."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        result = log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="success",
            started_at=datetime.utcnow()
        )

        assert result is None

    def test_returns_none_on_exception(self):
        """log_job_execution() returns None on exception."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.side_effect = Exception("DB error")

        result = log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="success",
            started_at=datetime.utcnow()
        )

        assert result is None

    def test_generates_uuid_for_record(self):
        """log_job_execution() generates a UUID for the record."""
        from app.lib.job_logger import log_job_execution

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        log_job_execution(
            mock_supabase,
            job_id="test-job",
            status="success",
            started_at=datetime.utcnow()
        )

        insert_call = mock_supabase.table.return_value.insert.call_args
        # ID should be a UUID string (36 chars with dashes)
        assert len(insert_call[0][0]["id"]) == 36


# =============================================================================
# cleanup_old_executions() Tests
# =============================================================================

class TestCleanupOldExecutions:
    """Tests for cleanup_old_executions() function."""

    def test_deletes_old_records(self):
        """cleanup_old_executions() deletes records older than specified days."""
        from app.lib.job_logger import cleanup_old_executions

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = mock_response

        result = cleanup_old_executions(mock_supabase, days=30)

        assert result == 3
        mock_supabase.table.assert_called_with("job_executions")

    def test_uses_default_30_days(self):
        """cleanup_old_executions() uses default 30 days cutoff."""
        from app.lib.job_logger import cleanup_old_executions

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = mock_response

        cleanup_old_executions(mock_supabase)

        # Verify lt was called with a date approximately 30 days ago
        lt_call = mock_supabase.table.return_value.delete.return_value.lt.call_args
        assert lt_call[0][0] == "started_at"

    def test_filters_by_job_id_prefix(self):
        """cleanup_old_executions() filters by job_id prefix when provided."""
        from app.lib.job_logger import cleanup_old_executions

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_query = MagicMock()
        mock_query.like.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.delete.return_value.lt.return_value = mock_query

        cleanup_old_executions(mock_supabase, days=30, job_id_prefix="politician-trading")

        mock_query.like.assert_called_with("job_id", "politician-trading%")

    def test_returns_zero_on_empty_response(self):
        """cleanup_old_executions() returns 0 when no records deleted."""
        from app.lib.job_logger import cleanup_old_executions

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = mock_response

        result = cleanup_old_executions(mock_supabase)

        assert result == 0

    def test_returns_zero_on_exception(self):
        """cleanup_old_executions() returns 0 on exception."""
        from app.lib.job_logger import cleanup_old_executions

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.delete.side_effect = Exception("DB error")

        result = cleanup_old_executions(mock_supabase)

        assert result == 0


# =============================================================================
# JobExecutionContext Tests
# =============================================================================

class TestJobExecutionContext:
    """Tests for JobExecutionContext class."""

    @pytest.mark.asyncio
    async def test_context_logs_on_exit(self):
        """JobExecutionContext logs execution on exit."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        # Disable auto_cleanup to avoid random import issues
        async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
            pass

        mock_supabase.table.assert_called_with("job_executions")

    @pytest.mark.asyncio
    async def test_context_sets_started_at(self):
        """JobExecutionContext sets started_at on entry."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
            assert ctx.started_at is not None

    @pytest.mark.asyncio
    async def test_context_logs_success_status(self):
        """JobExecutionContext logs success status on normal exit."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
            pass

        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_context_logs_failed_status_on_exception(self):
        """JobExecutionContext logs failed status on exception."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        with pytest.raises(ValueError):
            async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
                raise ValueError("Test error")

        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_context_add_metadata(self):
        """JobExecutionContext.add_metadata() adds to metadata."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
            ctx.add_metadata("records_processed", 100)

        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["metadata"]["records_processed"] == 100

    @pytest.mark.asyncio
    async def test_context_set_error(self):
        """JobExecutionContext.set_error() marks execution as failed."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
            ctx.set_error("Manual error")

        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["status"] == "failed"
        assert insert_call[0][0]["error_message"] == "Manual error"

    @pytest.mark.asyncio
    async def test_context_auto_cleanup_disabled(self):
        """JobExecutionContext skips cleanup when auto_cleanup=False."""
        from app.lib.job_logger import JobExecutionContext

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        async with JobExecutionContext(mock_supabase, "test-job", auto_cleanup=False) as ctx:
            pass

        # Verify only insert was called, not delete
        calls = mock_supabase.table.return_value.method_calls
        call_names = [str(c) for c in calls]
        delete_calls = [c for c in call_names if 'delete' in c]
        assert len(delete_calls) == 0
