# ADR-005: Error Handling Strategy

## Status
Accepted

## Context

The system has many failure modes:
- Network errors (timeouts, connection refused)
- Rate limiting (429 responses)
- Parse errors (unexpected HTML/PDF structure)
- Database errors (connection, query failures)
- Configuration errors (missing env vars)
- Trading errors (order rejected, insufficient funds)

Previously, errors were handled inconsistently:
- Generic `except Exception` catches
- Some functions return `None` on error
- Some raise, some log and continue
- No clear error categorization

## Decision

We implement a **custom exception hierarchy** in `politician_trading/exceptions.py`:

```
PTTError (base)
├── ConfigurationError
├── DatabaseError
│   ├── ConnectionError
│   └── QueryError
├── ScrapingError
│   ├── RateLimitError
│   ├── SourceUnavailableError
│   └── AuthenticationError
├── ParseError
│   ├── PDFParseError
│   ├── HTMLParseError
│   └── DataValidationError
├── TickerResolutionError
├── WorkflowError
│   ├── JobExecutionError
│   └── SchedulingError
└── TradingError
    ├── OrderExecutionError
    └── InsufficientFundsError
```

Usage patterns:

```python
# Catching specific errors
try:
    await scraper.fetch(url)
except RateLimitError as e:
    await asyncio.sleep(e.retry_after)
except ScrapingError as e:
    logger.error(f"Scraping failed: {e}")

# Catching all project errors
try:
    await workflow.run()
except PTTError as e:
    logger.error(f"Workflow failed: {e}")
    # Context available in e.context dict
```

## Consequences

### Positive
- **Clear categorization**: Know what type of error occurred
- **Rich context**: Exceptions carry relevant data
- **Selective handling**: Catch specific errors differently
- **Documentation**: Exception docstrings explain when raised
- **Type safety**: Type checkers understand the hierarchy

### Negative
- **Migration effort**: Update existing error handling
- **More code**: Need to raise/catch specific exceptions
- **Learning curve**: Team needs to know the hierarchy

### Guidelines
1. Always catch the most specific exception possible
2. Use `PTTError` for catch-all only at boundaries
3. Include context when raising (source, URL, etc.)
4. Log at the point of handling, not raising
5. Don't catch and re-raise without adding value
