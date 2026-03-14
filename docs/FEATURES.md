# GovMarket Feature Requirements

## Overview

This document defines all features for govmarket.trade, their acceptance criteria, and implementation status. ClawdBot should reference this document to prioritize work and verify feature completeness.

---

## Priority Definitions

| Priority | Definition | Response Time |
|----------|------------|---------------|
| **P0** | Critical - Site broken or major revenue impact | Immediate |
| **P1** | High - Important feature or significant bug | This sprint |
| **P2** | Medium - Enhancement or minor bug | Next sprint |
| **P3** | Low - Nice to have | Backlog |

---

## Feature Categories

### 1. 🏠 Core Platform

#### 1.1 Politician Directory
**Priority:** P0 (Complete)  
**Status:** ✅ Live

**Description:** Display all tracked politicians with basic information.

**Acceptance Criteria:**
- [ ] List all senators and representatives
- [ ] Show name, party, state, chamber
- [ ] Profile photo for each politician
- [ ] Link to individual politician page
- [ ] Pagination or infinite scroll for large lists
- [ ] Sort by name, state, party, trade activity

**Technical Notes:**
- Source data from Supabase PostgreSQL
- Cache with TanStack Query (React Query)
- Images stored/served via CDN
- Component: `client/src/components/`

---

#### 1.2 Trade History Display
**Priority:** P0 (Complete)  
**Status:** ✅ Live

**Description:** Show historical trades for each politician.

**Acceptance Criteria:**
- [ ] List all trades for a politician
- [ ] Show: date, ticker, company name, transaction type, amount range
- [ ] Link ticker to stock details
- [ ] Sort by date (newest first default)
- [ ] Filter by transaction type (buy/sell)
- [ ] Filter by date range
- [ ] Export to CSV

**Technical Notes:**
- Paginate with Supabase pagination
- Real-time via Supabase subscriptions
- Component: `client/src/components/LandingTradesTable.tsx`

---

#### 1.3 Search & Filtering
**Priority:** P1  
**Status:** 🔄 In Progress

**Description:** Allow users to search and filter politicians and trades.

**Acceptance Criteria:**
- [ ] Global search bar in header
- [ ] Search by politician name
- [ ] Search by ticker/company
- [ ] Filter politicians by party
- [ ] Filter politicians by chamber (Senate/House)
- [ ] Filter politicians by state
- [ ] Filter trades by amount range
- [ ] Combine multiple filters
- [ ] Clear all filters option
- [ ] URL reflects filter state (shareable)

**Technical Notes:**
- Debounce search input with custom hook
- Supabase full-text search or pg_trgm
- TanStack Query for caching search results

---

#### 1.4 Individual Stock Page
**Priority:** P1  
**Status:** ⏳ Not Started

**Description:** Show all political trading activity for a specific stock.

**Acceptance Criteria:**
- [ ] Page for each traded stock
- [ ] Stock price chart
- [ ] List all politicians who traded this stock
- [ ] Timeline of trades overlaid on price chart
- [ ] Company information (sector, market cap)
- [ ] Total political volume
- [ ] Recent news about the stock

**Technical Notes:**
- Integrate yfinance via python-etl-service
- Alpaca API for real-time data
- Cache in Supabase with TTL

---

### 2. 📊 Data & Analytics

#### 2.1 Dashboard/Overview
**Priority:** P1  
**Status:** 🔄 In Progress

**Description:** Landing page with key insights and recent activity.

**Acceptance Criteria:**
- [ ] Recent trades feed (last 24h/7d)
- [ ] Top traded stocks (volume)
- [ ] Most active politicians
- [ ] Market sentiment indicator
- [ ] Quick stats (total trades, total volume)
- [ ] Trending tickers

**Technical Notes:**
- Pre-compute with Supabase Edge Functions
- Quantum scheduler in Phoenix backend
- Component: `client/src/components/TopTickers.tsx`

---

#### 2.2 Performance Tracking
**Priority:** P2  
**Status:** ⏳ Not Started

**Description:** Track how politicians' trades perform vs market.

**Acceptance Criteria:**
- [ ] Calculate return on each trade (current vs purchase price)
- [ ] Politician performance leaderboard
- [ ] Compare to S&P 500 benchmark
- [ ] Time-weighted returns
- [ ] Risk-adjusted metrics (optional)
- [ ] Party performance comparison

**Technical Notes:**
- Complex calculations - may need background processing
- Define clear methodology and disclose it

---

#### 2.3 Pattern Detection
**Priority:** P2  
**Status:** ⏳ Not Started

**Description:** Identify unusual trading patterns.

**Acceptance Criteria:**
- [ ] Flag trades before major news
- [ ] Detect clustering (multiple politicians, same stock, same time)
- [ ] Committee-relevant trading detection
- [ ] Unusual volume alerts
- [ ] Historical pattern analysis

**Technical Notes:**
- ML models may be needed
- Be careful with accusations - flag for review, don't accuse

---

### 3. 👤 User Features

#### 3.1 User Accounts
**Priority:** P1  
**Status:** ⏳ Not Started

**Description:** Allow users to create accounts for personalized features.

**Acceptance Criteria:**
- [ ] Email/password registration
- [ ] OAuth (Google, GitHub)
- [ ] Email verification
- [ ] Password reset flow
- [ ] Profile page
- [ ] Account deletion (GDPR/CCPA)
- [ ] Session management

**Technical Notes:**
- Use Supabase Auth (built-in)
- OAuth providers configured in Supabase dashboard
- RLS policies for row-level security

---

#### 3.2 Watchlists
**Priority:** P1  
**Status:** ⏳ Not Started

**Description:** Let users save politicians and stocks to track.

**Acceptance Criteria:**
- [ ] Create named watchlists
- [ ] Add/remove politicians
- [ ] Add/remove stocks
- [ ] View watchlist as filtered view
- [ ] Watchlist dashboard widget
- [ ] Share watchlists (optional)

**Technical Notes:**
- Store in database linked to user
- Real-time updates on watched items

---

#### 3.3 Alerts & Notifications
**Priority:** P2  
**Status:** ⏳ Not Started

**Description:** Notify users of relevant trading activity.

**Acceptance Criteria:**
- [ ] Email alerts for watchlist activity
- [ ] Configure alert frequency (immediate, daily digest, weekly)
- [ ] Browser push notifications (optional)
- [ ] SMS alerts (premium)
- [ ] Alert for specific conditions (politician X buys Y)
- [ ] Unsubscribe easily

**Technical Notes:**
- Queue-based notification system
- Rate limit to prevent spam
- Track delivery and engagement

---

### 4. 💰 Monetization

#### 4.1 Subscription Tiers
**Priority:** P1  
**Status:** ⏳ Not Started

**Description:** Premium features for paying users.

**Tiers:**
```
FREE:
- Basic politician/trade viewing
- Limited history (90 days)
- Basic search/filter
- 5 watchlist items

PRO ($9.99/month):
- Full historical data
- Unlimited watchlists
- Email alerts
- CSV exports
- Advanced filters
- Ad-free experience

ENTERPRISE (Custom):
- API access
- Bulk data exports
- Custom integrations
- Priority support
- SLA guarantees
```

**Acceptance Criteria:**
- [ ] Stripe integration
- [ ] Plan selection page
- [ ] Billing portal (manage subscription)
- [ ] Usage limits enforced
- [ ] Upgrade/downgrade flows
- [ ] Trial period (7 days?)
- [ ] Cancellation flow
- [ ] Invoice generation

**Technical Notes:**
- Use Stripe Checkout and Customer Portal
- Implement webhooks for subscription events
- Track usage for limits

---

#### 4.2 API Access
**Priority:** P2  
**Status:** ⏳ Not Started

**Description:** RESTful API for programmatic access.

**Acceptance Criteria:**
- [ ] API key generation
- [ ] Rate limiting by tier
- [ ] Endpoints: politicians, trades, stocks
- [ ] Query parameters for filtering
- [ ] Pagination
- [ ] OpenAPI/Swagger docs
- [ ] Usage dashboard
- [ ] Webhook support (optional)

**Tiers:**
```
FREE: 100 requests/day
PRO: 10,000 requests/day
ENTERPRISE: Unlimited + webhooks
```

**Technical Notes:**
- Document thoroughly
- Version the API (v1, v2)
- Consider GraphQL as alternative

---

### 5. 🔧 Infrastructure

#### 5.1 Data Pipeline
**Priority:** P0  
**Status:** 🔄 Partial

**Description:** Automated data collection and processing.

**Acceptance Criteria:**
- [ ] Senate scraper runs daily
- [ ] House scraper runs daily
- [ ] PDF parsing for House trades
- [ ] Data validation rules
- [ ] Duplicate detection
- [ ] Error alerting
- [ ] Manual override for corrections
- [ ] Audit log of all data changes

**Technical Notes:**
- APScheduler in python-etl-service
- Quantum scheduler in Phoenix backend
- Store raw data in Supabase for reprocessing
- Scrapers: `python-etl-service/app/services/`

---

#### 5.2 Monitoring & Observability
**Priority:** P1  
**Status:** ⏳ Not Started

**Description:** Comprehensive system monitoring.

**Acceptance Criteria:**
- [ ] Uptime monitoring
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring (Core Web Vitals)
- [ ] Database health monitoring
- [ ] API response time tracking
- [ ] Alerting rules
- [ ] Dashboard for key metrics

**Technical Notes:**
- Fly.io health checks and metrics
- Phoenix Telemetry for backend metrics
- GitHub Actions CI/CD status
- Supabase dashboard for database health

---

#### 5.3 Security Hardening
**Priority:** P0  
**Status:** 🔄 Partial

**Description:** Security best practices implementation.

**Acceptance Criteria:**
- [ ] HTTPS everywhere
- [ ] CSP headers
- [ ] CORS properly configured
- [ ] Rate limiting on all endpoints
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Dependency scanning
- [ ] Security headers audit

**Technical Notes:**
- Supabase RLS policies for data access
- HTTPS forced on Fly.io
- Dependabot enabled in GitHub
- npm audit / pip audit in CI pipeline

---

### 6. 🎨 User Experience

#### 6.1 Mobile Responsiveness
**Priority:** P1  
**Status:** 🔄 In Progress

**Description:** Fully functional on mobile devices.

**Acceptance Criteria:**
- [ ] All pages render correctly on mobile
- [ ] Touch-friendly interactions
- [ ] Mobile-optimized navigation
- [ ] Tables convert to cards on mobile
- [ ] Charts resize appropriately
- [ ] No horizontal scrolling
- [ ] Test on iOS Safari and Android Chrome

**Technical Notes:**
- Use responsive design principles
- Test with browser DevTools
- Consider PWA for mobile

---

#### 6.2 Accessibility
**Priority:** P1  
**Status:** ⏳ Not Started

**Description:** WCAG 2.1 AA compliance.

**Acceptance Criteria:**
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] Color contrast meets standards
- [ ] Alt text on images
- [ ] Form labels present
- [ ] Focus indicators visible
- [ ] No seizure-inducing content

**Technical Notes:**
- Use axe-core for automated testing
- Manual testing with screen reader
- Fix all Lighthouse accessibility issues

---

#### 6.3 Performance Optimization
**Priority:** P1  
**Status:** 🔄 In Progress

**Description:** Fast, smooth user experience.

**Acceptance Criteria:**
- [ ] LCP < 2.5s
- [ ] FID < 100ms
- [ ] CLS < 0.1
- [ ] TTI < 3.5s
- [ ] Bundle size optimized
- [ ] Images optimized (WebP, lazy load)
- [ ] Code splitting implemented
- [ ] Caching strategy in place

**Technical Notes:**
- Use Lighthouse CI in pipeline
- Implement edge caching
- Lazy load below-fold content

---

## Feature Backlog

Features under consideration but not yet prioritized:

1. **Browser Extension** - Quick access to politician trades from any page
2. **Mobile App** - Native iOS/Android apps
3. **Portfolio Simulator** - "What if you invested like politician X"
4. **Social Features** - Comments, discussions
5. **Embeddable Widgets** - For other sites to show data
6. **Podcast/Newsletter** - Weekly trading roundup
7. **Educational Content** - How to use the data responsibly

---

## Definition of Done

A feature is only "Done" when:

1. ✅ All acceptance criteria met
2. ✅ Unit tests written and passing
3. ✅ Integration tests written and passing
4. ✅ E2E tests for user flows
5. ✅ Code reviewed
6. ✅ Documentation updated
7. ✅ Deployed to production
8. ✅ Monitored for 24h with no issues
9. ✅ Analytics tracking in place

---

*Last updated: January 2026*
*Review and update monthly*
