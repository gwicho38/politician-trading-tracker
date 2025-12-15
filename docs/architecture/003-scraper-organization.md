# ADR-003: Scraper Module Organization

## Status
Proposed

## Context

The `scrapers/scrapers.py` file has grown to ~2000 lines containing:
- `BaseScraper` abstract class
- `HouseDisclosureScraper` (US House)
- `CongressTradingScraper` (Congress.gov)
- `EUParliamentScraper`
- `QuiverQuantScraper`
- `PoliticianMatcher`
- Various helper functions and PDF parsing code

This makes the file:
- Hard to navigate
- Difficult to test individual scrapers
- Challenging to understand dependencies
- Prone to merge conflicts

## Decision (Proposed)

Reorganize the scrapers module into separate files:

```
scrapers/
    __init__.py          # Re-exports all scrapers
    base.py              # BaseScraper abstract class
    us_house.py          # HouseDisclosureScraper
    us_congress.py       # CongressTradingScraper
    eu_parliament.py     # EUParliamentScraper
    quiverquant.py       # QuiverQuantScraper
    matcher.py           # PoliticianMatcher
    parsers/
        __init__.py
        pdf.py           # PDF parsing utilities
        html.py          # HTML parsing utilities
```

Each scraper file should:
1. Import from `base.py`
2. Contain one main scraper class
3. Include scraper-specific parsing logic
4. Have its own test file

## Consequences

### Positive
- **Readability**: Each file has single responsibility
- **Testability**: Can test scrapers in isolation
- **Maintainability**: Changes to one scraper don't affect others
- **Onboarding**: Easier to understand one scraper at a time

### Negative
- **Migration effort**: Need to update all imports
- **More files**: More files to navigate
- **Circular imports**: Need to be careful with dependencies

### Migration Plan
1. Create new file structure
2. Move classes one at a time
3. Update `__init__.py` to re-export
4. Update imports throughout codebase
5. Delete old `scrapers.py`
