# Test Structure Overview

This repository follows a centralized test directory structure where all tests are organized within dedicated `tests/` directories, separated from the main codebase.

## Directory Structure

```
tests/
├── client/                          # React/TypeScript tests
│   ├── components/                  # Component tests
│   │   ├── ErrorBoundary.test.tsx
│   │   ├── WalletProvider.test.tsx
│   │   ├── SignalLineage.test.tsx
│   │   └── AlpacaConnectionStatus.test.tsx
│   ├── contexts/                    # Context tests
│   │   ├── AlertContext.test.tsx
│   │   └── CartContext.test.tsx
│   ├── hooks/                       # Custom hook tests
│   │   ├── useAlpacaData.test.ts
│   │   └── useSupabaseData.test.tsx
│   └── lib/                         # Utility library tests
│       └── fetchWithRetry.test.ts
├── supabase/                        # Edge Function tests
│   ├── trading-signals.test.ts
│   ├── sync-data.test.ts
│   ├── alpaca-account.test.ts
│   └── orders.test.ts
├── integration/                     # Cross-service integration tests
│   └── test_database_aggregations.py
├── unit/                           # Python unit tests
│   ├── test_signal_generator.py
│   ├── test_alpaca_client.py
│   └── ...
├── pipeline/                       # ETL pipeline tests
│   └── test_pipeline_e2e.py
├── fixtures/                       # Test data fixtures
│   └── test_data.py
└── __init__.py                     # Python test package

python-etl-service/tests/           # ETL service specific tests
├── test_base_etl.py
├── test_house_etl_service.py
├── test_senate_etl_service.py
└── ...
```

## Test Frameworks

| Component | Framework | Runner |
|-----------|-----------|--------|
| **React Client** | Vitest + React Testing Library | `cd client && npm run test` |
| **Python ETL** | pytest + pytest-asyncio | `cd python-etl-service && python -m pytest tests/` |
| **Supabase Functions** | Deno test | `deno test tests/supabase/*.test.ts` |

## Running Tests

### All Tests
```bash
# React tests
cd client && npm run test

# Python tests (with virtual env)
cd python-etl-service && source venv/bin/activate && python -m pytest

# Supabase tests
deno test tests/supabase/*.test.ts
```

### Specific Test Categories
```bash
# React component tests
cd client && npm run test tests/client/components/

# Python unit tests
cd python-etl-service && python -m pytest tests/unit/

# Integration tests
cd python-etl-service && python -m pytest tests/integration/
```

## Test Organization Principles

1. **Separation of Concerns**: Tests are completely separated from source code
2. **Framework-Specific Directories**: Each test framework has its own directory structure
3. **Clear Naming**: Test files follow `{component}.test.{ext}` naming convention
4. **Comprehensive Coverage**: All functions and components have corresponding tests
5. **Mock Management**: Proper mocking for external dependencies and APIs

## Coverage Goals

- **React Components**: 80%+ coverage for UI logic
- **Custom Hooks**: 100% coverage for business logic
- **Python ETL**: 90%+ coverage for data processing
- **Supabase Functions**: 100% coverage for API endpoints