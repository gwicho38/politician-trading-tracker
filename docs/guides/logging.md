# Logging Framework

The Politician Trading Tracker uses a comprehensive logging framework inspired by the [lsh-framework](https://github.com/gwicho38/lsh) logger.

## Features

- **Colored Console Output**: ANSI color codes for better readability in terminal
- **Structured JSON Logging**: All logs written to file in JSON format for easy parsing
- **Context-Based Loggers**: Create child loggers with specific contexts (e.g., `alpaca_client`, `database`)
- **Rich Metadata**: Attach structured metadata to log entries
- **Environment Configuration**: Control log level via `LOG_LEVEL` environment variable
- **Automatic Rotation**: Daily log files with `latest.log` symlink

## Quick Start

### Basic Usage

```python
from politician_trading.utils.logger import get_logger

logger = get_logger()
logger.info("Application started")
logger.warn("This is a warning")
logger.error("An error occurred", error=exception)
```

### Creating Context-Specific Loggers

```python
from politician_trading.utils.logger import create_logger

# Create logger for a specific module
db_logger = create_logger("database")
db_logger.info("Connected to database")

# Create logger for trading operations
trading_logger = create_logger("trading")
trading_logger.debug("Processing order", metadata={
    "ticker": "AAPL",
    "quantity": 100,
    "price": 150.25
})
```

### Using Metadata

Attach structured data to log entries for better analysis:

```python
logger.info("Order placed successfully", metadata={
    "order_id": "12345",
    "ticker": "TSLA",
    "quantity": 50,
    "side": "buy",
    "status": "submitted"
})
```

### Error Logging with Exceptions

```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", error=e, metadata={
        "operation": "risky_operation",
        "context": "additional details"
    })
```

## Configuration

### Log Level

Set the log level using the `LOG_LEVEL` environment variable in `.env`:

```bash
# .env
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARN, ERROR, CRITICAL
```

Available log levels (in order of severity):
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARN`: Warning messages for potentially problematic situations
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical messages for severe errors

### Log Output Locations

**Console (stdout)**:
- Colored text format for easy reading
- Shows: timestamp, level, context, message, metadata
- Only enabled when running in a TTY

**File (`logs/YYYY-MM-DD.log`)**:
- JSON format for structured parsing
- Includes: timestamp, level, message, logger name, metadata, source location
- Automatically rotates daily
- `logs/latest.log` symlink always points to today's log

## Output Examples

### Console Output

```
2025-11-01T11:54:34.913231 INFO     [politician_trading:alpaca_client] Order placed {"order_id": "12345", "ticker": "AAPL"}
2025-11-01T11:54:34.913309 WARNING  [politician_trading:database] Connection slow {"latency_ms": 250}
2025-11-01T11:54:34.913339 ERROR    [politician_trading:trading] Order failed {"ticker": "TSLA", "reason": "Insufficient funds"}
```

### File Output (JSON)

```json
{
  "timestamp": "2025-11-01T11:54:34.913231",
  "level": "INFO",
  "message": "Order placed",
  "logger": "politician_trading:alpaca_client",
  "metadata": {
    "order_id": "12345",
    "ticker": "AAPL",
    "quantity": 100
  },
  "source": {
    "file": "/path/to/alpaca_client.py",
    "line": 221,
    "function": "place_market_order"
  }
}
```

## Log Analysis

### Viewing Logs

```bash
# View latest logs
tail -f logs/latest.log

# View specific date
cat logs/2025-11-01.log

# Search for errors
grep '"level": "ERROR"' logs/latest.log

# Extract metadata with jq
cat logs/latest.log | jq '.metadata'
```

### Filtering by Context

```bash
# Show only alpaca_client logs
cat logs/latest.log | jq 'select(.logger | contains("alpaca_client"))'

# Show only database logs
cat logs/latest.log | jq 'select(.logger | contains("database"))'
```

### Analyzing Errors

```bash
# Count errors by type
cat logs/latest.log | jq -r 'select(.level == "ERROR") | .message' | sort | uniq -c

# Show error stack traces
cat logs/latest.log | jq 'select(.level == "ERROR") | .exception'
```

## Integration Examples

### In Alpaca Client

```python
from politician_trading.utils.logger import create_logger

logger = create_logger("alpaca_client")

def place_market_order(ticker, quantity, side):
    logger.debug("Placing market order", metadata={
        "ticker": ticker,
        "quantity": quantity,
        "side": side,
        "trading_mode": "paper"
    })

    try:
        order = submit_order(...)

        logger.info(f"Order placed successfully", metadata={
            "order_id": order.id,
            "ticker": ticker,
            "status": order.status
        })

        return order
    except Exception as e:
        logger.error("Failed to place order", error=e, metadata={
            "ticker": ticker,
            "quantity": quantity
        })
        raise
```

### In Database Module

```python
from politician_trading.utils.logger import create_logger

logger = create_logger("database")

def insert_order(order_data):
    logger.debug("Inserting order", metadata={
        "table": "trading_orders",
        "operation": "insert"
    })

    result = db.client.table("trading_orders").insert(order_data).execute()

    logger.info("Order inserted", metadata={
        "order_id": result.data[0]["id"],
        "ticker": order_data["ticker"]
    })

    return result
```

## Best Practices

1. **Use Appropriate Log Levels**:
   - `DEBUG`: Detailed flow of execution
   - `INFO`: Important business events (order placed, connection established)
   - `WARN`: Recoverable issues (slow query, deprecated API)
   - `ERROR`: Failures requiring attention

2. **Include Rich Metadata**:
   - Always include identifiers (order_id, ticker, user_id)
   - Add context that helps debugging (quantity, price, mode)
   - Don't include sensitive data (API keys, passwords)

3. **Create Context-Specific Loggers**:
   - Use `create_logger("module_name")` for each module
   - This makes filtering and analysis easier

4. **Log at Decision Points**:
   - Before and after critical operations
   - When entering/exiting important functions
   - When handling errors

5. **Don't Log Secrets**:
   - Never log API keys, passwords, or tokens
   - Truncate or mask sensitive data

## Testing

Run the included test script to verify logging is working:

```bash
# Test with INFO level (default)
python3 test_logger.py

# Test with DEBUG level
LOG_LEVEL=DEBUG python3 test_logger.py

# Test in JSON format
LSH_LOG_FORMAT=json python3 test_logger.py
```

## Troubleshooting

### No logs appearing in console

Check that `LOG_LEVEL` is set appropriately:
```bash
echo $LOG_LEVEL
```

### File logs not being created

Ensure the `logs/` directory exists and is writable:
```bash
mkdir -p logs
chmod 755 logs
```

### Logs missing metadata

Make sure you're passing the `metadata` parameter:
```python
logger.info("Message", metadata={"key": "value"})
```

## Related Documentation

- [lsh-framework Logger](https://github.com/gwicho38/lsh/blob/main/src/lib/logger.ts) - Original TypeScript implementation
- [Python logging module](https://docs.python.org/3/library/logging.html) - Underlying Python library
- [jq Manual](https://stedolan.github.io/jq/manual/) - JSON query tool for log analysis
