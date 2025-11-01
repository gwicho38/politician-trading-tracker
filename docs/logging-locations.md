# Logging Locations

Comprehensive list of all logging implementations throughout the Politician Trading Tracker application.

## Streamlit Pages

### Main App (`app.py`)
- **Startup**: Application initialization
- **Environment Check**: Missing/present environment variables
- **Database Stats**: Connection status and metric counts
- **Errors**: Environment variable and database errors

**Example Logs**:
```python
logger.info("Politician Trading Tracker starting")
logger.error("Missing required environment variables", metadata={"missing_vars": [...]})
logger.info("Connected to database for stats")
logger.debug("Politicians count retrieved", metadata={"count": 150})
```

### Trading Operations (`pages/3_💼_Trading_Operations.py`)
- **Page Load**: Trading operations page initialization
- **Manual Orders**: Order placement requests and results
- **Order Submission**: Alpaca API calls and responses
- **Database Saves**: Order persistence
- **Errors**: Order placement failures with context

**Example Logs**:
```python
logger.info("Trading Operations page loaded")
logger.info("Manual order placement requested", metadata={
    "ticker": "AAPL",
    "quantity": 10,
    "side": "buy",
    "trading_mode": "paper"
})
logger.info("Manual order placed successfully", metadata={
    "order_id": "uuid",
    "status": "submitted"
})
logger.error("Failed to place manual order", error=e, metadata={...})
```

### Data Collection (`pages/1_📥_Data_Collection.py`)
- **Page Load**: Data collection page initialization
- **Button Clicks**: Start collection and backfill ticker buttons
- **Source Selection**: Enabled data sources and parameters
- **Workflow Init**: Configuration and initialization
- **Collection Process**: Progress and status updates
- **Results**: Summary metrics and job-specific results
- **Errors**: Collection and backfill failures
- **Data Loading**: Recent disclosures retrieval

**Example Logs**:
```python
logger.info("Data Collection page loaded")
logger.info("Start Collection button clicked", metadata={
    "us_congress": True,
    "lookback_days": 30,
    ...
})
logger.info("Data sources configured", metadata={
    "enabled_sources": ["US Congress", "California"],
    "source_count": 2
})
logger.info("Data collection completed", metadata={
    "results": {...},
    "summary": {"total_new_disclosures": 50},
    "job_count": 2
})
logger.info("Job result: us_congress", metadata={
    "status": "completed",
    "new_disclosures": 25,
    "error_count": 0
})
logger.info("Backfill Missing Tickers button clicked")
logger.info("Ticker backfill completed", metadata={
    "total_processed": 100,
    "updated": 85,
    "no_ticker_found": 15
})
```

## Trading Modules

### Alpaca Client (`src/politician_trading/trading/alpaca_client.py`)
- **Initialization**: Client setup with mode (paper/live)
- **Account Info**: Account ID conversion to string
- **Order Placement**: Market, limit, stop orders with metadata
- **Order Status**: Order conversion and tracking
- **Errors**: API call failures

**Example Logs**:
```python
logger = create_logger("alpaca_client")
logger.info("Initialized Alpaca client in paper mode")
logger.debug("Placing market order", metadata={
    "ticker": "AAPL",
    "quantity": 10,
    "side": "buy",
    "trading_mode": "paper"
})
logger.info("Placed market buy order for 10 shares of AAPL", metadata={
    "order_id": "uuid",
    "status": "submitted",
    "trading_mode": "paper"
})
logger.error("Error placing market order for TSLA", error=e, metadata={...})
```

### Risk Manager (`src/politician_trading/trading/risk_manager.py`)
- **Initialization**: Risk parameter configuration
- **Signal Validation**: Confidence checks and rejection reasons
- **Position Sizing**: Risk calculations
- **Warnings**: Missing stop loss, invalid parameters

**Example Logs**:
```python
logger = create_logger("risk_manager")
logger.info("Initialized RiskManager", metadata={
    "max_position_size_pct": 10.0,
    "max_portfolio_risk_pct": 2.0,
    "min_confidence": 0.65
})
logger.debug("Validating signal", metadata={
    "ticker": "TSLA",
    "confidence": 0.85,
    "signal_type": "buy"
})
logger.info("Signal rejected - low confidence", metadata={
    "ticker": "AAPL",
    "confidence": 0.55,
    "min_required": 0.65
})
logger.warning("Signal missing stop loss", metadata={
    "ticker": "TSLA"
})
```

### Database Client (`src/politician_trading/database/database.py`)
- **Initialization**: Supabase connection
- **Queries**: Database operations
- **Errors**: Connection and query failures

**Example Logs**:
```python
logger = create_logger("database")
logger.info("Supabase client initialized successfully")
logger.error("Failed to initialize Supabase client", error=e)
```

## Log Output Examples

### Console (Colored, Human-Readable)
```
2025-11-01T12:00:00.123456 INFO     [politician_trading:app] Politician Trading Tracker starting
2025-11-01T12:00:01.234567 INFO     [politician_trading:alpaca_client] Initialized Alpaca client in paper mode
2025-11-01T12:00:02.345678 DEBUG    [politician_trading:alpaca_client] Placing market order {"ticker": "AAPL", "quantity": 10}
2025-11-01T12:00:03.456789 INFO     [politician_trading:alpaca_client] Order placed {"order_id": "uuid", "status": "submitted"}
2025-11-01T12:00:04.567890 ERROR    [politician_trading:trading_operations_page] Failed to place manual order
```

### File (JSON, Parseable)
```json
{
  "timestamp": "2025-11-01T12:00:03.456789",
  "level": "INFO",
  "message": "Order placed",
  "logger": "politician_trading:alpaca_client",
  "metadata": {
    "order_id": "d75b1027-8133-4b3f-907b-84d802aba0fb",
    "ticker": "AAPL",
    "quantity": 10,
    "status": "submitted",
    "trading_mode": "paper"
  },
  "source": {
    "file": "/path/to/alpaca_client.py",
    "line": 221,
    "function": "place_market_order"
  }
}
```

## Viewing Logs

### Real-time Monitoring
```bash
# Follow all logs
tail -f logs/latest.log

# Filter by module
tail -f logs/latest.log | grep "alpaca_client"

# Watch for errors
tail -f logs/latest.log | grep "ERROR"

# Pretty print JSON
tail -f logs/latest.log | jq '.'
```

### Analysis
```bash
# Count errors by type
cat logs/latest.log | jq 'select(.level == "ERROR") | .message' | sort | uniq -c

# Show all order placements
cat logs/latest.log | jq 'select(.message | contains("Order placed"))'

# Filter by ticker
cat logs/latest.log | jq 'select(.metadata.ticker == "AAPL")'

# Show collection results
cat logs/latest.log | jq 'select(.message | contains("Collection summary"))'

# Find slow operations (customize based on your needs)
cat logs/latest.log | jq 'select(.metadata.duration_seconds > 5)'
```

### Debugging Scenarios

**Scenario 1: Order not placing**
```bash
# Check order placement logs
cat logs/latest.log | jq 'select(.logger | contains("alpaca")) | select(.message | contains("order"))'

# Look for errors
cat logs/latest.log | jq 'select(.logger | contains("alpaca")) | select(.level == "ERROR")'
```

**Scenario 2: Data collection failing**
```bash
# Check collection process
cat logs/latest.log | jq 'select(.logger | contains("data_collection"))'

# See which sources failed
cat logs/latest.log | jq 'select(.message | contains("Job result")) | select(.metadata.status != "completed")'
```

**Scenario 3: Environment issues**
```bash
# Check environment configuration
cat logs/latest.log | jq 'select(.message | contains("environment"))'

# See missing variables
cat logs/latest.log | jq 'select(.metadata.missing_vars)'
```

## Log Levels

All modules use appropriate log levels:

- **DEBUG**: Detailed flow (order details, signal validation steps)
- **INFO**: Important events (orders placed, collections completed, initialization)
- **WARN**: Issues that don't stop execution (missing stop loss, slow operations)
- **ERROR**: Failures requiring attention (order failures, collection errors)
- **CRITICAL**: Severe errors (not currently used, reserved for critical failures)

## Configuration

Set log level in `.env`:
```bash
LOG_LEVEL=DEBUG  # Shows all logs
LOG_LEVEL=INFO   # Default, shows important events
LOG_LEVEL=ERROR  # Only shows errors
```

Or override at runtime:
```bash
LOG_LEVEL=DEBUG streamlit run app.py
```

## Log Rotation

Logs automatically rotate daily:
- New file created each day: `logs/YYYY-MM-DD.log`
- Symlink `logs/latest.log` always points to today's log
- Old logs are preserved for analysis

## Best Practices

When reading logs:
1. Use `jq` for JSON parsing and filtering
2. Filter by logger name for module-specific logs
3. Check metadata fields for context
4. Look at source location for code references
5. Follow error chains through exception details

When adding new logging:
1. Use appropriate log level
2. Include rich metadata
3. Log before and after critical operations
4. Don't log sensitive data (API keys, passwords)
5. Use context-specific logger names
