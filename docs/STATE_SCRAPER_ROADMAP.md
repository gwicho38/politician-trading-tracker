# State Scraper Implementation Roadmap

## Overview

This document provides a detailed roadmap for implementing production-ready scrapers for US state and international government disclosure systems.

## Current Status Summary

### ✅ Production Ready
- **US Congress (House)**: Fully implemented with ZIP index + PDF parsing
- **US Congress (Senate)**: Basic implementation, can be enhanced
- **UK Parliament**: Implemented using official API
- **EU Parliament**: Implemented with MEP profile scraping

### ⚠️ Scaffolded (Need Implementation)
- **California**: NetFile portal scraping skeleton
- **US States**: Texas, New York, Florida, Illinois, Pennsylvania, Massachusetts
- **EU Member States**: Germany, France, Italy, Spain, Netherlands

## Priority Ranking

Based on data quality, accessibility, and market impact, here's the recommended implementation order:

### Tier 1: High Priority (Implement First)
1. **California NetFile** - Large economy, structured data available
2. **New York JCOPE** - Major financial hub
3. **Texas Ethics Commission** - Large state, active disclosure system
4. **Florida Commission on Ethics** - Large state, Form 6 filings

### Tier 2: Medium Priority
5. **Illinois Ethics** - Major economy
6. **Pennsylvania Ethics** - Structured disclosure system
7. **Massachusetts Ethics** - Strong disclosure requirements
8. **German Bundestag** - Largest EU economy
9. **French Assemblée Nationale** - Major EU country

### Tier 3: Lower Priority
10. **Italian Parliament** - Complex multi-chamber system
11. **Spanish Congreso** - Emerging disclosure requirements
12. **Dutch Tweede Kamer** - Smaller economy, good data quality
13. **Additional US States** - Other major states as resources allow

---

## Implementation Guide by Source

### 1. California NetFile

**Status**: Scaffold exists, needs implementation

**Current Code**: `src/politician_trading/scrapers/scrapers_california.py`

**Data Sources**:
- NetFile Public Portals: `https://public.netfile.com/pub2/`
  - San Francisco (AID=SFO)
  - Los Angeles County (AID=LAC)
  - Sacramento County (AID=SAC)
  - Santa Clara County (AID=SCC)
  - Ventura County (AID=VCO)
- Cal-Access: `https://cal-access.sos.ca.gov/`

**Implementation Steps**:

1. **Understand NetFile Portal Structure**
   - Navigate to public portal
   - Identify search forms and result tables
   - Map data fields to TradingDisclosure model

2. **Handle JavaScript Rendering**
   - NetFile uses JavaScript-heavy interfaces
   - Options:
     - Selenium/Playwright for browser automation
     - Reverse-engineer API calls (check Network tab)
     - Use public data exports if available

3. **Parse Data Tables**
   - Extract transaction records from HTML tables
   - Parse amounts, dates, filers
   - Match politicians to records

4. **Implement Cal-Access Integration**
   - Download database exports
   - Parse fixed-width format files
   - Extract state-level filings

**Estimated Effort**: 2-3 weeks

**Challenges**:
- JavaScript-rendered content
- Multiple portal systems with different formats
- Rate limiting concerns

**Code Template**:
```python
async def _scrape_netfile_portal(self, portal_url: str) -> List[TradingDisclosure]:
    """Scrape NetFile portal using Playwright for JavaScript rendering"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(portal_url)
        # Navigate forms, extract data
        await browser.close()
```

---

### 2. New York JCOPE

**Status**: Scaffold exists, returns sample data

**Current Code**: `src/politician_trading/scrapers/scrapers_us_states.py::NewYorkJCOPEScraper`

**Data Source**: `https://www.jcope.ny.gov`

**Implementation Steps**:

1. **Research JCOPE System**
   - Navigate disclosure database
   - Identify access methods (portal, API, exports)
   - Document required parameters

2. **Implement Search & Retrieval**
   - If portal-based: Automate form submission
   - If API available: Use direct API calls
   - If exports available: Download and parse

3. **Parse Disclosure Forms**
   - Extract financial interests from PDFs or HTML
   - Map to standardized fields
   - Handle various disclosure types

4. **Match Politicians**
   - Build roster of NY officials
   - Match filings to politician records
   - Handle name variations

**Estimated Effort**: 2-3 weeks

**Challenges**:
- May require manual navigation/authentication
- PDF parsing if documents not structured
- Frequent system changes

---

### 3. Texas Ethics Commission

**Status**: Scaffold exists, returns sample data

**Current Code**: `src/politician_trading/scrapers/scrapers_us_states.py::TexasEthicsCommissionScraper`

**Data Source**: `https://www.ethics.state.tx.us`

**Implementation Steps**:

1. **Identify Data Access Method**
   - Search functionality
   - Bulk data downloads
   - API availability

2. **Parse Personal Financial Statements (PFS)**
   - Texas officials file annual PFS
   - Extract investment holdings
   - Parse stock transactions

3. **Handle Texas-Specific Formats**
   - Texas uses unique disclosure categories
   - Map to standard transaction types
   - Handle ranges and estimated values

**Estimated Effort**: 2 weeks

**Challenges**:
- Texas-specific terminology and categories
- May have limited search capabilities
- Varying filing formats

---

### 4. Florida Commission on Ethics

**Status**: Scaffold exists, returns sample data

**Current Code**: `src/politician_trading/scrapers/scrapers_us_states.py::FloridaCommissionEthicsScraper`

**Data Source**: `https://www.ethics.state.fl.us`

**Implementation Steps**:

1. **Access Form 6 Filings**
   - Form 6 is Florida's full disclosure form
   - Identify search/download system
   - Automate retrieval

2. **Parse Form 6 Data**
   - Extract asset holdings
   - Parse income sources
   - Identify securities transactions

3. **Build Florida Politician Roster**
   - Governor, Cabinet, Legislature
   - Match names to filings
   - Track current vs. former officials

**Estimated Effort**: 2 weeks

**Challenges**:
- PDF-based filings
- Manual search interface
- Large number of filers

---

### 5-7. Other US States (Illinois, Pennsylvania, Massachusetts)

**General Approach**:

1. **Research & Documentation**
   - Navigate official ethics site
   - Document disclosure requirements
   - Identify data access methods

2. **Implement Core Scraping**
   - Use BaseScraper framework
   - Add state-specific parsing
   - Handle unique formats

3. **Test & Validate**
   - Test with known filings
   - Validate data completeness
   - Check for edge cases

**Estimated Effort**: 1-2 weeks per state

---

### 8-9. German & French Scrapers

**Status**: Scaffolds exist, return sample data

**Current Code**: `src/politician_trading/scrapers/scrapers_eu.py`

**German Bundestag**:
- **Source**: `https://www.bundestag.de`
- **Data**: Shareholdings, board memberships, outside income
- **Format**: Profile pages in German
- **Challenges**: Language parsing, different disclosure thresholds (€25,000)

**French Assemblée Nationale**:
- **Source**: `https://www2.assemblee-nationale.fr` + HATVP
- **Data**: Asset declarations via HATVP (High Authority)
- **Format**: PDF declarations in French
- **Challenges**: French language, HATVP access requirements

**Implementation Steps**:

1. **Add Language Support**
   - Translation libraries for parsing
   - Multilingual field mapping

2. **Handle EU-Specific Formats**
   - Different disclosure thresholds
   - Asset vs. transaction focus
   - Board membership tracking

3. **Parse Structured vs. Unstructured Data**
   - Some countries have APIs
   - Others require PDF/HTML parsing

**Estimated Effort**: 2-3 weeks per country

---

## Technical Requirements

### Infrastructure

1. **Browser Automation** (if needed)
   ```bash
   uv add playwright
   playwright install
   ```

2. **Advanced PDF Parsing**
   ```bash
   # Already included:
   # - pdfplumber (primary)
   # - pytesseract + pdf2image (OCR fallback)
   ```

3. **Language Processing** (for international)
   ```bash
   uv add langdetect googletrans
   ```

### Database Schema

No changes needed - existing schema supports all disclosure types:
- `trading_disclosures` table handles all transaction types
- `raw_data` JSONB field preserves source-specific data
- `source_url` tracks original document

### Testing Strategy

For each new scraper:

1. **Unit Tests**
   - Test parsing logic with sample data
   - Validate data transformation
   - Check error handling

2. **Integration Tests**
   - Test against live system (with rate limiting)
   - Verify end-to-end flow
   - Check data quality

3. **Regression Tests**
   - Save sample responses
   - Test parser against known good data
   - Catch breaking changes

### Deployment Considerations

1. **Rate Limiting**
   - Each scraper needs appropriate delays
   - Some systems may IP-block aggressive scraping
   - Consider using proxies if needed

2. **Scheduling**
   - State filings typically annual or quarterly
   - Schedule appropriately (monthly for most)
   - Stagger runs to distribute load

3. **Monitoring**
   - Track success rates per scraper
   - Alert on failures
   - Monitor data quality metrics

---

## Development Workflow

### For Each New Scraper:

1. **Research Phase** (1-2 days)
   - Explore disclosure system
   - Document data structure
   - Identify technical approach

2. **Implementation Phase** (3-7 days)
   - Code scraper class
   - Implement parsing logic
   - Add validation

3. **Testing Phase** (2-3 days)
   - Write unit tests
   - Run integration tests
   - Validate sample data

4. **Integration Phase** (1-2 days)
   - Add to workflow
   - Update documentation
   - Configure scheduling

5. **Monitoring Phase** (ongoing)
   - Track scraper health
   - Fix issues as they arise
   - Adapt to system changes

---

## Resource Allocation

### Developer Time Required

**Per Scraper** (average):
- Research: 1-2 days
- Implementation: 3-7 days
- Testing: 2-3 days
- Integration: 1-2 days
- **Total: 7-14 days** per scraper

**For All Priority Scrapers** (Tiers 1-2):
- 9 scrapers × 10 days average = **90 developer days**
- With 1 full-time developer: **4-5 months**
- With 2 developers: **2-3 months**

### Incremental Approach

**Phase 1** (Month 1): California, New York
- Largest economies, best data availability
- Establish patterns for state scrapers

**Phase 2** (Month 2): Texas, Florida, Illinois
- Additional major states
- Refine scraping framework

**Phase 3** (Month 3): Pennsylvania, Massachusetts, Germany
- Round out US coverage
- Begin international expansion

**Phase 4** (Month 4+): France, Italy, Spain, Netherlands
- Complete EU major economies
- Add additional US states as needed

---

## Success Metrics

### Per Scraper:
- **Data Coverage**: >80% of recent filings captured
- **Success Rate**: >90% successful runs
- **Data Quality**: >95% valid records (pass validation)
- **Freshness**: Data updated within 48 hours of filing

### Overall System:
- **Uptime**: >99% (scrapers healthy)
- **Total Records**: Growing monthly
- **Response Time**: <60 seconds per scraper run
- **Alert Resolution**: <24 hours for critical failures

---

## Maintenance & Updates

### Ongoing Requirements:

1. **System Changes**
   - Government sites change frequently
   - Scrapers break when sites redesign
   - Plan for 2-4 hours/month per scraper

2. **Data Quality Monitoring**
   - Review validation errors
   - Investigate anomalies
   - Update parsers as needed

3. **Legal Compliance**
   - Respect robots.txt
   - Monitor for access restrictions
   - Ensure proper attribution

---

## Conclusion

This roadmap provides a structured approach to implementing comprehensive scraping coverage. The existing infrastructure (circuit breakers, monitoring, validation) provides a solid foundation for adding new scrapers efficiently.

**Key Takeaways**:
- Prioritize based on data quality and market impact
- Use incremental approach (one scraper at a time)
- Leverage existing framework and patterns
- Monitor and maintain continuously

**Next Steps**:
1. Review and approve priority ranking
2. Allocate development resources
3. Begin Phase 1 implementation
4. Establish monitoring and maintenance processes
