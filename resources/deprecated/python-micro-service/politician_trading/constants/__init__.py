"""
Centralized constants for the politician trading tracker application.

This module exports all constants to provide a single source of truth for
hardcoded values throughout the codebase.

Usage:
    from politician_trading.constants import Tables, Columns, Status, EnvKeys

    # Use constants instead of hardcoded strings
    result = db.table(Tables.POLITICIANS).select("*")
"""

from .database import Columns, Tables
from .env_keys import EnvDefaults, EnvKeys
from .statuses import (
    ActionType,
    DataSourceType,
    JobStatus,
    OrderStatus,
    ParseStatus,
    PoliticianRole,
    ProcessingStatus,
    SignalType,
    TradingMode,
    TransactionType,
)
from .storage import SourceTypes, StorageBuckets, StoragePaths
from .urls import ApiUrls, ConfigDefaults, WebUrls

__all__ = [
    # Database
    "Tables",
    "Columns",
    # Statuses
    "JobStatus",
    "OrderStatus",
    "ParseStatus",
    "ProcessingStatus",
    "TransactionType",
    "SignalType",
    "ActionType",
    "TradingMode",
    "PoliticianRole",
    "DataSourceType",
    # Environment
    "EnvKeys",
    "EnvDefaults",
    # Storage
    "StorageBuckets",
    "StoragePaths",
    "SourceTypes",
    # URLs and Config
    "ApiUrls",
    "WebUrls",
    "ConfigDefaults",
]
