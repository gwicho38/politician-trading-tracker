"""
Capitol Trades - Supabase Sync Module

This module provides functions to sync data from your Python scraper/processor
to the Supabase database used by the React frontend.

Usage:
    from supabase_sync import CapitolTradesSync
    
    sync = CapitolTradesSync()
    sync.upsert_politician(name="Nancy Pelosi", party="D", chamber="House", state="CA")
    sync.insert_trade(politician_id="...", ticker="NVDA", ...)
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("Please install supabase: pip install supabase")


class Party(Enum):
    DEMOCRAT = "D"
    REPUBLICAN = "R"
    INDEPENDENT = "I"
    OTHER = "Other"


class TradeType(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class PoliticianData:
    name: str
    party: str
    chamber: str
    jurisdiction_id: str
    state: Optional[str] = None
    avatar_url: Optional[str] = None


@dataclass
class TradeData:
    politician_id: str
    ticker: str
    company: str
    trade_type: str
    amount_range: str
    estimated_value: int
    filing_date: str
    transaction_date: str


class CapitolTradesSync:
    """
    Main sync class for Capitol Trades data.
    
    Initialize with Supabase credentials either from environment variables
    or passed directly.
    """
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        self.url = supabase_url or os.environ.get(
            "SUPABASE_URL", 
            "https://ogdwavsrcyleoxfsswbt.supabase.co"
        )
        self.key = supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY must be set in environment or passed to constructor"
            )
        
        self.client: Client = create_client(self.url, self.key)
    
    # ==================== JURISDICTIONS ====================
    
    def upsert_jurisdiction(
        self,
        id: str,
        name: str,
        flag: str
    ) -> Optional[Dict[str, Any]]:
        """
        Insert or update a jurisdiction.
        
        Args:
            id: Unique identifier (e.g., 'us-house', 'eu-parliament')
            name: Display name (e.g., 'US House', 'EU Parliament')
            flag: Emoji flag (e.g., '🇺🇸', '🇪🇺')
        
        Returns:
            The upserted record or None if failed
        """
        data = {"id": id, "name": name, "flag": flag}
        result = self.client.table("jurisdictions").upsert(data).execute()
        return result.data[0] if result.data else None
    
    def get_jurisdictions(self) -> List[Dict[str, Any]]:
        """Get all jurisdictions."""
        result = self.client.table("jurisdictions").select("*").execute()
        return result.data or []
    
    # ==================== POLITICIANS ====================
    
    def upsert_politician(
        self,
        name: str,
        party: str,
        chamber: str,
        jurisdiction_id: str,
        state: Optional[str] = None,
        avatar_url: Optional[str] = None,
        total_trades: int = 0,
        total_volume: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Insert or update a politician.
        
        Args:
            name: Full name
            party: 'D', 'R', 'I', or 'Other'
            chamber: 'House', 'Senate', etc.
            jurisdiction_id: Reference to jurisdiction
            state: Two-letter state code (optional)
            avatar_url: URL to profile image (optional)
            total_trades: Number of trades (will be recalculated)
            total_volume: Total trading volume (will be recalculated)
        
        Returns:
            The upserted record or None if failed
        """
        # Validate party
        valid_parties = ['D', 'R', 'I', 'Other']
        if party not in valid_parties:
            raise ValueError(f"party must be one of {valid_parties}")
        
        data = {
            "name": name,
            "party": party,
            "chamber": chamber,
            "jurisdiction_id": jurisdiction_id,
            "state": state,
            "avatar_url": avatar_url,
            "total_trades": total_trades,
            "total_volume": total_volume,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Check if exists by name
        existing = self.client.table("politicians").select("id").eq("name", name).execute()
        
        if existing.data:
            result = self.client.table("politicians").update(data).eq("id", existing.data[0]["id"]).execute()
        else:
            result = self.client.table("politicians").insert(data).execute()
        
        return result.data[0] if result.data else None
    
    def get_politician_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a politician by name."""
        result = self.client.table("politicians").select("*").eq("name", name).execute()
        return result.data[0] if result.data else None
    
    def get_politicians(self, jurisdiction_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all politicians, optionally filtered by jurisdiction."""
        query = self.client.table("politicians").select("*")
        if jurisdiction_id:
            query = query.eq("jurisdiction_id", jurisdiction_id)
        result = query.order("total_volume", desc=True).execute()
        return result.data or []
    
    def update_politician_totals(self, politician_id: str) -> None:
        """Recalculate a politician's trade totals from their trades."""
        trades = self.client.table("trades").select("estimated_value").eq("politician_id", politician_id).execute()
        
        if trades.data:
            total_trades = len(trades.data)
            total_volume = sum(t["estimated_value"] for t in trades.data)
            
            self.client.table("politicians").update({
                "total_trades": total_trades,
                "total_volume": total_volume,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", politician_id).execute()
    
    # ==================== TRADES ====================
    
    def insert_trade(
        self,
        politician_id: str,
        ticker: str,
        company: str,
        trade_type: str,
        amount_range: str,
        estimated_value: int,
        filing_date: str,
        transaction_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Insert a trade record.
        
        Args:
            politician_id: UUID of the politician
            ticker: Stock ticker symbol
            company: Company name
            trade_type: 'buy' or 'sell' (lowercase)
            amount_range: e.g., '$1,001 - $15,000'
            estimated_value: Integer estimate of value
            filing_date: 'YYYY-MM-DD' format
            transaction_date: 'YYYY-MM-DD' format
        
        Returns:
            The inserted record or None if failed
        """
        # Validate trade_type
        trade_type = trade_type.lower()
        if trade_type not in ['buy', 'sell']:
            raise ValueError("trade_type must be 'buy' or 'sell'")
        
        data = {
            "politician_id": politician_id,
            "ticker": ticker.upper(),
            "company": company,
            "trade_type": trade_type,
            "amount_range": amount_range,
            "estimated_value": estimated_value,
            "filing_date": filing_date,
            "transaction_date": transaction_date
        }
        
        result = self.client.table("trades").insert(data).execute()
        return result.data[0] if result.data else None
    
    def bulk_insert_trades(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Insert multiple trades at once.
        
        Args:
            trades: List of trade dictionaries
        
        Returns:
            List of inserted records
        """
        # Normalize trade_type to lowercase
        for trade in trades:
            trade["trade_type"] = trade["trade_type"].lower()
            trade["ticker"] = trade["ticker"].upper()
        
        result = self.client.table("trades").insert(trades).execute()
        return result.data or []
    
    def get_trades(
        self,
        limit: int = 100,
        politician_id: Optional[str] = None,
        jurisdiction_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get trades with optional filters."""
        query = self.client.table("trades").select("*, politician:politicians(*)")
        
        if politician_id:
            query = query.eq("politician_id", politician_id)
        
        result = query.order("filing_date", desc=True).limit(limit).execute()
        return result.data or []
    
    def check_trade_exists(
        self,
        politician_id: str,
        ticker: str,
        transaction_date: str,
        trade_type: str
    ) -> bool:
        """Check if a trade already exists (for deduplication)."""
        result = self.client.table("trades").select("id").eq(
            "politician_id", politician_id
        ).eq("ticker", ticker).eq("transaction_date", transaction_date).eq(
            "trade_type", trade_type.lower()
        ).execute()
        return len(result.data) > 0 if result.data else False
    
    # ==================== CHART DATA ====================
    
    def upsert_chart_data(
        self,
        year: int,
        month: str,
        buys: int,
        sells: int,
        volume: int
    ) -> Optional[Dict[str, Any]]:
        """
        Insert or update monthly chart data.
        
        Args:
            year: Year (e.g., 2024)
            month: Month abbreviation (e.g., 'Jan', 'Feb')
            buys: Number of buy trades
            sells: Number of sell trades
            volume: Total trading volume
        """
        data = {
            "year": year,
            "month": month,
            "buys": buys,
            "sells": sells,
            "volume": volume
        }
        
        existing = self.client.table("chart_data").select("id").eq("year", year).eq("month", month).execute()
        
        if existing.data:
            result = self.client.table("chart_data").update(data).eq("id", existing.data[0]["id"]).execute()
        else:
            result = self.client.table("chart_data").insert(data).execute()
        
        return result.data[0] if result.data else None
    
    def recalculate_chart_data(self) -> None:
        """Recalculate all chart data from trades."""
        # Get all trades
        trades = self.client.table("trades").select("trade_type, estimated_value, filing_date").execute()
        
        if not trades.data:
            return
        
        # Aggregate by year/month
        monthly_data: Dict[str, Dict[str, Any]] = {}
        
        for trade in trades.data:
            date = datetime.strptime(trade["filing_date"], "%Y-%m-%d")
            key = f"{date.year}-{date.strftime('%b')}"
            
            if key not in monthly_data:
                monthly_data[key] = {
                    "year": date.year,
                    "month": date.strftime("%b"),
                    "buys": 0,
                    "sells": 0,
                    "volume": 0
                }
            
            if trade["trade_type"] == "buy":
                monthly_data[key]["buys"] += 1
            else:
                monthly_data[key]["sells"] += 1
            
            monthly_data[key]["volume"] += trade["estimated_value"]
        
        # Upsert all
        for data in monthly_data.values():
            self.upsert_chart_data(**data)
    
    # ==================== DASHBOARD STATS ====================
    
    def update_dashboard_stats(
        self,
        total_trades: int,
        total_volume: int,
        active_politicians: int,
        jurisdictions_tracked: int,
        average_trade_size: int,
        recent_filings: int
    ) -> Optional[Dict[str, Any]]:
        """Update dashboard statistics."""
        data = {
            "total_trades": total_trades,
            "total_volume": total_volume,
            "active_politicians": active_politicians,
            "jurisdictions_tracked": jurisdictions_tracked,
            "average_trade_size": average_trade_size,
            "recent_filings": recent_filings,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        existing = self.client.table("dashboard_stats").select("id").limit(1).execute()
        
        if existing.data:
            result = self.client.table("dashboard_stats").update(data).eq("id", existing.data[0]["id"]).execute()
        else:
            result = self.client.table("dashboard_stats").insert(data).execute()
        
        return result.data[0] if result.data else None
    
    def recalculate_dashboard_stats(self) -> Dict[str, Any]:
        """Recalculate all dashboard statistics from the data."""
        politicians = self.client.table("politicians").select("id", count="exact").execute()
        trades = self.client.table("trades").select("estimated_value").execute()
        jurisdictions = self.client.table("jurisdictions").select("id", count="exact").execute()
        
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent = self.client.table("trades").select("id", count="exact").gte("filing_date", week_ago).execute()
        
        total_volume = sum(t["estimated_value"] for t in trades.data) if trades.data else 0
        total_trades = len(trades.data) if trades.data else 0
        avg_trade_size = total_volume // total_trades if total_trades > 0 else 0
        
        return self.update_dashboard_stats(
            total_trades=total_trades,
            total_volume=total_volume,
            active_politicians=politicians.count or 0,
            jurisdictions_tracked=jurisdictions.count or 0,
            average_trade_size=avg_trade_size,
            recent_filings=recent.count or 0
        )
    
    # ==================== SYNC LOGGING ====================
    
    def start_sync_log(
        self,
        sync_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a sync operation and create a log entry.
        
        Args:
            sync_type: Type of sync ('filing', 'politician', 'trade', 'full_sync', 'chart_data', 'dashboard_stats')
            metadata: Optional additional metadata
        
        Returns:
            The sync log ID
        """
        data = {
            "sync_type": sync_type,
            "status": "running",
            "metadata": metadata or {},
            "started_at": datetime.utcnow().isoformat()
        }
        
        result = self.client.table("sync_logs").insert(data).execute()
        return result.data[0]["id"] if result.data else None
    
    def complete_sync_log(
        self,
        log_id: str,
        status: str = "success",
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """
        Complete a sync operation log.
        
        Args:
            log_id: The sync log ID
            status: 'success' or 'failed'
            records_processed: Total records processed
            records_created: New records created
            records_updated: Records updated
            error_message: Error message if failed
        """
        data = {
            "status": status,
            "records_processed": records_processed,
            "records_created": records_created,
            "records_updated": records_updated,
            "error_message": error_message,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        self.client.table("sync_logs").update(data).eq("id", log_id).execute()
    
    # ==================== NOTIFICATIONS ====================
    
    def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: 'info', 'success', 'warning', or 'error'
            user_id: Target user ID or None for global notification
        """
        data = {
            "title": title,
            "message": message,
            "type": notification_type,
            "user_id": user_id,
            "read": False
        }
        
        result = self.client.table("notifications").insert(data).execute()
        return result.data[0] if result.data else None
    
    def notify_admins_on_failure(self, sync_type: str, error_message: str) -> None:
        """
        Notify all admin users when a sync operation fails.
        
        Args:
            sync_type: Type of sync that failed
            error_message: Error message to include
        """
        # Get all admin users
        admins = self.client.table("user_roles").select("user_id").eq("role", "admin").execute()
        
        for admin in admins.data or []:
            self.create_notification(
                title="Sync Failed",
                message=f"{sync_type} sync failed: {error_message}",
                notification_type="error",
                user_id=admin["user_id"]
            )
    
    # ==================== HIGH-LEVEL SYNC ====================
    
    def sync_filing(self, filing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync a complete filing (politician + trades) with logging.
        
        Args:
            filing_data: {
                "politician": {
                    "name": str,
                    "party": str,
                    "chamber": str,
                    "jurisdiction_id": str,
                    "state": str (optional)
                },
                "trades": [
                    {
                        "ticker": str,
                        "company": str,
                        "type": str,
                        "amount_range": str,
                        "estimated_value": int,
                        "filing_date": str,
                        "transaction_date": str
                    }
                ]
            }
        
        Returns:
            Sync result with stats
        """
        pol_data = filing_data["politician"]
        log_id = self.start_sync_log("filing", {"politician": pol_data["name"]})
        
        try:
            # Upsert politician
            politician = self.upsert_politician(
                name=pol_data["name"],
                party=pol_data["party"],
                chamber=pol_data["chamber"],
                jurisdiction_id=pol_data.get("jurisdiction_id", "us-house"),
                state=pol_data.get("state")
            )
            
            if not politician:
                raise Exception(f"Failed to upsert politician: {pol_data['name']}")
            
            # Insert trades (with deduplication)
            new_trades = 0
            total_trades = len(filing_data["trades"])
            
            for trade in filing_data["trades"]:
                # Check if trade already exists
                if not self.check_trade_exists(
                    politician["id"],
                    trade["ticker"],
                    trade["transaction_date"],
                    trade["type"]
                ):
                    self.insert_trade(
                        politician_id=politician["id"],
                        ticker=trade["ticker"],
                        company=trade["company"],
                        trade_type=trade["type"],
                        amount_range=trade["amount_range"],
                        estimated_value=trade["estimated_value"],
                        filing_date=trade["filing_date"],
                        transaction_date=trade["transaction_date"]
                    )
                    new_trades += 1
            
            # Update totals
            self.update_politician_totals(politician["id"])
            
            # Create notification if new trades
            if new_trades > 0:
                self.create_notification(
                    title="New Filing",
                    message=f"{pol_data['name']} filed {new_trades} new trade(s)",
                    notification_type="info"
                )
            
            # Complete sync log
            self.complete_sync_log(
                log_id,
                status="success",
                records_processed=total_trades,
                records_created=new_trades,
                records_updated=1 if politician else 0
            )
            
            return {
                "status": "success",
                "politician_id": politician["id"],
                "trades_processed": total_trades,
                "new_trades": new_trades
            }
            
        except Exception as e:
            self.complete_sync_log(log_id, status="failed", error_message=str(e))
            self.notify_admins_on_failure("Filing", str(e))
            raise
    
    def full_sync(self) -> Dict[str, Any]:
        """
        Run a full recalculation of all derived data with logging.
        
        Returns:
            Updated dashboard stats
        """
        log_id = self.start_sync_log("full_sync")
        
        try:
            # Recalculate all politician totals
            politicians = self.get_politicians()
            for pol in politicians:
                self.update_politician_totals(pol["id"])
            
            # Recalculate chart data
            self.recalculate_chart_data()
            
            # Recalculate dashboard stats
            stats = self.recalculate_dashboard_stats()
            
            self.complete_sync_log(
                log_id,
                status="success",
                records_processed=len(politicians),
                records_updated=len(politicians)
            )
            
            return stats
            
        except Exception as e:
            self.complete_sync_log(log_id, status="failed", error_message=str(e))
            self.notify_admins_on_failure("Full", str(e))
            raise


# Convenience function for quick usage
def get_sync_client() -> CapitolTradesSync:
    """Get a configured sync client using environment variables."""
    return CapitolTradesSync()


if __name__ == "__main__":
    # Test the sync
    sync = get_sync_client()
    
    # Example: Sync a filing
    test_filing = {
        "politician": {
            "name": "Test Politician",
            "party": "D",
            "chamber": "House",
            "jurisdiction_id": "us-house",
            "state": "CA"
        },
        "trades": [
            {
                "ticker": "AAPL",
                "company": "Apple Inc.",
                "type": "buy",
                "amount_range": "$15,001 - $50,000",
                "estimated_value": 32500,
                "filing_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "transaction_date": (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%d")
            }
        ]
    }
    
    print("Testing sync...")
    sync.sync_filing(test_filing)
    print("Sync complete!")
    
    stats = sync.recalculate_dashboard_stats()
    print(f"Dashboard stats: {stats}")
