# CLAUDE.md - Project Configuration for ClawdBot

## Project Overview

**govmarket.trade** (Politician Trading Tracker) is a web application that tracks and displays stock trades made by US politicians, making congressional trading data accessible and transparent to the public.

**Repository:** `gwicho38/politician-trading-tracker`
**Live Site:** https://govmarket.trade

---

## Critical Rules

- **ALWAYS** use Supabase, never raw PostgreSQL
- **NEVER** use mock data - all frontend functions must be wired with real data
- If using curl multiple times in a session, create an mcli local command for that logic
- **ALWAYS** run tests before committing
- **NEVER** commit secrets or credentials

---

## Tech Stack

### Frontend (Client)
- **Framework:** React 18.3 + Vite 5.4
- **Language:** TypeScript 5.8
- **Styling:** Tailwind CSS 3.4 + Shadcn/UI + Radix UI
- **State Management:** TanStack Query (React Query) 5.83
- **Forms:** React Hook Form + Zod validation
- **Charts:** Recharts 2.15
- **Web3:** Wagmi, Viem, RainbowKit
- **Database Client:** @supabase/supabase-js
- **Testing:** Vitest + Playwright

### Backend (Server)
- **Framework:** Phoenix 1.7.21 (Elixir)
- **Language:** Elixir ~1.14
- **HTTP Server:** Bandit
- **ORM:** Ecto + Phoenix Ecto
- **Job Scheduler:** Quantum
- **Testing:** ExUnit + Mox

### Data Pipeline (ETL Service)
- **Framework:** FastAPI 0.128
- **Language:** Python 3.11+
- **Package Manager:** UV
- **PDF Parsing:** pdfplumber, pytesseract
- **Web Scraping:** BeautifulSoup, Playwright, cloudscraper
- **ML:** PyTorch, scikit-learn, XGBoost, LightGBM
- **Trading APIs:** Alpaca, yfinance
- **Testing:** pytest

### Database
- **Platform:** Supabase (PostgreSQL)
- **Connection:** Pooler (aws-1-eu-north-1.pooler.supabase.com:6543)

### Infrastructure
- **Hosting:** Fly.io (all services)
- **CI/CD:** GitHub Actions
- **Edge Functions:** Supabase (Deno)

---

## Development Commands

### Quick Start
```bash
make setup              # Install all dependencies
make dev                # Start all services (localhost:9090)
```

### Frontend (client/)
```bash
npm run dev             # Vite dev server
npm run build           # Production build
npm run lint            # ESLint
npm test                # Vitest unit tests
npm run test:e2e        # Playwright E2E tests
```

### Backend (server/)
```bash
mix deps.get            # Install dependencies
mix phx.server          # Start server (localhost:4000)
mix test                # Run ExUnit tests
mix format              # Format code
```

### ETL Service (python-etl-service/)
```bash
uv sync                 # Install dependencies
pytest                  # Run tests
pytest -v --cov         # Tests with coverage
ruff check app/         # Linting
black app/              # Formatting
```

### All Services
```bash
make test               # Run all tests
make lint               # Lint all code
make build              # Build for production
make deploy             # Deploy to Fly.io
```

### mcli Workflows
```bash
mcli run client deploy           # Deploy React app
mcli run server deploy           # Deploy Phoenix server
mcli run etl trigger --house     # Trigger House ETL
mcli run jobs status             # View all job statuses
mcli run services deploy-all     # Deploy all services
mcli run supabase tables         # List database tables
```

---

## Project Structure

```
politician-trading-tracker/
├── client/                    # React + Vite frontend
│   ├── src/
│   │   ├── components/        # UI components (Shadcn/UI)
│   │   ├── pages/             # Route pages
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utilities + Supabase client
│   │   └── types/             # TypeScript definitions
│   └── tests/                 # Vitest + Playwright tests
│
├── server/                    # Phoenix Elixir API
│   ├── lib/server/            # Business logic
│   ├── lib/server_web/        # Web layer (routes, controllers)
│   └── test/                  # ExUnit tests
│
├── python-etl-service/        # FastAPI ETL service
│   ├── app/
│   │   ├── services/          # ETL scrapers (house, senate, quiver)
│   │   ├── routes/            # API endpoints
│   │   └── lib/               # Shared utilities
│   └── tests/                 # pytest tests
│
├── supabase/
│   ├── migrations/            # Database migrations
│   ├── functions/             # Edge Functions (Deno)
│   └── sql/                   # SQL utilities
│
├── .mcli/workflows/           # mcli automation commands
├── .github/workflows/         # CI/CD pipelines
├── docs/                      # Documentation
│
├── CLAUDE.md                  # This file (in .claude/)
├── CLAWDBOT_INSTRUCTIONS.md   # Autonomous agent instructions
├── claude-progress.txt        # Agent progress tracker
└── FEATURES.md                # Feature requirements
```

---

## Data Sources

### Senate Trades
- URL: https://efdsearch.senate.gov
- Format: HTML tables
- Scraper: `python-etl-service/app/services/senate/`

### House Trades
- URL: https://disclosures-clerk.house.gov/
- Format: PDF documents (requires OCR parsing)
- Scraper: `python-etl-service/app/services/house/`

### Stock Data
- APIs: Alpaca, Yahoo Finance, QuiverQuant
- Data: Prices, tickers, company info, trading signals

---

## Environment Variables

### Client (.env)
```bash
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_URL=
```

### Server (.env)
```bash
DATABASE_URL=
SECRET_KEY_BASE=
PHX_HOST=
```

### ETL Service (.env)
```bash
SUPABASE_URL=
SUPABASE_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
QUIVER_API_KEY=
```

---

## Testing Requirements

- All new features need unit tests
- Bug fixes need regression tests
- UI changes need Playwright E2E tests
- Python ETL needs pytest coverage
- Elixir backend needs ExUnit tests

### Run All Tests
```bash
make test
```

---

## Deployment

### Deploy All Services
```bash
make deploy
# or
mcli run services deploy-all
```

### Deploy Individual Services
```bash
mcli run client deploy    # Frontend to Fly.io
mcli run server deploy    # Phoenix to Fly.io
```

### Deploy Edge Functions
```bash
make deploy-functions
```

---

## CI/CD Requirements

### CRITICAL: CI Must Pass Before Work is Complete
**NEVER declare work complete until CI passes on GitHub.** This is a hard requirement.

### CI/CD Workflow
1. **Before starting work**: Check current CI status with `gh run list --limit 3`
2. **After pushing changes**: Monitor CI with `gh run watch` or `gh run list`
3. **If CI fails**: Fix immediately, push fix, wait for green CI
4. **Only after CI passes**: Declare the task complete

### CI Commands
```bash
gh run list --limit 5              # Check recent CI runs
gh run view <run-id> --log-failed  # View failure logs
gh run watch <run-id>              # Watch run in real-time
```

---

## Code Conventions

### Git Workflow
- Branch from `main` for features: `feature/description`
- Branch from `main` for fixes: `fix/description`
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`

### Code Style
- **TypeScript:** ESLint + Prettier
- **Python:** Black + Ruff (line-length 100)
- **Elixir:** mix format

---

## ClawdBot Integration

This repo is configured for autonomous development with ClawdBot:

1. **CLAWDBOT_INSTRUCTIONS.md** - Full operating manual for the agent
2. **claude-progress.txt** - Persistent memory across sessions
3. **FEATURES.md** - Feature requirements and priorities
4. **.github/workflows/clawdbot.yml** - Automated agent runs

### Agent Workflow
1. Read `claude-progress.txt` first
2. Check GitHub issues
3. Follow TDD protocol
4. Update progress after each session
5. Never commit without tests passing

---

## Monitoring

- **Uptime:** Fly.io health checks
- **Logs:** `flyctl logs -a <app-name>`
- **Database:** Supabase dashboard
- **CI/CD:** GitHub Actions

---

## Contacts

- **Owner:** Luis (gwicho38)
- **Repository:** https://github.com/gwicho38/politician-trading-tracker

---

*Last updated: January 2026*
