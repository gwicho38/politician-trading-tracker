"""
Feature Pipeline Service

Extracts features and labels for ML model training from:
- Trading disclosures (Supabase)
- Stock price data (yfinance)
- News sentiment (Ollama LLM)
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://ollama.lefv.info")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")

# Label thresholds based on 7-day forward returns
LABEL_THRESHOLDS = {
    'strong_buy': 0.05,    # > 5% return
    'buy': 0.02,           # 2-5% return
    'sell': -0.02,         # -2% to -5% return
    'strong_sell': -0.05,  # < -5% return
}


def get_supabase() -> Client:
    """Get Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_label(forward_return_7d: float) -> int:
    """
    Generate label based on 7-day forward stock return.

    Returns:
        2: strong_buy (return > 5%)
        1: buy (return 2-5%)
        0: hold (return -2% to 2%)
       -1: sell (return -5% to -2%)
       -2: strong_sell (return < -5%)
    """
    if forward_return_7d > LABEL_THRESHOLDS['strong_buy']:
        return 2
    elif forward_return_7d > LABEL_THRESHOLDS['buy']:
        return 1
    elif forward_return_7d < LABEL_THRESHOLDS['strong_sell']:
        return -2
    elif forward_return_7d < LABEL_THRESHOLDS['sell']:
        return -1
    else:
        return 0


class FeaturePipeline:
    """
    Pipeline for extracting features and labels from trading disclosures.

    Features are extracted from:
    1. Disclosure data (politician count, buy/sell ratio, bipartisan, etc.)
    2. Politician metadata (party, committee relevance)
    3. Market data (price momentum, sector performance)
    4. Sentiment (LLM-derived news sentiment)
    """

    def __init__(self):
        self.supabase = get_supabase()

    async def prepare_training_data(
        self,
        lookback_days: int = 365,
        min_politicians: int = 2,
        exclude_recent_days: int = 7,
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Prepare labeled training data from historical disclosures.

        Args:
            lookback_days: Number of days of historical data to use
            min_politicians: Minimum politicians trading to include ticker
            exclude_recent_days: Exclude recent days (need forward returns)

        Returns:
            Tuple of (features_df, labels_array)
        """
        logger.info(f"Preparing training data for last {lookback_days} days...")

        # 1. Fetch disclosures
        disclosures = await self._fetch_disclosures(lookback_days, exclude_recent_days)
        logger.info(f"Fetched {len(disclosures)} disclosures")

        if not disclosures:
            return pd.DataFrame(), np.array([])

        # 2. Aggregate by ticker per week
        weekly_aggregations = self._aggregate_by_week(disclosures, min_politicians)
        logger.info(f"Created {len(weekly_aggregations)} weekly ticker aggregations")

        # 3. Fetch stock returns for labeling
        weekly_aggregations = await self._add_stock_returns(weekly_aggregations)

        # 4. Extract features for each aggregation
        features_list = []
        labels = []

        for agg in weekly_aggregations:
            if agg.get('forward_return_7d') is None:
                continue  # Skip if no return data

            features = self._extract_features(agg)
            label = generate_label(agg['forward_return_7d'])

            features_list.append(features)
            labels.append(label)

        if not features_list:
            return pd.DataFrame(), np.array([])

        features_df = pd.DataFrame(features_list)
        labels_array = np.array(labels)

        logger.info(f"Prepared {len(features_df)} labeled samples")
        logger.info(f"Label distribution: {dict(zip(*np.unique(labels_array, return_counts=True)))}")

        return features_df, labels_array

    async def _fetch_disclosures(
        self,
        lookback_days: int,
        exclude_recent_days: int,
    ) -> List[Dict[str, Any]]:
        """Fetch trading disclosures from Supabase."""
        end_date = datetime.utcnow() - timedelta(days=exclude_recent_days)
        start_date = end_date - timedelta(days=lookback_days)

        all_disclosures = []
        page_size = 1000
        offset = 0

        while True:
            result = self.supabase.table('trading_disclosures').select(
                'id, asset_ticker, transaction_type, amount_range_min, amount_range_max, '
                'transaction_date, disclosure_date, politician_id, '
                'politician:politicians(id, full_name, party, state, chamber)'
            ).eq('status', 'active').not_.is_('asset_ticker', 'null').gte(
                'transaction_date', start_date.date().isoformat()
            ).lte(
                'transaction_date', end_date.date().isoformat()
            ).range(offset, offset + page_size - 1).execute()

            if not result.data:
                break

            all_disclosures.extend(result.data)
            offset += len(result.data)

            if len(result.data) < page_size:
                break

        return all_disclosures

    def _aggregate_by_week(
        self,
        disclosures: List[Dict[str, Any]],
        min_politicians: int,
    ) -> List[Dict[str, Any]]:
        """Aggregate disclosures by ticker per week."""
        # Group by ticker and week
        weekly_data = defaultdict(lambda: defaultdict(list))

        for d in disclosures:
            ticker = d.get('asset_ticker', '').upper()
            if not ticker or len(ticker) > 10:
                continue

            tx_date = datetime.fromisoformat(d['transaction_date'].replace('Z', '+00:00'))
            week_key = tx_date.isocalendar()[:2]  # (year, week_number)

            weekly_data[(ticker, week_key)]['disclosures'].append(d)

        # Aggregate each ticker-week
        aggregations = []

        for (ticker, week_key), data in weekly_data.items():
            disclosures_list = data['disclosures']
            if not disclosures_list:
                continue

            # Calculate features
            buys = 0
            sells = 0
            buy_volume = 0
            sell_volume = 0
            politicians = set()
            parties = set()
            disclosure_delays = []

            for d in disclosures_list:
                tx_type = (d.get('transaction_type') or '').lower()
                min_val = d.get('amount_range_min') or 0
                max_val = d.get('amount_range_max') or min_val
                volume = (min_val + max_val) / 2

                if 'purchase' in tx_type or 'buy' in tx_type:
                    buys += 1
                    buy_volume += volume
                elif 'sale' in tx_type or 'sell' in tx_type:
                    sells += 1
                    sell_volume += volume

                if d.get('politician_id'):
                    politicians.add(d['politician_id'])

                if d.get('politician', {}).get('party'):
                    parties.add(d['politician']['party'])

                # Disclosure delay
                if d.get('transaction_date') and d.get('disclosure_date'):
                    tx_date = datetime.fromisoformat(d['transaction_date'].replace('Z', '+00:00'))
                    disc_date = datetime.fromisoformat(d['disclosure_date'].replace('Z', '+00:00'))
                    delay = (disc_date - tx_date).days
                    if delay >= 0:
                        disclosure_delays.append(delay)

            # Filter by minimum politicians
            if len(politicians) < min_politicians:
                continue

            # Get week start date for labeling
            year, week_num = week_key
            week_start = datetime.fromisocalendar(year, week_num, 1)

            aggregations.append({
                'ticker': ticker,
                'week_start': week_start.date().isoformat(),
                'politician_count': len(politicians),
                'buy_count': buys,
                'sell_count': sells,
                'buy_sell_ratio': buys / sells if sells > 0 else (10 if buys > 0 else 1),
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'net_volume': buy_volume - sell_volume,
                'total_volume': buy_volume + sell_volume,
                'bipartisan': 'D' in parties and 'R' in parties,
                'parties': list(parties),
                'avg_disclosure_delay': np.mean(disclosure_delays) if disclosure_delays else 30,
                'disclosure_count': len(disclosures_list),
            })

        return aggregations

    async def _add_stock_returns(
        self,
        aggregations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Add forward stock returns to aggregations."""
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed - skipping stock returns")
            return aggregations

        # Group by ticker for efficient fetching
        tickers = list(set(a['ticker'] for a in aggregations))
        logger.info(f"Fetching stock data for {len(tickers)} tickers...")

        # Determine date range
        all_dates = [datetime.fromisoformat(a['week_start']) for a in aggregations]
        min_date = min(all_dates) - timedelta(days=30)
        max_date = max(all_dates) + timedelta(days=40)  # Need 30 days forward

        # Fetch in batches to avoid rate limits
        price_data = {}
        batch_size = 100

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            try:
                data = yf.download(
                    batch,
                    start=min_date.strftime('%Y-%m-%d'),
                    end=max_date.strftime('%Y-%m-%d'),
                    progress=False,
                    group_by='ticker',
                )

                if len(batch) == 1:
                    # Single ticker returns different format
                    price_data[batch[0]] = data['Close']
                else:
                    for ticker in batch:
                        if ticker in data.columns.get_level_values(0):
                            price_data[ticker] = data[ticker]['Close']

            except Exception as e:
                logger.warning(f"Failed to fetch batch starting at {i}: {e}")

        # Calculate returns for each aggregation
        for agg in aggregations:
            ticker = agg['ticker']
            week_start = datetime.fromisoformat(agg['week_start'])

            if ticker not in price_data:
                agg['forward_return_7d'] = None
                agg['forward_return_30d'] = None
                continue

            prices = price_data[ticker]

            try:
                # Get price at week start (or closest available)
                start_prices = prices[prices.index >= week_start.strftime('%Y-%m-%d')]
                if len(start_prices) == 0:
                    agg['forward_return_7d'] = None
                    agg['forward_return_30d'] = None
                    continue

                price_start = start_prices.iloc[0]

                # 7-day forward price
                date_7d = week_start + timedelta(days=7)
                prices_7d = prices[prices.index >= date_7d.strftime('%Y-%m-%d')]
                if len(prices_7d) > 0:
                    price_7d = prices_7d.iloc[0]
                    agg['forward_return_7d'] = (price_7d - price_start) / price_start
                else:
                    agg['forward_return_7d'] = None

                # 30-day forward price
                date_30d = week_start + timedelta(days=30)
                prices_30d = prices[prices.index >= date_30d.strftime('%Y-%m-%d')]
                if len(prices_30d) > 0:
                    price_30d = prices_30d.iloc[0]
                    agg['forward_return_30d'] = (price_30d - price_start) / price_start
                else:
                    agg['forward_return_30d'] = None

                # Add market momentum (20-day lookback)
                date_20d_back = week_start - timedelta(days=20)
                prices_20d_back = prices[prices.index <= week_start.strftime('%Y-%m-%d')]
                prices_20d_back = prices_20d_back[prices_20d_back.index >= date_20d_back.strftime('%Y-%m-%d')]
                if len(prices_20d_back) >= 2:
                    agg['market_momentum'] = (prices_20d_back.iloc[-1] - prices_20d_back.iloc[0]) / prices_20d_back.iloc[0]
                else:
                    agg['market_momentum'] = 0

            except Exception as e:
                logger.warning(f"Error calculating returns for {ticker}: {e}")
                agg['forward_return_7d'] = None
                agg['forward_return_30d'] = None

        return aggregations

    def _extract_features(self, aggregation: Dict[str, Any]) -> Dict[str, float]:
        """Extract feature vector from aggregation."""
        return {
            'politician_count': aggregation.get('politician_count', 0),
            'buy_sell_ratio': min(aggregation.get('buy_sell_ratio', 1.0), 10.0),  # Cap ratio
            'recent_activity_30d': aggregation.get('disclosure_count', 0),
            'bipartisan': 1.0 if aggregation.get('bipartisan', False) else 0.0,
            'net_volume': aggregation.get('net_volume', 0),
            'volume_magnitude': np.log1p(abs(aggregation.get('total_volume', 0))),
            'party_alignment': 0.5,  # Placeholder - would need majority party data
            'committee_relevance': 0.5,  # Placeholder - would need sector-committee mapping
            'disclosure_delay': aggregation.get('avg_disclosure_delay', 30),
            'sentiment_score': 0.0,  # Placeholder - would need Ollama sentiment
            'market_momentum': aggregation.get('market_momentum', 0.0),
            'sector_performance': 0.0,  # Placeholder - would need sector ETF data
        }

    async def extract_sentiment(
        self,
        ticker: str,
        news_text: str,
    ) -> float:
        """
        Use Ollama to extract sentiment score from news text.

        Args:
            ticker: Stock ticker
            news_text: News article or snippet

        Returns:
            Sentiment score from -1 (bearish) to 1 (bullish)
        """
        prompt = f"""Analyze the sentiment of this news about {ticker} stock.
Rate the sentiment as a number from -1 (very bearish) to 1 (very bullish).
0 means neutral.

News: {news_text[:1000]}

Return ONLY a number between -1 and 1:"""

        try:
            headers = {"Content-Type": "application/json"}
            if OLLAMA_API_KEY:
                headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OLLAMA_URL}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a financial analyst. Respond only with a number."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 10,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()
                answer = result.get("choices", [{}])[0].get("message", {}).get("content", "0").strip()

                # Parse the number
                try:
                    score = float(answer)
                    return max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
                except ValueError:
                    return 0.0

        except Exception as e:
            logger.warning(f"Sentiment extraction failed for {ticker}: {e}")
            return 0.0


class TrainingJob:
    """Background job for ML model training."""

    def __init__(
        self,
        job_id: str,
        lookback_days: int = 365,
        model_type: str = 'xgboost',
    ):
        self.job_id = job_id
        self.lookback_days = lookback_days
        self.model_type = model_type
        self.status = "pending"
        self.progress = 0
        self.current_step = ""
        self.result_summary = {}
        self.error_message = None
        self.model_id = None
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
        """Convert job state to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "model_type": self.model_type,
            "lookback_days": self.lookback_days,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "model_id": self.model_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    async def run(self):
        """Execute the training job."""
        from app.services.ml_signal_model import (
            CongressSignalModel,
            MODEL_STORAGE_PATH,
            upload_model_to_storage,
        )

        self.status = "running"
        self.started_at = datetime.utcnow()
        self.current_step = "Preparing training data..."
        self.progress = 10

        try:
            supabase = get_supabase()

            # Create model record in database
            model_result = supabase.table('ml_models').insert({
                'model_name': f'congress_signal_{self.job_id}',
                'model_version': '1.0.0',
                'model_type': self.model_type,
                'status': 'training',
                'training_started_at': self.started_at.isoformat(),
                'hyperparameters': {
                    'lookback_days': self.lookback_days,
                    'model_type': self.model_type,
                },
            }).execute()

            self.model_id = model_result.data[0]['id']

            # Prepare training data
            pipeline = FeaturePipeline()
            features_df, labels = await pipeline.prepare_training_data(
                lookback_days=self.lookback_days,
            )

            if len(features_df) < 100:
                raise ValueError(f"Insufficient training data: {len(features_df)} samples")

            self.current_step = "Training model..."
            self.progress = 50

            # Train model
            model = CongressSignalModel()
            training_result = model.train(features_df, labels)

            self.current_step = "Saving model..."
            self.progress = 80

            # Save model artifact locally
            model_path = f"{MODEL_STORAGE_PATH}/{self.model_id}.pkl"
            model.save(model_path)

            # Upload to Supabase Storage for persistent storage across restarts
            self.current_step = "Uploading to storage..."
            self.progress = 85
            storage_path = upload_model_to_storage(self.model_id, model_path)
            if storage_path:
                logger.info(f"[{self.job_id}] Model uploaded to storage: {storage_path}")
            else:
                logger.warning(f"[{self.job_id}] Failed to upload model to storage - model may not persist")

            # Update model record
            supabase.table('ml_models').update({
                'status': 'active',
                'training_completed_at': datetime.utcnow().isoformat(),
                'metrics': training_result['metrics'],
                'feature_importance': training_result['feature_importance'],
                'hyperparameters': training_result['hyperparameters'],
                'model_artifact_path': model_path,
                'training_samples': int(training_result['metrics']['training_samples']),
                'validation_samples': int(training_result['metrics']['validation_samples']),
            }).eq('id', self.model_id).execute()

            # Archive previous active models
            supabase.table('ml_models').update({
                'status': 'archived',
            }).eq('status', 'active').neq('id', self.model_id).execute()

            self.status = "completed"
            self.progress = 100
            self.current_step = "Training completed"
            self.result_summary = training_result['metrics']
            self.completed_at = datetime.utcnow()

            logger.info(f"[{self.job_id}] Training completed: {training_result['metrics']}")

        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            self.completed_at = datetime.utcnow()

            # Update model record if created
            if self.model_id:
                try:
                    supabase.table('ml_models').update({
                        'status': 'failed',
                        'error_message': str(e),
                    }).eq('id', self.model_id).execute()
                except Exception:
                    pass

            logger.error(f"[{self.job_id}] Training failed: {e}")


# Global job registry
_training_jobs: Dict[str, TrainingJob] = {}


def get_training_job(job_id: str) -> Optional[TrainingJob]:
    """Get a training job by ID."""
    return _training_jobs.get(job_id)


def create_training_job(
    lookback_days: int = 365,
    model_type: str = 'xgboost',
) -> TrainingJob:
    """Create a new training job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    job = TrainingJob(job_id, lookback_days, model_type)
    _training_jobs[job_id] = job
    return job


async def run_training_job_in_background(job: TrainingJob):
    """Run a training job in the background."""
    await job.run()
