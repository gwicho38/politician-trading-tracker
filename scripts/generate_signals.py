#!/usr/bin/env python3
"""
Generate trading signals from existing clean disclosure data
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from politician_trading.signals.signal_generator import SignalGenerator
from politician_trading.utils.logger import create_logger

logger = create_logger("generate_signals")

def main():
    print("\n" + "="*80)
    print("Generating Trading Signals from Clean Data")
    print("="*80 + "\n")

    # Connect to database
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Fetch all disclosures with tickers (no date filter for now since data is old)
    print(f"📊 Fetching all disclosures with tickers...")

    query = db.client.table("trading_disclosures").select("*")
    query = query.not_.is_("asset_ticker", "null")
    query = query.neq("asset_ticker", "")
    query = query.order("transaction_date", desc=True)

    response = query.execute()
    disclosures = response.data

    print(f"✅ Found {len(disclosures)} disclosures with tickers\n")

    if not disclosures:
        print("❌ No disclosures found. Run data collection first.")
        return

    # Group by ticker
    disclosures_by_ticker = {}
    for d in disclosures:
        ticker = d.get("asset_ticker")
        if ticker and ticker not in ["--", "N/A"]:
            if ticker not in disclosures_by_ticker:
                disclosures_by_ticker[ticker] = []
            disclosures_by_ticker[ticker].append(d)

    print(f"📈 Grouped into {len(disclosures_by_ticker)} unique tickers\n")

    # Show top tickers by activity
    print("Top 10 most traded tickers:")
    sorted_tickers = sorted(disclosures_by_ticker.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for i, (ticker, discs) in enumerate(sorted_tickers, 1):
        print(f"{i:2}. {ticker:6} - {len(discs)} trades")
    print()

    # Generate signals
    print("🎯 Generating trading signals...")
    generator = SignalGenerator(
        model_version="v1.0",
        use_ml=False,  # Use heuristics
        confidence_threshold=0.65,
    )

    # Generate with market data
    print("   Fetching market data and analyzing...")
    signals = generator.generate_signals(disclosures_by_ticker, fetch_market_data=True)

    print(f"✅ Generated {len(signals)} signals\n")

    if not signals:
        print("❌ No signals met confidence threshold")
        return

    # Show signal summary
    buy_signals = [s for s in signals if s.signal_type.value in ["buy", "strong_buy"]]
    sell_signals = [s for s in signals if s.signal_type.value in ["sell", "strong_sell"]]
    hold_signals = [s for s in signals if s.signal_type.value == "hold"]

    print(f"Signal breakdown:")
    print(f"  🟢 Buy/Strong Buy:  {len(buy_signals)}")
    print(f"  🔴 Sell/Strong Sell: {len(sell_signals)}")
    print(f"  🟡 Hold:             {len(hold_signals)}")
    print()

    # Show top 5 buy signals
    if buy_signals:
        print("Top 5 Buy Signals (by confidence):")
        top_buys = sorted(buy_signals, key=lambda x: x.confidence_score, reverse=True)[:5]
        for i, signal in enumerate(top_buys, 1):
            print(f"{i}. {signal.ticker:6} - {signal.signal_type.value:12} - "
                  f"Confidence: {signal.confidence_score:.1%} - "
                  f"Politicians: {signal.politician_activity_count}")
        print()

    # Save to database
    print("💾 Saving signals to database...")
    saved = 0
    errors = 0

    for signal in signals:
        try:
            data = {
                "ticker": signal.ticker,
                "asset_name": signal.asset_name,
                "signal_type": signal.signal_type.value,
                "signal_strength": signal.signal_strength.value,
                "confidence_score": signal.confidence_score,
                "target_price": float(signal.target_price) if signal.target_price else None,
                "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
                "take_profit": float(signal.take_profit) if signal.take_profit else None,
                "generated_at": signal.generated_at.isoformat(),
                "valid_until": signal.valid_until.isoformat() if signal.valid_until else None,
                "model_version": signal.model_version,
                "politician_activity_count": signal.politician_activity_count,
                "total_transaction_volume": float(signal.total_transaction_volume) if signal.total_transaction_volume else None,
                "buy_sell_ratio": signal.buy_sell_ratio,
                "features": signal.features,
                "disclosure_ids": signal.disclosure_ids,
                "is_active": signal.is_active,
                "notes": signal.notes,
            }

            db.client.table("trading_signals").insert(data).execute()
            saved += 1

        except Exception as e:
            errors += 1
            logger.error(f"Failed to save signal for {signal.ticker}: {e}")

    print(f"✅ Saved {saved} signals to database")
    if errors > 0:
        print(f"⚠️  {errors} signals failed to save")

    print("\n" + "="*80)
    print("✅ Signal generation complete!")
    print("   View signals in the Trading Signals page of the Streamlit app")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
