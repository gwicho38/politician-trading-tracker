"""
Monitoring and status reporting for politician trading data collection
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import WorkflowConfig
from .database import PoliticianTradingDB

logger = logging.getLogger(__name__)
console = Console()


class PoliticianTradingMonitor:
    """Monitor and report on politician trading data collection"""

    def __init__(self, config: WorkflowConfig = None):
        self.config = config or WorkflowConfig.default()
        self.db = PoliticianTradingDB(self.config)

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown",
            "database": {"status": "unknown"},
            "data_freshness": {"status": "unknown"},
            "recent_jobs": {"status": "unknown"},
            "errors": [],
        }

        try:
            # Test database connection
            db_health = await self._check_database_health()
            health["database"] = db_health

            # Check data freshness
            freshness = await self._check_data_freshness()
            health["data_freshness"] = freshness

            # Check recent job status
            job_health = await self._check_recent_jobs()
            health["recent_jobs"] = job_health

            # Determine overall status
            if all(h["status"] == "healthy" for h in [db_health, freshness, job_health]):
                health["status"] = "healthy"
            elif any(h["status"] == "critical" for h in [db_health, freshness, job_health]):
                health["status"] = "critical"
            else:
                health["status"] = "degraded"

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["status"] = "critical"
            health["errors"].append(str(e))

        return health

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations"""
        try:
            # Test connection with a simple query
            result = self.db.client.table("data_pull_jobs").select("count").execute()

            return {
                "status": "healthy",
                "connection": "ok",
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "critical",
                "connection": "failed",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }

    async def _check_data_freshness(self) -> Dict[str, Any]:
        """Check how fresh our data is"""
        try:
            # Get most recent disclosure
            recent_disclosures = (
                self.db.client.table("trading_disclosures")
                .select("created_at")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            # Get most recent successful job
            recent_jobs = (
                self.db.client.table("data_pull_jobs")
                .select("completed_at")
                .eq("status", "completed")
                .order("completed_at", desc=True)
                .limit(1)
                .execute()
            )

            now = datetime.now(timezone.utc)
            status = "healthy"

            # Check if we have recent data
            if recent_disclosures.data:
                last_disclosure = datetime.fromisoformat(
                    recent_disclosures.data[0]["created_at"].replace("Z", "+00:00")
                )
                hours_since_disclosure = (now - last_disclosure).total_seconds() / 3600

                if hours_since_disclosure > 168:  # 1 week
                    status = "critical"
                elif hours_since_disclosure > 48:  # 2 days
                    status = "degraded"
            else:
                status = "critical"  # No disclosures at all

            # Check recent job success
            if recent_jobs.data:
                last_job = datetime.fromisoformat(
                    recent_jobs.data[0]["completed_at"].replace("Z", "+00:00")
                )
                hours_since_job = (now - last_job).total_seconds() / 3600

                if hours_since_job > 24:  # Should run at least daily
                    status = "degraded" if status == "healthy" else status
            else:
                status = "critical"  # No successful jobs

            return {
                "status": status,
                "last_disclosure": (
                    recent_disclosures.data[0]["created_at"] if recent_disclosures.data else None
                ),
                "last_successful_job": (
                    recent_jobs.data[0]["completed_at"] if recent_jobs.data else None
                ),
                "hours_since_disclosure": (
                    hours_since_disclosure if recent_disclosures.data else None
                ),
                "hours_since_job": hours_since_job if recent_jobs.data else None,
            }

        except Exception as e:
            return {"status": "critical", "error": str(e)}

    async def _check_recent_jobs(self) -> Dict[str, Any]:
        """Check recent job execution status"""
        try:
            # Get jobs from last 24 hours
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)

            recent_jobs = (
                self.db.client.table("data_pull_jobs")
                .select("*")
                .gte("started_at", yesterday.isoformat())
                .order("started_at", desc=True)
                .execute()
            )

            if not recent_jobs.data:
                return {
                    "status": "degraded",
                    "message": "No jobs executed in last 24 hours",
                    "job_count": 0,
                }

            jobs = recent_jobs.data
            total_jobs = len(jobs)
            failed_jobs = len([j for j in jobs if j["status"] == "failed"])
            success_rate = (total_jobs - failed_jobs) / total_jobs if total_jobs > 0 else 0

            if success_rate >= 0.8:
                status = "healthy"
            elif success_rate >= 0.5:
                status = "degraded"
            else:
                status = "critical"

            return {
                "status": status,
                "job_count": total_jobs,
                "failed_jobs": failed_jobs,
                "success_rate": round(success_rate * 100, 1),
                "recent_jobs": jobs[:5],  # Last 5 jobs
            }

        except Exception as e:
            return {"status": "critical", "error": str(e)}

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the data collection"""
        try:
            # Get total counts
            politicians_result = self.db.client.table("politicians").select("id").execute()

            disclosures_result = self.db.client.table("trading_disclosures").select("id").execute()

            jobs_result = self.db.client.table("data_pull_jobs").select("id").execute()

            # Get breakdown by region/role
            us_politicians = (
                self.db.client.table("politicians")
                .select("id")
                .in_("role", ["us_house_rep", "us_senator"])
                .execute()
            )

            eu_politicians = (
                self.db.client.table("politicians").select("id").eq("role", "eu_mep").execute()
            )

            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_disclosures = (
                self.db.client.table("trading_disclosures")
                .select("id")
                .gte("created_at", thirty_days_ago.isoformat())
                .execute()
            )

            # Get top assets by volume
            top_assets = (
                self.db.client.table("trading_disclosures")
                .select("asset_ticker")
                .not_.is_("asset_ticker", "null")
                .limit(100)
                .execute()
            )

            return {
                "total_counts": {
                    "politicians": len(politicians_result.data) if politicians_result.data else 0,
                    "disclosures": len(disclosures_result.data) if disclosures_result.data else 0,
                    "jobs": len(jobs_result.data) if jobs_result.data else 0,
                },
                "politician_breakdown": {
                    "us_total": len(us_politicians.data) if us_politicians.data else 0,
                    "eu_total": len(eu_politicians.data) if eu_politicians.data else 0,
                },
                "recent_activity": {
                    "disclosures_last_30_days": (
                        len(recent_disclosures.data) if recent_disclosures.data else 0
                    )
                },
                "top_assets": top_assets.data if top_assets.data else [],
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get detailed stats: {e}")
            return {"error": str(e)}

    def display_health_report(self, health: Dict[str, Any]):
        """Display a formatted health report"""
        console.print("\n🏛️ Politician Trading Monitor - System Health", style="bold cyan")

        # Overall status
        status_color = {
            "healthy": "green",
            "degraded": "yellow",
            "critical": "red",
            "unknown": "white",
        }.get(health["status"], "white")

        status_panel = Panel(
            f"Overall Status: [{status_color}]{health['status'].upper()}[/{status_color}]\n"
            f"Last Check: {health['timestamp']}",
            title="🎯 System Status",
            border_style=status_color,
        )
        console.print(status_panel)

        # Database health
        db_status = health.get("database", {})
        db_color = "green" if db_status.get("status") == "healthy" else "red"

        db_panel = Panel(
            f"Connection: [{db_color}]{db_status.get('connection', 'unknown')}[/{db_color}]\n"
            f"Last Check: {db_status.get('last_check', 'unknown')}",
            title="💾 Database",
            border_style=db_color,
        )
        console.print(db_panel)

        # Data freshness
        freshness = health.get("data_freshness", {})
        fresh_color = {"healthy": "green", "degraded": "yellow", "critical": "red"}.get(
            freshness.get("status"), "white"
        )

        fresh_text = (
            f"Status: [{fresh_color}]{freshness.get('status', 'unknown')}[/{fresh_color}]\n"
        )

        if freshness.get("hours_since_disclosure"):
            fresh_text += (
                f"Hours since last disclosure: {freshness['hours_since_disclosure']:.1f}\n"
            )
        if freshness.get("hours_since_job"):
            fresh_text += f"Hours since last job: {freshness['hours_since_job']:.1f}"

        fresh_panel = Panel(fresh_text, title="🕒 Data Freshness", border_style=fresh_color)
        console.print(fresh_panel)

        # Recent jobs
        jobs = health.get("recent_jobs", {})
        job_color = {"healthy": "green", "degraded": "yellow", "critical": "red"}.get(
            jobs.get("status"), "white"
        )

        job_text = f"Status: [{job_color}]{jobs.get('status', 'unknown')}[/{job_color}]\n"
        if jobs.get("job_count"):
            job_text += f"Jobs (24h): {jobs['job_count']}\n"
            job_text += f"Success Rate: {jobs.get('success_rate', 0)}%"

        job_panel = Panel(job_text, title="🔄 Recent Jobs", border_style=job_color)
        console.print(job_panel)

        # Errors
        if health.get("errors"):
            error_panel = Panel("\n".join(health["errors"]), title="⚠️ Errors", border_style="red")
            console.print(error_panel)

    def display_stats_report(self, stats: Dict[str, Any]):
        """Display detailed statistics"""
        if "error" in stats:
            console.print(f"❌ Failed to generate stats: {stats['error']}", style="red")
            return

        console.print("\n📊 Detailed Statistics", style="bold blue")

        # Summary table
        summary_table = Table(title="Summary Counts")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", justify="right", style="green")

        total = stats.get("total_counts", {})
        breakdown = stats.get("politician_breakdown", {})

        summary_table.add_row("Total Politicians", f"{total.get('politicians', 0):,}")
        summary_table.add_row("- US Politicians", f"{breakdown.get('us_total', 0):,}")
        summary_table.add_row("- EU Politicians", f"{breakdown.get('eu_total', 0):,}")
        summary_table.add_row("Total Disclosures", f"{total.get('disclosures', 0):,}")
        summary_table.add_row(
            "Recent Disclosures (30d)",
            f"{stats.get('recent_activity', {}).get('disclosures_last_30_days', 0):,}",
        )
        summary_table.add_row("Total Jobs", f"{total.get('jobs', 0):,}")

        console.print(summary_table)

        # Top assets
        if stats.get("top_assets"):
            assets_table = Table(title="Recent Assets")
            assets_table.add_column("Asset Ticker", style="cyan")

            # Group by asset ticker to count occurrences
            from collections import Counter

            asset_counts = Counter(
                asset.get("asset_ticker", "Unknown") for asset in stats["top_assets"]
            )

            for asset_ticker, count in asset_counts.most_common(5):  # Top 5
                assets_table.add_row(asset_ticker)

            console.print(assets_table)


async def run_health_check() -> Dict[str, Any]:
    """Standalone function to run health check"""
    monitor = PoliticianTradingMonitor()
    return await monitor.get_system_health()


async def run_stats_report() -> Dict[str, Any]:
    """Standalone function to generate stats report"""
    monitor = PoliticianTradingMonitor()
    return await monitor.get_detailed_stats()


if __name__ == "__main__":
    # Allow running this file directly for testing
    async def main():
        monitor = PoliticianTradingMonitor()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Checking system health...", total=None)

            health = await monitor.get_system_health()
            progress.update(task, description="Generating detailed stats...")

            stats = await monitor.get_detailed_stats()
            progress.remove_task(task)

        monitor.display_health_report(health)
        monitor.display_stats_report(stats)

    asyncio.run(main())
