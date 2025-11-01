# Logging Quick Reference

Quick guide for using the logging framework in Politician Trading Tracker.

## Import

```python
from politician_trading.utils.logger import create_logger

logger = create_logger("your_module_name")
```

## Basic Logging

```python
logger.debug("Detailed debug info")
logger.info("Important business event")
logger.warn("Something unusual happened")
logger.error("An error occurred", error=exception)
```

## With Metadata

```python
logger.info("Order placed", metadata={
    "order_id": "12345",
    "ticker": "AAPL",
    "quantity": 100,
    "price": 150.25,
    "mode": "paper"
})
```

## Error with Exception

```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", error=e, metadata={
        "operation": "risky_operation",
        "input": input_data
    })
```

## Set Log Level

In `.env`:
```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARN, ERROR, CRITICAL
```

Or at runtime:
```bash
LOG_LEVEL=DEBUG python3 your_script.py
```

## View Logs

```bash
# Follow latest logs
tail -f logs/latest.log

# Search for errors
grep ERROR logs/latest.log

# Pretty print JSON logs
cat logs/latest.log | jq '.'

# Filter by module
cat logs/latest.log | jq 'select(.logger | contains("alpaca"))'

# Show only error messages
cat logs/latest.log | jq 'select(.level == "ERROR") | .message'
```

## Common Patterns

### Module Initialization
```python
from politician_trading.utils.logger import create_logger

logger = create_logger("module_name")

def __init__(self):
    logger.info("Initializing module", metadata={
        "config": self.config,
        "mode": self.mode
    })
```

### Before/After Operations
```python
def place_order(ticker, quantity):
    logger.debug("Placing order", metadata={
        "ticker": ticker,
        "quantity": quantity
    })

    result = api.place_order(...)

    logger.info("Order placed", metadata={
        "order_id": result.id,
        "status": result.status
    })
```

### Database Operations
```python
logger.debug("Executing query", metadata={
    "table": "trading_orders",
    "operation": "insert",
    "filters": filters
})
```

### API Calls
```python
logger.debug("Calling API", metadata={
    "endpoint": "/api/orders",
    "method": "POST",
    "payload_size": len(payload)
})
```

## Tips

✅ **DO**:
- Use metadata for structured data
- Include identifiers (order_id, ticker, etc.)
- Log at decision points
- Use appropriate log levels

❌ **DON'T**:
- Log sensitive data (API keys, passwords)
- Use print() statements
- Log in tight loops (use sparingly)
- Forget to handle exceptions

## Examples by Module

### Alpaca Client
```python
logger = create_logger("alpaca_client")

logger.info("Order submitted", metadata={
    "order_id": order.id,
    "ticker": ticker,
    "side": side,
    "status": order.status,
    "trading_mode": "paper"
})
```

### Database
```python
logger = create_logger("database")

logger.debug("Inserting record", metadata={
    "table": "politicians",
    "operation": "upsert",
    "record_id": politician_id
})
```

### Scrapers
```python
logger = create_logger("scraper:us_congress")

logger.info("Scraping complete", metadata={
    "records_found": len(records),
    "records_new": new_count,
    "duration_ms": elapsed_time
})
```

## Log Levels Guide

| Level | When to Use | Example |
|-------|------------|---------|
| DEBUG | Detailed flow | "Parsing JSON response" |
| INFO | Business events | "Order placed successfully" |
| WARN | Recoverable issues | "API rate limit approaching" |
| ERROR | Failures | "Failed to connect to database" |
| CRITICAL | Severe errors | "System shutdown initiated" |
