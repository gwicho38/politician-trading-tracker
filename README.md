# Politician Trading Tracker

Track and analyze financial disclosures from US Congress members using data from official government sources and third-party aggregators.

## Overview

This project provides a full-stack application for collecting, processing, and analyzing politician trading disclosures. It uses a **tripartite architecture** with three main components:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Client** | React + TypeScript + Vite | Web frontend with dashboard, trading signals, and portfolio management |
| **Server** | Elixir Phoenix | API server, background jobs, WebSocket connections, and business logic |
| **ETL Service** | Python | Data ingestion from Congress.gov, QuiverQuant, and PDF parsing |

All components connect to **Supabase** (PostgreSQL) as the shared data layer.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Client    │     │   Server    │     │   ETL Service   │
│   (React)   │     │  (Phoenix)  │     │    (Python)     │
└──────┬──────┘     └──────┬──────┘     └────────┬────────┘
       │                   │                     │
       └───────────────────┼─────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Supabase   │
                    │ (PostgreSQL)│
                    └─────────────┘
```

## Features

### Data Sources

- **US Congress** - House and Senate financial disclosures via Congress.gov API
- **QuiverQuant** - Third-party aggregator with enriched trading data
- **PDF Parsing** - Direct extraction from disclosure PDFs using pdfplumber

### Client Features

- Modern dashboard with trading activity overview
- ML-powered trading signal recommendations
- Portfolio tracking and order management
- Politician search and filtering
- User authentication via Supabase Auth

### Server Features

- REST API for client consumption
- Background job processing (Oban)
- Real-time updates via Phoenix Channels
- Lambda sandbox for secure code execution

### ETL Features

- Automated data collection pipelines
- Politician matching and deduplication
- Ticker symbol extraction and validation
- Scheduled job execution via cron

## Quick Start

```bash
# Clone the repository
git clone https://github.com/gwicho38/politician-trading-tracker.git
cd politician-trading-tracker

# Start all services locally
make dev

# Or start individual components:
cd client && bun dev          # React frontend at http://localhost:5173
cd server && mix phx.server   # Phoenix server at http://localhost:4000
cd python-etl-service && python -m app.main  # ETL service
```

## Project Structure

```
politician-trading-tracker/
├── client/                 # React frontend (Vite + TypeScript + Tailwind)
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route pages
│   │   ├── hooks/          # Custom React hooks
│   │   └── lib/            # Utilities and Supabase client
│   └── package.json
│
├── server/                 # Elixir Phoenix backend
│   ├── lib/
│   │   ├── politician_trading/        # Business logic
│   │   └── politician_trading_web/    # Web layer (controllers, channels)
│   └── mix.exs
│
├── python-etl-service/     # Python ETL microservice
│   ├── app/
│   │   ├── lib/            # Shared utilities (database, parser, pdf_utils)
│   │   ├── services/       # ETL services (house, senate, quiverquant)
│   │   └── main.py         # Service entry point
│   └── requirements.txt
│
├── supabase/               # Database configuration
│   ├── functions/          # Edge Functions
│   └── sql/                # Schema migrations
│
├── .mcli/workflows/        # CLI workflow commands
│   ├── client.py           # Client deployment commands
│   ├── server.py           # Server deployment + lambda subcommands
│   ├── etl.py              # ETL + congress/quiver/backfill/ml subcommands
│   ├── jobs.py             # Cross-service job monitoring
│   ├── supabase.py         # Database management
│   └── services.sh         # Fly.io orchestration
│
└── docs/                   # Documentation
```

## Installation

### Prerequisites

- **Node.js 20+** or **Bun** (for client)
- **Elixir 1.15+** and **Erlang/OTP 26+** (for server)
- **Python 3.11+** with **uv** (for ETL service)
- **Supabase** account (for database)

### Setup Each Component

```bash
# Client
cd client
bun install  # or npm install

# Server
cd server
mix deps.get
mix ecto.setup

# ETL Service
cd python-etl-service
uv sync  # or pip install -r requirements.txt
```

### Environment Variables

Each component needs its own `.env` file:

```bash
# Copy example files
cp client/.env.production.example client/.env
cp server/.env.example server/.env
cp .env.example .env  # Root for ETL service
```

## Configuration

### Client (client/.env)

```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:4000  # Phoenix server URL
```

### Server (server/.env)

```bash
DATABASE_URL=ecto://postgres:password@localhost/politician_trading_dev
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
SECRET_KEY_BASE=your_phoenix_secret_key
```

### ETL Service (.env in root)

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
QUIVER_API_KEY=your_quiver_key  # Optional, for QuiverQuant data
CONGRESS_API_KEY=your_congress_key  # Optional, for Congress.gov API
```

## Usage

### Development

Start all services for local development:

```bash
# Terminal 1: Client
cd client && bun dev
# Opens http://localhost:5173

# Terminal 2: Server
cd server && mix phx.server
# API at http://localhost:4000

# Terminal 3: ETL (run as needed)
cd python-etl-service && python -m app.main
```

### CLI Workflows (mcli)

The project uses `mcli` for deployment and management workflows:

```bash
# Client commands
mcli run client deploy           # Deploy React app to Fly.io
mcli run client status           # Check deployment status

# Server commands
mcli run server deploy           # Deploy Phoenix server to Fly.io
mcli run server status           # Check server status
mcli run server lambda validate  # Test Lambda sandbox

# ETL commands
mcli run etl trigger --house     # Trigger House ETL job
mcli run etl trigger --senate    # Trigger Senate ETL job
mcli run etl congress test       # Test Congress.gov API
mcli run etl quiver fetch        # Fetch QuiverQuant data
mcli run etl backfill repair     # Fix data quality issues
mcli run etl ml train            # Train ML models

# Cross-service commands
mcli run jobs status             # View all job statuses
mcli run supabase tables         # List database tables
mcli run services deploy-all     # Deploy all services
```

### Web Application Pages

- **Dashboard** - Overview of trading activity and market signals
- **Trading Signals** - ML-powered buy/sell recommendations
- **Portfolio** - Track investments and performance
- **Orders** - Execute and manage trades
- **Politicians** - Browse and search politician disclosures

## Deployment

All services deploy to **Fly.io** with Docker containers.

### Deploy Individual Services

```bash
# Deploy client (React)
mcli run client deploy

# Deploy server (Phoenix)
mcli run server deploy

# Deploy ETL service
cd python-etl-service && fly deploy
```

### Deploy All Services

```bash
mcli run services deploy-all
```

### Fly.io Configuration

Each service has its own `fly.toml`:
- `client/fly.toml` - React static site
- `server/fly.toml` - Phoenix application
- `python-etl-service/fly.toml` - Python worker

### Database Setup

1. Create a Supabase project at https://supabase.com
2. Run migrations from `supabase/sql/`
3. Set environment variables in each service

## Database Schema

Core tables in Supabase PostgreSQL:

| Table | Purpose |
|-------|---------|
| `politicians` | Politician profiles (name, party, state, chamber) |
| `trading_disclosures` | Individual trade transactions |
| `scheduled_jobs` | ETL job definitions and schedules |
| `job_executions` | Job run history and logs |
| `data_pull_jobs` | Data collection tracking |

See `supabase/sql/` for complete schema definitions.

## Development

### Client Development

```bash
cd client
bun dev              # Start dev server
bun run build        # Production build
bun run lint         # ESLint
bun run test         # Vitest
bun run e2e          # Playwright E2E tests
```

### Server Development

```bash
cd server
mix deps.get         # Install dependencies
mix ecto.setup       # Create and migrate database
mix phx.server       # Start server
mix test             # Run tests
```

### ETL Development

```bash
cd python-etl-service
uv sync              # Install dependencies
pytest               # Run tests
ruff check app/      # Linting
```

## Testing

```bash
# Client (Vitest + Playwright)
cd client && bun test && bun run e2e

# Server (ExUnit)
cd server && mix test

# ETL (pytest)
cd python-etl-service && pytest
```

## Data Sources

### Official Sources

- [US House Financial Disclosures](https://disclosures-clerk.house.gov/)
- [US Senate Financial Disclosures](https://efdsearch.senate.gov/)
- [Congress.gov API](https://api.congress.gov/)

### Third-Party Aggregators

- [QuiverQuant](https://www.quiverquant.com/) - Aggregated congress trading data

## Architecture

### Tripartite Design

The application follows a tripartite architecture separating concerns:

| Layer | Component | Responsibilities |
|-------|-----------|------------------|
| **Presentation** | Client (React) | UI rendering, user interactions, state management |
| **Application** | Server (Phoenix) | Business logic, API endpoints, real-time features |
| **Data** | ETL Service (Python) | Data ingestion, transformation, ML processing |

### Communication Patterns

```
Client ←──REST/WebSocket──→ Server ←──HTTP──→ ETL Service
   │                          │                    │
   └──────────────────────────┼────────────────────┘
                              │
                        ┌─────▼─────┐
                        │  Supabase │
                        │    (DB)   │
                        └───────────┘
```

- **Client → Server**: REST API for CRUD, WebSocket for real-time updates
- **Server → ETL**: HTTP triggers for job execution
- **All → Supabase**: Direct database access via Supabase client libraries

### Workflow Management

CLI workflows (`.mcli/workflows/`) provide unified management:

| Workflow | Scope | Commands |
|----------|-------|----------|
| `client.py` | React frontend | deploy, status, logs, open |
| `server.py` | Phoenix server | deploy, status, logs, jobs, lambda |
| `etl.py` | Python ETL | trigger, status, congress, quiver, backfill, ml |
| `jobs.py` | All services | unified job monitoring |
| `supabase.py` | Database | tables, schema, query |
| `services.sh` | Deployment | deploy-all, status |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Component-Specific Guidelines

- **Client**: Follow React/TypeScript conventions, use existing UI components
- **Server**: Follow Elixir conventions, add ExUnit tests
- **ETL**: Follow Python conventions, add pytest tests

## License

MIT License - see LICENSE file for details

## Disclaimer

This project is for research and transparency purposes only. The data collected is from publicly available government sources.

## Documentation

- [Architecture Decisions](docs/architecture/README.md) - ADRs for major decisions
- [Pipeline Architecture](docs/PIPELINE_ARCHITECTURE.md) - ETL pipeline design
- [Database Setup](docs/database/DATABASE_SETUP.md) - Schema and migrations
- [Deployment Guide](docs/deployment/DEPLOYMENT.md) - Production deployment

## Support

- Issues: [GitHub Issues](https://github.com/gwicho38/politician-trading-tracker/issues)
- Documentation: See `docs/` directory
