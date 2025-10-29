# Streamlit Deployment Guide

This guide explains how to deploy the Politician Trading Tracker as a Streamlit web application.

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Configure Environment

Option A: Using `.env` file (recommended for local development):

```bash
cp .env.example .env
# Edit .env with your configuration
```

Option B: Using Streamlit secrets (recommended for Streamlit Cloud):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your configuration
```

### 3. Run Locally

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Configuration

### Required Configuration

**Supabase** (Database):
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon/public key
- `SUPABASE_SERVICE_KEY`: Your Supabase service role key (optional, for admin operations)

**Alpaca** (Trading - Optional):
- `ALPACA_API_KEY`: Your Alpaca API key
- `ALPACA_SECRET_KEY`: Your Alpaca secret key
- `ALPACA_PAPER`: Set to `true` for paper trading, `false` for live

### Optional Configuration

- `QUIVER_API_KEY`: QuiverQuant API key for enhanced Congress data
- `TRADING_MIN_CONFIDENCE`: Minimum signal confidence (default: 0.65)
- `RISK_MAX_POSITION_SIZE_PCT`: Max position size % (default: 10.0)
- `RISK_MAX_PORTFOLIO_RISK_PCT`: Max risk per trade % (default: 2.0)

## Deployment Options

### Option 1: Streamlit Community Cloud (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add Streamlit app"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Set main file path to `app.py`
   - Click "Deploy"

3. **Configure Secrets**:
   - In Streamlit Cloud dashboard, go to your app settings
   - Click "Secrets" in the sidebar
   - Copy contents from `.streamlit/secrets.toml.example`
   - Fill in your actual values
   - Save

4. **Done!** Your app will be live at `https://[your-app-name].streamlit.app`

### Option 2: Self-Hosted with Docker

1. **Create Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. **Build and run**:

```bash
docker build -t politician-trading-tracker .
docker run -p 8501:8501 \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_ANON_KEY=your_key \
  -e ALPACA_API_KEY=your_key \
  -e ALPACA_SECRET_KEY=your_secret \
  politician-trading-tracker
```

### Option 3: Traditional Server Deployment

1. **Set up Python environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

2. **Configure environment**:

```bash
export SUPABASE_URL=your_url
export SUPABASE_ANON_KEY=your_key
# ... other variables
```

3. **Run with systemd** (Linux):

Create `/etc/systemd/system/politician-trading.service`:

```ini
[Unit]
Description=Politician Trading Tracker
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/politician-trading-tracker
Environment="SUPABASE_URL=your_url"
Environment="SUPABASE_ANON_KEY=your_key"
ExecStart=/path/to/venv/bin/streamlit run app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable politician-trading
sudo systemctl start politician-trading
```

4. **Set up reverse proxy** (nginx):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Pages Overview

The Streamlit app includes the following pages:

1. **Home** (`app.py`): Dashboard with quick stats and navigation
2. **Data Collection** (`pages/1_📥_Data_Collection.py`): Scrape politician trading data
3. **Trading Signals** (`pages/2_🎯_Trading_Signals.py`): Generate AI-powered signals
4. **Trading Operations** (`pages/3_💼_Trading_Operations.py`): Execute trades
5. **Portfolio** (`pages/4_📈_Portfolio.py`): Monitor positions and performance
6. **Settings** (`pages/5_⚙️_Settings.py`): Configure the system

## Features

- 📊 Real-time politician trading data collection
- 🤖 AI-powered trading signal generation
- 💼 Paper and live trading via Alpaca API
- 📈 Portfolio monitoring and risk management
- ⚙️ Configurable risk parameters
- 📱 Mobile-responsive interface

## Database Setup

Before using the app, set up your database:

1. **Create Supabase project** at [supabase.com](https://supabase.com)

2. **Run SQL migrations**:
   ```sql
   -- In Supabase SQL editor, run:
   -- 1. politician_trading_schema.sql
   -- 2. trading_schema.sql
   ```

3. **Get API keys** from Supabase project settings

## Security Best Practices

1. **Never commit secrets**:
   - `.env` and `.streamlit/secrets.toml` are gitignored
   - Never commit API keys to version control

2. **Use environment-specific keys**:
   - Development: Paper trading keys
   - Production: Separate live trading keys

3. **Enable RLS** (Row Level Security) in Supabase:
   - Policies are included in schema files
   - Review and adjust based on your needs

4. **HTTPS only** for production:
   - Use SSL/TLS certificates
   - Streamlit Cloud provides HTTPS automatically

## Troubleshooting

### Database Connection Issues

```python
# Test connection
from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig

config = SupabaseConfig.from_env()
db = SupabaseClient(config)

# Should not raise errors
response = db.client.table("politicians").select("id").limit(1).execute()
```

### Alpaca API Issues

```python
# Test Alpaca connection
from politician_trading.trading.alpaca_client import AlpacaTradingClient
import os

client = AlpacaTradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

# Should return account info
account = client.get_account()
print(account)
```

### Port Already in Use

If port 8501 is busy:

```bash
streamlit run app.py --server.port 8502
```

## Performance Optimization

1. **Enable caching**:
   - Streamlit's `@st.cache_data` is used throughout
   - Database queries are optimized

2. **Limit data fetch**:
   - Recent disclosures: 100 records
   - Active signals: 100 records
   - Adjust in code if needed

3. **Database indexes**:
   - Indexes are created in schema files
   - Ensure they're applied to your database

## Monitoring

### Application Logs

Streamlit logs are available in:
- Console output (when running locally)
- Streamlit Cloud logs (in dashboard)
- System logs (if using systemd)

### Database Monitoring

Monitor via Supabase dashboard:
- Query performance
- Table sizes
- Active connections

### Trading Monitoring

Check regularly:
- Portfolio performance
- Open positions
- Risk metrics
- Order execution

## Support

- **Documentation**: See [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/gwicho38/politician-trading-tracker/issues)
- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io)

## Disclaimer

This software is for educational purposes only. Trading involves substantial risk. You are solely responsible for your trading decisions.
