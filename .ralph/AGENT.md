# Ralph Agent Configuration

## Autonomous Operation Mode

Ralph operates as a **continuous improvement agent**. Unlike task-driven development, Ralph:
- Analyzes the codebase to discover issues
- Reasons about improvement priorities
- Self-assigns tasks based on impact
- Maintains a perpetual backlog of improvements

## Analysis Commands

### Initial Analysis (Run at start of each session)
```bash
# Check test status
cd python-etl-service && uv run pytest --tb=short -q
cd ../client && npm test -- --reporter=dot
cd ../server && mix test --max-failures=5

# Check linting status
cd python-etl-service && ruff check app/ --statistics
cd ../client && npm run lint -- --format=compact

# Check for type issues
cd python-etl-service && uv run mypy app/ --ignore-missing-imports 2>&1 | head -20
```

### Security Analysis
```bash
# Check for outdated dependencies with vulnerabilities
cd python-etl-service && uv pip list --outdated
cd ../client && npm audit --audit-level=moderate

# Scan for secrets accidentally committed
grep -rn "password\|secret\|api_key\|token" --include="*.py" --include="*.ts" --include="*.env*" . 2>/dev/null | grep -v node_modules | grep -v ".pyc" | head -20
```

### Code Quality Analysis
```bash
# Find complex functions (cyclomatic complexity)
cd python-etl-service && ruff check app/ --select=C901

# Find duplicate code patterns
grep -rn "def " python-etl-service/app/ | wc -l  # Count functions
grep -rn "async def " python-etl-service/app/ | wc -l  # Count async functions
```

## Build & Test Instructions

### Python ETL Service
```bash
cd python-etl-service
uv sync                    # Install dependencies
uv run pytest              # Run tests
uv run pytest -v --cov     # Tests with coverage
ruff check app/            # Linting
ruff format app/           # Auto-format
```

### React Client
```bash
cd client
npm install                # Install dependencies
npm test                   # Run Vitest tests
npm run lint               # ESLint
npm run build              # Production build
```

### Elixir Server
```bash
cd server
mix deps.get               # Install dependencies
mix test                   # Run ExUnit tests
mix format                 # Format code
mix phx.server             # Start server
```

## Reasoning Framework

When deciding what to work on, use this priority matrix:

| Impact | Effort | Priority |
|--------|--------|----------|
| High   | Low    | 🔴 Do First |
| High   | High   | 🟡 Plan Carefully |
| Low    | Low    | 🟢 Quick Win |
| Low    | High   | ⚪ Deprioritize |

### Impact Factors
- **Security**: Vulnerabilities = highest impact
- **Stability**: Production bugs > dev-only issues
- **Testing**: Critical paths > edge cases
- **Typing**: Public APIs > internal code

### Effort Estimation
- **1 loop**: Single file, < 50 lines changed
- **2-3 loops**: Multiple files, < 200 lines
- **4+ loops**: Architectural change, break into smaller tasks

## Commit Guidelines

```bash
# Conventional commits
git commit -m "fix(etl): add input validation to transaction parser"
git commit -m "feat(client): add loading states to trade table"
git commit -m "test(server): add edge case tests for auth flow"
git commit -m "refactor(etl): extract retry logic into utility"
git commit -m "security(api): add rate limiting to public endpoints"
```

## Environment Setup

### Prerequisites
- Python 3.11+ with UV
- Node.js 18+ with npm
- Elixir 1.14+
- Supabase CLI (for local development)

### Environment Variables
See `.env.example` files in each service directory.

## Notes
- Always run tests before committing
- Update fix_plan.md after each task
- Discover new issues while working - add them to backlog
- The backlog should never be empty
