# Politician Trading Tracker - React + Supabase
# Comprehensive Makefile for project management

.PHONY: help setup dev build test clean deploy lint format install-frontend install-backend install-all \
	test-all test-python test-etl test-elixir test-client test-react test-edge test-deno \
	test-python-cov test-python-fast test-elixir-cov test-react-cov test-watch

# Default target
help:
	@echo "🚀 Politician Trading Tracker - React + Supabase"
	@echo ""
	@echo "Available commands:"
	@echo "  setup            - Initial project setup (install all dependencies)"
	@echo "  dev              - Start both React + Python servers concurrently"
	@echo "  dev-react        - Start React frontend only"
	@echo "  dev-python       - Run Python workflow once"
	@echo "  dev-python-watch - Run Python workflow continuously"
	@echo "  build            - Build for production"
	@echo "  clean            - Clean build artifacts and caches"
	@echo "  deploy           - Deploy to production"
	@echo "  deploy-functions - Deploy Supabase Edge Functions"
	@echo "  lint             - Run linting"
	@echo "  format           - Format code"
	@echo "  install-frontend - Install React dependencies"
	@echo "  install-backend  - Install Python dependencies"
	@echo "  install-all      - Install all dependencies"
	@echo ""
	@echo "Testing commands:"
	@echo "  test             - Run all tests (Python, Elixir, React, Edge Functions)"
	@echo "  test-python      - Run Python ETL service tests"
	@echo "  test-python-cov  - Run Python tests with coverage report"
	@echo "  test-python-fast - Run Python tests without coverage (faster)"
	@echo "  test-elixir      - Run Elixir Phoenix server tests"
	@echo "  test-elixir-cov  - Run Elixir tests with coverage"
	@echo "  test-react       - Run React client tests"
	@echo "  test-react-cov   - Run React tests with coverage"
	@echo "  test-react-watch - Run React tests in watch mode"
	@echo "  test-edge        - Run Supabase Edge Function tests (Deno)"
	@echo "  test-edge-watch  - Run Edge Function tests in watch mode"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup && make dev"

# Setup and Installation
setup: install-all
	@echo "✅ Project setup complete!"
	@echo "Run 'make dev' to start development servers"

install-all: install-backend install-frontend

install-backend:
	@echo "🐍 Installing Python dependencies..."
	uv sync --dev

install-frontend:
	@echo "⚛️ Installing React dependencies..."
	cd client && npm install

# Development - Run both frontend and backend concurrently
dev:
	@echo "🚀 Starting development servers..."
	@echo "React app: http://localhost:9090 (or next available port)"
	@echo "Python backend: Running workflow monitor"
	@echo ""
	@echo "Press Ctrl+C to stop all servers"
	@echo ""
	@trap 'kill 0' EXIT; \
	(cd client && npm run dev) & \
	(uv run python -c "from politician_trading.workflow import PoliticianTradingWorkflow; from politician_trading.config import WorkflowConfig; w = PoliticianTradingWorkflow(WorkflowConfig.default()); import asyncio; asyncio.run(w.run_full_collection())" 2>&1 | while read line; do echo "[Python] $$line"; done) & \
	wait

# Development - React only
dev-react:
	@echo "⚛️ Starting React development server only..."
	cd client && npm run dev

# Development - Python workflow once
dev-python:
	@echo "🐍 Running Python workflow once..."
	uv run python -c "from politician_trading.workflow import PoliticianTradingWorkflow; from politician_trading.config import WorkflowConfig; w = PoliticianTradingWorkflow(WorkflowConfig.default()); import asyncio; asyncio.run(w.run_full_collection())"

# Development - Python workflow continuous
dev-python-watch:
	@echo "🐍 Starting Python workflow in watch mode..."
	uv run python -m politician_trading.workflow

# Building
build: build-frontend build-backend
	@echo "✅ All builds completed!"

build-frontend:
	@echo "🔨 Building React app for production..."
	cd client && npm run build

build-backend:
	@echo "🔨 Building Python package..."
	uv build

# Testing - Run all tests
test: test-all
	@echo "✅ All tests completed!"

test-all: test-python test-elixir test-react test-edge
	@echo ""
	@echo "=========================================="
	@echo "✅ All test suites completed!"
	@echo "=========================================="

# Legacy aliases
test-backend: test-python
test-frontend: test-react

# ============================================
# Python Tests - All Python tests
# ============================================
test-python: test-python-server test-python-etl
	@echo "✅ All Python tests completed!"

# Server/Core Python tests (tests/ at root)
test-python-server:
	@echo "🐍 Running Python server/core tests..."
	uv run pytest tests/ -v

test-python-server-cov:
	@echo "🐍 Running Python server tests with coverage..."
	uv run pytest tests/ -v \
		--cov=server/politician_trading \
		--cov-report=term-missing \
		--cov-report=html:coverage-html

# ETL Service Python tests (python-etl-service/tests/)
test-python-etl:
	@echo "🐍 Running Python ETL service tests..."
	@if [ -f python-etl-service/.venv/bin/pytest ]; then \
		cd python-etl-service && .venv/bin/pytest tests/ -v; \
	elif [ -f python-etl-service/venv/bin/pytest ]; then \
		cd python-etl-service && venv/bin/pytest tests/ -v; \
	else \
		cd python-etl-service && python -m pytest tests/ -v; \
	fi

test-etl: test-python-etl

test-python-cov: test-python-server-cov
	@echo "✅ Python coverage report generated!"

test-python-fast:
	@echo "🐍 Running Python tests (fast mode)..."
	uv run pytest tests/ -q --tb=short
	@if [ -f python-etl-service/.venv/bin/pytest ]; then \
		cd python-etl-service && .venv/bin/pytest tests/ -q --tb=short; \
	elif [ -f python-etl-service/venv/bin/pytest ]; then \
		cd python-etl-service && venv/bin/pytest tests/ -q --tb=short; \
	fi

# ============================================
# Elixir Phoenix Server Tests
# ============================================
test-elixir:
	@echo "🧪 Running Elixir Phoenix server tests..."
	cd server && mix test

test-elixir-cov:
	@echo "🧪 Running Elixir tests with coverage..."
	cd server && mix test --cover

test-elixir-verbose:
	@echo "🧪 Running Elixir tests (verbose)..."
	cd server && mix test --trace

# ============================================
# React Client Tests (Vitest)
# ============================================
test-react:
	@echo "⚛️ Running React client tests..."
	cd client && npm run test

test-react-cov:
	@echo "⚛️ Running React tests with coverage..."
	cd client && npm run test:coverage

test-react-watch:
	@echo "⚛️ Running React tests in watch mode..."
	cd client && npm run test:watch

test-client: test-react

# ============================================
# Supabase Edge Function Tests (Deno)
# ============================================
test-edge:
	@echo "🦕 Running Supabase Edge Function tests (Deno)..."
	@if command -v deno >/dev/null 2>&1; then \
		cd supabase/functions && deno test --allow-all; \
	else \
		echo "⚠️  Deno not installed. Install with: curl -fsSL https://deno.land/install.sh | sh"; \
		echo "   Or: brew install deno"; \
		exit 1; \
	fi

test-edge-watch:
	@echo "🦕 Running Edge Function tests in watch mode..."
	@if command -v deno >/dev/null 2>&1; then \
		cd supabase/functions && deno test --allow-all --watch; \
	else \
		echo "⚠️  Deno not installed. Install with: curl -fsSL https://deno.land/install.sh | sh"; \
		exit 1; \
	fi

test-edge-verbose:
	@echo "🦕 Running Edge Function tests (verbose)..."
	@if command -v deno >/dev/null 2>&1; then \
		cd supabase/functions && deno test --allow-all --reporter=verbose; \
	else \
		echo "⚠️  Deno not installed."; \
		exit 1; \
	fi

test-deno: test-edge

# ============================================
# Individual Test Files
# ============================================
test-python-file:
	@echo "🐍 Running specific Python test file..."
	@echo "Usage: make test-python-file FILE=tests/test_example.py"
	cd python-etl-service && uv run pytest $(FILE) -v

test-elixir-file:
	@echo "🧪 Running specific Elixir test file..."
	@echo "Usage: make test-elixir-file FILE=test/server_test.exs"
	cd server && mix test $(FILE)

test-edge-file:
	@echo "🦕 Running specific Edge Function test..."
	@echo "Usage: make test-edge-file FILE=functions/orders/index.test.ts"
	@if command -v deno >/dev/null 2>&1; then \
		cd supabase && deno test --allow-all $(FILE); \
	else \
		echo "⚠️  Deno not installed."; \
		exit 1; \
	fi

# ============================================
# Test Summary
# ============================================
test-summary:
	@echo ""
	@echo "📊 Test Suite Summary"
	@echo "=========================================="
	@echo ""
	@echo "Python Server/Core (tests/):"
	@printf "  %d test files\n" $$(find tests -name "test_*.py" 2>/dev/null | wc -l)
	@printf "  %d test functions\n" $$(grep -r "def test_" tests/ 2>/dev/null | wc -l)
	@echo ""
	@echo "Python ETL Service (python-etl-service/tests/):"
	@printf "  %d test files\n" $$(find python-etl-service/tests -name "test_*.py" 2>/dev/null | wc -l)
	@printf "  %d test functions\n" $$(grep -r "def test_" python-etl-service/tests/ 2>/dev/null | wc -l)
	@echo ""
	@echo "Elixir Server (server/test/):"
	@printf "  %d test files\n" $$(find server/test -name "*_test.exs" 2>/dev/null | wc -l)
	@printf "  %d test cases\n" $$(grep -r 'test "' server/test/ 2>/dev/null | wc -l)
	@echo ""
	@echo "React Client (client/src/):"
	@printf "  %d test files\n" $$(find client/src \( -name "*.test.ts" -o -name "*.test.tsx" \) 2>/dev/null | wc -l)
	@printf "  %d test cases\n" $$(grep -rh "it(" client/src/ --include="*.test.ts" --include="*.test.tsx" 2>/dev/null | wc -l)
	@echo ""
	@echo "Edge Functions (supabase/functions/):"
	@printf "  %d test files\n" $$(find supabase/functions -name "*.test.ts" 2>/dev/null | wc -l)
	@printf "  %d Deno tests\n" $$(grep -r "Deno.test" supabase/functions/ 2>/dev/null | wc -l)
	@echo ""
	@echo "=========================================="
	@echo ""
	@echo "Total test files: $$(( \
		$$(find tests -name "test_*.py" 2>/dev/null | wc -l) + \
		$$(find python-etl-service/tests -name "test_*.py" 2>/dev/null | wc -l) + \
		$$(find server/test -name "*_test.exs" 2>/dev/null | wc -l) + \
		$$(find client/src \( -name "*.test.ts" -o -name "*.test.tsx" \) 2>/dev/null | wc -l) + \
		$$(find supabase/functions -name "*.test.ts" 2>/dev/null | wc -l) \
	))"

# Code Quality
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Linting Python code..."
	uv run ruff check server/ tests/ scripts/
	uv run mypy server/

lint-frontend:
	@echo "🔍 Linting React code..."
	cd client && npm run lint

format: format-backend format-frontend

format-backend:
	@echo "💅 Formatting Python code..."
	uv run black server/ tests/ scripts/
	uv run isort server/ tests/ scripts/

format-frontend:
	@echo "💅 Formatting React code..."
	cd client && npm run format

# Deployment
deploy: deploy-frontend deploy-backend
	@echo "✅ Deployment complete!"

deploy-frontend:
	@echo "🚀 Deploying React app..."
	@echo "Choose deployment method:"
	@echo "  1. Vercel:    ./scripts/deploy_vercel.sh"
	@echo "  2. Netlify:   ./scripts/deploy_netlify.sh"
	@echo "  3. Docker:    ./scripts/deploy_docker.sh"
	@echo "  4. Manual:    ./scripts/deploy_manual.sh"
	@echo ""
	@echo "Example: ./scripts/deploy_vercel.sh"

deploy-backend: deploy-functions

deploy-functions:
	@echo "🚀 Deploying Supabase Edge Functions to main project..."
	cd client && npx supabase functions deploy trading-signals --project-ref uljsqvwkomdrlnofmlad --no-verify-jwt
	cd client && npx supabase functions deploy portfolio --project-ref uljsqvwkomdrlnofmlad --no-verify-jwt
	cd client && npx supabase functions deploy politician-trading-collect --project-ref uljsqvwkomdrlnofmlad --no-verify-jwt
	cd client && npx supabase functions deploy collect-us-house --project-ref uljsqvwkomdrlnofmlad --no-verify-jwt
	@echo "✅ Edge Functions deployed to uljsqvwkomdrlnofmlad"

# Database
db-setup:
	@echo "🗄️ Setting up database..."
	@echo "Run this SQL in your Supabase dashboard:"
	@echo "https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql"
	@echo ""
	@cat supabase/sql/create_missing_tables.sql

db-seed:
	@echo "🌱 Seeding database..."
	uv run politician-trading-seed

# Cleaning
clean: clean-frontend clean-backend clean-builds

clean-frontend:
	@echo "🧹 Cleaning React build artifacts..."
	cd client && rm -rf dist node_modules/.vite

clean-backend:
	@echo "🧹 Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

clean-builds:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info/
	uv run pip cache purge

# Development shortcuts (aliases)
dev-frontend: dev-react

dev-backend: dev-python-watch

# Production shortcuts
prod-build: build
	@echo "📦 Production build ready in:"
	@echo "  - React: client/dist/"
	@echo "  - Python: dist/"

prod-deploy: deploy
	@echo "🌐 Production deployment complete!"

# Health checks
check: check-backend check-frontend

check-backend:
	@echo "🔍 Checking Python environment..."
	uv run python server/verify_debug_setup.py

check-frontend:
	@echo "🔍 Checking React environment..."
	cd client && npm run build

# Monitoring
monitor:
	@echo "🔍 Starting backend monitoring..."
	@./scripts/monitor_backend.sh

db-logs:
	@echo "📊 Recent Action Logs from Database:"
	@echo "====================================="
	@uv run python scripts/show_action_logs.py

# CI/CD
ci: lint test-all build
	@echo "✅ CI pipeline passed!"

ci-fast: lint-frontend test-python-fast test-react build-frontend
	@echo "✅ Fast CI pipeline passed!"

ci-python: lint-backend test-python-cov
	@echo "✅ Python CI passed!"

ci-react: lint-frontend test-react-cov build-frontend
	@echo "✅ React CI passed!"

ci-elixir: test-elixir-cov
	@echo "✅ Elixir CI passed!"

ci-edge: test-edge
	@echo "✅ Edge Functions CI passed!"

# Utility
update-deps:
	@echo "📦 Updating dependencies..."
	uv lock --upgrade
	cd client && npm update

version:
	@echo "📋 Version information:"
	@uv run python -c "import politician_trading; print('Python package:', politician_trading.__version__ if hasattr(politician_trading, '__version__') else 'unknown')"
	@echo "React app: Check client/package.json"

# Emergency cleanup
nuke: clean
	@echo "💥 Emergency cleanup - removing all dependencies..."
	rm -rf .venv/
	cd client && rm -rf node_modules/
	@echo "Run 'make setup' to reinstall everything"
