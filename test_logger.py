#!/usr/bin/env python3
"""
Test script for the new logging utility
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from politician_trading.utils.logger import create_logger, get_logger

# Test default logger
print("=" * 80)
print("Testing Default Logger")
print("=" * 80)

logger = get_logger()
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warn("This is a warning message")
logger.error("This is an error message")

# Test with metadata
logger.info("Processing order", metadata={
    "order_id": "12345",
    "ticker": "AAPL",
    "quantity": 100,
    "price": 150.25
})

# Test child logger
print("\n" + "=" * 80)
print("Testing Child Logger (alpaca_client)")
print("=" * 80)

alpaca_logger = create_logger("alpaca_client")
alpaca_logger.info("Initializing Alpaca client", metadata={
    "mode": "paper",
    "api_key_prefix": "PKA8"
})
alpaca_logger.debug("Placing market order", metadata={
    "ticker": "TSLA",
    "quantity": 10,
    "side": "buy"
})
alpaca_logger.info("Order placed successfully", metadata={
    "order_id": "d75b1027-8133-4b3f-907b-84d802aba0fb",
    "status": "submitted"
})

# Test database logger
print("\n" + "=" * 80)
print("Testing Database Logger")
print("=" * 80)

db_logger = create_logger("database")
db_logger.info("Connecting to Supabase", metadata={
    "url": "https://uljsqvwkomdrlnofmlad.supabase.co"
})
db_logger.debug("Executing query", metadata={
    "table": "trading_orders",
    "operation": "insert"
})

# Test error with exception
print("\n" + "=" * 80)
print("Testing Error Logging with Exception")
print("=" * 80)

try:
    raise ValueError("This is a test exception")
except Exception as e:
    alpaca_logger.error("Failed to process order", error=e, metadata={
        "ticker": "AAPL",
        "reason": "Invalid quantity"
    })

print("\n" + "=" * 80)
print("Logger Test Complete!")
print("=" * 80)
print(f"\nCheck the log file at: {Path(__file__).parent / 'logs' / 'latest.log'}")
