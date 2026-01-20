# Politician Trading Tracker - Code Audit Report

**Audit Date:** January 2026
**Auditor:** Automated Code Audit System
**Repository:** politician-trading-tracker
**Commit:** 43be0ee (main branch)

---

## Executive Summary

The Politician Trading Tracker is a **sophisticated, production-grade full-stack application** that tracks political figure financial disclosures and generates ML-powered trading signals. The codebase demonstrates solid engineering practices with clear separation of concerns, comprehensive data flows, and modern architecture patterns.

### Overall Assessment

| Category | Rating | Notes |
|----------|--------|-------|
| **Architecture** | ★★★★☆ | Well-structured microservices with clear boundaries |
| **Code Quality** | ★★★★☆ | Good patterns, some areas need improvement |
| **Testing** | ★★★☆☆ | Strong E2E, weak frontend unit coverage |
| **Security** | ★★☆☆☆ | **CRITICAL ISSUES** - hardcoded secrets |
| **Documentation** | ★★★★☆ | Good inline documentation, architecture docs exist |
| **CI/CD** | ★★★☆☆ | Pipeline exists but doesn't block on failures |

### Critical Findings Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| **CRITICAL** | 3 | Hardcoded API keys, exposed secrets in .env files |
| **HIGH** | 6 | CORS *, missing input validation, pickle deserialization |
| **MEDIUM** | 8 | Rate limiting, error handling, logging gaps |
| **LOW** | 10+ | Code duplication, type coverage, minor patterns |

---

## Table of Contents

0. [Feature Entry Points Index](#0-feature-entry-points-index) ← **START HERE FOR CODE NAVIGATION**
   - [Dashboard](#01-dashboard) | [Trading Signals](#02-trading-signals) | [Portfolio](#03-portfolio-management)
   - [Orders](#04-order-execution) | [Signal Generation](#05-signal-generation-ml) | [ETL](#06-data-collection-etl)
   - [Scrapers](#07-web-scrapers) | [Reference Portfolio](#08-reference-portfolio) | [Auth](#09-authentication)
   - [Scheduled Jobs](#010-scheduled-jobs) | [Phoenix Server](#011-phoenix-api-server) | [Cart](#012-shopping-cart)
   - [Signal Playground](#013-signal-playground) | [Data Quality](#014-data-quality-monitoring) | [Error Reports](#015-error-reporting)
   - [Tests](#016-tests-entry-points)
1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Codebase Structure](#3-codebase-structure)
4. [Backend Analysis](#4-backend-analysis)
5. [Frontend Analysis](#5-frontend-analysis)
6. [Database & Supabase](#6-database--supabase)
7. [Testing Assessment](#7-testing-assessment)
8. [Security Audit](#8-security-audit)
9. [Code Quality Issues](#9-code-quality-issues)
10. [Recommendations](#10-recommendations)
11. [Appendix](#11-appendix)

---

## 0. Feature Entry Points Index

This section provides quick navigation to all major features with file locations shown in context.

### Quick Reference Table

| Feature | Primary Entry Point | Type |
|---------|---------------------|------|
| [Dashboard](#01-dashboard) | `client/src/pages/Index.tsx` | Frontend |
| [Trading Signals](#02-trading-signals) | `client/src/pages/TradingSignals.tsx` | Frontend |
| [Portfolio Management](#03-portfolio-management) | `client/src/pages/Portfolio.tsx` | Frontend |
| [Order Execution](#04-order-execution) | `supabase/functions/orders/index.ts` | Edge Function |
| [Signal Generation](#05-signal-generation-ml) | `supabase/functions/trading-signals/index.ts` | Edge Function |
| [Data Collection (ETL)](#06-data-collection-etl) | `python-micro-service/.../workflow.py` | Python |
| [Web Scrapers](#07-web-scrapers) | `python-micro-service/.../scrapers/scrapers.py` | Python |
| [Reference Portfolio](#08-reference-portfolio) | `supabase/functions/reference-portfolio/index.ts` | Edge Function |
| [Authentication](#09-authentication) | `client/src/pages/Auth.tsx` | Frontend |
| [Scheduled Jobs](#010-scheduled-jobs) | `supabase/functions/scheduled-sync/index.ts` | Edge Function |
| [Phoenix API Server](#011-phoenix-api-server) | `server/lib/server_web/router.ex` | Elixir |

---

### 0.1 Dashboard

**Purpose:** Main landing page with market overview, recent trades, and statistics

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   └── Index.tsx              ← ENTRY POINT (route: /)
│       ├── components/
│       │   ├── Dashboard.tsx          ← Main dashboard component
│       │   ├── RecentTrades.tsx       ← Recent trades widget
│       │   ├── LandingTradesTable.tsx ← Trades table
│       │   └── SyncStatus.tsx         ← Data sync indicator
│       └── hooks/
│           └── useSupabaseData.ts     ← Data fetching (useDashboardStats, useChartData)
```

**Key Functions:**
- `Index.tsx` → Default export, renders `<Dashboard />`
- `useSupabaseData.ts:useDashboardStats()` → Fetches `dashboard_stats` table
- `useSupabaseData.ts:useChartData()` → Fetches `chart_data` for visualizations

---

### 0.2 Trading Signals

**Purpose:** Display ML-generated trading signals with filtering and sorting

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   └── TradingSignals.tsx     ← ENTRY POINT (route: /trading-signals)
│       ├── components/
│       │   └── TradingSignals.tsx     ← Signal display component
│       └── hooks/
│           └── useSupabaseData.ts     ← useTradingSignals()
│
├── supabase/
│   └── functions/
│       └── trading-signals/
│           └── index.ts               ← EDGE FUNCTION (signal generation)
│               ├── get-signals        ← POST: Fetch active signals
│               ├── generate-signals   ← POST: User-triggered generation
│               ├── regenerate-signals ← POST: Scheduled regeneration
│               └── preview-signals    ← POST: Preview with custom weights
```

**Key Functions:**
- `TradingSignals.tsx` → Page component with signal grid
- `trading-signals/index.ts:handleGetSignals()` → Returns paginated signals
- `trading-signals/index.ts:generateSignals()` → ML + heuristic signal creation

---

### 0.3 Portfolio Management

**Purpose:** Track positions, P&L, and portfolio metrics

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   └── Portfolio.tsx          ← ENTRY POINT (route: /portfolio)
│       ├── hooks/
│       │   ├── useAlpacaAccount.ts    ← Account data hook
│       │   └── useAlpacaPositions.ts  ← Positions hook
│       └── components/
│           └── trading/
│               └── PositionsTable.tsx ← Positions display
│
├── supabase/
│   └── functions/
│       ├── portfolio/
│       │   └── index.ts               ← EDGE FUNCTION (portfolio ops)
│       └── alpaca-account/
│           └── index.ts               ← EDGE FUNCTION (Alpaca integration)
```

**Key Functions:**
- `Portfolio.tsx` → Main portfolio view
- `useAlpacaAccount.ts:useAlpacaAccount()` → Fetches account from Alpaca API
- `alpaca-account/index.ts` → Proxies requests to Alpaca Trading API

---

### 0.4 Order Execution

**Purpose:** Place and manage trading orders via Alpaca

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   ├── Orders.tsx             ← ENTRY POINT (route: /orders)
│       │   └── TradingOperations.tsx  ← ENTRY POINT (route: /trading-operations)
│       └── hooks/
│           └── useOrders.ts           ← Order management hook
│
├── supabase/
│   └── functions/
│       └── orders/
│           └── index.ts               ← EDGE FUNCTION (order execution)
│               ├── place-order        ← POST: Submit order to Alpaca
│               ├── get-orders         ← GET: Fetch order history
│               └── cancel-order       ← POST: Cancel pending order
```

**Key Functions:**
- `Orders.tsx` → Order history display
- `TradingOperations.tsx` → Active trading interface
- `orders/index.ts:placeOrder()` → Submits order to Alpaca API
- `useOrders.ts:usePlaceOrder()` → Mutation hook for order placement

---

### 0.5 Signal Generation (ML)

**Purpose:** Generate trading signals from politician disclosure data using ML

```
politician-trading-tracker/
├── supabase/
│   └── functions/
│       └── trading-signals/
│           └── index.ts               ← EDGE FUNCTION ENTRY POINT
│               ├── generateHeuristicSignals()  ← Rule-based signals
│               ├── fetchMLPredictions()        ← Calls ETL ML API
│               └── blendSignals()              ← 60% heuristic + 40% ML
│
├── python-micro-service/
│   └── politician_trading/
│       └── signals/
│           ├── signal_generator.py    ← ML MODEL ENTRY POINT
│           │   ├── SignalGenerator class
│           │   ├── generate_signals()
│           │   └── train_model()
│           ├── features.py            ← Feature engineering (12 features)
│           └── cli.py                 ← CLI: politician-trading-signals
│
├── python-etl-service/
│   └── app/
│       ├── main.py                    ← FastAPI entry
│       └── routes/
│           └── ml.py                  ← /ml/predict, /ml/batch-predict
```

**Key Functions:**
- `signal_generator.py:SignalGenerator.generate_signals()` → Main ML pipeline
- `features.py:compute_features()` → 12-feature engineering
- `trading-signals/index.ts:blendSignals()` → Combines ML + heuristic

---

### 0.6 Data Collection (ETL)

**Purpose:** Orchestrate data collection from government sources

```
politician-trading-tracker/
├── python-micro-service/
│   └── politician_trading/
│       ├── workflow.py                ← MAIN ORCHESTRATOR ENTRY POINT
│       │   ├── PoliticianTradingWorkflow class
│       │   ├── run_full_collection()
│       │   ├── _collect_us_congress_data()
│       │   ├── _collect_eu_parliament_data()
│       │   └── _collect_uk_parliament_data()
│       ├── config.py                  ← Configuration management
│       ├── connectivity.py            ← Database connections
│       ├── data_sources.py            ← Source definitions
│       └── exceptions.py              ← Custom exception hierarchy
│
├── python-etl-service/
│   └── app/
│       ├── main.py                    ← FastAPI ENTRY POINT
│       ├── routes/
│       │   └── etl.py                 ← /etl/trigger, /etl/status
│       └── services/
│           ├── house_etl.py           ← House disclosure ETL
│           └── senate_etl.py          ← Senate disclosure ETL
```

**CLI Entry Points (from pyproject.toml):**
```bash
politician-trading          # → workflow.py:main()
politician-trading-seed     # → scripts/seed_database.py:main()
politician-trading-signals  # → signals/cli.py:main()
politician-trading-trade    # → trading/cli.py:main()
```

**Key Functions:**
- `workflow.py:PoliticianTradingWorkflow.run_full_collection()` → Main entry
- `house_etl.py:run_house_etl()` → House disclosure scraping
- `senate_etl.py:run_senate_etl()` → Senate disclosure scraping

---

### 0.7 Web Scrapers

**Purpose:** Scrape financial disclosures from various government websites

```
politician-trading-tracker/
├── python-micro-service/
│   └── politician_trading/
│       └── scrapers/
│           ├── scrapers.py                   ← MAIN SCRAPER ENTRY (2,002 LOC)
│           │   ├── BaseScraper class
│           │   ├── CongressScraper
│           │   └── run_all_scrapers()
│           ├── house_disclosure_scraper.py   ← US House (1,327 LOC)
│           ├── scrapers_california.py        ← California state
│           ├── scrapers_us_states.py         ← Other US states
│           ├── scrapers_uk.py                ← UK Parliament
│           ├── scrapers_eu.py                ← EU Parliament
│           ├── scrapers_third_party.py       ← QuiverQuant, etc.
│           ├── scrapers_corporate_registry.py ← UK Companies House
│           └── data_sources.py               ← Source URLs, rate limits
```

**Key Classes:**
- `scrapers.py:BaseScraper` → Abstract scraper with circuit breaker
- `house_disclosure_scraper.py:HouseDisclosureScraper` → US House ETF
- `data_sources.py:SOURCES` → Dict of all data source configurations

---

### 0.8 Reference Portfolio

**Purpose:** Automated paper trading based on high-confidence signals

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   └── ReferencePortfolio.tsx ← ENTRY POINT (route: /reference-portfolio)
│       └── hooks/
│           └── useReferencePortfolio.ts ← Portfolio state hook
│
├── supabase/
│   ├── functions/
│   │   └── reference-portfolio/
│   │       └── index.ts               ← EDGE FUNCTION ENTRY POINT
│   │           ├── processSignalQueue()  ← Process pending signals
│   │           ├── executeSignal()       ← Place order for signal
│   │           └── syncPortfolioState()  ← Update portfolio metrics
│   └── migrations/
│       └── 20260109_reference_portfolio.sql ← Schema definition
```

**Database Tables:**
- `reference_portfolio_config` → Risk parameters (singleton)
- `reference_portfolio_state` → Real-time metrics
- `reference_portfolio_positions` → Open/closed positions
- `reference_portfolio_signal_queue` → Pending signal queue

---

### 0.9 Authentication

**Purpose:** User authentication via Supabase Auth

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   └── Auth.tsx               ← ENTRY POINT (route: /auth)
│       ├── hooks/
│       │   ├── useAuth.ts             ← Auth state hook
│       │   └── useWalletAuth.ts       ← Web3 wallet auth
│       ├── contexts/
│       │   └── AlertContext.tsx       ← Connection health tracking
│       └── components/
│           └── WalletProvider.tsx     ← RainbowKit setup
│
├── supabase/
│   └── (Auth handled by Supabase platform)
```

**Key Functions:**
- `Auth.tsx` → Login/signup form
- `useAuth.ts:useAuth()` → Returns `{ user, session, signIn, signOut }`
- `useWalletAuth.ts:useWalletAuth()` → Web3 wallet connection

---

### 0.10 Scheduled Jobs

**Purpose:** Periodic data sync, signal regeneration, stats updates

```
politician-trading-tracker/
├── supabase/
│   ├── functions/
│   │   ├── scheduled-sync/
│   │   │   └── index.ts               ← ORCHESTRATOR ENTRY POINT
│   │   │       ├── mode=daily         ← Charts + stats + parties
│   │   │       ├── mode=full          ← Include data collection
│   │   │       └── mode=quick         ← Stats only
│   │   └── sync-data/
│   │       └── index.ts               ← SYNC OPERATIONS ENTRY POINT
│   │           ├── sync-all           ← Sync politicians
│   │           ├── sync-trades        ← Sync disclosures
│   │           ├── update-stats       ← Dashboard statistics
│   │           ├── update-chart-data  ← Chart aggregations
│   │           └── update-politician-parties ← Ollama lookup
│   └── migrations/
│       └── 20251222_enable_pg_cron_jobs.sql ← Cron schedules
```

**Cron Schedules (pg_cron):**
| Schedule | Function | Purpose |
|----------|----------|---------|
| `0 */4 * * *` | scheduled-sync | Data sync every 4h |
| `30 */4 * * *` | trading-signals/regenerate | Signal gen every 4h |
| `0 * * * *` | sync-data/update-stats | Hourly stats |

---

### 0.11 Phoenix API Server

**Purpose:** Elixir/Phoenix backend for health checks and job management

```
politician-trading-tracker/
├── server/
│   ├── lib/
│   │   ├── server_web/
│   │   │   ├── router.ex              ← ROUTING ENTRY POINT
│   │   │   │   └── Routes: /api/health, /api/jobs, /api/ml
│   │   │   ├── endpoint.ex            ← HTTP endpoint config
│   │   │   └── controllers/
│   │   │       ├── health_controller.ex ← GET /api/health
│   │   │       ├── job_controller.ex    ← Job management
│   │   │       └── ml_controller.ex     ← ML model operations
│   │   └── server/
│   │       ├── application.ex         ← OTP application
│   │       ├── scheduler.ex           ← Quantum cron jobs
│   │       └── supabase_client.ex     ← Supabase connection
│   ├── config/
│   │   └── runtime.exs                ← Runtime config
│   └── fly.toml                       ← Fly.io deployment
```

**Key Routes:**
- `GET /api/health` → Health check endpoint
- `GET /api/jobs` → List scheduled jobs
- `POST /api/ml/train` → Trigger ML training

---

### 0.12 Shopping Cart

**Purpose:** Add signals to cart for batch trading

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── contexts/
│       │   └── CartContext.tsx        ← CART STATE ENTRY POINT
│       │       ├── CartProvider
│       │       ├── useCart()
│       │       └── addToCart(), removeFromCart()
│       └── components/
│           └── cart/
│               └── CartSheet.tsx      ← Cart UI component
│
├── supabase/
│   └── migrations/
│       └── 20260108_user_carts.sql    ← Cart table schema
```

**Key Functions:**
- `CartContext.tsx:CartProvider` → Wraps app with cart state
- `CartContext.tsx:useCart()` → Returns `{ items, addToCart, removeFromCart, total }`

---

### 0.13 Signal Playground

**Purpose:** Test signal generation with custom weight configurations

```
politician-trading-tracker/
├── client/
│   └── src/
│       ├── pages/
│       │   └── SignalPlayground.tsx   ← ENTRY POINT (route: /signal-playground)
│       ├── hooks/
│       │   ├── useSignalPlayground.ts ← Playground state
│       │   └── useSignalPresets.ts    ← Weight presets
│       └── components/
│           └── signal-playground/
│               ├── WeightSliders.tsx  ← Weight adjustment UI
│               └── PreviewResults.tsx ← Signal preview display
```

**Key Functions:**
- `SignalPlayground.tsx` → Interactive signal testing
- `useSignalPlayground.ts:usePreviewSignals()` → Calls preview-signals endpoint

---

### 0.14 Data Quality Monitoring

**Purpose:** Monitor data freshness and quality metrics

```
politician-trading-tracker/
├── client/
│   └── src/
│       └── pages/
│           └── DataQuality.tsx        ← ENTRY POINT (route: /data-quality)
│
├── supabase/
│   └── migrations/
│       └── 20260105_data_quality_schema.sql ← Quality tables
│           ├── data_quality_scores
│           ├── data_freshness_metrics
│           └── source_health_status
```

---

### 0.15 Error Reporting

**Purpose:** User error reports with auto-correction via LLM

```
politician-trading-tracker/
├── client/
│   └── src/
│       └── components/
│           └── ReportErrorModal.tsx   ← Error report UI
│
├── supabase/
│   └── functions/
│       └── process-error-reports/
│           └── index.ts               ← EDGE FUNCTION ENTRY POINT
│               └── processErrorReport() → Ollama auto-correction
│
├── python-etl-service/
│   └── app/
│       └── services/
│           └── error_report_processor.py ← Batch processing
```

---

### 0.16 Tests Entry Points

```
politician-trading-tracker/
├── tests/                              ← PYTHON TESTS
│   ├── unit/
│   │   ├── test_signal_generator.py   ← Signal tests (897 LOC)
│   │   ├── test_alpaca_client.py      ← Trading client tests
│   │   └── test_ticker_filter.py      ← Filter tests
│   ├── integration/
│   │   ├── test_e2e_trading_flow.py   ← Full trading flow (628 LOC)
│   │   └── test_scraper_integration.py ← Scraper tests
│   └── fixtures/
│       └── test_data.py               ← TestDataFactory
│
├── client/
│   ├── src/
│   │   └── contexts/
│   │       ├── AlertContext.test.tsx  ← Context tests (409 LOC)
│   │       └── CartContext.test.tsx   ← Cart tests (473 LOC)
│   └── e2e/                           ← PLAYWRIGHT E2E TESTS
│       ├── auth.spec.ts               ← Auth flow tests
│       ├── dashboard.spec.ts          ← Dashboard tests
│       ├── portfolio.spec.ts          ← Portfolio tests
│       └── trading-operations.spec.ts ← Trading tests
```

---

## 1. Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                                 │
│  govmarket.trade                                                         │
│  - Trading signals display                                               │
│  - Portfolio management                                                  │
│  - Shopping cart for signals                                             │
└────────────────────────────────────────────────────────────────────────┘
                              │ HTTPS + JWT
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SUPABASE (PostgreSQL + Edge Functions)                │
│  uljsqvwkomdrlnofmlad.supabase.co                                       │
│  - Database (RLS enabled)                                                │
│  - Edge Functions (Deno)                                                 │
│  - Real-time subscriptions                                               │
│  - Storage buckets                                                       │
└────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ ETL Service  │   │ Phoenix Server   │   │ External APIs    │
│ (Python)     │   │ (Elixir)         │   │                  │
│ Fly.io       │   │ Fly.io           │   │ - Alpaca Trading │
│              │   │                  │   │ - Yahoo Finance  │
│ - Scrapers   │   │ - Health checks  │   │ - Ollama LLM     │
│ - ML Models  │   │ - Job scheduling │   │ - Congress API   │
│ - Signals    │   │ - Data quality   │   │ - UK Parliament  │
└──────────────┘   └──────────────────┘   └──────────────────┘
```

### Data Flow

```
Government Sources (Congress, Parliament, SEC)
        ↓
Python Scrapers (Rate-limited, Circuit breaker)
        ↓
Data Processing & Normalization (ETL Pipeline)
        ↓
Supabase PostgreSQL (RLS, Audit trails)
        ↓
ML Signal Generation (XGBoost/LightGBM)
        ↓
React Frontend (React Query → Supabase Client)
        ↓
User Interface (Dashboard, Trading, Portfolio)
        ↓
Alpaca Trading API (Paper/Live trading)
```

### Key Architectural Patterns

| Pattern | Implementation | Location |
|---------|----------------|----------|
| Microservices | Python ETL, Phoenix API, Supabase Functions | `python-etl-service/`, `server/`, `supabase/functions/` |
| Circuit Breaker | Per-source failure tracking | `scrapers/data_sources.py` |
| Rate Limiting | Adaptive backoff (1s-60s) | `scrapers/`, edge functions |
| Event Sourcing | Immutable audit trail | `signal_audit_trail` table |
| CQRS | Read/write separation via edge functions | `supabase/functions/` |

---

## 2. Technology Stack

### Frontend (Client)
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3.1 | UI framework |
| TypeScript | 5.8.3 | Type safety |
| Vite | 5.4.19 | Build tool |
| TanStack React Query | 5.83.0 | Server state management |
| Tailwind CSS | 3.4.17 | Styling |
| Radix UI | Latest | Accessible components |
| Recharts | 2.15.4 | Data visualization |
| Wagmi + Viem | 2.9.0 | Web3 wallet integration |
| Playwright | 1.49.0 | E2E testing |

### Backend (Python)
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.9-3.12 | Runtime |
| FastAPI | Latest | REST API framework |
| Supabase | 2.18.1+ | Database client |
| XGBoost | 2.0.0+ | ML model training |
| LightGBM | 4.0.0+ | Alternative ML model |
| Playwright | Latest | Browser automation for scraping |
| alpaca-py | 0.29.0+ | Trading API client |
| yfinance | 0.2.40+ | Market data |

### Backend (Elixir)
| Technology | Version | Purpose |
|------------|---------|---------|
| Phoenix | 1.7 | API framework |
| Ecto | Latest | Database ORM |
| Quantum | Latest | Job scheduling |
| Bandit | Latest | HTTP server |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Supabase | Database, Auth, Edge Functions, Storage |
| Fly.io | ETL service, Phoenix server hosting |
| pg_cron | Scheduled jobs |
| Docker | Containerization |

---

## 3. Codebase Structure

### Directory Layout

```
politician-trading-tracker/
├── client/                          # React frontend (33,646 LOC)
│   ├── src/
│   │   ├── pages/                  # 15+ route pages
│   │   ├── components/             # 100+ React components
│   │   │   └── ui/                 # 49 shadcn/ui components
│   │   ├── contexts/               # Cart, Alert contexts
│   │   ├── hooks/                  # 16+ custom hooks
│   │   └── integrations/           # Supabase client
│   └── e2e/                        # 21 Playwright test files
│
├── python-micro-service/           # Python data/ML service (33,282 LOC)
│   └── politician_trading/
│       ├── scrapers/               # Data collectors
│       ├── pipeline/               # ETL orchestration
│       ├── signals/                # Trading signals
│       ├── ml/                     # ML models
│       └── trading/                # Trading logic
│
├── python-etl-service/             # ETL microservice (5,247 LOC)
│   ├── main.py                     # FastAPI entry point
│   ├── house_etl.py               # House disclosure ETL
│   └── senate_etl.py              # Senate disclosure ETL
│
├── server/                         # Elixir/Phoenix API
│   └── lib/
│       ├── server_web/controllers/ # HTTP controllers
│       └── server/                 # Application logic
│
├── supabase/
│   ├── functions/                  # 10+ Edge functions
│   └── migrations/                 # 20+ database migrations
│
├── tests/                          # Python test suite (40 files)
│   ├── unit/                       # 14 unit test files
│   ├── integration/                # 18 integration tests
│   └── fixtures/                   # Test data factory
│
├── docs/                           # Documentation
│   ├── architecture/               # Architecture decisions
│   └── releases/                   # Release notes
│
└── scripts/                        # 30+ utility scripts
```

### Code Statistics

| Component | Lines of Code | Files |
|-----------|---------------|-------|
| Frontend (React) | ~33,646 | 150+ |
| Python Backend | ~38,529 | 100+ |
| Supabase Functions | ~8,000 | 25+ |
| Elixir Server | ~3,000 | 30+ |
| Tests | ~15,000 | 67 |
| **Total** | **~98,000+** | **370+** |

---

## 4. Backend Analysis

### 4.1 Python ETL Architecture

**Strengths:**
- Well-defined exception hierarchy with context
- Circuit breaker pattern for external API resilience
- Adaptive rate limiting with exponential backoff
- Clean separation between scrapers, transformers, and pipeline

**Issues Identified:**

| Issue | Severity | Location | Description |
|-------|----------|----------|-------------|
| Broad exception handlers | MEDIUM | `house_etl.py`, `senate_etl.py` | 10+ instances of `except Exception as e:` |
| Print statements | LOW | `error_report_processor.py` | 9+ `print()` calls instead of logging |
| TODO comments | LOW | `sources/us_house.py:50,74` | Incomplete implementations |
| Duplicate data sources | MEDIUM | `scrapers/data_sources.py` | Definition exists in 2 locations |
| Hardcoded thresholds | LOW | Multiple files | Magic values for delays, confidence |

### 4.2 ML Signal Generation

**Feature Engineering (12 Features):**
1. `politician_count` - Unique politicians trading
2. `buy_sell_ratio` - Buy/Sell transaction ratio
3. `recent_activity_30d` - Recent trading activity
4. `bipartisan` - Cross-party trading indicator
5. `net_volume` - Buy minus sell volume
6. `volume_magnitude` - Log of transaction volume
7. `party_alignment` - Majority party agreement
8. `committee_relevance` - Committee-sector alignment
9. `market_momentum` - 20-day price momentum
10. `sector_performance` - Sector ETF performance
11. `sentiment_score` - LLM news sentiment
12. `disclosure_delay` - Trade to disclosure delay

**Model Training:**
- XGBoost (primary) and LightGBM (alternative)
- 7-day forward returns for label generation
- Optuna for hyperparameter tuning
- Model versioning and artifact storage in Supabase

### 4.3 API Endpoints (FastAPI)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health check |
| `/etl/trigger` | POST | Trigger House/Senate ETL |
| `/etl/status/{job_id}` | GET | Check ETL job status |
| `/ml/predict` | POST | Single ML prediction |
| `/ml/batch-predict` | POST | Batch ML predictions |
| `/ml/train` | POST | Train new model |
| `/quality/validate-tickers` | POST | Validate ticker data |
| `/error-reports/process` | POST | Process error reports |

---

## 5. Frontend Analysis

### 5.1 Component Architecture

**Strengths:**
- Modern React patterns (hooks, context, React Query)
- Comprehensive error boundaries (2-level: root + route)
- Good separation of concerns
- Consistent naming conventions
- Well-structured state management

**State Management:**
```
Context API (shared state)
├── CartContext (localStorage + Supabase)
└── AlertContext (centralized alerts)

React Query (server state)
├── 68 instances of useQuery/useMutation
├── 5-minute stale time defaults
└── Circuit breaker pattern

Local State (component-specific)
└── useState for UI state
```

### 5.2 TypeScript Configuration

| Setting | Value | Assessment |
|---------|-------|------------|
| `strict` | false | ⚠️ Should be enabled |
| `skipLibCheck` | true | OK for build speed |
| `noUnusedLocals` | false | ⚠️ Could catch issues |

**Recommendation:** Enable strict mode incrementally for better type safety.

### 5.3 Issues Identified

| Issue | Severity | Description |
|-------|----------|-------------|
| Limited unit tests | HIGH | Only 7 test files for 100+ components |
| TypeScript strict mode off | MEDIUM | Allows type errors |
| Hardcoded Supabase URL | MEDIUM | `useWalletAuth.ts:6` |
| Some `any` types | LOW | Data transformations |

---

## 6. Database & Supabase

### 6.1 Schema Overview

**Core Tables (40+):**

| Category | Tables |
|----------|--------|
| Trading Data | `trading_signals`, `trading_disclosures`, `politicians` |
| ML/Signals | `ml_models`, `ml_training_data`, `feature_definitions` |
| Audit Trail | `signal_audit_trail`, `signal_lifecycle`, `order_state_log` |
| Portfolio | `reference_portfolio_*` (6 tables) |
| Operations | `scheduled_jobs`, `job_executions`, `sync_logs` |

### 6.2 Row Level Security (RLS)

**Implemented Policies:**
- ✅ Public read for signals and portfolio
- ✅ User-isolated carts and API keys
- ✅ Service role for admin operations
- ✅ Immutable audit trail (triggers prevent UPDATE/DELETE)

### 6.3 Edge Functions (10+)

| Function | Purpose | Schedule |
|----------|---------|----------|
| `trading-signals` | Generate ML-powered signals | Every 4 hours |
| `scheduled-sync` | Data synchronization | Every 4 hours |
| `sync-data` | Update stats, charts, parties | Hourly |
| `reference-portfolio` | Automated paper trading | Signal-triggered |
| `orders` | Order execution | On-demand |
| `alpaca-account` | Alpaca integration | On-demand |

### 6.4 Scheduled Jobs (pg_cron)

```sql
-- Signal generation: every 4 hours at :30
30 */4 * * * → trading-signals/regenerate-signals

-- Data sync: every 4 hours
0 */4 * * * → scheduled-sync?mode=daily

-- Stats update: hourly
0 * * * * → sync-data/update-stats
```

---

## 7. Testing Assessment

### 7.1 Test Coverage Summary

| Category | Files | Coverage | Quality |
|----------|-------|----------|---------|
| Unit Tests (Backend) | 14 | ~70% | ★★★★☆ |
| Unit Tests (Frontend) | 7 | <20% | ★★☆☆☆ |
| Integration Tests | 18 | ~60% | ★★★★☆ |
| E2E Tests (Playwright) | 21 | ~85% | ★★★★☆ |
| E2E Tests (Backend Flow) | 2 | 100% | ★★★★★ |

### 7.2 Test Frameworks

| Framework | Purpose | Location |
|-----------|---------|----------|
| pytest | Python tests | `tests/` |
| Vitest | React unit tests | `client/src/**/*.test.tsx` |
| Playwright | E2E browser tests | `client/e2e/` |
| pytest-cov | Coverage reporting | CI pipeline |

### 7.3 Coverage Gaps

**Critical Gaps:**

| Area | Current Coverage | Target |
|------|------------------|--------|
| React Components | <20% | 60%+ |
| Scraper Modules | <30% (skipped) | 70% |
| ML Models | <10% | 50% |
| Async/Concurrency | <20% | 50% |

**Missing Test Types:**
- ❌ Security testing (auth bypass, injection)
- ❌ Accessibility testing (a11y)
- ❌ Load/performance testing
- ❌ Visual regression testing
- ❌ API contract testing

### 7.4 CI/CD Pipeline Issues

```yaml
# Current issue in .github/workflows/ci.yml
continue-on-error: true  # ⚠️ Allows failures to pass
```

**Recommendations:**
1. Set `continue-on-error: false`
2. Add frontend E2E tests to pipeline
3. Add coverage enforcement (block if below threshold)

---

## 8. Security Audit

### 8.1 CRITICAL Issues

#### Issue #1: Hardcoded API Keys
**Severity:** CRITICAL
**Location:** `supabase/functions/sync-data/index.ts:825`

```typescript
// INSECURE - hardcoded API key
const OLLAMA_API_KEY = '2df4dc81117fa1845a8ee21a6a315676...'
```

**Impact:** Anyone with repo access can use this key.
**Fix:** Use `Deno.env.get('OLLAMA_API_KEY')`

---

#### Issue #2: Exposed Secrets in .env Files
**Severity:** CRITICAL
**Locations:** `.env`, `.env.politician-trading`, `server/.env`, `client/.env*`

**Exposed Credentials:**
- `SUPABASE_SERVICE_KEY` - Full admin access
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` - Trading API
- `STRIPE_PUBLISHABLE_KEY` - Payment processing
- `DATABASE_URL` - Direct database access
- `CONGRESS_API_KEY`, `UK_COMPANIES_HOUSE_API_KEY`
- Backup files: `.env.backup.*` (3 files)

**Impact:** Complete system compromise possible.
**Fix:** Rotate ALL credentials immediately, delete backups.

---

#### Issue #3: Overly Permissive CORS
**Severity:** CRITICAL
**Location:** All Supabase edge functions

```typescript
// INSECURE
'Access-Control-Allow-Origin': '*'
```

**Impact:** CSRF attacks, credential theft from any origin.
**Fix:** Restrict to specific trusted origins.

---

### 8.2 HIGH Severity Issues

| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| Timing-unsafe key comparison | `orders/index.ts` | Timing attacks | Use `crypto.timingSafeEqual()` |
| Missing input validation | Edge functions | Injection, crashes | Add Zod schema validation |
| Pickle deserialization | `signal_generator.py` | RCE if data controlled | Use JSON, validate sources |
| Service role key exposure | Edge function auth | Admin access | Use for internal ops only |

### 8.3 MEDIUM Severity Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| No rate limiting on APIs | DoS, brute force | Implement per-user/IP limits |
| Missing security headers | XSS, clickjacking | Add HSTS, CSP, X-Frame-Options |
| JWT in localStorage | Token theft via XSS | Use HttpOnly cookies |
| Insufficient audit logging | Forensics gaps | Log all auth failures |

### 8.4 Recommended Actions

**Immediate (This Week):**
1. Rotate ALL exposed API keys and credentials
2. Remove hardcoded OLLAMA_API_KEY
3. Delete `.env.backup.*` files
4. Restrict CORS to specific origins
5. Add input validation to all API endpoints

**Short Term (This Month):**
1. Implement rate limiting
2. Add security headers
3. Use timing-safe comparison for auth
4. Add comprehensive security logging
5. Run dependency security audit (`safety check`, `npm audit`)

---

## 9. Code Quality Issues

### 9.1 Backend Issues

| Issue | Severity | Count | Files |
|-------|----------|-------|-------|
| Broad exception handlers | MEDIUM | 10+ | ETL modules |
| Print instead of logging | LOW | 9+ | `error_report_processor.py` |
| Incomplete TODOs | LOW | 2 | `sources/us_house.py` |
| Duplicate definitions | MEDIUM | 2 | `data_sources.py` |
| Hardcoded magic values | LOW | 10+ | Multiple |

### 9.2 Frontend Issues

| Issue | Severity | Files Affected |
|-------|----------|----------------|
| TypeScript strict mode off | MEDIUM | All |
| Limited type coverage | MEDIUM | Data transformations |
| Some `any` types | LOW | API responses |
| Incomplete error handling | MEDIUM | Async operations |

### 9.3 Architecture Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| Dependency duplication | MEDIUM | `requirements.txt` vs `pyproject.toml` |
| Config inconsistency | LOW | Multiple `.env` patterns |
| Commented-out features | LOW | Admin panel disabled |

---

## 10. Recommendations

### 10.1 Priority 1 - Critical (Immediate)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | Rotate all exposed credentials | 2h | CRITICAL |
| 2 | Remove hardcoded API keys | 1h | CRITICAL |
| 3 | Fix CORS configuration | 1h | CRITICAL |
| 4 | Delete .env backup files | 0.5h | CRITICAL |
| 5 | Add input validation | 4h | HIGH |

### 10.2 Priority 2 - High (This Sprint)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 6 | Add frontend unit tests | 16h | HIGH |
| 7 | Enable TypeScript strict mode | 8h | MEDIUM |
| 8 | Fix CI to block on failures | 2h | HIGH |
| 9 | Implement rate limiting | 8h | HIGH |
| 10 | Add security headers | 4h | MEDIUM |

### 10.3 Priority 3 - Medium (This Month)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 11 | Enable skipped scraper tests | 8h | MEDIUM |
| 12 | Add ML model tests | 16h | MEDIUM |
| 13 | Implement secrets management | 8h | HIGH |
| 14 | Add comprehensive logging | 8h | MEDIUM |
| 15 | Refactor exception handlers | 4h | LOW |

### 10.4 Priority 4 - Low (Backlog)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 16 | Add accessibility testing | 16h | LOW |
| 17 | Add visual regression tests | 8h | LOW |
| 18 | Add load testing | 16h | MEDIUM |
| 19 | Consolidate config management | 8h | LOW |
| 20 | Document component APIs | 16h | LOW |

---

## 11. Appendix

### 11.1 Key Files Reference

| File | Purpose |
|------|---------|
| `client/src/App.tsx` | React app entry point |
| `client/src/hooks/useSupabaseData.ts` | Main data fetching hooks |
| `python-micro-service/politician_trading/workflow.py` | ETL orchestrator |
| `python-micro-service/politician_trading/signals/signal_generator.py` | ML signal generation |
| `supabase/functions/trading-signals/index.ts` | Signal edge function |
| `.github/workflows/ci.yml` | CI/CD pipeline |

### 11.2 Database Tables (Key Tables)

| Table | Purpose | RLS |
|-------|---------|-----|
| `trading_signals` | ML-generated signals | Public read |
| `trading_disclosures` | Source disclosure data | Public read |
| `politicians` | Politician profiles | Public read |
| `user_carts` | Shopping cart | User-isolated |
| `user_api_keys` | API credentials | User-isolated |
| `signal_audit_trail` | Immutable audit | Public read, no modify |
| `reference_portfolio_*` | Paper trading | Public read |

### 11.3 Deployment URLs

| Service | URL |
|---------|-----|
| Frontend | https://govmarket.trade |
| Supabase | https://uljsqvwkomdrlnofmlad.supabase.co |
| ETL Service | https://politician-trading-etl.fly.dev |
| Phoenix Server | https://politician-trading-server.fly.dev |

### 11.4 Audit Methodology

1. **Static Analysis:** Automated code scanning with grep patterns
2. **Architecture Review:** Directory structure and data flow analysis
3. **Security Scan:** Secret detection, vulnerability patterns
4. **Test Coverage:** Test file inventory and gap analysis
5. **Dependency Review:** Package version and vulnerability check

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2026 | Initial comprehensive audit |

---

*This audit document should be reviewed quarterly and updated with each major release.*
