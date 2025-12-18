# Politician Trading Tracker - React + Supabase
# Comprehensive Makefile for project management

.PHONY: help setup dev build test clean deploy lint format install-frontend install-backend install-all

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
	@echo "  test             - Run all tests"
	@echo "  clean            - Clean build artifacts and caches"
	@echo "  deploy           - Deploy to production"
	@echo "  deploy-functions - Deploy Supabase Edge Functions"
	@echo "  lint             - Run linting"
	@echo "  format           - Format code"
	@echo "  install-frontend - Install React dependencies"
	@echo "  install-backend  - Install Python dependencies"
	@echo "  install-all      - Install all dependencies"
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

# Testing
test: test-backend test-frontend
	@echo "✅ All tests passed!"

test-backend:
	@echo "🧪 Running Python tests..."
	uv run pytest tests/ -v --cov=server/politician_trading --cov-report=term-missing

test-frontend:
	@echo "🧪 Running React tests..."
	cd client && npm test -- --watchAll=false --passWithNoTests

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
ci: lint test build
	@echo "✅ CI pipeline passed!"

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
