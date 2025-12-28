# Politician Trading Tracker Server

A minimal Phoenix API server that connects to Supabase PostgreSQL for tracking politician stock trading disclosures.

## Quick Start

```bash
# Install dependencies
mix deps.get

# Start the server
mix phx.server

# Or start with interactive shell
iex -S mix phx.server
```

The server runs at http://localhost:4000

## Health Check

```bash
# Liveness check (server running)
curl http://localhost:4000/health

# Readiness check (database connected)
curl http://localhost:4000/health/ready
```

## Database Connection

The server connects to Supabase PostgreSQL via the transaction pooler.

**Connection String:**
```
postgresql://postgres.uljsqvwkomdrlnofmlad:***@aws-1-eu-north-1.pooler.supabase.com:6543/postgres
```

### Query the Database (IEx)

```elixir
# Check health
Server.health_check()

# List tables
Server.Repo.query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

# Query trades
Server.Repo.query("SELECT * FROM politician_trades LIMIT 5")
```

### Available Tables

| Table | Description |
|-------|-------------|
| `politicians` | Politician profiles |
| `politician_trades` | Trade disclosures |
| `trading_disclosures` | Official disclosure documents |
| `trading_orders` | User trading orders |
| `trading_signals` | Generated trading signals |
| `portfolios` | User portfolios |
| `sync_logs` | Data sync history |
| `scheduled_jobs` | Background job registry |

## Project Structure

```
server/
├── config/
│   ├── config.exs     # Base configuration
│   ├── dev.exs        # Development (pooler connection)
│   ├── test.exs       # Test (local PostgreSQL)
│   └── runtime.exs    # Production (environment variables)
├── lib/
│   ├── server/
│   │   ├── application.ex  # OTP Application
│   │   └── repo.ex         # Ecto Repository
│   ├── server.ex           # Main module
│   └── server_web/
│       ├── endpoint.ex     # HTTP Endpoint
│       ├── router.ex       # Routes
│       └── controllers/
│           ├── error_json.ex
│           └── health_controller.ex
└── priv/
    └── repo/
        └── migrations/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/ready` | Database connectivity check |
| * | `/api/*` | API routes (to be added) |

## Configuration

### Development

Uses hardcoded credentials in `config/dev.exs`. Override with:

```bash
DATABASE_PASSWORD=xxx mix phx.server
```

### Production

Required environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_PASSWORD` | Supabase database password | (required) |
| `SECRET_KEY_BASE` | Phoenix secret key | (required) |
| `DATABASE_HOST` | Database host | aws-1-eu-north-1.pooler.supabase.com |
| `DATABASE_PORT` | Database port | 6543 |
| `DATABASE_USER` | Database user | postgres.uljsqvwkomdrlnofmlad |
| `PHX_HOST` | Application host | localhost |
| `PORT` | HTTP port | 4000 |

Generate a secret key:
```bash
mix phx.gen.secret
```

## Next Steps

To add schemas:

```bash
# Generate a schema (without Phoenix generators for minimal setup)
# Create lib/server/schemas/politician.ex manually

# Run migrations
mix ecto.migrate
```

Example schema:
```elixir
defmodule Server.Schemas.Politician do
  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: true}
  schema "politicians" do
    field :name, :string
    field :party, :string
    field :state, :string
    field :chamber, :string
    timestamps()
  end
end
```

## Development

```bash
# Compile
mix compile

# Run tests
mix test

# Format code
mix format

# Start IEx
iex -S mix
```
