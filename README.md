# Politician Trading Tracker

Comprehensive politician trading disclosure tracker with scrapers for multiple jurisdictions including US Congress, EU Parliament, UK Parliament, US states, and more.

## Overview

This project provides a unified framework for collecting, processing, and analyzing financial disclosures and trading activities of politicians worldwide. It includes scrapers for official government sources, data normalization, database storage, and ML preprocessing capabilities.

## Features

### Scrapers

- **US Federal**
  - US House of Representatives
  - US Senate
  - Third-party aggregators (QuiverQuant, etc.)

- **US State Level**
  - California (NetFile, FPPC)
  - Texas
  - New York
  - Florida
  - And more...

- **International**
  - EU Parliament
  - UK Parliament
  - EU Member States (Germany, France, Italy, Spain, Netherlands)

- **Corporate Registries**
  - SEC filings
  - State business registries
  - International corporate registries

### Data Processing

- Automated data collection workflows
- Politician matching and deduplication
- Data normalization and validation
- Supabase database integration
- ML preprocessing for analysis

### Monitoring & Scheduling

- Real-time scraping status monitoring
- Scheduled data collection via cron/daemon
- Error tracking and alerting
- Job status tracking

## Installation

```bash
# Clone the repository
git clone https://github.com/gwicho38/politician-trading-tracker.git
cd politician-trading-tracker

# Install with pip
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Create a `.env` file with the following variables:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
SUPABASE_SERVICE_KEY=your_service_key

# API Keys (optional for enhanced data)
QUIVER_API_KEY=your_quiver_key

# Scraping Configuration
SCRAPING_DELAY=1.0
MAX_RETRIES=3
TIMEOUT=30
```

## Usage

### Command Line Interface

```bash
# Run full collection workflow
politician-trading collect

# Seed database with sample data
politician-trading-seed

# Check status
politician-trading status

# Run specific scraper
politician-trading scrape --source us-congress
politician-trading scrape --source uk-parliament
politician-trading scrape --source california
```

### Python API

```python
from politician_trading.workflow import PoliticianTradingWorkflow
from politician_trading.config import WorkflowConfig

# Initialize workflow
config = WorkflowConfig.default()
workflow = PoliticianTradingWorkflow(config)

# Run full collection
results = await workflow.run_full_collection()

# Check status
status = await workflow.get_status()
```

### Scrapers

```python
from politician_trading.scrapers import (
    CongressTradingScraper,
    UKParliamentScraper,
    CaliforniaScraper
)

# US Congress scraper
scraper = CongressTradingScraper()
async with scraper:
    house_disclosures = await scraper.scrape_house_disclosures()
    senate_disclosures = await scraper.scrape_senate_disclosures()

# UK Parliament scraper
uk_scraper = UKParliamentScraper()
async with uk_scraper:
    uk_disclosures = await uk_scraper.scrape_mp_interests()
```

## Database Schema

The project uses a normalized database schema with the following main tables:

- `politicians` - Politician profile information
- `trading_disclosures` - Individual trading/financial disclosures
- `data_pull_jobs` - Job tracking for collection runs

See `supabase/sql/politician_trading_schema.sql` for the complete schema.

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/politician_trading --cov-report=html

# Lint code
black src/ tests/
isort src/ tests/
ruff check src/ tests/
```

### Adding New Scrapers

1. Create a new scraper module in `src/politician_trading/scrapers/`
2. Inherit from base scraper class or implement required interface
3. Add scraper to workflow in `workflow.py`
4. Add tests in `tests/integration/`
5. Update documentation

Example:

```python
from politician_trading.scrapers.base import BaseScraper
from politician_trading.models import TradingDisclosure

class NewJurisdictionScraper(BaseScraper):
    async def scrape_disclosures(self) -> List[TradingDisclosure]:
        # Implementation
        pass
```

## Testing

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit

# Run only integration tests
pytest tests/integration

# Skip slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=src/politician_trading --cov-report=html
```

## Deployment

### Supabase Functions

Deploy the automated collection function:

```bash
cd supabase
supabase functions deploy politician-trading-collect
```

### Scheduled Jobs

Set up cron jobs for automated collection:

```bash
# Daily collection at 2 AM
0 2 * * * politician-trading collect --mode daily

# Weekly full scan on Sundays at 3 AM
0 3 * * 0 politician-trading collect --mode full
```

## Data Sources

### Official Sources

- [US House Financial Disclosures](https://disclosures-clerk.house.gov/)
- [US Senate Financial Disclosures](https://efdsearch.senate.gov/)
- [UK Parliament Register of Interests](https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/)
- [EU Parliament Declarations](https://www.europarl.europa.eu/meps/en/declarations)

### Third-Party Aggregators

- QuiverQuant
- Capitol Trades
- Various state disclosure systems

## Architecture

```
politician-trading-tracker/
├── src/politician_trading/
│   ├── scrapers/          # Data collection modules
│   ├── database/          # Database operations
│   ├── models/            # Data models
│   ├── preprocessing/     # ML preprocessing
│   ├── ml/                # ML features
│   ├── config.py          # Configuration
│   ├── workflow.py        # Main orchestration
│   └── monitoring.py      # Status monitoring
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   └── guides/
├── supabase/
│   ├── functions/
│   └── sql/
└── scripts/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This project is for research and transparency purposes only. Always comply with terms of service and robots.txt when scraping data. The data collected is from publicly available sources.

## Acknowledgments

- Data sources: US House, US Senate, UK Parliament, EU Parliament, and various state governments
- Built with inspiration from transparency and government accountability projects

## Support

- Issues: [GitHub Issues](https://github.com/gwicho38/politician-trading-tracker/issues)
- Documentation: See `docs/` directory
