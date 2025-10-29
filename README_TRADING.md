# Trading Features - Quick Start

This document provides a quick overview of the new automated trading features. For detailed documentation, see [docs/TRADING_GUIDE.md](docs/TRADING_GUIDE.md).

## Overview

The Politician Trading Tracker now includes powerful automated trading capabilities:

- **AI-Powered Signal Generation**: ML-based buy/sell/hold recommendations based on politician trading activity
- **Alpaca API Integration**: Execute trades via Alpaca's brokerage API
- **Paper Trading**: Test strategies risk-free with simulated trading
- **Live Trading**: Execute real trades with comprehensive risk management
- **Risk Management**: Built-in position sizing, exposure limits, and stop losses

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Set Up Alpaca Account

1. Sign up at [https://alpaca.markets/](https://alpaca.markets/)
2. Get your API keys
3. Add keys to `.env`:

```bash
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_PAPER=true
```

### 3. Set Up Database

```bash
# Apply trading schema
supabase db push
# Or manually:
psql -h your-host -U user -d db -f supabase/sql/trading_schema.sql
```

### 4. Generate Trading Signals

```bash
# Collect politician trading data
politician-trading collect

# Generate AI-powered trading signals
politician-trading-signals generate --days 30
```

### 5. Execute Trades (Paper Trading)

```bash
# Dry run (no execution)
politician-trading-trade trade --days 7 --dry-run

# Execute paper trades
politician-trading-trade trade --days 7 --auto
```

### 6. Monitor Your Portfolio

```bash
# View portfolio summary
politician-trading-trade portfolio

# View open positions
politician-trading-trade positions

# Monitor for risk management
politician-trading-trade monitor
```

## Key Features

### Signal Generation

- **Multi-Factor Analysis**: Analyzes politician counts, buy/sell ratios, transaction volumes, party affiliations, and more
- **ML Models**: Uses Gradient Boosting and heuristic rules to generate signals
- **Confidence Scores**: Each signal includes a confidence score (0-100%)
- **Price Targets**: Automatic calculation of target prices, stop losses, and take profits

### Trading Execution

- **Alpaca Integration**: Direct integration with Alpaca API for reliable execution
- **Multiple Order Types**: Market, limit, stop, stop-limit, and trailing stop orders
- **Paper & Live Trading**: Test strategies risk-free before deploying real capital
- **Auto-Execution**: Optional automatic trade execution based on signals

### Risk Management

- **Position Sizing**: Automatically calculates position sizes based on portfolio and risk tolerance
- **Exposure Limits**: Enforces maximum position sizes and total portfolio exposure
- **Stop Losses**: Automatic stop loss placement and monitoring
- **Portfolio Monitoring**: Continuous monitoring of positions against risk parameters

## CLI Commands

### Signal Generation

```bash
# Generate signals
politician-trading-signals generate --days 30

# List active signals
politician-trading-signals list
```

### Trading Operations

```bash
# View account
politician-trading-trade account

# View positions
politician-trading-trade positions

# Execute trades
politician-trading-trade trade --days 7 --auto

# Monitor positions
politician-trading-trade monitor

# Portfolio summary
politician-trading-trade portfolio

# Manual order
politician-trading-trade order AAPL 10 --side buy
```

### Add `--live` flag for live trading (paper trading is default)

```bash
politician-trading-trade account --live
politician-trading-trade positions --live
```

## Example Workflow

```bash
# 1. Collect latest politician trading data
politician-trading collect

# 2. Generate trading signals
politician-trading-signals generate --days 30 --min-confidence 0.7

# 3. Review signals
politician-trading-signals list

# 4. Dry run to see what trades would be made
politician-trading-trade trade --days 7 --dry-run

# 5. Execute trades in paper account
politician-trading-trade trade --days 7 --auto

# 6. Monitor your portfolio
politician-trading-trade portfolio
politician-trading-trade positions
```

## Configuration

Key configuration options in `.env`:

```bash
# Alpaca API
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true

# Trading
TRADING_AUTO_EXECUTE=false
TRADING_MIN_CONFIDENCE=0.65

# Risk Management
RISK_MAX_POSITION_SIZE_PCT=10.0
RISK_MAX_PORTFOLIO_RISK_PCT=2.0
RISK_MAX_TOTAL_EXPOSURE_PCT=80.0
RISK_MAX_POSITIONS=20
```

## Safety Features

1. **Paper Trading Default**: All commands default to paper trading
2. **Dry Run Mode**: Test trade execution without actually placing orders
3. **Confirmation Required**: Live trading always asks for confirmation
4. **Risk Limits**: Enforced position sizing and exposure limits
5. **Stop Losses**: Automatic stop loss placement and monitoring

## Paper Trading vs Live Trading

### Paper Trading (Default)

- No real money at risk
- Perfect for testing strategies
- Same API as live trading
- Unlimited capital to experiment

```bash
politician-trading-trade trade --days 7 --auto
```

### Live Trading (Real Money)

- Requires `--live` flag
- Always asks for confirmation
- Use only after thorough testing

```bash
politician-trading-trade trade --days 7 --auto --live
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Politician Trading Tracker                  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                     │
│  • Web scrapers (Congress, EU, UK, State legislatures)      │
│  • Disclosure parsing and normalization                      │
│  • Storage in Supabase                                       │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Signal Generation Layer                   │
│  • Feature engineering (40+ features)                        │
│  • ML models (Gradient Boosting, Random Forest)             │
│  • Heuristic rules (buy/sell ratios, bipartisan agreement)  │
│  • Confidence scoring                                        │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Trading Strategy Layer                    │
│  • Signal evaluation and filtering                           │
│  • Risk management and position sizing                       │
│  • Portfolio management                                      │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
│  • Alpaca API integration                                    │
│  • Order placement and monitoring                            │
│  • Position tracking                                         │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

New tables for trading:

- **trading_signals**: Generated buy/sell/hold signals
- **trading_orders**: Order execution records
- **portfolios**: Portfolio tracking and metrics
- **positions**: Individual position records

## API Integration

The system integrates with:

- **Alpaca Trading API**: For order execution and account management
- **Alpaca Market Data API**: For real-time and historical price data
- **Yahoo Finance**: Fallback for market data

## Performance Metrics

Track key metrics:

- **Total Return**: Overall portfolio return
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Exposure**: Percentage of portfolio invested

## Best Practices

1. **Start with Paper Trading**: Always test with paper trading first
2. **Use High Confidence Thresholds**: Only trade signals with >70% confidence
3. **Set Conservative Risk Limits**: Start with 5% max position size, 1% max risk
4. **Monitor Regularly**: Check portfolio daily
5. **Diversify**: Don't concentrate in single sectors or politicians
6. **Regular Signal Updates**: Generate new signals daily
7. **Gradual Scaling**: Start small and scale up slowly

## Limitations & Disclaimers

**IMPORTANT DISCLAIMERS:**

1. **Past Performance ≠ Future Results**: Historical politician trades don't guarantee future returns
2. **Risk of Loss**: Trading involves substantial risk of loss
3. **Not Financial Advice**: This software is for educational purposes only
4. **Legal Compliance**: Ensure compliance with all applicable securities laws
5. **No Guarantees**: No guarantee of profitability or accuracy
6. **User Responsibility**: You are solely responsible for your trading decisions

## Support

For detailed documentation, see:

- [Trading Guide](docs/TRADING_GUIDE.md): Comprehensive trading documentation
- [Deployment Guide](docs/DEPLOYMENT.md): Deployment instructions
- [API Documentation](https://alpaca.markets/docs/): Alpaca API reference

## License

MIT License - see [LICENSE](LICENSE) file

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Disclaimer

**Trading stocks involves substantial risk of loss. This software is provided for educational and research purposes only. The authors and contributors are not responsible for any financial losses, damages, or legal issues arising from the use of this software. Always conduct thorough research and consider consulting with a financial advisor before trading.**
