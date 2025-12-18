"""
Capital Trades Synchronization Service

Handles synchronization between the complex politician_trading schema
and the simplified capital_trades schema for the React frontend.
"""

# type: ignore  # Supabase client returns dynamic JSON types that are hard to type properly

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from supabase import create_client, Client

from ..scrapers.seed_database import get_supabase_client
from ..utils.logger import create_logger

logger = create_logger("capital_trades_sync")


@dataclass
class PoliticianMapping:
    """Mapping between politician_trading.politicians and capital_trades.politicians"""
    id: str
    name: str
    party: str  # 'D', 'R', 'I', or 'Other'
    chamber: str  # 'House', 'Senate'
    jurisdiction_id: str  # 'us-house', 'us-senate', etc.
    state: Optional[str] = None
    avatar_url: Optional[str] = None
    total_trades: int = 0
    total_volume: int = 0


@dataclass
class TradeMapping:
    """Mapping between trading_disclosures and capital_trades.trades"""
    politician_id: str
    ticker: str
    company: str
    trade_type: str  # 'buy' or 'sell'
    amount_range: str
    estimated_value: int
    filing_date: str  # YYYY-MM-DD
    transaction_date: str  # YYYY-MM-DD


class PoliticianTransformer:
    """Transforms politician records from complex to simplified schema"""

    @staticmethod
    def transform_politician(politician_record: Dict[str, Any]) -> PoliticianMapping:  # type: ignore
        """Transform a politician record from the complex schema"""
        # Map role to chamber
        role = politician_record.get('role', '').lower()
        if 'house' in role:
            chamber = 'House'
            jurisdiction_id = 'us-house'
        elif 'senate' in role or 'senator' in role:
            chamber = 'Senate'
            jurisdiction_id = 'us-senate'
        else:
            chamber = 'Other'
            jurisdiction_id = 'other'

        # Standardize party
        party = politician_record.get('party', 'Other')
        if party not in ['D', 'R', 'I', 'Other']:
            party = 'Other'

        return PoliticianMapping(
            id=politician_record['id'],
            name=politician_record.get('full_name', politician_record.get('name', 'Unknown')),
            party=party,
            chamber=chamber,
            jurisdiction_id=jurisdiction_id,
            state=politician_record.get('state_or_country'),
            avatar_url=None,  # Will be added later if available
            total_trades=0,  # Will be calculated
            total_volume=0   # Will be calculated
        )


class TradeTransformer:
    """Transforms trade records from complex to simplified schema"""

    @staticmethod
    def transform_trade(disclosure_record: Dict[str, Any], politician_id: str) -> TradeMapping:
        """Transform a trading disclosure record to a trade record"""
        # Map transaction type
        transaction_type = disclosure_record.get('transaction_type', '').lower()
        if 'buy' in transaction_type or 'purchase' in transaction_type:
            trade_type = 'buy'
        elif 'sell' in transaction_type or 'sale' in transaction_type:
            trade_type = 'sell'
        else:
            trade_type = 'buy'  # Default to buy if unclear

        # Calculate estimated value from amount range
        estimated_value = TradeTransformer._calculate_estimated_value(
            disclosure_record.get('amount_range_min'),
            disclosure_record.get('amount_range_max'),
            disclosure_record.get('amount_exact')
        )

        # Format amount range
        amount_range = TradeTransformer._format_amount_range(
            disclosure_record.get('amount_range_min'),
            disclosure_record.get('amount_range_max'),
            disclosure_record.get('amount_exact')
        )

        return TradeMapping(
            politician_id=politician_id,
            ticker=disclosure_record.get('asset_ticker', ''),
            company=disclosure_record.get('asset_name', ''),
            trade_type=trade_type,
            amount_range=amount_range,
            estimated_value=estimated_value,
            filing_date=disclosure_record.get('disclosure_date', '').split('T')[0] if disclosure_record.get('disclosure_date') else '',
            transaction_date=disclosure_record.get('transaction_date', '').split('T')[0] if disclosure_record.get('transaction_date') else ''
        )

    @staticmethod
    def _calculate_estimated_value(min_val: Optional[float], max_val: Optional[float], exact_val: Optional[float]) -> int:
        """Calculate estimated value from amount fields"""
        if exact_val:
            return int(exact_val)
        elif min_val and max_val:
            return int((min_val + max_val) / 2)
        elif min_val:
            return int(min_val)
        elif max_val:
            return int(max_val)
        else:
            return 0

    @staticmethod
    def _format_amount_range(min_val: Optional[float], max_val: Optional[float], exact_val: Optional[float]) -> str:
        """Format amount range as string"""
        if exact_val:
            return f"${exact_val:,.0f}"
        elif min_val and max_val:
            return f"${min_val:,.0f} - ${max_val:,.0f}"
        elif min_val:
            return f"${min_val:,.0f}+"
        elif max_val:
            return f"Up to ${max_val:,.0f}"
        else:
            return "Unknown"


class CapitalTradesSync:
    """Main synchronization service for capital trades data"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logger

    def sync_all_politicians(self) -> int:  # type: ignore
        """Sync all politicians from complex to simplified schema"""
        self.logger.info("Starting politician synchronization")

        # Get all politicians from complex schema
        politicians = self.supabase.table("politicians").select("*").execute()

        synced_count = 0
        if politicians.data:
            for politician in politicians.data:
                try:
                    # Type cast to Dict
                    politician_dict = dict(politician) if politician else {}
                    mapping = PoliticianTransformer.transform_politician(politician_dict)
                    self._upsert_politician(mapping)
                    synced_count += 1
                except Exception as e:
                    politician_id = politician.get('id', 'unknown') if politician else 'unknown'
                    self.logger.error(f"Failed to sync politician {politician_id}: {e}")

        self.logger.info(f"Synchronized {synced_count} politicians")
        return synced_count

    def sync_politician_trades(self, politician_id: str) -> int:
        """Sync all trades for a specific politician"""
        self.logger.info(f"Syncing trades for politician {politician_id}")

        # Get politician mapping first
        politician_mapping = self._get_politician_mapping(politician_id)
        if not politician_mapping:
            self.logger.error(f"No mapping found for politician {politician_id}")
            return 0

        # Get all disclosures for this politician
        disclosures = self.supabase.table("trading_disclosures") \
            .select("*") \
            .eq("politician_id", politician_id) \
            .execute()

        synced_count = 0
        for disclosure in disclosures.data:
            try:
                trade_mapping = TradeTransformer.transform_trade(disclosure, politician_mapping.id)
                self._insert_trade(trade_mapping)
                synced_count += 1
            except Exception as e:
                self.logger.error(f"Failed to sync trade {disclosure.get('id')}: {e}")

        # Update politician totals
        self._update_politician_totals(politician_mapping.id)

        self.logger.info(f"Synchronized {synced_count} trades for politician {politician_id}")
        return synced_count

    def sync_all_trades(self) -> int:
        """Sync all trades from complex to simplified schema"""
        self.logger.info("Starting trade synchronization")

        # Get all disclosures
        disclosures = self.supabase.table("trading_disclosures").select("*").execute()

        synced_count = 0
        for disclosure in disclosures.data:
            try:
                politician_id = disclosure['politician_id']
                politician_mapping = self._get_politician_mapping(politician_id)

                if politician_mapping:
                    trade_mapping = TradeTransformer.transform_trade(disclosure, politician_mapping.id)
                    self._insert_trade(trade_mapping)
                    synced_count += 1
            except Exception as e:
                self.logger.error(f"Failed to sync disclosure {disclosure.get('id')}: {e}")

        # Update all politician totals
        self._update_all_politician_totals()

        self.logger.info(f"Synchronized {synced_count} trades")
        return synced_count

    def update_dashboard_stats(self) -> None:
        """Update dashboard statistics"""
        self.logger.info("Updating dashboard statistics")

        # Calculate stats
        stats = self._calculate_dashboard_stats()

        # Upsert to dashboard_stats table
        self.supabase.table("dashboard_stats").upsert({
            "total_trades": stats['total_trades'],
            "total_volume": stats['total_volume'],
            "active_politicians": stats['active_politicians'],
            "jurisdictions_tracked": stats['jurisdictions_tracked'],
            "average_trade_size": stats['average_trade_size'],
            "recent_filings": stats['recent_filings'],
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        self.logger.info("Dashboard statistics updated")

    def update_chart_data(self) -> None:
        """Update monthly chart data aggregation"""
        self.logger.info("Updating chart data aggregation")

        # Aggregate data by year and month
        chart_data = self._aggregate_chart_data()

        # Upsert each month's data
        for data_point in chart_data:
            self.supabase.table("chart_data").upsert({
                "year": data_point['year'],
                "month": data_point['month'],
                "buys": data_point['buys'],
                "sells": data_point['sells'],
                "volume": data_point['volume'],
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        self.logger.info(f"Updated chart data for {len(chart_data)} months")

    def _upsert_politician(self, mapping: PoliticianMapping) -> None:
        """Upsert a politician to the simplified schema"""
        data = {
            "name": mapping.name,
            "party": mapping.party,
            "chamber": mapping.chamber,
            "jurisdiction_id": mapping.jurisdiction_id,
            "state": mapping.state,
            "avatar_url": mapping.avatar_url,
            "total_trades": mapping.total_trades,
            "total_volume": mapping.total_volume,
            "updated_at": datetime.utcnow().isoformat()
        }

        # Check if exists by name (since we don't have direct ID mapping)
        existing = self.supabase.table("politicians") \
            .select("id") \
            .eq("name", mapping.name) \
            .execute()

        if existing.data:
            # Update existing
            self.supabase.table("politicians") \
                .update(data) \
                .eq("id", existing.data[0]["id"]) \
                .execute()
        else:
            # Insert new
            self.supabase.table("politicians").insert(data).execute()

    def _insert_trade(self, mapping: TradeMapping) -> None:
        """Insert a trade record (skip if already exists)"""
        # Check for duplicate (same politician, ticker, transaction_date)
        existing = self.supabase.table("trades") \
            .select("id") \
            .eq("politician_id", mapping.politician_id) \
            .eq("ticker", mapping.ticker) \
            .eq("transaction_date", mapping.transaction_date) \
            .execute()

        if existing.data:
            return  # Skip duplicate

        data = {
            "politician_id": mapping.politician_id,
            "ticker": mapping.ticker,
            "company": mapping.company,
            "trade_type": mapping.trade_type,
            "amount_range": mapping.amount_range,
            "estimated_value": mapping.estimated_value,
            "filing_date": mapping.filing_date,
            "transaction_date": mapping.transaction_date
        }

        self.supabase.table("trades").insert(data).execute()

    def _get_politician_mapping(self, original_id: str) -> Optional[PoliticianMapping]:
        """Get the simplified schema politician ID for an original politician ID"""
        # This is a simplified mapping - in practice, we'd need a mapping table
        # For now, we'll search by name similarity
        politician = self.supabase.table("politicians") \
            .select("*") \
            .eq("id", original_id) \
            .execute()

        if politician.data:
            record = politician.data[0]
            return PoliticianMapping(
                id=record['id'],
                name=record['name'],
                party=record['party'],
                chamber=record['chamber'],
                jurisdiction_id=record['jurisdiction_id'],
                state=record.get('state'),
                avatar_url=record.get('avatar_url'),
                total_trades=record.get('total_trades', 0),
                total_volume=record.get('total_volume', 0)
            )

        return None

    def _update_politician_totals(self, politician_id: str) -> None:
        """Update total trades and volume for a politician"""
        trades = self.supabase.table("trades") \
            .select("estimated_value") \
            .eq("politician_id", politician_id) \
            .execute()

        if trades.data:
            total_trades = len(trades.data)
            total_volume = sum(trade['estimated_value'] for trade in trades.data)
        else:
            total_trades = 0
            total_volume = 0

        self.supabase.table("politicians").update({
            "total_trades": total_trades,
            "total_volume": total_volume,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", politician_id).execute()

    def _update_all_politician_totals(self) -> None:
        """Update totals for all politicians"""
        politicians = self.supabase.table("politicians").select("id").execute()

        for politician in politicians.data:
            self._update_politician_totals(politician['id'])

    def _calculate_dashboard_stats(self) -> Dict[str, Any]:
        """Calculate dashboard statistics"""
        # Total trades
        trades_result = self.supabase.table("trades").select("estimated_value", count="exact").execute()
        total_trades = trades_result.count or 0
        total_volume = sum(trade['estimated_value'] for trade in trades_result.data) if trades_result.data else 0

        # Active politicians
        politicians_result = self.supabase.table("politicians").select("id", count="exact").execute()
        active_politicians = politicians_result.count or 0

        # Jurisdictions tracked
        jurisdictions_result = self.supabase.table("jurisdictions").select("id", count="exact").execute()
        jurisdictions_tracked = jurisdictions_result.count or 0

        # Average trade size
        average_trade_size = total_volume // total_trades if total_trades > 0 else 0

        # Recent filings (last 7 days)
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_result = self.supabase.table("trades") \
            .select("id", count="exact") \
            .gte("filing_date", week_ago) \
            .execute()
        recent_filings = recent_result.count or 0

        return {
            "total_trades": total_trades,
            "total_volume": total_volume,
            "active_politicians": active_politicians,
            "jurisdictions_tracked": jurisdictions_tracked,
            "average_trade_size": average_trade_size,
            "recent_filings": recent_filings
        }

    def _aggregate_chart_data(self) -> List[Dict[str, Any]]:
        """Aggregate trade data by year and month for charts"""
        # Get all trades with filing dates
        trades = self.supabase.table("trades").select("trade_type", "estimated_value", "filing_date").execute()

        if not trades.data:
            return []

        # Aggregate by year and month
        monthly_data = {}

        for trade in trades.data:
            try:
                filing_date = trade.get('filing_date', '')
                if not filing_date:
                    continue

                # Parse date to get year and month
                date_obj = datetime.fromisoformat(filing_date.replace('Z', '+00:00'))
                year = date_obj.year
                month = date_obj.strftime('%b')  # Jan, Feb, etc.

                key = f"{year}-{month}"

                if key not in monthly_data:
                    monthly_data[key] = {
                        'year': year,
                        'month': month,
                        'buys': 0,
                        'sells': 0,
                        'volume': 0
                    }

                # Count buys/sells and sum volume
                trade_type = trade.get('trade_type', '').lower()
                estimated_value = trade.get('estimated_value', 0) or 0

                if trade_type == 'buy':
                    monthly_data[key]['buys'] += 1
                elif trade_type == 'sell':
                    monthly_data[key]['sells'] += 1

                monthly_data[key]['volume'] += estimated_value

            except (ValueError, AttributeError) as e:
                self.logger.warning(f"Error processing trade for chart data: {e}")
                continue

        # Convert to list and sort by year/month
        result = list(monthly_data.values())
        result.sort(key=lambda x: (x['year'], x['month']))

        return result

    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity between complex and simplified schemas"""
        self.logger.info("Starting data integrity validation")

        validation_results = {
            "politicians": self._validate_politicians_integrity(),
            "trades": self._validate_trades_integrity(),
            "statistics": self._validate_statistics_integrity(),
            "overall_status": "unknown"
        }

        # Determine overall status
        all_passed = all(
            result.get("status") == "passed"
            for result in validation_results.values()
            if isinstance(result, dict) and "status" in result
        )

        validation_results["overall_status"] = "passed" if all_passed else "failed"

        self.logger.info(f"Data integrity validation completed: {validation_results['overall_status']}")
        return validation_results

    def _validate_politicians_integrity(self) -> Dict[str, Any]:
        """Validate politician data integrity"""
        try:
            # Check that all politicians in complex schema have mappings in simplified schema
            complex_politicians = self.supabase.table("politicians").select("id, full_name").execute()
            simplified_politicians = self.supabase.table("politicians").select("name").execute()

            complex_names = set()
            if complex_politicians.data:
                complex_names = {p.get('full_name') or p.get('name', '') for p in complex_politicians.data}

            simplified_names = set()
            if simplified_politicians.data:
                simplified_names = {p.get('name', '') for p in simplified_politicians.data}

            missing_mappings = complex_names - simplified_names
            extra_mappings = simplified_names - complex_names

            return {
                "status": "passed" if not missing_mappings else "failed",
                "complex_count": len(complex_names),
                "simplified_count": len(simplified_names),
                "missing_mappings": list(missing_mappings),
                "extra_mappings": list(extra_mappings)
            }
        except Exception as e:
            self.logger.error(f"Politician validation error: {e}")
            return {"status": "error", "error": str(e)}

    def _validate_trades_integrity(self) -> Dict[str, Any]:
        """Validate trade data integrity"""
        try:
            # Check trade counts and data consistency
            complex_trades = self.supabase.table("trading_disclosures").select("id", count="exact").execute()
            simplified_trades = self.supabase.table("trades").select("id", count="exact").execute()

            complex_count = complex_trades.count or 0
            simplified_count = simplified_trades.count or 0

            # Check for data consistency (simplified trades should be subset of complex)
            status = "passed" if simplified_count <= complex_count else "warning"

            return {
                "status": status,
                "complex_trades": complex_count,
                "simplified_trades": simplified_count,
                "ratio": simplified_count / complex_count if complex_count > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Trade validation error: {e}")
            return {"status": "error", "error": str(e)}

    def _validate_statistics_integrity(self) -> Dict[str, Any]:
        """Validate statistics data integrity"""
        try:
            # Check dashboard statistics
            stats = self.supabase.table("dashboard_stats").select("*").execute()

            if not stats.data:
                return {"status": "failed", "error": "No dashboard statistics found"}

            latest_stats = stats.data[0]

            # Validate that stats make sense
            issues = []

            if latest_stats.get('total_trades', 0) < 0:
                issues.append("Negative total trades")

            if latest_stats.get('total_volume', 0) < 0:
                issues.append("Negative total volume")

            if latest_stats.get('active_politicians', 0) < 0:
                issues.append("Negative active politicians")

            # Check if stats are reasonably up to date (within last 24 hours)
            updated_at = latest_stats.get('updated_at')
            if updated_at:
                try:
                    # Parse ISO datetime
                    import datetime
                    updated_time = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    hours_old = (datetime.datetime.utcnow() - updated_time).total_seconds() / 3600

                    if hours_old > 24:
                        issues.append(".1f")
                except:
                    issues.append("Invalid updated_at timestamp")

            return {
                "status": "passed" if not issues else "warning",
                "issues": issues,
                "stats": {
                    "total_trades": latest_stats.get('total_trades'),
                    "total_volume": latest_stats.get('total_volume'),
                    "active_politicians": latest_stats.get('active_politicians'),
                    "jurisdictions_tracked": latest_stats.get('jurisdictions_tracked'),
                    "average_trade_size": latest_stats.get('average_trade_size'),
                    "recent_filings": latest_stats.get('recent_filings')
                }
            }
        except Exception as e:
            self.logger.error(f"Statistics validation error: {e}")
            return {"status": "error", "error": str(e)}