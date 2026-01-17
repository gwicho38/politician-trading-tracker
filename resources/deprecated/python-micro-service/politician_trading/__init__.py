"""
Politician Trading Tracker - Track and analyze politician financial disclosures.

This package provides tools for collecting, processing, and analyzing financial
disclosure data from politicians across multiple jurisdictions including the
US Congress, EU Parliament, UK Parliament, and US state governments.

Main Modules:
    workflow: Main orchestration for data collection pipelines
    scrapers: Web scrapers for various data sources
    database: Supabase database interface
    signals: Trading signal generation from disclosure patterns
    trading: Automated trading execution (paper and live)
    models: Data models (Politician, TradingDisclosure, etc.)
    config: Configuration management
    exceptions: Custom exception hierarchy
    types: TypedDict definitions for type safety

Quick Start:
    from politician_trading.workflow import run_politician_trading_collection

    # Run a full data collection
    results = await run_politician_trading_collection()

    # Generate trading signals
    from politician_trading.signals import SignalGenerator
    generator = SignalGenerator()
    signals = await generator.generate_signals()

Configuration:
    Set the following environment variables:
    - SUPABASE_URL: Your Supabase project URL
    - SUPABASE_ANON_KEY: Your Supabase anonymous/public key
    - SUPABASE_SERVICE_ROLE_KEY: (Optional) For admin operations

See Also:
    - docs/: Detailed documentation
    - CLAUDE.md: AI assistant instructions
    - README.md: Project overview
"""

__version__ = "1.0.0"
