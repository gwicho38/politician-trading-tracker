# ADR-002: Supabase as Backend Database

## Status
Accepted

## Context

The project needs a database to store:
- Politician records (~1000s)
- Trading disclosures (~100,000s)
- Job execution history
- User sessions and preferences (for Streamlit UI)
- Trading signals and orders

Options considered:
1. **SQLite**: Simple, local, no setup
2. **PostgreSQL**: Powerful, requires hosting
3. **Supabase**: Hosted PostgreSQL with extras

## Decision

We use **Supabase** as the backend database because it provides:

1. **Hosted PostgreSQL**: No infrastructure to manage
2. **Built-in Auth**: Google OAuth integration for Streamlit
3. **Row Level Security**: Fine-grained access control
4. **Realtime subscriptions**: For live updates in UI
5. **Edge Functions**: For scheduled jobs (cron)
6. **Storage**: For PDF documents and raw responses
7. **Free tier**: Suitable for development/small scale

Configuration:
```python
# Required environment variables
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # Optional, for admin ops
```

## Consequences

### Positive
- **Zero ops**: No database administration needed
- **Auth included**: OAuth setup is straightforward
- **Good DX**: Dashboard for debugging, SQL editor
- **Generous free tier**: 500MB database, 1GB storage
- **Backups**: Automatic daily backups

### Negative
- **Vendor lock-in**: Supabase-specific features used
- **Latency**: Remote database adds network latency
- **Cost at scale**: Paid plans for larger usage
- **Client limitations**: Python client not fully async

### Mitigations
- Keep core logic database-agnostic where possible
- Use connection pooling for performance
- Monitor usage to predict tier upgrades
- Consider local PostgreSQL for heavy development
