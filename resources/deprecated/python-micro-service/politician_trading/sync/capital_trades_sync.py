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
        politician_id = politician_record.get('id', 'unknown')
        original_name = politician_record.get('full_name', politician_record.get('name', 'Unknown'))
        original_role = politician_record.get('role', '')
        original_party = politician_record.get('party', 'Other')

        logger.debug(f"[PoliticianTransformer.transform] START", {
            "politician_id": politician_id,
            "original_name": original_name,
            "original_role": original_role,
            "original_party": original_party
        })

        # Map role to chamber
        role = original_role.lower()
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
        party = original_party
        if party not in ['D', 'R', 'I', 'Other']:
            logger.debug(f"[PoliticianTransformer.transform] Non-standard party '{party}' -> 'Other'")
            party = 'Other'

        result = PoliticianMapping(
            id=politician_id,
            name=original_name,
            party=party,
            chamber=chamber,
            jurisdiction_id=jurisdiction_id,
            state=politician_record.get('state_or_country'),
            avatar_url=None,  # Will be added later if available
            total_trades=0,  # Will be calculated
            total_volume=0   # Will be calculated
        )

        logger.debug(f"[PoliticianTransformer.transform] END", {
            "politician_id": politician_id,
            "mapped_chamber": chamber,
            "mapped_jurisdiction": jurisdiction_id,
            "mapped_party": party
        })

        return result


class TradeTransformer:
    """Transforms trade records from complex to simplified schema"""

    @staticmethod
    def transform_trade(disclosure_record: Dict[str, Any], politician_id: str) -> TradeMapping:
        """Transform a trading disclosure record to a trade record"""
        disclosure_id = disclosure_record.get('id', 'unknown')
        original_transaction_type = disclosure_record.get('transaction_type', '')
        ticker = disclosure_record.get('asset_ticker', '')

        logger.debug(f"[TradeTransformer.transform] START", {
            "disclosure_id": disclosure_id,
            "politician_id": politician_id,
            "ticker": ticker,
            "original_transaction_type": original_transaction_type
        })

        # Map transaction type
        transaction_type = original_transaction_type.lower()
        if 'buy' in transaction_type or 'purchase' in transaction_type:
            trade_type = 'buy'
        elif 'sell' in transaction_type or 'sale' in transaction_type:
            trade_type = 'sell'
        else:
            trade_type = 'buy'  # Default to buy if unclear
            logger.debug(f"[TradeTransformer.transform] Unknown transaction type '{original_transaction_type}' -> 'buy'")

        # Calculate estimated value from amount range
        amount_min = disclosure_record.get('amount_range_min')
        amount_max = disclosure_record.get('amount_range_max')
        amount_exact = disclosure_record.get('amount_exact')

        estimated_value = TradeTransformer._calculate_estimated_value(amount_min, amount_max, amount_exact)

        # Format amount range
        amount_range = TradeTransformer._format_amount_range(amount_min, amount_max, amount_exact)

        filing_date = disclosure_record.get('disclosure_date', '').split('T')[0] if disclosure_record.get('disclosure_date') else ''
        transaction_date = disclosure_record.get('transaction_date', '').split('T')[0] if disclosure_record.get('transaction_date') else ''

        result = TradeMapping(
            politician_id=politician_id,
            ticker=ticker,
            company=disclosure_record.get('asset_name', ''),
            trade_type=trade_type,
            amount_range=amount_range,
            estimated_value=estimated_value,
            filing_date=filing_date,
            transaction_date=transaction_date
        )

        logger.debug(f"[TradeTransformer.transform] END", {
            "disclosure_id": disclosure_id,
            "mapped_trade_type": trade_type,
            "estimated_value": estimated_value,
            "ticker": ticker,
            "filing_date": filing_date
        })

        return result

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
        self.logger.info("[sync_all_politicians] START")

        # Get all politicians from complex schema
        self.logger.debug("[sync_all_politicians] Fetching politicians from database...")
        politicians = self.supabase.table("politicians").select("*").execute()

        total_count = len(politicians.data) if politicians.data else 0
        self.logger.info(f"[sync_all_politicians] Found {total_count} politicians to sync")

        synced_count = 0
        error_count = 0

        if politicians.data:
            for i, politician in enumerate(politicians.data):
                try:
                    # Type cast to Dict
                    politician_dict = dict(politician) if politician else {}
                    politician_id = politician_dict.get('id', 'unknown')

                    self.logger.debug(f"[sync_all_politicians] Processing {i+1}/{total_count}: {politician_id}")

                    mapping = PoliticianTransformer.transform_politician(politician_dict)
                    self._upsert_politician(mapping)
                    synced_count += 1

                    # Log progress every 50 records
                    if synced_count % 50 == 0:
                        self.logger.info(f"[sync_all_politicians] Progress: {synced_count}/{total_count} synced")

                except Exception as e:
                    error_count += 1
                    politician_id = politician.get('id', 'unknown') if politician else 'unknown'
                    self.logger.error(f"[sync_all_politicians] Failed to sync politician {politician_id}: {e}")

        self.logger.info(f"[sync_all_politicians] END", {
            "total": total_count,
            "synced": synced_count,
            "errors": error_count
        })
        return synced_count

    def sync_politician_trades(self, politician_id: str) -> int:
        """Sync all trades for a specific politician"""
        self.logger.info(f"[sync_politician_trades] START", {"politician_id": politician_id})

        # Get politician mapping first
        self.logger.debug(f"[sync_politician_trades] Getting politician mapping...")
        politician_mapping = self._get_politician_mapping(politician_id)
        if not politician_mapping:
            self.logger.error(f"[sync_politician_trades] No mapping found for politician {politician_id}")
            return 0

        self.logger.debug(f"[sync_politician_trades] Found mapping: {politician_mapping.name}")

        # Get all disclosures for this politician
        self.logger.debug(f"[sync_politician_trades] Fetching disclosures...")
        disclosures = self.supabase.table("trading_disclosures") \
            .select("*") \
            .eq("politician_id", politician_id) \
            .execute()

        total_count = len(disclosures.data) if disclosures.data else 0
        self.logger.info(f"[sync_politician_trades] Found {total_count} disclosures")

        synced_count = 0
        error_count = 0

        for i, disclosure in enumerate(disclosures.data):
            try:
                disclosure_id = disclosure.get('id', 'unknown')
                self.logger.debug(f"[sync_politician_trades] Processing disclosure {i+1}/{total_count}: {disclosure_id}")

                trade_mapping = TradeTransformer.transform_trade(disclosure, politician_mapping.id)
                self._insert_trade(trade_mapping)
                synced_count += 1
            except Exception as e:
                error_count += 1
                self.logger.error(f"[sync_politician_trades] Failed to sync trade {disclosure.get('id')}: {e}")

        # Update politician totals
        self.logger.debug(f"[sync_politician_trades] Updating politician totals...")
        self._update_politician_totals(politician_mapping.id)

        self.logger.info(f"[sync_politician_trades] END", {
            "politician_id": politician_id,
            "total": total_count,
            "synced": synced_count,
            "errors": error_count
        })
        return synced_count

    def sync_all_trades(self) -> int:
        """Sync all trades from complex to simplified schema"""
        self.logger.info("[sync_all_trades] START")

        # Get all disclosures
        self.logger.debug("[sync_all_trades] Fetching all disclosures...")
        disclosures = self.supabase.table("trading_disclosures").select("*").execute()

        total_count = len(disclosures.data) if disclosures.data else 0
        self.logger.info(f"[sync_all_trades] Found {total_count} disclosures to sync")

        synced_count = 0
        error_count = 0
        skipped_count = 0

        for i, disclosure in enumerate(disclosures.data):
            try:
                disclosure_id = disclosure.get('id', 'unknown')
                politician_id = disclosure['politician_id']

                self.logger.debug(f"[sync_all_trades] Processing {i+1}/{total_count}: disclosure={disclosure_id}")

                politician_mapping = self._get_politician_mapping(politician_id)

                if politician_mapping:
                    trade_mapping = TradeTransformer.transform_trade(disclosure, politician_mapping.id)
                    self._insert_trade(trade_mapping)
                    synced_count += 1
                else:
                    skipped_count += 1
                    self.logger.warn(f"[sync_all_trades] No politician mapping for disclosure {disclosure_id}")

                # Log progress every 100 records
                if (i + 1) % 100 == 0:
                    self.logger.info(f"[sync_all_trades] Progress: {i+1}/{total_count} processed")

            except Exception as e:
                error_count += 1
                self.logger.error(f"[sync_all_trades] Failed to sync disclosure {disclosure.get('id')}: {e}")

        # Update all politician totals
        self.logger.info("[sync_all_trades] Updating all politician totals...")
        self._update_all_politician_totals()

        self.logger.info(f"[sync_all_trades] END", {
            "total": total_count,
            "synced": synced_count,
            "skipped": skipped_count,
            "errors": error_count
        })
        return synced_count

    def update_dashboard_stats(self) -> None:
        """Update dashboard statistics"""
        self.logger.info("[update_dashboard_stats] START")

        # Calculate stats
        self.logger.debug("[update_dashboard_stats] Calculating statistics...")
        stats = self._calculate_dashboard_stats()

        self.logger.info("[update_dashboard_stats] Calculated stats", stats)

        # Upsert to dashboard_stats table
        self.logger.debug("[update_dashboard_stats] Upserting to dashboard_stats table...")
        self.supabase.table("dashboard_stats").upsert({
            "total_trades": stats['total_trades'],
            "total_volume": stats['total_volume'],
            "active_politicians": stats['active_politicians'],
            "jurisdictions_tracked": stats['jurisdictions_tracked'],
            "average_trade_size": stats['average_trade_size'],
            "recent_filings": stats['recent_filings'],
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        self.logger.info("[update_dashboard_stats] END - Dashboard statistics updated")

    def update_chart_data(self) -> None:
        """Update monthly chart data aggregation"""
        self.logger.info("[update_chart_data] START")

        # Aggregate data by year and month
        self.logger.debug("[update_chart_data] Aggregating data by year/month...")
        chart_data = self._aggregate_chart_data()

        self.logger.info(f"[update_chart_data] Aggregated {len(chart_data)} months of data")

        # Upsert each month's data
        for i, data_point in enumerate(chart_data):
            self.logger.debug(f"[update_chart_data] Upserting {data_point['year']}-{data_point['month']}", {
                "buys": data_point['buys'],
                "sells": data_point['sells'],
                "volume": data_point['volume']
            })
            self.supabase.table("chart_data").upsert({
                "year": data_point['year'],
                "month": data_point['month'],
                "buys": data_point['buys'],
                "sells": data_point['sells'],
                "volume": data_point['volume'],
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        self.logger.info(f"[update_chart_data] END - Updated {len(chart_data)} months")

    def _upsert_politician(self, mapping: PoliticianMapping) -> None:
        """Upsert a politician to the simplified schema"""
        self.logger.debug(f"[_upsert_politician] START: {mapping.name}")

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
            existing_id = existing.data[0]["id"]
            self.logger.debug(f"[_upsert_politician] Updating existing politician id={existing_id}")
            self.supabase.table("politicians") \
                .update(data) \
                .eq("id", existing_id) \
                .execute()
        else:
            # Insert new
            self.logger.debug(f"[_upsert_politician] Inserting new politician: {mapping.name}")
            self.supabase.table("politicians").insert(data).execute()

        self.logger.debug(f"[_upsert_politician] END: {mapping.name}")

    def _insert_trade(self, mapping: TradeMapping) -> None:
        """Insert a trade record (skip if already exists)"""
        self.logger.debug(f"[_insert_trade] START: {mapping.ticker} for politician {mapping.politician_id}")

        # Check for duplicate (same politician, ticker, transaction_date)
        existing = self.supabase.table("trades") \
            .select("id") \
            .eq("politician_id", mapping.politician_id) \
            .eq("ticker", mapping.ticker) \
            .eq("transaction_date", mapping.transaction_date) \
            .execute()

        if existing.data:
            self.logger.debug(f"[_insert_trade] SKIP duplicate: {mapping.ticker} on {mapping.transaction_date}")
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
        self.logger.debug(f"[_insert_trade] INSERTED: {mapping.ticker} ({mapping.trade_type}) value=${mapping.estimated_value}")

    def _get_politician_mapping(self, original_id: str) -> Optional[PoliticianMapping]:
        """Get the simplified schema politician ID for an original politician ID"""
        self.logger.debug(f"[_get_politician_mapping] Looking up politician id={original_id}")

        politician = self.supabase.table("politicians") \
            .select("*") \
            .eq("id", original_id) \
            .execute()

        if politician.data:
            record = politician.data[0]
            self.logger.debug(f"[_get_politician_mapping] Found: {record['name']}")
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

        self.logger.debug(f"[_get_politician_mapping] NOT FOUND: id={original_id}")
        return None

    def _update_politician_totals(self, politician_id: str) -> None:
        """Update total trades and volume for a politician"""
        self.logger.debug(f"[_update_politician_totals] START: politician_id={politician_id}")

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

        self.logger.debug(f"[_update_politician_totals] Updating: trades={total_trades}, volume=${total_volume}")

        self.supabase.table("politicians").update({
            "total_trades": total_trades,
            "total_volume": total_volume,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", politician_id).execute()

        self.logger.debug(f"[_update_politician_totals] END: politician_id={politician_id}")

    def _update_all_politician_totals(self) -> None:
        """Update totals for all politicians"""
        self.logger.info("[_update_all_politician_totals] START")

        politicians = self.supabase.table("politicians").select("id").execute()
        total_count = len(politicians.data) if politicians.data else 0

        self.logger.info(f"[_update_all_politician_totals] Updating {total_count} politicians")

        for i, politician in enumerate(politicians.data):
            self._update_politician_totals(politician['id'])
            if (i + 1) % 50 == 0:
                self.logger.info(f"[_update_all_politician_totals] Progress: {i+1}/{total_count}")

        self.logger.info(f"[_update_all_politician_totals] END - Updated {total_count} politicians")

    def _calculate_dashboard_stats(self) -> Dict[str, Any]:
        """Calculate dashboard statistics"""
        self.logger.debug("[_calculate_dashboard_stats] START")

        # Total trades
        self.logger.debug("[_calculate_dashboard_stats] Fetching trades count...")
        trades_result = self.supabase.table("trades").select("estimated_value", count="exact").execute()
        total_trades = trades_result.count or 0
        total_volume = sum(trade['estimated_value'] for trade in trades_result.data) if trades_result.data else 0
        self.logger.debug(f"[_calculate_dashboard_stats] trades={total_trades}, volume=${total_volume}")

        # Active politicians
        self.logger.debug("[_calculate_dashboard_stats] Fetching politicians count...")
        politicians_result = self.supabase.table("politicians").select("id", count="exact").execute()
        active_politicians = politicians_result.count or 0
        self.logger.debug(f"[_calculate_dashboard_stats] active_politicians={active_politicians}")

        # Jurisdictions tracked
        self.logger.debug("[_calculate_dashboard_stats] Fetching jurisdictions count...")
        jurisdictions_result = self.supabase.table("jurisdictions").select("id", count="exact").execute()
        jurisdictions_tracked = jurisdictions_result.count or 0
        self.logger.debug(f"[_calculate_dashboard_stats] jurisdictions={jurisdictions_tracked}")

        # Average trade size
        average_trade_size = total_volume // total_trades if total_trades > 0 else 0

        # Recent filings (last 7 days)
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        self.logger.debug(f"[_calculate_dashboard_stats] Fetching recent filings since {week_ago}...")
        recent_result = self.supabase.table("trades") \
            .select("id", count="exact") \
            .gte("filing_date", week_ago) \
            .execute()
        recent_filings = recent_result.count or 0
        self.logger.debug(f"[_calculate_dashboard_stats] recent_filings={recent_filings}")

        stats = {
            "total_trades": total_trades,
            "total_volume": total_volume,
            "active_politicians": active_politicians,
            "jurisdictions_tracked": jurisdictions_tracked,
            "average_trade_size": average_trade_size,
            "recent_filings": recent_filings
        }

        self.logger.debug("[_calculate_dashboard_stats] END", stats)
        return stats

    def _aggregate_chart_data(self) -> List[Dict[str, Any]]:
        """Aggregate trade data by year and month for charts"""
        self.logger.debug("[_aggregate_chart_data] START")

        # Get all trades with filing dates
        self.logger.debug("[_aggregate_chart_data] Fetching trades...")
        trades = self.supabase.table("trades").select("trade_type", "estimated_value", "filing_date").execute()

        if not trades.data:
            self.logger.debug("[_aggregate_chart_data] No trades found")
            return []

        self.logger.debug(f"[_aggregate_chart_data] Processing {len(trades.data)} trades")

        # Aggregate by year and month
        monthly_data = {}
        error_count = 0

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
                error_count += 1
                self.logger.warning(f"[_aggregate_chart_data] Error processing trade: {e}")
                continue

        # Convert to list and sort by year/month
        result = list(monthly_data.values())
        result.sort(key=lambda x: (x['year'], x['month']))

        self.logger.debug(f"[_aggregate_chart_data] END", {
            "months_aggregated": len(result),
            "trades_processed": len(trades.data),
            "errors": error_count
        })

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