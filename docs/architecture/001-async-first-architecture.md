# ADR-001: Async-First Architecture

## Status
Accepted

## Context

The politician trading tracker needs to collect data from many web sources
(US Congress, EU Parliament, UK Parliament, state governments, etc.). Each
source may have:

- Network latency (100ms-2s per request)
- Rate limits requiring delays between requests
- Multiple pages/documents to fetch per source
- Independent data that can be collected in parallel

A synchronous approach would result in very long collection times as each
request blocks the next.

## Decision

We use an **async-first architecture** throughout the codebase:

1. **All scrapers are async**: Using `aiohttp` for HTTP requests
2. **Database operations support async**: Though Supabase client may not be fully async
3. **Workflow orchestration is async**: Multiple sources can run concurrently
4. **Entry points use `asyncio.run()`**: For CLI and scheduled jobs

Key patterns:
```python
# Scraper pattern
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.text()

# Workflow pattern
async def run_full_collection():
    results = await asyncio.gather(
        collect_us_congress(),
        collect_eu_parliament(),
        return_exceptions=True
    )
```

## Consequences

### Positive
- **Performance**: Multiple sources collected concurrently
- **Responsiveness**: Long operations don't block the event loop
- **Scalability**: Easy to add more sources without increasing total time
- **Rate limit friendly**: Can manage delays without blocking

### Negative
- **Complexity**: Async code is harder to debug
- **Testing**: Requires async test fixtures (`pytest-asyncio`)
- **Mixed sync/async**: Some libraries (Supabase) aren't fully async
- **Error handling**: Need to handle exceptions in gather() carefully

### Mitigations
- Use `return_exceptions=True` in gather() to prevent one failure from stopping all
- Wrap sync operations in executor if needed
- Use structured logging to trace async execution
