# External Data Sources and Metrics

This document catalogs every metric and data item populated from external data sources in the Politician Trading Tracker application.

---

## Table of Contents

1. [Complete Data Flow Reference](#1-complete-data-flow-reference)
   - [Dashboard Metrics](#11-dashboard-metrics)
   - [Politicians Data](#12-politicians-data)
   - [Trading Disclosures](#13-trading-disclosures)
   - [Charts & Aggregations](#14-charts--aggregations)
   - [Trading & Portfolio](#15-trading--portfolio)
   - [Detail Views](#16-detail-views)
2. [Government Disclosure Sources](#2-government-disclosure-sources)
   - [US House Financial Disclosures](#21-us-house-financial-disclosures)
   - [US Senate Financial Disclosures](#22-us-senate-financial-disclosures)
   - [California NetFile Disclosures](#23-california-netfile-disclosures)
   - [EU Parliament Declarations](#24-eu-parliament-declarations)
3. [Third-Party Data Aggregators](#3-third-party-data-aggregators)
   - [QuiverQuant Congress Trading](#31-quiverquant-congress-trading)
4. [Reference Data APIs](#4-reference-data-apis)
   - [Congress.gov API](#41-congressgov-api)
5. [Trading & Market Data APIs](#5-trading--market-data-apis)
   - [Alpaca Trading API](#51-alpaca-trading-api)
   - [Yahoo Finance API](#52-yahoo-finance-api)
6. [AI/ML Services](#6-aiml-services)
   - [Ollama LLM Service](#61-ollama-llm-service)
   - [Python ETL ML Service](#62-python-etl-ml-service)
7. [Database Schema Reference](#7-database-schema-reference)
8. [Data Flow Diagram](#8-data-flow-diagram)
9. [Environment Variables](#9-environment-variables)

---

## 1. Complete Data Flow Reference

This section maps every metric from external source → processing function → invoker → database → React hook → UI component.

### 1.1 Dashboard Metrics

| ✓ | Metric | External Source | ETL Function | Invoker | DB Table.Field | React Hook | UI Component |
|---|--------|-----------------|--------------|---------|----------------|------------|--------------|
| [ ] | Total Trades | House/Senate PDFs | `house_etl.py:run_house_etl()` | `sync-data/index.ts:handleUpdateStats()` | `dashboard_stats.total_trades` | `useDashboardStats()` | `Dashboard.tsx` → StatsCard |
| [ ] | Total Volume | House/Senate PDFs | `senate_etl.py:run_senate_etl()` | `sync-data/index.ts:handleUpdateStats()` | `dashboard_stats.total_volume` | `useDashboardStats()` | `Dashboard.tsx` → StatsCard |
| [ ] | Active Politicians | House/Senate XML | `politician.py:find_or_create_politician()` | `sync-data/index.ts:handleUpdateStats()` | `dashboard_stats.active_politicians` | `useDashboardStats()` | `Dashboard.tsx` → StatsCard |
| [ ] | Trades This Month | Computed | `sync-data/index.ts` aggregation | `scheduled-sync/index.ts` | `dashboard_stats.trades_this_month` | `useDashboardStats()` | `Dashboard.tsx` → StatsCard |
| [ ] | Average Trade Size | Computed | `sync-data/index.ts` aggregation | `scheduled-sync/index.ts` | `dashboard_stats.average_trade_size` | `useDashboardStats()` | `Dashboard.tsx` → StatsCard |
| [ ] | Top Traded Stock | Computed | `sync-data/index.ts` aggregation | `scheduled-sync/index.ts` | `dashboard_stats.top_traded_stock` | `useDashboardStats()` | `Dashboard.tsx` → StatsCard |

**File References:**
- ETL: `python-etl-service/app/services/house_etl.py` lines 1-500
- ETL: `python-etl-service/app/services/senate_etl.py` lines 1-400
- Edge Function: `server/supabase/functions/sync-data/index.ts` lines 70-120
- Hook: `client/src/hooks/useSupabaseData.ts` lines 394-421
- Component: `client/src/components/Dashboard.tsx` lines 19-100

---

### 1.2 Politicians Data

| ✓ | Metric | External Source | ETL Function | Invoker | DB Table.Field | React Hook | UI Component |
|---|--------|-----------------|--------------|---------|----------------|------------|--------------|
| [ ] | Politician Name | House PDFs / Senate XML | `house_etl.py:parse_transaction_from_row()` | `PoliticianTradingHouseJob` | `politicians.full_name` | `usePoliticians()` | `PoliticiansView.tsx` |
| [ ] | Party Affiliation | Senate XML / QuiverQuant | `senate_etl.py:fetch_senators_from_xml()` | `PoliticianTradingSenateJob` | `politicians.party` | `usePoliticians()` | `PoliticiansView.tsx`, `TopTraders.tsx` |
| [ ] | Chamber | House/Senate classification | `find_or_create_politician()` | ETL jobs | `politicians.chamber` | `usePoliticians()` | `PoliticiansView.tsx` |
| [ ] | State | House/Senate records | ETL parsing | ETL jobs | `politicians.state_or_country` | `usePoliticians()` | `PoliticiansView.tsx` |
| [ ] | BioGuide ID | Congress.gov API | `bioguide_enrichment.py:run_bioguide_enrichment()` | `BioguideEnrichmentJob` | `politicians.bioguide_id` | `usePoliticians()` | Internal linking |
| [ ] | Total Trades (per politician) | Computed | `sync-data:handleUpdatePoliticianTotals()` | `scheduled-sync/index.ts` | `politicians.total_trades` | `usePoliticians()` | `PoliticiansView.tsx`, `TopTraders.tsx` |
| [ ] | Total Volume (per politician) | Computed | `sync-data:handleUpdatePoliticianTotals()` | `scheduled-sync/index.ts` | `politicians.total_volume` | `usePoliticians()` | `PoliticiansView.tsx`, `TopTraders.tsx` |

**File References:**
- ETL: `python-etl-service/app/services/house_etl.py` lines 200-350
- ETL: `python-etl-service/app/services/senate_etl.py` lines 70-150
- ETL: `python-etl-service/app/services/bioguide_enrichment.py` lines 1-200
- Edge Function: `server/supabase/functions/sync-data/index.ts` lines 200-300
- Hook: `client/src/hooks/useSupabaseData.ts` lines 99-138
- Component: `client/src/components/PoliticiansView.tsx` lines 1-200
- Component: `client/src/components/TopTraders.tsx` lines 9-70

---

### 1.3 Trading Disclosures

| ✓ | Metric | External Source | ETL Function | Invoker | DB Table.Field | React Hook | UI Component |
|---|--------|-----------------|--------------|---------|----------------|------------|--------------|
| [ ] | Asset Name | House/Senate PDFs | `house_etl.py:parse_transaction_from_row()` | `PoliticianTradingHouseJob` | `trading_disclosures.asset_name` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Asset Ticker | House/Senate PDFs + backfill | `ticker_backfill.py:run_ticker_backfill()` | `TickerBackfillJob` | `trading_disclosures.asset_ticker` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Transaction Type | House/Senate PDFs | `house_etl.py:parse_transaction_from_row()` | ETL jobs | `trading_disclosures.transaction_type` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Transaction Date | House/Senate PDFs | ETL parsing | ETL jobs | `trading_disclosures.transaction_date` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Disclosure Date | House/Senate PDFs | ETL parsing | ETL jobs | `trading_disclosures.disclosure_date` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Amount Range Min | House/Senate PDFs | ETL parsing | ETL jobs | `trading_disclosures.amount_range_min` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Amount Range Max | House/Senate PDFs | ETL parsing | ETL jobs | `trading_disclosures.amount_range_max` | `useTradingDisclosures()` | `FilingsView.tsx`, `LandingTradesTable.tsx` |
| [ ] | Source URL | Constructed | ETL processing | ETL jobs | `trading_disclosures.source_url` | `useTradingDisclosures()` | `FilingsView.tsx` (link) |
| [ ] | Asset Owner | House/Senate PDFs | ETL parsing | ETL jobs | `trading_disclosures.asset_owner` | `useTradingDisclosures()` | Detail modals |

**File References:**
- ETL: `python-etl-service/app/services/house_etl.py` lines 250-400
- ETL: `python-etl-service/app/services/ticker_backfill.py` lines 1-150
- Hook: `client/src/hooks/useSupabaseData.ts` lines 204-294
- Component: `client/src/components/FilingsView.tsx` lines 1-200
- Component: `client/src/components/LandingTradesTable.tsx` lines 1-700

---

### 1.4 Charts & Aggregations

| ✓ | Metric | External Source | ETL Function | Invoker | DB Table.Field | React Hook | UI Component |
|---|--------|-----------------|--------------|---------|----------------|------------|--------------|
| [ ] | Monthly Buy Count | Computed from disclosures | `sync-data:handleUpdateChartData()` | `scheduled-sync/index.ts` | `chart_data.buy_count` | `useChartData()` | `TradeChart.tsx` |
| [ ] | Monthly Sell Count | Computed from disclosures | `sync-data:handleUpdateChartData()` | `scheduled-sync/index.ts` | `chart_data.sell_count` | `useChartData()` | `TradeChart.tsx` |
| [ ] | Monthly Volume | Computed from disclosures | `sync-data:handleUpdateChartData()` | `scheduled-sync/index.ts` | `chart_data.volume` | `useChartData()` | `TradeChart.tsx`, `VolumeChart.tsx` |
| [ ] | Monthly Unique Politicians | Computed from disclosures | `sync-data:handleUpdateChartData()` | `scheduled-sync/index.ts` | `chart_data.unique_politicians` | `useChartData()` | `TradeChart.tsx` |
| [ ] | Top Tickers (Global) | Computed from disclosures | Database view aggregation | On-demand | `top_tickers` view | `useTopTickers()` | `TopTickers.tsx` |
| [ ] | Top Tickers (Monthly) | Computed from disclosures | `sync-data:handleUpdateChartData()` | `scheduled-sync/index.ts` | `chart_data.top_tickers` (JSON) | `useChartData()` | `MonthDetailModal.tsx` |

**File References:**
- Edge Function: `server/supabase/functions/sync-data/index.ts` lines 500-650
- Hook: `client/src/hooks/useSupabaseData.ts` lines 303-388
- Component: `client/src/components/TradeChart.tsx` lines 46-200
- Component: `client/src/components/TopTickers.tsx` lines 1-100

---

### 1.5 Trading & Portfolio

| ✓ | Metric | External Source | ETL Function | Invoker | DB Table.Field | React Hook | UI Component |
|---|--------|-----------------|--------------|---------|----------------|------------|--------------|
| [ ] | Order Status | Alpaca API | `orders/index.ts:handleGetOrders()` | `OrdersJob` / User action | `trading_orders.status` | `useOrders()` | Orders table |
| [ ] | Order Fill Price | Alpaca API | `orders/index.ts:handleSyncOrders()` | `OrdersJob` | `trading_orders.filled_avg_price` | `useOrders()` | Orders table |
| [ ] | Order Quantity | Alpaca API | `orders/index.ts` | User action | `trading_orders.quantity` | `useOrders()` | Orders table |
| [ ] | Position Quantity | Alpaca API | `alpaca-account/index.ts:handleGetPositions()` | User action | Memory/Alpaca | `useAlpacaPositions()` | Portfolio dashboard |
| [ ] | Position Value | Alpaca API | `alpaca-account/index.ts:handleGetPositions()` | User action | Memory/Alpaca | `useAlpacaPositions()` | Portfolio dashboard |
| [ ] | Unrealized P&L | Alpaca API | `alpaca-account/index.ts:handleGetPositions()` | User action | Memory/Alpaca | `useAlpacaPositions()` | Portfolio dashboard |
| [ ] | Account Balance | Alpaca API | `alpaca-account/index.ts:handleGetAccount()` | User action | Memory/Alpaca | `useAlpacaAccount()` | Account summary |
| [ ] | Signal Type | ML Model | `trading-signals/index.ts` | `TradingSignalsJob` | `trading_signals.signal_type` | Direct query | Signal dashboard |
| [ ] | Signal Confidence | ML Model | `trading-signals/index.ts` | `TradingSignalsJob` | `trading_signals.confidence_score` | Direct query | Signal dashboard |
| [ ] | Reference Portfolio Value | Alpaca API + Computed | `reference-portfolio/index.ts` | `ReferencePortfolioSyncJob` | `reference_portfolio_positions` | Admin only | Portfolio dashboard |

**File References:**
- Edge Function: `server/supabase/functions/orders/index.ts` lines 200-500
- Edge Function: `server/supabase/functions/alpaca-account/index.ts` lines 58-150
- Edge Function: `server/supabase/functions/trading-signals/index.ts` lines 1-300
- Hook: `client/src/hooks/useOrders.ts` lines 74-122
- Hook: `client/src/hooks/useAlpacaPositions.ts` lines 46-95

---

### 1.6 Detail Views

| ✓ | Metric | External Source | ETL Function | Invoker | DB Table.Field | React Hook | UI Component |
|---|--------|-----------------|--------------|---------|----------------|------------|--------------|
| [ ] | Politician Total Trades | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `usePoliticianDetail()` | `PoliticianProfileModal.tsx` |
| [ ] | Politician Total Volume | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `usePoliticianDetail()` | `PoliticianProfileModal.tsx` |
| [ ] | Politician Buy/Sell/Hold Counts | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `usePoliticianDetail()` | `PoliticianProfileModal.tsx` |
| [ ] | Politician Top Tickers | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `usePoliticianDetail()` | `PoliticianProfileModal.tsx` |
| [ ] | Politician Recent Trades | Client-fetched | N/A | React hook | `trading_disclosures` | `usePoliticianDetail()` | `PoliticianProfileModal.tsx` |
| [ ] | Ticker Trade Count | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `useTickerDetail()` | `TickerDetailModal.tsx` |
| [ ] | Ticker Total Volume | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `useTickerDetail()` | `TickerDetailModal.tsx` |
| [ ] | Ticker Top Politicians | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `useTickerDetail()` | `TickerDetailModal.tsx` |
| [ ] | Month Buy/Sell Breakdown | Client-computed | N/A (client aggregation) | React hook | Computed in-memory | `useMonthDetail()` | `MonthDetailModal.tsx` |

**File References:**
- Hook: `client/src/hooks/useSupabaseData.ts` lines 439-712
- Component: `client/src/components/detail-modals/PoliticianProfileModal.tsx` lines 1-325
- Component: `client/src/components/detail-modals/TickerDetailModal.tsx`
- Component: `client/src/components/detail-modals/MonthDetailModal.tsx`

---

## 2. Government Disclosure Sources

### 2.1 US House Financial Disclosures

| Attribute | Value |
|-----------|-------|
| **Source Name** | US House of Representatives Financial Disclosures |
| **Official URL** | https://disclosures-clerk.house.gov |
| **Data URL Pattern** | `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.ZIP` |
| **ETL Service** | `python-etl-service/app/services/house_etl.py` |
| **Scheduler Job** | `PoliticianTradingHouseJob` |
| **Schedule** | Every 6 hours |
| **Data Format** | ZIP archive containing index file + individual PDF disclosures |

#### Fields Populated

**Table: `politicians`**
| ✓ | Field | Source Field | Description |
|---|-------|--------------|-------------|
| [ ] | `first_name` | Parsed from PDF | Politician first name |
| [ ] | `last_name` | Parsed from PDF | Politician last name |
| [ ] | `full_name` | Parsed from PDF | Combined name |
| [ ] | `state_or_country` | State/District | State abbreviation |
| [ ] | `district` | State/District | Congressional district |
| [ ] | `role` | Fixed | "Representative" |
| [ ] | `chamber` | Fixed | "House" |

**Table: `trading_disclosures`**
| ✓ | Field | Source Field | Description |
|---|-------|--------------|-------------|
| [ ] | `asset_name` | PDF table | Full asset/security name |
| [ ] | `asset_ticker` | PDF table | Stock ticker symbol (extracted) |
| [ ] | `asset_type` | PDF table | Type of asset (stock, bond, etc.) |
| [ ] | `transaction_type` | PDF table | "purchase", "sale", "exchange" |
| [ ] | `transaction_date` | PDF table | Date of transaction |
| [ ] | `disclosure_date` | Filing date | Date disclosed to House clerk |
| [ ] | `amount_range_min` | PDF table | Lower bound of amount range |
| [ ] | `amount_range_max` | PDF table | Upper bound of amount range |
| [ ] | `source_url` | Constructed | URL to original PDF |
| [ ] | `source_document_id` | doc_id | Unique document identifier |
| [ ] | `asset_owner` | PDF table | "Self", "Spouse", "Joint", etc. |
| [ ] | `comments` | PDF table | Additional transaction notes |

---

### 2.2 US Senate Financial Disclosures

| Attribute | Value |
|-----------|-------|
| **Source Name** | US Senate Electronic Filing Database (EFD) |
| **Official URL** | https://efdsearch.senate.gov/search/ |
| **Senator List** | https://www.senate.gov/general/contact_information/senators_cfm.xml |
| **ETL Service** | `python-etl-service/app/services/senate_etl.py` |
| **Scheduler Job** | `PoliticianTradingSenateJob` |
| **Schedule** | Every 6 hours |
| **Data Format** | HTML pages (requires Playwright browser automation) |

#### Fields Populated

**Table: `politicians`**
| ✓ | Field | Source Field | Description |
|---|-------|--------------|-------------|
| [ ] | `first_name` | XML/HTML | Senator first name |
| [ ] | `last_name` | XML/HTML | Senator last name |
| [ ] | `full_name` | XML/HTML | Combined name |
| [ ] | `party` | XML | "D", "R", or "I" |
| [ ] | `state_or_country` | XML | State abbreviation |
| [ ] | `bioguide_id` | XML | Congress.gov BioGuide ID |
| [ ] | `role` | Fixed | "Senator" |
| [ ] | `chamber` | Fixed | "Senate" |

**Table: `trading_disclosures`**
| ✓ | Field | Source Field | Description |
|---|-------|--------------|-------------|
| [ ] | `asset_name` | HTML table | Full asset/security name |
| [ ] | `asset_ticker` | HTML table | Stock ticker symbol |
| [ ] | `asset_type` | HTML table | Type of asset |
| [ ] | `transaction_type` | HTML table | "purchase", "sale", "exchange" |
| [ ] | `transaction_date` | HTML table | Date of transaction |
| [ ] | `disclosure_date` | HTML table | Date disclosed to Senate |
| [ ] | `amount_range_min` | HTML table | Lower bound of amount range |
| [ ] | `amount_range_max` | HTML table | Upper bound of amount range |
| [ ] | `source_url` | PTR URL | Link to Senate EFD page |
| [ ] | `asset_owner` | HTML table | Owner of the asset |
| [ ] | `comments` | HTML table | Additional notes |

---

### 2.3 California NetFile Disclosures

| Attribute | Value |
|-----------|-------|
| **Source Name** | California NetFile Financial Disclosures |
| **Official URL** | https://netfile.com |
| **ETL Service** | `politician-trading-collect` Edge Function |
| **Scheduler Job** | `PoliticianTradingCaliforniaJob` |
| **Schedule** | Every 6 hours |
| **Status** | Planned (stub implementation) |

#### Fields Populated

**Table: `politicians`**
| ✓ | Field | Source Field | Description |
|---|-------|--------------|-------------|
| [ ] | `full_name` | API | California official name |
| [ ] | `state_or_country` | Fixed | "CA" |
| [ ] | `role` | API | State office held |

---

### 2.4 EU Parliament Declarations

| Attribute | Value |
|-----------|-------|
| **Source Name** | EU Parliament Financial Declarations |
| **Official URL** | https://www.europarl.europa.eu |
| **ETL Service** | `politician-trading-collect` Edge Function |
| **Scheduler Job** | `PoliticianTradingEuJob` |
| **Schedule** | Every 6 hours |
| **Status** | Planned (stub implementation) |

#### Fields Populated

**Table: `politicians`**
| ✓ | Field | Source Field | Description |
|---|-------|--------------|-------------|
| [ ] | `full_name` | API | MEP full name |
| [ ] | `eu_id` | API | EU Parliament member ID |
| [ ] | `state_or_country` | API | Member state |
| [ ] | `role` | Fixed | "MEP" |

---

## 3. Third-Party Data Aggregators

### 3.1 QuiverQuant Congress Trading

| Attribute | Value |
|-----------|-------|
| **Source Name** | QuiverQuant Congress Trading |
| **Web URL** | https://www.quiverquant.com/congresstrading/ |
| **API URL** | https://api.quiverquant.com/beta/live/congresstrading |
| **ETL Service** | `politician-trading-collect` Edge Function |
| **Scheduler Job** | `PoliticianTradingQuiverJob` |
| **Schedule** | Every minute (testing) / Every 6 hours (production) |
| **Authentication** | Bearer token (API key from `user_api_keys.quiverquant_api_key`) |

#### QuiverQuant API Response Schema

```json
{
  "Representative": "Jonathan Jackson",
  "BioGuideID": "J000309",
  "ReportDate": "2026-01-08",
  "TransactionDate": "2025-12-22",
  "Ticker": "HOOD",
  "Transaction": "Sale",
  "Range": "$15,001 - $50,000",
  "House": "Representatives",
  "Amount": "15001.0",
  "Party": "D",
  "last_modified": "2026-01-09",
  "TickerType": "ST",
  "Description": null,
  "ExcessReturn": -6.39,
  "PriceChange": -5.70,
  "SPYChange": 0.69
}
```

#### Fields Populated

**Table: `politicians`**
| ✓ | Field | QuiverQuant Field | Description |
|---|-------|-------------------|-------------|
| [ ] | `full_name` | `Representative` | Politician full name |
| [ ] | `bioguide_id` | `BioGuideID` | Congress.gov identifier |
| [ ] | `party` | `Party` | "D", "R", or "I" |
| [ ] | `chamber` | `House` | "Representatives" or "Senate" |

**Table: `trading_disclosures`**
| ✓ | Field | QuiverQuant Field | Description |
|---|-------|-------------------|-------------|
| [ ] | `asset_ticker` | `Ticker` | Stock ticker symbol |
| [ ] | `asset_name` | `Description` | Asset description (falls back to ticker) |
| [ ] | `transaction_type` | `Transaction` | Normalized to "purchase"/"sale" |
| [ ] | `transaction_date` | `TransactionDate` | Date of trade |
| [ ] | `disclosure_date` | `ReportDate` | Date disclosed |
| [ ] | `amount_range_min` | Parsed from `Range` | Lower bound |
| [ ] | `amount_range_max` | Parsed from `Range` | Upper bound |
| [ ] | `source_url` | Fixed | QuiverQuant URL |

**Additional QuiverQuant-Only Metrics** (stored in `raw_data` JSON):
| ✓ | Metric | Description |
|---|--------|-------------|
| [ ] | `ExcessReturn` | Performance vs SPY benchmark (%) |
| [ ] | `PriceChange` | Actual price change since trade (%) |
| [ ] | `SPYChange` | S&P 500 change over same period (%) |
| [ ] | `TickerType` | Asset type code ("ST" = Stock) |

---

## 4. Reference Data APIs

### 4.1 Congress.gov API

| Attribute | Value |
|-----------|-------|
| **Source Name** | Congress.gov Member API |
| **API URL** | https://api.congress.gov/v3/member |
| **ETL Service** | `python-etl-service/app/services/bioguide_enrichment.py` |
| **Scheduler Job** | `BioguideEnrichmentJob` |
| **Schedule** | Daily at 3 AM UTC |
| **Authentication** | API key (`CONGRESS_API_KEY` env var) |
| **Rate Limit** | 0.5s delay between requests |

#### Fields Populated (Enrichment)

**Table: `politicians`**
| ✓ | Field | API Field | Description |
|---|-------|-----------|-------------|
| [ ] | `bioguide_id` | `bioguideId` | Unique Congress identifier |
| [ ] | `first_name` | `firstName` | Official first name |
| [ ] | `last_name` | `lastName` | Official last name |
| [ ] | `party` | `partyName` | Full party name |
| [ ] | `state_or_country` | `state` | State abbreviation |
| [ ] | `district` | `district` | Congressional district (House only) |
| [ ] | `role` | `chamber` | "Senate" or "House" |
| [ ] | `term_start` | `terms[].startYear` | Current term start |
| [ ] | `term_end` | `terms[].endYear` | Current term end |

---

## 5. Trading & Market Data APIs

### 5.1 Alpaca Trading API

| Attribute | Value |
|-----------|-------|
| **Source Name** | Alpaca Markets Trading API |
| **Paper URL** | https://paper-api.alpaca.markets |
| **Live URL** | https://api.alpaca.markets |
| **Edge Functions** | `orders/index.ts`, `alpaca-account/index.ts`, `reference-portfolio/index.ts` |
| **Scheduler Jobs** | `AlpacaAccountJob`, `OrdersJob`, `PortfolioJob`, `PortfolioSnapshotJob` |
| **Authentication** | API key + Secret key (from `user_api_keys` or `trading_accounts`) |

#### Fields Populated

**Table: `trading_orders`**
| ✓ | Field | Alpaca Field | Description |
|---|-------|--------------|-------------|
| [ ] | `alpaca_order_id` | `id` | Alpaca's order UUID |
| [ ] | `alpaca_client_order_id` | `client_order_id` | Client-provided order ID |
| [ ] | `ticker` | `symbol` | Stock symbol |
| [ ] | `side` | `side` | "buy" or "sell" |
| [ ] | `quantity` | `qty` | Number of shares |
| [ ] | `order_type` | `type` | "market", "limit", "stop", etc. |
| [ ] | `limit_price` | `limit_price` | Limit price (if applicable) |
| [ ] | `stop_price` | `stop_price` | Stop price (if applicable) |
| [ ] | `status` | `status` | Order status |
| [ ] | `filled_quantity` | `filled_qty` | Shares filled |
| [ ] | `filled_avg_price` | `filled_avg_price` | Average fill price |
| [ ] | `submitted_at` | `submitted_at` | Submission timestamp |
| [ ] | `filled_at` | `filled_at` | Fill timestamp |
| [ ] | `canceled_at` | `canceled_at` | Cancellation timestamp |
| [ ] | `expired_at` | `expired_at` | Expiration timestamp |

**Table: `reference_portfolio_positions`**
| ✓ | Field | Alpaca Field | Description |
|---|-------|--------------|-------------|
| [ ] | `ticker` | `symbol` | Stock symbol |
| [ ] | `quantity` | `qty` | Shares held |
| [ ] | `average_entry_price` | `avg_entry_price` | Cost basis per share |
| [ ] | `current_price` | Latest quote | Real-time price |
| [ ] | `market_value` | `market_value` | Current position value |
| [ ] | `unrealized_pl` | `unrealized_pl` | Unrealized P&L |
| [ ] | `unrealized_plpc` | `unrealized_plpc` | Unrealized P&L % |

**Table: `portfolios`**
| ✓ | Field | Alpaca Field | Description |
|---|-------|--------------|-------------|
| [ ] | `cash_balance` | `cash` | Available cash |
| [ ] | `current_value` | `portfolio_value` | Total portfolio value |

---

### 5.2 Yahoo Finance API

| Attribute | Value |
|-----------|-------|
| **Source Name** | Yahoo Finance Chart API |
| **API URL** | `https://query1.finance.yahoo.com/v8/finance/chart/{ticker}` |
| **Edge Function** | `trading-signals/index.ts` |
| **Usage** | Signal generation, price validation |
| **Authentication** | None (public API) |

#### Fields Used

**Table: `trading_signals`** (indirectly)
| ✓ | Metric | Yahoo Field | Description |
|---|--------|-------------|-------------|
| [ ] | Current Price | `chart.result[0].meta.regularMarketPrice` | Latest market price |
| [ ] | Historical Prices | `chart.result[0].indicators.quote[0].close` | Closing prices |
| [ ] | Volume | `chart.result[0].indicators.quote[0].volume` | Trading volume |

---

## 6. AI/ML Services

### 6.1 Ollama LLM Service

| Attribute | Value |
|-----------|-------|
| **Source Name** | Ollama Local LLM Inference |
| **Default URL** | https://ollama.lefv.info |
| **ETL Services** | `error_report_processor.py`, `party_enrichment.py`, `name_enrichment.py` |
| **Scheduler Job** | `PartyEnrichmentJob` |
| **Status** | Optional (graceful fallback if unavailable) |

#### Fields Populated (Enrichment)

**Table: `politicians`**
| ✓ | Field | LLM Output | Description |
|---|-------|------------|-------------|
| [ ] | `party` | Inferred | Party affiliation from context |
| [ ] | `full_name` | Normalized | Canonical name form |

**Table: `error_reports`**
| ✓ | Field | LLM Output | Description |
|---|-------|------------|-------------|
| [ ] | `category` | Classification | Error category |
| [ ] | `severity` | Assessment | Error severity level |

---

### 6.2 Python ETL ML Service

| Attribute | Value |
|-----------|-------|
| **Source Name** | Python ETL Service ML Endpoints |
| **Production URL** | https://politician-trading-etl.fly.dev |
| **Edge Function** | `trading-signals/index.ts` |
| **Scheduler Job** | `TradingSignalsJob` |

#### Endpoints

| ✓ | Endpoint | Method | Description |
|---|----------|--------|-------------|
| [ ] | `/ml/models/active` | GET | List active ML models |
| [ ] | `/ml/batch-predict` | POST | Batch signal predictions |
| [ ] | `/signals/apply-lambda` | POST | Apply scoring functions |

#### Fields Populated

**Table: `trading_signals`**
| ✓ | Field | ML Output | Description |
|---|-------|-----------|-------------|
| [ ] | `signal_type` | Prediction | "buy", "sell", or "hold" |
| [ ] | `confidence_score` | Model confidence | 0.0 to 1.0 |
| [ ] | `signal_strength` | Strength bucket | "strong", "medium", "weak" |
| [ ] | `target_price` | Price prediction | Expected target price |
| [ ] | `stop_loss` | Risk management | Stop loss level |
| [ ] | `take_profit` | Risk management | Take profit level |
| [ ] | `model_version` | Model ID | Which model generated signal |
| [ ] | `features` | Feature vector | Input features (JSON) |
| [ ] | `analysis` | Explanation | Signal analysis (JSON) |

---

## 7. Database Schema Reference

### Core Tables and External Source Mapping

| ✓ | Table | Primary External Sources | Update Frequency |
|---|-------|-------------------------|------------------|
| [ ] | `politicians` | House PDFs, Senate XML, Congress.gov, QuiverQuant | 6 hours |
| [ ] | `trading_disclosures` | House PDFs, Senate HTML, QuiverQuant | 6 hours |
| [ ] | `trading_orders` | Alpaca API | Real-time |
| [ ] | `trading_signals` | ML Service, Yahoo Finance | Daily |
| [ ] | `reference_portfolio_positions` | Alpaca API | Real-time |
| [ ] | `portfolios` | Alpaca API | Real-time |
| [ ] | `chart_data` | Aggregated from disclosures | Daily |
| [ ] | `dashboard_stats` | Aggregated from disclosures | Daily |

### Computed/Aggregated Metrics

**Table: `dashboard_stats`**
| ✓ | Metric | Computation | Description |
|---|--------|-------------|-------------|
| [ ] | `total_trades` | COUNT(trading_disclosures) | Total disclosure count |
| [ ] | `total_volume` | SUM(amount_range_avg) | Estimated trading volume |
| [ ] | `active_politicians` | COUNT(DISTINCT politician_id) | Politicians with trades |
| [ ] | `trades_this_month` | COUNT WHERE month = current | Monthly trade count |
| [ ] | `average_trade_size` | AVG(amount_range_avg) | Average transaction size |
| [ ] | `top_traded_stock` | MODE(asset_ticker) | Most traded ticker |

**Table: `chart_data`**
| ✓ | Metric | Computation | Description |
|---|--------|-------------|-------------|
| [ ] | `buy_count` | COUNT WHERE type='purchase' | Monthly buys |
| [ ] | `sell_count` | COUNT WHERE type='sale' | Monthly sells |
| [ ] | `total_volume` | SUM(amount_range_avg) | Monthly volume |
| [ ] | `unique_politicians` | COUNT(DISTINCT politician_id) | Active politicians |
| [ ] | `top_tickers` | GROUP BY ticker, TOP 5 | Most traded tickers |
| [ ] | `party_breakdown` | GROUP BY party | Trades by party |

**Table: `politicians`** (Aggregated)
| ✓ | Metric | Computation | Description |
|---|--------|-------------|-------------|
| [ ] | `total_trades` | COUNT(disclosures) | Politician's trade count |
| [ ] | `total_volume` | SUM(amount_range_avg) | Politician's total volume |

---

## 8. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  House PDFs  │  │ Senate HTML  │  │ QuiverQuant  │  │ Congress.gov │    │
│  │  (Clerk)     │  │ (EFD Search) │  │    (API)     │  │    (API)     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         ▼                 ▼                 ▼                 ▼             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    Python ETL Service                            │       │
│  │  house_etl.py │ senate_etl.py │ quiver │ bioguide_enrichment.py │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      Supabase PostgreSQL                         │       │
│  │  politicians │ trading_disclosures │ chart_data │ dashboard_stats│       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    Edge Functions (Deno)                         │       │
│  │  trading-signals │ sync-data │ orders │ reference-portfolio      │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│         │                                           │                       │
│         ▼                                           ▼                       │
│  ┌──────────────┐  ┌──────────────┐        ┌──────────────┐                │
│  │Yahoo Finance │  │  ML Service  │        │  Alpaca API  │                │
│  │   (Prices)   │  │ (Predictions)│        │  (Trading)   │                │
│  └──────────────┘  └──────────────┘        └──────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │     React Client (UI)     │
                    │   Dashboard │ Politicians │
                    │   Trades │ Signals │ Orders│
                    └──────────────────────────┘
```

---

## 9. Environment Variables

### Required for Core Functionality

```bash
# Supabase (Database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Required for ETL Jobs

```bash
# Congress.gov API (BioGuide enrichment)
CONGRESS_API_KEY=your-congress-api-key
```

### Required for Trading Features

```bash
# Alpaca Trading
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
ALPACA_PAPER=true  # true for paper trading, false for live
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # optional override
```

### Optional Services

```bash
# QuiverQuant API (enhanced data)
QUIVERQUANT_API_KEY=your-quiver-key

# Ollama LLM (name/party enrichment)
OLLAMA_BASE_URL=https://ollama.lefv.info

# Python ETL Service
ETL_API_URL=https://politician-trading-etl.fly.dev
```

---

## Quick Reference: Source to Table Mapping

| ✓ | External Source | Primary Table(s) | Key Fields |
|---|----------------|------------------|------------|
| [ ] | House Clerk PDFs | `politicians`, `trading_disclosures` | name, ticker, amount, dates |
| [ ] | Senate EFD | `politicians`, `trading_disclosures` | name, ticker, amount, dates |
| [ ] | QuiverQuant | `politicians`, `trading_disclosures` | name, ticker, party, performance |
| [ ] | Congress.gov | `politicians` | bioguide_id, party, term dates |
| [ ] | Alpaca | `trading_orders`, `portfolios`, `positions` | orders, balances, positions |
| [ ] | Yahoo Finance | `trading_signals` | prices, volume |
| [ ] | ML Service | `trading_signals` | predictions, confidence |
| [ ] | Ollama | `politicians`, `error_reports` | party inference, categorization |

---

*Last updated: 2026-01-19*
