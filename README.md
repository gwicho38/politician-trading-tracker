# Politician Trading Tracker

🚀 **React + Supabase** politician trading disclosure tracker with comprehensive scrapers for US Congress, EU Parliament, UK Parliament, US states, and more.

## Overview

This project provides a modern web application for collecting, processing, and analyzing financial disclosures and trading activities of politicians worldwide. It features:

- **Modern React UI** with TypeScript and Tailwind CSS
- **Supabase Backend** with PostgreSQL database and Edge Functions
- **Comprehensive Scrapers** for official government sources
- **Real-time Trading Signals** with ML-powered analysis
- **User Authentication** and subscription management
- **Admin Dashboard** for data management

**Architecture:** React SPA → Supabase Edge Functions → PostgreSQL Database

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

## Quick Start

```bash
# Clone the repository
git clone https://github.com/gwicho38/politician-trading-tracker.git
cd politician-trading-tracker

# One-command setup (installs all dependencies)
make setup

# Start development servers
make dev

# Open http://localhost:5173 in your browser
```

## Installation

### Option 1: Makefile (Recommended)

```bash
make setup          # Install all dependencies
make dev           # Start development servers
make build         # Build for production
make test          # Run all tests
```

### Option 2: Manual Setup

```bash
# Install Python dependencies
uv sync --dev

# Install React dependencies
cd submodules/capital-trades && npm install

# Set up environment variables
cp .env.example .env
cp submodules/capital-trades/.env.production.example submodules/capital-trades/.env.production
# Edit both .env files with your configuration
```

## Configuration

### Python Backend (.env)

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# API Keys (optional for enhanced data)
QUIVER_API_KEY=your_quiver_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# Scraping Configuration
SCRAPING_DELAY=1.0
MAX_RETRIES=3
TIMEOUT=30
```

### React Frontend (submodules/capital-trades/.env.production)

```bash
# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Application Configuration
VITE_APP_TITLE="Politician Trading Tracker"
VITE_APP_VERSION="1.0.0"
VITE_APP_ENVIRONMENT="production"

# Feature Flags
VITE_ENABLE_LIVE_TRADING=false
VITE_ENABLE_DEBUG_MODE=false
```

## Usage

### Web Application

Start the development server and open http://localhost:5173:

```bash
make dev
```

**Available Pages:**
- **Dashboard** - Overview of trading activity and signals
- **Trading Signals** - ML-powered trading recommendations
- **Portfolio** - Track your investments
- **Orders** - Manage trading orders
- **Admin** - Data management and system monitoring

### Command Line Interface

```bash
# Run full collection workflow
uv run politician-trading collect

# Seed database with sample data
uv run politician-trading-seed

# Check status
uv run politician-trading status

# Run specific scraper
uv run politician-trading scrape --source us-congress
uv run politician-trading scrape --source uk-parliament
uv run politician-trading scrape --source california
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

## Deployment

### Production Deployment

```bash
# Build for production
make build

# Deploy React app (choose one method)
./scripts/deploy_vercel.sh    # Vercel
./scripts/deploy_netlify.sh   # Netlify
./scripts/deploy_docker.sh    # Docker
./scripts/deploy_manual.sh    # Manual

# Deploy Supabase Edge Functions
make deploy-backend
```

### Environment Setup

1. **Supabase Project**: Create at https://supabase.com
2. **Database Schema**: Run SQL in Supabase dashboard:
   ```sql
   -- Copy contents from supabase/sql/create_missing_tables.sql
   ```
3. **Edge Functions**: Deploy via Supabase CLI:
   ```bash
   supabase functions deploy trading-signals --project-ref YOUR_PROJECT_REF
   supabase functions deploy orders --project-ref YOUR_PROJECT_REF
   supabase functions deploy portfolio --project-ref YOUR_PROJECT_REF
   ```

## Database Schema

The project uses a normalized database schema with the following main tables:

- `politician_trades` - Main trading data table
- `user_sessions` - User authentication sessions
- `action_logs` - Application action logging
- `scheduled_jobs` - Job scheduling system

See `supabase/sql/` for complete schema definitions.

## Development

### Setup Development Environment

```bash
# One-command setup
make setup

# Start development servers (React + Python)
make dev

# React app: http://localhost:9090 (or next available port)
# Python API: Available via Supabase Edge Functions
```

### Development Workflow

```bash
# Run all tests
make test

# Run linting and formatting
make lint
make format

# Build for production
make build

# Clean development artifacts
make clean
```

### Code Quality

```bash
# Python linting and formatting
uv run ruff check src/ tests/ scripts/
uv run black src/ tests/ scripts/
uv run isort src/ tests/ scripts/
uv run mypy src/

# React linting and formatting
cd submodules/capital-trades && npm run lint
cd submodules/capital-trades && npm run format
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
