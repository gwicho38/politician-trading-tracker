# MCLI Workflows - Politician Trading Tracker

CLI workflows for managing the tripartite architecture (Client, Server, ETL Service).

## Workflow Structure

Workflows are organized to reflect the three main application components:

```
.mcli/workflows/
├── client.py           # React frontend deployment
├── server.py           # Phoenix server + lambda subcommands
├── etl.py              # ETL + congress/quiver/backfill/ml subcommands
├── jobs.py             # Cross-service job monitoring
├── supabase.py         # Database management
├── services.sh         # Fly.io deployment orchestration
└── workflows.lock.json # Command registry
```

## Quick Reference

### Client Commands

```bash
mcli run client deploy       # Deploy React app to Fly.io
mcli run client status       # Check deployment status
mcli run client logs         # Stream logs
mcli run client open         # Open in browser
```

### Server Commands

```bash
mcli run server deploy       # Deploy Phoenix server to Fly.io
mcli run server status       # Check server status
mcli run server logs         # Stream logs
mcli run server jobs         # View Phoenix job queue

# Lambda subcommands
mcli run server lambda validate       # Validate Lambda sandbox
mcli run server lambda test-security  # Test security rules
mcli run server lambda apply          # Apply Lambda changes
mcli run server lambda help           # Show Lambda help
mcli run server lambda examples       # Show usage examples
```

### ETL Commands

```bash
mcli run etl trigger --house    # Trigger House ETL job
mcli run etl trigger --senate   # Trigger Senate ETL job
mcli run etl trigger --update   # Update existing records
mcli run etl status             # View ETL status
mcli run etl status --watch     # Watch status in real-time

# Congress.gov subcommands
mcli run etl congress test             # Test Congress.gov API
mcli run etl congress list-members     # List congress members
mcli run etl congress member-info      # Get member details
mcli run etl congress search           # Search members
mcli run etl congress bills            # List member bills
mcli run etl congress votes            # Get voting record
mcli run etl congress test-member      # Test specific member

# QuiverQuant subcommands
mcli run etl quiver test               # Test QuiverQuant connection
mcli run etl quiver fetch              # Fetch trading data
mcli run etl quiver politician-trades  # Query trades by politician
mcli run etl quiver list-politicians   # List available politicians
mcli run etl quiver recent             # Get recent trades
mcli run etl quiver stats              # Show data statistics
mcli run etl quiver sync               # Sync to database
mcli run etl quiver compare            # Compare with local data
mcli run etl quiver export             # Export to file
mcli run etl quiver status             # Check API status

# Backfill subcommands
mcli run etl backfill repair           # Fix data quality issues
mcli run etl backfill validate         # Validate data integrity
mcli run etl backfill analyze          # Analyze data quality

# ML subcommands
mcli run etl ml train                  # Train ML models
mcli run etl ml status                 # Check training status
mcli run etl ml predict                # Run predictions
mcli run etl ml test                   # Test model performance
mcli run etl ml export                 # Export model artifacts
mcli run etl ml config                 # Show ML configuration
```

### Cross-Service Commands

```bash
# Job monitoring
mcli run jobs status                   # View all job statuses

# Database management
mcli run supabase tables               # List database tables
mcli run supabase schema               # Show table schemas
mcli run supabase query                # Execute SQL queries

# Deployment orchestration
mcli run services deploy-all           # Deploy all services
mcli run services status               # Check all statuses
```

## Architecture Alignment

| Workflow | Component | Technology | Purpose |
|----------|-----------|------------|---------|
| `client.py` | Client | React/Vite | Web frontend |
| `server.py` | Server | Phoenix/Elixir | API server, jobs, lambda |
| `etl.py` | ETL Service | Python | Data ingestion, ML |
| `jobs.py` | All | - | Unified job monitoring |
| `supabase.py` | Database | PostgreSQL | Schema, queries |
| `services.sh` | Deployment | Fly.io | Multi-service deploy |

## Adding New Commands

### Python Workflow

```python
import click

@click.group()
def my_workflow():
    """My workflow description."""
    pass

@my_workflow.command()
def my_command():
    """Command description."""
    click.echo("Running command...")

# Entry point for mcli
app = my_workflow
```

### Shell Workflow

```bash
#!/bin/zsh
# Description: My shell workflow

case "$1" in
    my-command)
        echo "Running command..."
        ;;
    *)
        echo "Usage: mcli run my-workflow [my-command]"
        ;;
esac
```

## Documentation

- [MCLI Documentation](https://github.com/gwicho38/mcli)
- [Project README](../../README.md)
- [Architecture Guide](../../docs/CODEBASE_ARCHITECTURE.md)

---

*Last updated: January 2026*
