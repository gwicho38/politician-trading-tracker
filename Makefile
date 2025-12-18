# Politician Trading Tracker - React + Supabase
# Comprehensive Makefile for project management

.PHONY: help setup dev build test clean deploy lint format install-frontend install-backend install-all

# Default target
help:
	@echo "🚀 Politician Trading Tracker - React + Supabase"
	@echo ""
	@echo "Available commands:"
	@echo "  setup          - Initial project setup (install all dependencies)"
	@echo "  dev            - Start development servers (React + Python)"
	@echo "  build          - Build for production"
	@echo "  test           - Run all tests"
	@echo "  clean          - Clean build artifacts and caches"
	@echo "  deploy         - Deploy to production"
	@echo "  lint           - Run linting"
	@echo "  format         - Format code"
	@echo "  install-frontend - Install React dependencies"
	@echo "  install-backend  - Install Python dependencies"
	@echo "  install-all     - Install all dependencies"
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
	cd submodules/capital-trades && npm install

# Development
dev:
	@echo "🚀 Starting development servers..."
	@echo "React app: http://localhost:9090 (or next available port)"
	@echo "Python API: Available via Supabase Edge Functions"
	@echo ""
	@echo "Starting React development server..."
	cd submodules/capital-trades && npm run dev

# Building
build: build-frontend build-backend
	@echo "✅ All builds completed!"

build-frontend:
	@echo "🔨 Building React app for production..."
	cd submodules/capital-trades && npm run build

build-backend:
	@echo "🔨 Building Python package..."
	uv build

# Testing
test: test-backend test-frontend
	@echo "✅ All tests passed!"

test-backend:
	@echo "🧪 Running Python tests..."
	uv run pytest tests/ -v --cov=src/politician_trading --cov-report=term-missing

test-frontend:
	@echo "🧪 Running React tests..."
	cd submodules/capital-trades && npm test -- --watchAll=false --passWithNoTests

# Code Quality
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Linting Python code..."
	uv run ruff check src/ tests/ scripts/
	uv run mypy src/

lint-frontend:
	@echo "🔍 Linting React code..."
	cd submodules/capital-trades && npm run lint

format: format-backend format-frontend

format-backend:
	@echo "💅 Formatting Python code..."
	uv run black src/ tests/ scripts/
	uv run isort src/ tests/ scripts/

format-frontend:
	@echo "💅 Formatting React code..."
	cd submodules/capital-trades && npm run format

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

deploy-backend:
	@echo "🚀 Deploying Supabase Edge Functions..."
	supabase functions deploy trading-signals --project-ref uljsqvwkomdrlnofmlad
	supabase functions deploy orders --project-ref uljsqvwkomdrlnofmlad
	supabase functions deploy portfolio --project-ref uljsqvwkomdrlnofmlad

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
	cd submodules/capital-trades && rm -rf dist node_modules/.vite

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

# Development shortcuts
dev-frontend:
	@echo "⚛️ Starting React development server..."
	cd submodules/capital-trades && npm run dev

dev-backend:
	@echo "🐍 Starting Python development server..."
	uv run python -m politician_trading.workflow

# Production shortcuts
prod-build: build
	@echo "📦 Production build ready in:"
	@echo "  - React: submodules/capital-trades/dist/"
	@echo "  - Python: dist/"

prod-deploy: deploy
	@echo "🌐 Production deployment complete!"

# Health checks
check: check-backend check-frontend

check-backend:
	@echo "🔍 Checking Python environment..."
	uv run python src/verify_debug_setup.py

check-frontend:
	@echo "🔍 Checking React environment..."
	cd submodules/capital-trades && npm run build

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
	cd submodules/capital-trades && npm update

version:
	@echo "📋 Version information:"
	@uv run python -c "import politician_trading; print('Python package:', politician_trading.__version__ if hasattr(politician_trading, '__version__') else 'unknown')"
	@echo "React app: Check submodules/capital-trades/package.json"

# Emergency cleanup
nuke: clean
	@echo "💥 Emergency cleanup - removing all dependencies..."
	rm -rf .venv/
	cd submodules/capital-trades && rm -rf node_modules/
	@echo "Run 'make setup' to reinstall everything"
