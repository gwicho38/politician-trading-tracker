# Politician Trading Tracker - Codebase Architecture

## Overview

The Politician Trading Tracker uses a **tripartite architecture** with three main application components, all connecting to Supabase as the shared data layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRIPARTITE ARCHITECTURE                         │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│       CLIENT        │       SERVER        │          ETL SERVICE            │
│      (React)        │     (Phoenix)       │           (Python)              │
├─────────────────────┼─────────────────────┼─────────────────────────────────┤
│ • Web UI            │ • REST API          │ • Data ingestion                │
│ • Dashboard         │ • Business logic    │ • Congress.gov API              │
│ • Authentication    │ • Background jobs   │ • QuiverQuant API               │
│ • State management  │ • WebSocket/PubSub  │ • PDF parsing                   │
│ • Routing           │ • Lambda sandbox    │ • ML training                   │
└─────────┬───────────┴──────────┬──────────┴──────────────┬──────────────────┘
          │                      │                         │
          └──────────────────────┼─────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │        SUPABASE         │
                    │      (PostgreSQL)       │
                    │                         │
                    │  • politicians          │
                    │  • trading_disclosures  │
                    │  • scheduled_jobs       │
                    │  • job_executions       │
                    └─────────────────────────┘
```

---

## 1. CLIENT (React Frontend)

**Location:** `client/`

**Technology Stack:**
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS + shadcn/ui
- Supabase JS client for auth and data
- TanStack Query for data fetching

### Directory Structure

```
client/
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── ui/             # shadcn/ui primitives
│   │   ├── dashboard/      # Dashboard-specific components
│   │   └── layout/         # Layout components (nav, sidebar)
│   ├── pages/              # Route page components
│   │   ├── Dashboard.tsx
│   │   ├── TradingSignals.tsx
│   │   ├── Portfolio.tsx
│   │   ├── Orders.tsx
│   │   └── Politicians.tsx
│   ├── hooks/              # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useTrades.ts
│   │   └── usePolicians.ts
│   ├── lib/                # Utilities and clients
│   │   ├── supabase.ts     # Supabase client singleton
│   │   ├── api.ts          # API client for Phoenix server
│   │   └── utils.ts        # Helper functions
│   └── App.tsx             # Root component with routing
├── e2e/                    # Playwright E2E tests
├── package.json
└── vite.config.ts
```

### Key Features

1. **Authentication** - Supabase Auth with OAuth providers
2. **Dashboard** - Trading activity overview with charts
3. **Trading Signals** - ML-powered recommendations
4. **Portfolio** - User portfolio tracking
5. **Orders** - Trade execution interface
6. **Politicians** - Browse and search disclosures

### Build & Deploy

```bash
cd client
bun install          # Install dependencies
bun dev              # Development server (http://localhost:5173)
bun run build        # Production build
bun run preview      # Preview production build
```

---

## 2. SERVER (Elixir Phoenix)

**Location:** `server/`

**Technology Stack:**
- Elixir 1.15+ with Phoenix 1.7
- Ecto for database access
- Oban for background jobs
- Phoenix Channels for real-time

### Directory Structure

```
server/
├── lib/
│   ├── politician_trading/           # Business logic (contexts)
│   │   ├── politicians.ex            # Politician context
│   │   ├── disclosures.ex            # Disclosure context
│   │   ├── jobs.ex                   # Job management
│   │   └── lambda/                   # Lambda sandbox
│   │       ├── sandbox.ex            # Code execution sandbox
│   │       └── validator.ex          # Security validation
│   ├── politician_trading_web/       # Web layer
│   │   ├── controllers/              # REST API controllers
│   │   ├── channels/                 # WebSocket channels
│   │   ├── router.ex                 # Route definitions
│   │   └── endpoint.ex               # HTTP endpoint config
│   └── politician_trading.ex         # Application entry
├── config/
│   ├── config.exs                    # Base config
│   ├── dev.exs                       # Development config
│   ├── prod.exs                      # Production config
│   └── runtime.exs                   # Runtime config (env vars)
├── mix.exs                           # Project definition
└── fly.toml                          # Fly.io deployment config
```

### Key Features

1. **REST API** - CRUD endpoints for all resources
2. **Background Jobs** - Oban for scheduled tasks
3. **WebSocket** - Real-time updates via Phoenix Channels
4. **Lambda Sandbox** - Secure code execution environment

### API Endpoints

```
GET    /api/politicians           # List politicians
GET    /api/politicians/:id       # Get politician details
GET    /api/disclosures           # List disclosures
GET    /api/disclosures/:id       # Get disclosure details
POST   /api/jobs/trigger          # Trigger ETL job
GET    /api/jobs/status           # Get job statuses
POST   /api/lambda/execute        # Execute lambda code
```

### Build & Deploy

```bash
cd server
mix deps.get         # Install dependencies
mix ecto.setup       # Create and migrate DB
mix phx.server       # Start server (http://localhost:4000)
mix test             # Run tests
```

---

## 3. ETL SERVICE (Python)

**Location:** `python-etl-service/`

**Technology Stack:**
- Python 3.11+
- FastAPI for HTTP endpoints
- Supabase Python client
- pdfplumber for PDF parsing
- httpx for API requests

### Directory Structure

```
python-etl-service/
├── app/
│   ├── lib/                      # Shared utilities
│   │   ├── __init__.py           # Public exports
│   │   ├── database.py           # Supabase client
│   │   ├── parser.py             # Text parsing utilities
│   │   ├── pdf_utils.py          # PDF extraction
│   │   └── politician.py         # Politician lookup/create
│   ├── services/                 # ETL services
│   │   ├── house_etl.py          # House disclosure ETL
│   │   ├── senate_etl.py         # Senate disclosure ETL
│   │   └── quiverquant.py        # QuiverQuant ETL
│   └── main.py                   # Service entry point
├── requirements.txt
├── Dockerfile
└── fly.toml                      # Fly.io deployment config
```

### Key Features

1. **House ETL** - Parse House financial disclosures
2. **Senate ETL** - Parse Senate financial disclosures
3. **QuiverQuant ETL** - Fetch aggregated trading data
4. **PDF Parsing** - Extract tables from disclosure PDFs
5. **Politician Matching** - Find or create politician records
6. **Ticker Extraction** - Extract stock symbols from text

### Shared Library (`app/lib/`)

The shared library consolidates common functions:

```python
from app.lib import (
    # Database
    get_supabase,
    upload_transaction_to_supabase,

    # Parser
    clean_asset_name,
    extract_ticker_from_text,
    parse_value_range,
    sanitize_string,

    # PDF
    extract_tables_from_pdf,
    extract_text_from_pdf,

    # Politician
    find_or_create_politician,
)
```

### Build & Deploy

```bash
cd python-etl-service
uv sync              # Install dependencies
python -m app.main   # Run service
pytest               # Run tests
```

---

## 4. DATABASE SCHEMA

### Core Tables

#### `politicians`
```sql
CREATE TABLE politicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    full_name VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    chamber VARCHAR(20),          -- 'house' or 'senate'
    role VARCHAR(50),             -- 'Representative' or 'Senator'
    party VARCHAR(50),
    state VARCHAR(2),
    district VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `trading_disclosures`
```sql
CREATE TABLE trading_disclosures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID REFERENCES politicians(id),
    transaction_date DATE,
    disclosure_date DATE,
    transaction_type VARCHAR(50),  -- 'purchase', 'sale', etc.
    asset_name VARCHAR(255),
    asset_ticker VARCHAR(20),
    asset_type VARCHAR(50),
    amount_range_min NUMERIC,
    amount_range_max NUMERIC,
    source_url TEXT,
    source_document_id VARCHAR(100),
    raw_data JSONB,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT idx_disclosures_unique UNIQUE (
        politician_id, transaction_date, asset_name,
        transaction_type, disclosure_date
    )
);
```

#### `scheduled_jobs`
```sql
CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(100) UNIQUE,
    job_name VARCHAR(200),
    job_function VARCHAR(200),
    schedule_type VARCHAR(20),     -- 'interval' or 'cron'
    schedule_value VARCHAR(100),
    enabled BOOLEAN DEFAULT true,
    last_successful_run TIMESTAMPTZ,
    last_attempted_run TIMESTAMPTZ,
    next_scheduled_run TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    max_consecutive_failures INTEGER DEFAULT 3,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `job_executions`
```sql
CREATE TABLE job_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,   -- 'success', 'failed', 'cancelled'
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds DECIMAL(10,3),
    error_message TEXT,
    logs TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. CLI WORKFLOWS

**Location:** `.mcli/workflows/`

The project uses `mcli` for deployment and management workflows. After restructuring, workflows are organized by application component:

### Workflow Structure

```
.mcli/workflows/
├── client.py           # React frontend commands
├── server.py           # Phoenix server + lambda subcommands
├── etl.py              # ETL + congress/quiver/backfill/ml subcommands
├── jobs.py             # Cross-service job monitoring
├── supabase.py         # Database management
├── services.sh         # Fly.io deployment orchestration
└── workflows.lock.json # Registry of available commands
```

### Available Commands

#### Client (`mcli run client`)
- `deploy` - Deploy to Fly.io
- `status` - Check deployment status
- `logs` - Stream logs
- `open` - Open in browser

#### Server (`mcli run server`)
- `deploy` - Deploy to Fly.io
- `status` - Check server status
- `logs` - Stream logs
- `jobs` - View Phoenix job queue
- `lambda validate` - Validate Lambda sandbox
- `lambda test-security` - Test security rules
- `lambda apply` - Apply Lambda changes

#### ETL (`mcli run etl`)
- `trigger` - Trigger ETL jobs (`--house`, `--senate`, `--update`)
- `status` - View ETL status
- `congress test` - Test Congress.gov API
- `congress list-members` - List congress members
- `quiver test` - Test QuiverQuant connection
- `quiver fetch` - Fetch QuiverQuant data
- `backfill repair` - Fix data quality issues
- `backfill validate` - Validate data integrity
- `ml train` - Train ML models
- `ml status` - Check training status

#### Jobs (`mcli run jobs`)
- `status` - View all job statuses across services

#### Supabase (`mcli run supabase`)
- `tables` - List database tables
- `schema` - Show table schemas
- `query` - Execute SQL queries

#### Services (`mcli run services`)
- `deploy-all` - Deploy all services
- `status` - Check all service statuses

---

## 6. DATA FLOW

### ETL Pipeline

```
┌─────────────────┐
│   Data Sources  │
│  (Congress.gov, │
│  QuiverQuant)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ETL Service   │
│                 │
│ 1. Fetch data   │
│ 2. Parse/clean  │
│ 3. Match pols   │
│ 4. Extract info │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Supabase     │
│   (PostgreSQL)  │
│                 │
│ • politicians   │
│ • disclosures   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│     Server      │────▶│     Client      │
│   (Phoenix)     │     │    (React)      │
│                 │     │                 │
│ • API queries   │     │ • Display data  │
│ • Business logic│     │ • User actions  │
└─────────────────┘     └─────────────────┘
```

### Request Flow (Client → Server → DB)

1. **Client** makes API request to Phoenix server
2. **Server** authenticates via Supabase JWT
3. **Server** queries Supabase PostgreSQL
4. **Server** returns JSON response
5. **Client** renders data in UI

### Job Execution Flow

1. **Scheduler** (cron or manual) triggers ETL job
2. **ETL Service** fetches data from external APIs
3. **ETL Service** processes and transforms data
4. **ETL Service** upserts to Supabase
5. **Job execution** logged to `job_executions` table
6. **Server** can query job status
7. **Client** displays job status in admin UI

---

## 7. DEPLOYMENT

All services deploy to **Fly.io** using Docker containers.

### Deployment Topology

```
┌─────────────────────────────────────────────────────────────┐
│                         FLY.IO                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │    Client    │  │    Server    │  │   ETL Service    │  │
│  │   (React)    │  │  (Phoenix)   │  │    (Python)      │  │
│  │              │  │              │  │                  │  │
│  │ Static files │  │ Web + Jobs   │  │ Scheduled tasks  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │     Supabase     │
                    │   (PostgreSQL)   │
                    │   (Hosted)       │
                    └──────────────────┘
```

### Deploy Commands

```bash
# Deploy all services
mcli run services deploy-all

# Or deploy individually
mcli run client deploy
mcli run server deploy
cd python-etl-service && fly deploy
```

---

## 8. DEVELOPMENT WORKFLOW

### Local Development

1. Start all three services in separate terminals
2. All connect to the same Supabase instance (dev or local)

```bash
# Terminal 1: Client
cd client && bun dev

# Terminal 2: Server
cd server && mix phx.server

# Terminal 3: ETL (as needed)
cd python-etl-service && python -m app.main
```

### Testing

```bash
# Client
cd client && bun test && bun run e2e

# Server
cd server && mix test

# ETL
cd python-etl-service && pytest
```

### Code Quality

```bash
# Client
cd client && bun run lint && bun run format

# Server
cd server && mix format && mix credo

# ETL
cd python-etl-service && ruff check app/ && black app/
```

---

**Document Updated:** January 2026
**Architecture Version:** Tripartite (Client + Server + ETL)
