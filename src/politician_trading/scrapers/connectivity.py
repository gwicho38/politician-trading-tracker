"""
Continuous Supabase connectivity validation and monitoring
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .config import WorkflowConfig
from .database import PoliticianTradingDB

logger = logging.getLogger(__name__)
console = Console()


class SupabaseConnectivityValidator:
    """Validates and monitors Supabase connectivity in real-time"""

    def __init__(self, config: WorkflowConfig = None):
        self.config = config or WorkflowConfig.default()
        self.db = PoliticianTradingDB(self.config)
        self.last_test_results = {}

    async def validate_connectivity(self) -> Dict[str, Any]:
        """Comprehensive connectivity validation"""
        validation_start = time.time()
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "unknown",
            "tests": {},
            "duration_ms": 0,
            "supabase_url": self.config.supabase.url,
            "connectivity_score": 0,
        }

        tests = [
            ("basic_connection", self._test_basic_connection),
            ("read_operations", self._test_read_operations),
            ("write_operations", self._test_write_operations),
            ("table_access", self._test_table_access),
            ("job_tracking", self._test_job_tracking),
            ("real_time_sync", self._test_real_time_sync),
        ]

        passed_tests = 0

        for test_name, test_func in tests:
            try:
                test_start = time.time()
                test_result = await test_func()
                test_duration = (time.time() - test_start) * 1000

                results["tests"][test_name] = {
                    "status": "passed" if test_result["success"] else "failed",
                    "duration_ms": round(test_duration, 2),
                    "details": test_result,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                if test_result["success"]:
                    passed_tests += 1

            except Exception as e:
                results["tests"][test_name] = {
                    "status": "error",
                    "duration_ms": 0,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        # Calculate overall status
        connectivity_score = (passed_tests / len(tests)) * 100
        results["connectivity_score"] = round(connectivity_score, 1)

        if connectivity_score >= 90:
            results["overall_status"] = "excellent"
        elif connectivity_score >= 75:
            results["overall_status"] = "good"
        elif connectivity_score >= 50:
            results["overall_status"] = "degraded"
        else:
            results["overall_status"] = "critical"

        results["duration_ms"] = round((time.time() - validation_start) * 1000, 2)
        self.last_test_results = results

        return results

    async def _test_basic_connection(self) -> Dict[str, Any]:
        """Test basic database connection"""
        try:
            # Test basic REST API connectivity instead of RPC
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.config.supabase.url + "/rest/v1/",
                    headers={"apikey": self.config.supabase.key},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Basic connection successful",
                        "status_code": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text[:100]}",
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_read_operations(self) -> Dict[str, Any]:
        """Test read operations"""
        try:
            # Try reading from multiple tables
            tables_to_test = [
                "politicians",
                "trading_disclosures",
                "data_pull_jobs",
                "data_sources",
            ]
            read_results = {}
            schema_missing = False

            for table in tables_to_test:
                try:
                    result = self.db.client.table(table).select("*").limit(1).execute()
                    read_results[table] = "accessible"
                except Exception as e:
                    error_msg = str(e)
                    if "Could not find" in error_msg and "schema cache" in error_msg:
                        read_results[table] = "table_missing"
                        schema_missing = True
                    else:
                        read_results[table] = f"error: {error_msg[:50]}..."

            accessible_count = sum(1 for status in read_results.values() if status == "accessible")
            missing_count = sum(1 for status in read_results.values() if status == "table_missing")

            if schema_missing and accessible_count == 0:
                return {
                    "success": False,
                    "tables_tested": read_results,
                    "accessible_tables": accessible_count,
                    "missing_tables": missing_count,
                    "message": "Database schema not set up. Run 'mcli workflow politician-trading setup --generate-schema' to get setup instructions.",
                }
            else:
                success = accessible_count > 0
                return {
                    "success": success,
                    "tables_tested": read_results,
                    "accessible_tables": accessible_count,
                    "missing_tables": missing_count,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_write_operations(self) -> Dict[str, Any]:
        """Test write operations with a connectivity test record"""
        try:
            test_job_id = f"connectivity_test_{int(time.time())}"

            # Create a test job record
            try:
                insert_result = (
                    self.db.client.table("data_pull_jobs")
                    .insert(
                        {
                            "job_type": "connectivity_test",
                            "status": "running",
                            "started_at": datetime.utcnow().isoformat(),
                            "config_snapshot": {
                                "test": True,
                                "validator": "SupabaseConnectivityValidator",
                            },
                        }
                    )
                    .execute()
                )
            except Exception as e:
                if "Could not find" in str(e) and "schema cache" in str(e):
                    return {
                        "success": False,
                        "error": "Table 'data_pull_jobs' not found",
                        "message": "Database schema not set up. Run schema setup first.",
                    }
                else:
                    raise e

            # Get the inserted record ID
            if insert_result.data and len(insert_result.data) > 0:
                inserted_id = insert_result.data[0]["id"]

                # Update the record
                update_result = (
                    self.db.client.table("data_pull_jobs")
                    .update(
                        {
                            "status": "completed",
                            "completed_at": datetime.utcnow().isoformat(),
                            "records_processed": 1,
                        }
                    )
                    .eq("id", inserted_id)
                    .execute()
                )

                # Read it back
                read_result = (
                    self.db.client.table("data_pull_jobs")
                    .select("*")
                    .eq("id", inserted_id)
                    .execute()
                )
            else:
                return {"success": False, "error": "Failed to get inserted record ID"}

            # Clean up test record
            self.db.client.table("data_pull_jobs").delete().eq("id", inserted_id).execute()

            return {
                "success": True,
                "message": "Write operations successful",
                "operations_tested": ["insert", "update", "select", "delete"],
                "test_record_id": test_job_id,
                "record_retrieved": len(read_result.data) > 0 if read_result.data else False,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_table_access(self) -> Dict[str, Any]:
        """Test access to all required tables"""
        try:
            required_tables = {
                "politicians": ["id", "full_name", "role"],
                "trading_disclosures": ["id", "politician_id", "transaction_date"],
                "data_pull_jobs": ["id", "job_type", "status"],
                "data_sources": ["id", "name", "url"],
            }

            table_access = {}

            for table_name, required_columns in required_tables.items():
                try:
                    # Test table structure
                    result = (
                        self.db.client.table(table_name)
                        .select(",".join(required_columns))
                        .limit(1)
                        .execute()
                    )
                    table_access[table_name] = {
                        "accessible": True,
                        "columns_verified": required_columns,
                        "record_count_sample": len(result.data) if result.data else 0,
                    }
                except Exception as e:
                    table_access[table_name] = {"accessible": False, "error": str(e)}

            accessible_count = sum(
                1 for info in table_access.values() if info.get("accessible", False)
            )

            return {
                "success": accessible_count == len(required_tables),
                "tables_tested": len(required_tables),
                "tables_accessible": accessible_count,
                "table_details": table_access,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_job_tracking(self) -> Dict[str, Any]:
        """Test job tracking functionality"""
        try:
            # Get recent jobs
            recent_jobs = (
                self.db.client.table("data_pull_jobs")
                .select("*")
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )

            # Get job statistics
            job_stats = self.db.client.table("data_pull_jobs").select("status").execute()

            status_counts = {}
            if job_stats.data:
                for job in job_stats.data:
                    status = job.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "success": True,
                "recent_jobs_count": len(recent_jobs.data) if recent_jobs.data else 0,
                "total_jobs": len(job_stats.data) if job_stats.data else 0,
                "status_distribution": status_counts,
                "job_tracking_functional": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_real_time_sync(self) -> Dict[str, Any]:
        """Test real-time synchronization capabilities"""
        try:
            # Create a timestamped record and verify immediate retrieval
            timestamp = datetime.utcnow().isoformat()
            test_source_id = f"rt_test_{int(time.time())}"

            # Insert
            insert_result = (
                self.db.client.table("data_sources")
                .insert(
                    {
                        "name": "Real-time Test Source",
                        "url": "https://test.example.com",
                        "source_type": "test",
                        "region": "test",
                        "is_active": True,
                        "created_at": timestamp,
                    }
                )
                .execute()
            )

            if insert_result.data and len(insert_result.data) > 0:
                inserted_id = insert_result.data[0]["id"]

                # Immediate read-back
                result = (
                    self.db.client.table("data_sources").select("*").eq("id", inserted_id).execute()
                )

                # Clean up
                self.db.client.table("data_sources").delete().eq("id", inserted_id).execute()
            else:
                return {"success": False, "error": "Failed to insert test record"}

            sync_successful = len(result.data) > 0 if result.data else False

            return {
                "success": sync_successful,
                "message": "Real-time sync test completed",
                "record_immediately_available": sync_successful,
                "test_timestamp": timestamp,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def display_connectivity_report(self, results: Dict[str, Any]):
        """Display a formatted connectivity report"""
        console.print(
            f"\n🔗 Supabase Connectivity Report - {results['timestamp']}", style="bold cyan"
        )

        # Overall status
        status_colors = {
            "excellent": "bright_green",
            "good": "green",
            "degraded": "yellow",
            "critical": "red",
        }

        status_color = status_colors.get(results["overall_status"], "white")

        overall_panel = Panel(
            f"Status: [{status_color}]{results['overall_status'].upper()}[/{status_color}]\n"
            f"Connectivity Score: {results['connectivity_score']}%\n"
            f"Test Duration: {results['duration_ms']}ms\n"
            f"Supabase URL: {results['supabase_url']}",
            title="🎯 Overall Connectivity",
            border_style=status_color,
        )
        console.print(overall_panel)

        # Test results table
        test_table = Table(title="Test Results")
        test_table.add_column("Test", style="cyan")
        test_table.add_column("Status", style="bold")
        test_table.add_column("Duration", justify="right")
        test_table.add_column("Details")

        for test_name, test_result in results["tests"].items():
            status = test_result["status"]
            status_style = {"passed": "green", "failed": "red", "error": "red"}.get(status, "white")

            details = ""
            if "details" in test_result:
                if "message" in test_result["details"]:
                    details = test_result["details"]["message"]
                elif "operations_tested" in test_result["details"]:
                    details = f"Ops: {', '.join(test_result['details']['operations_tested'])}"
                elif "tables_accessible" in test_result["details"]:
                    details = f"{test_result['details']['tables_accessible']}/{test_result['details']['tables_tested']} tables"

            if "error" in test_result:
                details = (
                    test_result["error"][:50] + "..."
                    if len(test_result["error"]) > 50
                    else test_result["error"]
                )

            test_table.add_row(
                test_name.replace("_", " ").title(),
                f"[{status_style}]{status.upper()}[/{status_style}]",
                f"{test_result['duration_ms']:.1f}ms",
                details,
            )

        console.print(test_table)

    async def continuous_monitoring(self, interval_seconds: int = 30, duration_minutes: int = 0):
        """Run continuous connectivity monitoring"""
        console.print(
            f"🔄 Starting continuous Supabase connectivity monitoring (interval: {interval_seconds}s)",
            style="bold blue",
        )

        start_time = time.time()
        check_count = 0

        try:
            while True:
                check_count += 1
                console.print(
                    f"\n📊 Check #{check_count} - {datetime.now().strftime('%H:%M:%S')}",
                    style="dim",
                )

                # Run validation
                results = await self.validate_connectivity()
                self.display_connectivity_report(results)

                # Check duration limit
                if duration_minutes > 0:
                    elapsed_minutes = (time.time() - start_time) / 60
                    if elapsed_minutes >= duration_minutes:
                        console.print(
                            f"\n⏰ Monitoring completed after {duration_minutes} minutes",
                            style="green",
                        )
                        break

                # Wait for next check
                console.print(
                    f"\n⏱️ Next check in {interval_seconds} seconds... (Ctrl+C to stop)", style="dim"
                )
                await asyncio.sleep(interval_seconds)

        except KeyboardInterrupt:
            console.print("\n👋 Monitoring stopped by user", style="yellow")
        except Exception as e:
            console.print(f"\n❌ Monitoring error: {e}", style="red")


async def run_connectivity_validation() -> Dict[str, Any]:
    """Standalone function to run connectivity validation"""
    validator = SupabaseConnectivityValidator()
    return await validator.validate_connectivity()


async def run_continuous_monitoring(interval: int = 30, duration: int = 0):
    """Standalone function for continuous monitoring"""
    validator = SupabaseConnectivityValidator()
    await validator.continuous_monitoring(interval, duration)


if __name__ == "__main__":
    # Allow running this file directly for testing
    async def main():
        validator = SupabaseConnectivityValidator()

        console.print("🧪 Running Supabase connectivity validation...", style="bold blue")
        results = await validator.validate_connectivity()
        validator.display_connectivity_report(results)

    asyncio.run(main())
