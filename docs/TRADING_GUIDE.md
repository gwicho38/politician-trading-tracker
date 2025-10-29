# Politician Trading Tracker - Trading Guide

This guide explains how to use the automated trading features of the Politician Trading Tracker, including signal generation, paper trading, and live trading with Alpaca API integration.

## Table of Contents

1. [Overview](#overview)
2. [Setup](#setup)
3. [Signal Generation](#signal-generation)
4. [Trading Operations](#trading-operations)
5. [Risk Management](#risk-management)
6. [Paper Trading vs Live Trading](#paper-trading-vs-live-trading)
7. [CLI Reference](#cli-reference)
8. [Best Practices](#best-practices)

## Overview

The trading system consists of three main components:

1. **Signal Generation**: Analyzes politician trading disclosures and generates buy/sell/hold signals using ML and heuristic models
2. **Trading Execution**: Executes trades via Alpaca API based on generated signals
3. **Risk Management**: Ensures trades comply with risk limits and position sizing rules

### Architecture

```
Politician Disclosures → Signal Generator → Trading Strategy → Alpaca API → Execution
                              ↓                    ↓
                         Risk Analysis      Portfolio Management
```

## Setup

### 1. Install Dependencies

```bash
# Install the package with all dependencies
pip install -e .
```

### 2. Set Up Alpaca Account

1. Sign up for an Alpaca account at [https://alpaca.markets/](https://alpaca.markets/)
2. Get your API keys from the Alpaca dashboard
3. Start with paper trading (free) to test the system

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Alpaca Trading API
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_PAPER=true  # Set to false for live trading

# Trading Configuration
TRADING_AUTO_EXECUTE=false  # Enable automatic trade execution
TRADING_MIN_CONFIDENCE=0.65  # Minimum signal confidence (0.0-1.0)

# Risk Management
RISK_MAX_POSITION_SIZE_PCT=10.0  # Max position size as % of portfolio
RISK_MAX_PORTFOLIO_RISK_PCT=2.0  # Max risk per trade as % of portfolio
RISK_MAX_TOTAL_EXPOSURE_PCT=80.0  # Max total exposure as % of portfolio
RISK_MAX_POSITIONS=20  # Maximum number of open positions
```

### 4. Set Up Database Schema

Run the trading schema SQL to create necessary tables:

```bash
# Using Supabase CLI
supabase db push

# Or manually execute the SQL file
psql -h your-db-host -U your-user -d your-db -f supabase/sql/trading_schema.sql
```

## Signal Generation

### How Signals Are Generated

The signal generator analyzes politician trading disclosures using:

1. **Transaction Features**: Buy/sell ratios, transaction counts, net sentiment
2. **Politician Features**: Number of unique politicians, concentration metrics
3. **Party/Role Features**: Democratic vs Republican activity, Senator vs House activity
4. **Volume Features**: Transaction amounts, buy vs sell volume
5. **Temporal Features**: Recent activity, acceleration of trading
6. **Market Features**: Price changes, volatility, volume trends

### Generate Signals

```bash
# Generate signals from last 30 days of disclosures
politician-trading-signals generate --days 30

# With custom confidence threshold
politician-trading-signals generate --days 30 --min-confidence 0.7

# Without fetching market data (faster but less accurate)
politician-trading-signals generate --days 30 --no-market-data

# Output as JSON
politician-trading-signals generate --days 30 --output json
```

### Understanding Signals

Each signal includes:

- **Signal Type**: `BUY`, `SELL`, `STRONG_BUY`, `STRONG_SELL`, or `HOLD`
- **Confidence Score**: 0.0 to 1.0 (higher is better)
- **Signal Strength**: `VERY_WEAK`, `WEAK`, `MODERATE`, `STRONG`, `VERY_STRONG`
- **Price Targets**: Target price, stop loss, take profit
- **Supporting Data**: Number of politicians, buy/sell ratio, transaction volume

### View Active Signals

```bash
# List signals from last 7 days
politician-trading-signals list --days 7
```

## Trading Operations

### View Account Information

```bash
# Paper trading account (default)
politician-trading-trade account

# Live trading account
politician-trading-trade account --live
```

### View Open Positions

```bash
# Paper trading positions
politician-trading-trade positions

# Live trading positions
politician-trading-trade positions --live
```

### Execute Trades Based on Signals

```bash
# DRY RUN: Evaluate signals without executing (RECOMMENDED FIRST)
politician-trading-trade trade --days 7 --dry-run

# Paper trading with auto-execution
politician-trading-trade trade --days 7 --auto

# Live trading with auto-execution (requires confirmation)
politician-trading-trade trade --days 7 --auto --live
```

### Manual Order Placement

```bash
# Market buy order (paper trading)
politician-trading-trade order AAPL 10 --side buy

# Limit buy order (paper trading)
politician-trading-trade order AAPL 10 --side buy --order-type limit --limit-price 150.00

# Market sell order (live trading)
politician-trading-trade order AAPL 10 --side sell --live
```

### Monitor Positions

```bash
# Check positions and execute risk management rules
politician-trading-trade monitor

# For live trading
politician-trading-trade monitor --live
```

### View Portfolio Summary

```bash
# Comprehensive portfolio and risk metrics
politician-trading-trade portfolio

# For live trading
politician-trading-trade portfolio --live
```

## Risk Management

The risk manager enforces several important limits:

### Position Sizing

Calculates appropriate position sizes based on:
- Portfolio value
- Signal confidence
- Stop loss distance
- Risk tolerance

### Risk Limits

1. **Max Position Size**: Default 10% of portfolio per position
2. **Max Risk Per Trade**: Default 2% of portfolio at risk per trade
3. **Max Total Exposure**: Default 80% of portfolio invested
4. **Max Positions**: Default 20 open positions

### Automatic Position Closing

Positions are automatically flagged for closing when:
- Stop loss is hit
- Take profit target is reached
- Loss exceeds 20% (emergency stop)

## Paper Trading vs Live Trading

### Paper Trading (Recommended for Testing)

- Uses Alpaca's paper trading environment
- No real money at risk
- Same API and features as live trading
- Perfect for testing strategies
- Default mode for all commands

```bash
# All commands default to paper trading
politician-trading-trade account
politician-trading-trade positions
politician-trading-trade trade --days 7 --auto
```

### Live Trading (Real Money)

- Executes real trades with real money
- Requires `--live` flag
- Always asks for confirmation
- Use only after thorough testing

```bash
# Live trading requires explicit --live flag
politician-trading-trade account --live
politician-trading-trade positions --live
politician-trading-trade trade --days 7 --auto --live
```

## CLI Reference

### Signal Commands

```bash
# Generate signals
politician-trading-signals generate [OPTIONS]
  --days INTEGER              Look back period in days (default: 30)
  --min-confidence FLOAT      Minimum confidence threshold (default: 0.6)
  --fetch-market-data/--no-market-data  Fetch market data (default: true)
  --output [table|json]       Output format (default: table)

# List active signals
politician-trading-signals list [OPTIONS]
  --days INTEGER              Show signals from last N days (default: 7)
```

### Trading Commands

```bash
# View account
politician-trading-trade account [OPTIONS]
  --live                      Use live trading (default: paper)

# View positions
politician-trading-trade positions [OPTIONS]
  --live                      Use live trading (default: paper)

# Execute trades
politician-trading-trade trade [OPTIONS]
  --days INTEGER              Look back period for signals (default: 7)
  --live                      Use live trading (default: paper)
  --auto                      Auto-execute trades
  --dry-run                   Dry run without execution (default: true)

# Monitor positions
politician-trading-trade monitor [OPTIONS]
  --live                      Use live trading (default: paper)

# View portfolio
politician-trading-trade portfolio [OPTIONS]
  --live                      Use live trading (default: paper)

# Place manual order
politician-trading-trade order TICKER QUANTITY [OPTIONS]
  --side [buy|sell]           Buy or sell (required)
  --order-type [market|limit] Order type (default: market)
  --limit-price FLOAT         Limit price for limit orders
  --live                      Use live trading (default: paper)
```

## Best Practices

### 1. Start with Paper Trading

Always test your strategy thoroughly with paper trading before using real money:

```bash
# 1. Generate signals
politician-trading-signals generate --days 30

# 2. Run dry-run evaluation
politician-trading-trade trade --days 7 --dry-run

# 3. If satisfied, enable paper trading execution
politician-trading-trade trade --days 7 --auto

# 4. Monitor for several days/weeks
politician-trading-trade portfolio
politician-trading-trade positions
```

### 2. Set Conservative Risk Limits

Start with conservative risk parameters:

```bash
# In .env file
RISK_MAX_POSITION_SIZE_PCT=5.0   # Conservative: 5% per position
RISK_MAX_PORTFOLIO_RISK_PCT=1.0  # Conservative: 1% risk per trade
RISK_MAX_TOTAL_EXPOSURE_PCT=50.0 # Conservative: 50% max exposure
RISK_MAX_POSITIONS=10            # Conservative: max 10 positions
```

### 3. Use High Confidence Thresholds

Only trade high-confidence signals:

```bash
TRADING_MIN_CONFIDENCE=0.7  # Only trade signals with 70%+ confidence
```

### 4. Regular Monitoring

Monitor your portfolio regularly:

```bash
# Daily checks
politician-trading-trade portfolio --live
politician-trading-trade positions --live
politician-trading-trade monitor --live
```

### 5. Gradual Scaling

If moving to live trading:

1. Start with very small position sizes
2. Test with 1-2 signals only
3. Monitor closely for 1-2 weeks
4. Gradually increase size if performance is good

### 6. Keep Logs

The system logs all operations. Review logs regularly:

```bash
# Check logs for errors or issues
tail -f logs/trading.log
```

### 7. Diversification

- Don't concentrate in single sectors
- Respect the max positions limit
- Consider politician diversity (not just following 1-2 politicians)

### 8. Regular Signal Generation

Run signal generation regularly to get fresh signals:

```bash
# Set up a cron job to generate signals daily
0 9 * * * politician-trading-signals generate --days 30
```

### 9. Backtesting

Before live trading, backtest your strategy:

```python
from politician_trading.signals.signal_generator import SignalGenerator
from politician_trading.trading.strategy import TradingStrategy

# Load historical data
# Generate signals
# Simulate trades
# Calculate performance metrics
```

### 10. Emergency Procedures

Have a plan for emergencies:

```bash
# Close all positions immediately if needed
# (This would need to be implemented as a CLI command)

# Or manually via Alpaca dashboard
# https://app.alpaca.markets/
```

## Example Workflow

### Complete Trading Workflow

```bash
# Step 1: Collect politician trading data
politician-trading collect

# Step 2: Generate signals
politician-trading-signals generate --days 30 --min-confidence 0.7

# Step 3: Review signals
politician-trading-signals list

# Step 4: Evaluate trades (dry run)
politician-trading-trade trade --days 7 --dry-run

# Step 5: Check current portfolio
politician-trading-trade portfolio

# Step 6: Execute trades (paper trading)
politician-trading-trade trade --days 7 --auto

# Step 7: Monitor positions
politician-trading-trade positions
politician-trading-trade monitor

# Step 8: Review performance
politician-trading-trade portfolio
```

## Troubleshooting

### Common Issues

1. **"ALPACA_API_KEY and ALPACA_SECRET_KEY must be set"**
   - Check your `.env` file
   - Ensure keys are correctly copied from Alpaca dashboard

2. **"Signal confidence below threshold"**
   - Lower `TRADING_MIN_CONFIDENCE` in `.env`
   - Or generate more signals with `--min-confidence` option

3. **"Maximum positions limit reached"**
   - Close some existing positions
   - Increase `RISK_MAX_POSITIONS` in `.env`

4. **"Insufficient buying power"**
   - Positions are using too much capital
   - Close positions or add more capital

5. **"No signals generated meeting confidence threshold"**
   - Not enough politician trading activity
   - Lower confidence threshold
   - Increase look-back period (`--days`)

## Support and Resources

- **Alpaca Documentation**: [https://alpaca.markets/docs/](https://alpaca.markets/docs/)
- **Paper Trading**: [https://alpaca.markets/docs/trading/paper-trading/](https://alpaca.markets/docs/trading/paper-trading/)
- **API Limits**: [https://alpaca.markets/docs/api-references/trading-api/#rate-limit](https://alpaca.markets/docs/api-references/trading-api/#rate-limit)

## Disclaimer

**IMPORTANT**: This software is provided for educational and research purposes. Trading stocks involves substantial risk of loss. Past performance of politicians' trades does not guarantee future results. You are solely responsible for your trading decisions and any losses incurred. Always conduct thorough research and consider consulting with a financial advisor before trading.

The authors and contributors of this software are not responsible for any financial losses, damages, or legal issues arising from the use of this software.
