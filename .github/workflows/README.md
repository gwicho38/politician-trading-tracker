# CI/CD Workflows

## Overview

This directory contains GitHub Actions workflows for automated testing, quality checks, and deployment.

## Workflows

### CI/CD Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

**Jobs:**

#### 1. **Test Job** (Matrix: Ubuntu/macOS × Python 3.9-3.12)
Runs core quality checks and unit tests across multiple platforms and Python versions.

**Steps:**
- Lint with `ruff`
- Format check with `black`
- Type check with `mypy`
- Run unit tests with coverage
- Run pipeline tests
- Upload coverage to Codecov

**Status:** Required for merge

---

#### 2. **Integration Tests Job**
Runs all integration tests after unit tests pass.

**Tests:**
- Database integration tests
- API client integration tests
- Scraper integration tests
- Other integration tests in `tests/integration/`

**Environment Variables:**
- `ALPACA_PAPER_API_KEY` - Mock API key for testing
- `ALPACA_PAPER_SECRET_KEY` - Mock secret key for testing

**Status:** Required for merge

---

#### 3. **E2E Tests Job** 🎯
Runs comprehensive end-to-end trading flow test.

**Test Scenario:**
Nancy Pelosi sells AAPL → Signal generated → Added to cart → Executed via Alpaca → Appears in portfolio

**What's Tested:**
- ✅ Politician trade data seeding
- ✅ ML-based signal generation
- ✅ Paywall access control (Pro vs Free tier)
- ✅ Shopping cart operations
- ✅ Alpaca API integration (mocked)
- ✅ Portfolio position tracking
- ✅ Complete data traceability

**Test File:** `tests/integration/test_e2e_trading_flow.py`

**Environment Variables:**
- `ALPACA_PAPER_API_KEY` - Mock API key for testing
- `ALPACA_PAPER_SECRET_KEY` - Mock secret key for testing

**Artifacts:**
- `e2e-test-results` - JUnit XML test report

**Status:** Required for merge

---

#### 4. **Build Job**
Builds the Python package after all tests pass.

**Dependencies:** Requires `test`, `integration-tests`, and `e2e-tests` to complete successfully

**Steps:**
- Build Python package using `build`
- Upload build artifacts

**Artifacts:**
- `dist/` - Built package distributions (wheel and sdist)

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────┐
│                 Push to main/develop                │
│                  or Pull Request                    │
└─────────────────┬───────────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────────┐
│  Test Job (Matrix: Ubuntu/macOS × Python 3.9-3.12) │
│  • Lint (ruff)                                      │
│  • Format (black)                                   │
│  • Type check (mypy)                                │
│  • Unit tests + coverage                            │
│  • Pipeline tests                                   │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         v                 v
┌──────────────────┐  ┌─────────────────────┐
│ Integration Tests│  │  E2E Tests          │
│ • Database tests │  │  • Trading flow     │
│ • API tests      │  │  • Paywall          │
│ • Scraper tests  │  │  • Cart → Alpaca    │
└────────┬─────────┘  └──────────┬──────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     v
         ┌───────────────────────┐
         │     Build Job         │
         │  • Package build      │
         │  • Upload artifacts   │
         └───────────────────────┘
```

## Status Badges

Add these badges to your README.md:

### CI/CD Status
```markdown
![CI/CD Pipeline](https://github.com/gwicho38/politician-trading-tracker/actions/workflows/ci.yml/badge.svg)
```

### Individual Job Status
```markdown
![Tests](https://github.com/gwicho38/politician-trading-tracker/actions/workflows/ci.yml/badge.svg?job=test)
![E2E Tests](https://github.com/gwicho38/politician-trading-tracker/actions/workflows/ci.yml/badge.svg?job=e2e-tests)
![Build](https://github.com/gwicho38/politician-trading-tracker/actions/workflows/ci.yml/badge.svg?job=build)
```

## Running Tests Locally

### All Tests
```bash
# Run everything (unit, pipeline, integration, E2E)
pytest

# With coverage
pytest --cov=src/politician_trading --cov-report=html
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Pipeline Tests
```bash
pytest tests/pipeline/ -v
```

### Integration Tests
```bash
# Set mock environment variables
export ALPACA_PAPER_API_KEY="PKTEST1234567890"
export ALPACA_PAPER_SECRET_KEY="test_secret_key_12345"

# Run integration tests
pytest tests/integration/ -v -s
```

### E2E Tests Only
```bash
# Set mock environment variables
export ALPACA_PAPER_API_KEY="PKTEST1234567890"
export ALPACA_PAPER_SECRET_KEY="test_secret_key_12345"

# Run E2E test with verbose output
pytest tests/integration/test_e2e_trading_flow.py -v -s
```

## Environment Variables

### Required for Local Testing

The following environment variables are automatically set in GitHub Actions but need to be set locally:

```bash
# Alpaca API Keys (mock values for testing - not real keys)
export ALPACA_PAPER_API_KEY="PKTEST1234567890"
export ALPACA_PAPER_SECRET_KEY="test_secret_key_12345"
```

**Note:** These are **mock values** used for testing. The E2E test uses mocked Alpaca API responses, so real API keys are not required.

### Optional for Real Integration Testing

If you want to test against real Alpaca paper trading (not recommended for CI):

```bash
# Real Alpaca Paper Trading Keys
export ALPACA_PAPER_API_KEY="PK..."  # Your real paper trading key
export ALPACA_PAPER_SECRET_KEY="..."  # Your real paper trading secret
```

## Debugging Failed Workflows

### View E2E Test Output
1. Go to Actions tab in GitHub
2. Click on the failed workflow run
3. Click on "E2E Tests" job
4. Expand "Run E2E trading flow test" step
5. Review detailed console output with ✅/❌ indicators

### Download Test Reports
1. Scroll to bottom of workflow run page
2. Download "e2e-test-results" artifact
3. Open `e2e-test-report.xml` in JUnit viewer

### Common Issues

#### Import Errors
```
ModuleNotFoundError: No module named 'politician_trading'
```

**Solution:** Ensure package is installed with `-e` flag:
```bash
pip install -e ".[dev]"
```

#### Streamlit Warnings
```
WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext!
```

**Solution:** These warnings are expected when running Streamlit code in tests. They can be safely ignored.

#### Mock API Connection Failed
```
AssertionError: Alpaca connection failed
```

**Solution:** Check that mock environment variables are set correctly in workflow.

## Adding New Tests to CI/CD

### Add Unit Test
1. Create test file in `tests/unit/`
2. Follow naming convention: `test_*.py`
3. Tests will automatically run in "Test Job"

### Add Integration Test
1. Create test file in `tests/integration/`
2. Add any required environment variables to `integration-tests` job
3. Tests will automatically run in "Integration Tests Job"

### Add E2E Test Scenario
1. Add new test method to `test_e2e_trading_flow.py`
2. Update `tests/integration/README_E2E_TEST.md` with new scenario
3. Tests will automatically run in "E2E Tests Job"

## Performance Benchmarks

| Job | Duration (avg) | Parallelization |
|-----|---------------|-----------------|
| Test (single matrix) | ~3-5 min | 8 parallel jobs |
| Integration Tests | ~2-3 min | No |
| E2E Tests | ~5-10 sec | No |
| Build | ~1-2 min | No |
| **Total Pipeline** | **~5-8 min** | 8 parallel + 3 sequential |

## Coverage Requirements

- **Unit Tests:** Target 80% coverage
- **Integration Tests:** Must pass (no coverage requirement)
- **E2E Tests:** Must pass (validates end-to-end flow)

## Merge Requirements

All of the following must pass before merge:
- ✅ All matrix test jobs (8 jobs: 2 OS × 4 Python versions)
- ✅ Integration tests
- ✅ E2E tests
- ✅ Build succeeds

## Related Documentation

- [E2E Test Documentation](../../tests/integration/README_E2E_TEST.md)
- [Test Fixtures](../../tests/fixtures/test_data.py)
- [Contributing Guidelines](../../CONTRIBUTING.md)

## Maintenance

### Updating Python Versions
Edit the matrix in `ci.yml`:
```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11', '3.12', '3.13']  # Add new versions here
```

### Updating Dependencies
Dependencies are installed via:
```bash
pip install -e ".[dev]"
```

To update dependencies, modify `pyproject.toml` under `[project.optional-dependencies]`.

### Adding New Jobs
Add new job after `e2e-tests`:
```yaml
my-new-job:
  name: My New Job
  runs-on: ubuntu-latest
  needs: test
  steps:
    - uses: actions/checkout@v4
    - # ... your steps
```

Then update build dependencies:
```yaml
build:
  needs: [test, integration-tests, e2e-tests, my-new-job]
```
