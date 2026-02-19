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
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
import httpx
from app.lib.database import get_supabase
from app.models.training_config import TrainingConfig, DEFAULT_THRESHOLDS_5CLASS

logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://ollama.lefv.info")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")

# Legacy label thresholds (kept for backward compat with tests importing this)
LABEL_THRESHOLDS = {
    'strong_buy': 0.05,
    'buy': 0.02,
    'sell': -0.02,
    'strong_sell': -0.05,
}

# Market regime tickers added to yfinance batch download
MARKET_TICKERS = ["^VIX", "SPY"]

# SPDR Sector ETFs for market breadth calculation
from app.services.sector_cache import SECTOR_ETFS


def generate_label(
    forward_return: float,
    num_classes: int = 5,
    thresholds: Optional[Dict[str, float]] = None,
) -> int:
    """
    Generate label based on forward stock return.

    5-class mode:
        2: strong_buy, 1: buy, 0: hold, -1: sell, -2: strong_sell
    3-class mode:
        1: buy, 0: hold, -1: sell
    """
    if thresholds is None:
        thresholds = LABEL_THRESHOLDS

    if num_classes == 3:
        buy_thresh = thresholds.get("buy", 0.02)
        sell_thresh = thresholds.get("sell", -0.02)
        if forward_return > buy_thresh:
            return 1
        elif forward_return < sell_thresh:
            return -1
        else:
            return 0
    else:
        # 5-class (original logic)
        if forward_return > thresholds.get('strong_buy', 0.05):
            return 2
        elif forward_return > thresholds.get('buy', 0.02):
            return 1
        elif forward_return < thresholds.get('strong_sell', -0.05):
            return -2
        elif forward_return < thresholds.get('sell', -0.02):
            return -1
        else:
            return 0


class FeaturePipeline:
    """
    Pipeline for extracting features and labels from trading disclosures.

    Features are extracted from:
    1. Disclosure data (politician count, buy/sell ratio, bipartisan, etc.)
    2. Politician metadata (party alignment, chamber-based committee relevance)
    3. Market data (price momentum, sector performance, VIX, SPY, breadth)
    4. Sentiment (LLM-derived sentiment, opt-in)
    """

    def __init__(self):
        self.supabase = get_supabase()

    async def prepare_training_data(
        self,
        lookback_days: int = 365,
        min_politicians: int = 2,
        exclude_recent_days: int = 7,
        config: Optional[TrainingConfig] = None,
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Prepare labeled training data from historical disclosures.

        Args:
            lookback_days: Number of days of historical data to use
            min_politicians: Minimum politicians trading to include ticker
            exclude_recent_days: Exclude recent days (need forward returns)
            config: TrainingConfig for feature selection and labeling

        Returns:
            Tuple of (features_df, labels_array)
        """
        if config is None:
            config = TrainingConfig(lookback_days=lookback_days)

        actual_lookback = config.lookback_days
        # Need enough forward days for the prediction window
        actual_exclude = max(exclude_recent_days, config.prediction_window_days + 3)

        logger.info(f"Preparing training data for last {actual_lookback} days (window={config.prediction_window_days}d, classes={config.num_classes})...")

        # 1. Fetch disclosures
        disclosures = await self._fetch_disclosures(actual_lookback, actual_exclude)
        logger.info(f"Fetched {len(disclosures)} disclosures")

        if not disclosures:
            return pd.DataFrame(), np.array([])

        # 2. Aggregate by ticker per week
        weekly_aggregations = self._aggregate_by_week(disclosures, min_politicians)
        logger.info(f"Created {len(weekly_aggregations)} weekly ticker aggregations")

        # 3. Fetch stock returns + market regime data
        weekly_aggregations = await self._add_stock_returns(weekly_aggregations, config)

        # 4. Add sector performance if enabled
        if config.features.enable_sector:
            self._add_sector_performance(weekly_aggregations)

        # 5. Extract features for each aggregation
        features_list = []
        labels = []

        # Determine which return column to use for labeling
        return_key = f'forward_return_{config.prediction_window_days}d'

        for agg in weekly_aggregations:
            fwd_return = agg.get(return_key)
            if fwd_return is None:
                # Fallback: try 7d return for backward compat
                fwd_return = agg.get('forward_return_7d')
            if fwd_return is None:
                continue

            features = self._extract_features(agg, config)
            label = generate_label(fwd_return, config.num_classes, config.thresholds)

            features_list.append(features)
            labels.append(label)

        if not features_list:
            return pd.DataFrame(), np.array([])

        features_df = pd.DataFrame(features_list)
        labels_array = np.array(labels)

        logger.info(f"Prepared {len(features_df)} labeled samples")
        logger.info(f"Label distribution: {dict(zip(*np.unique(labels_array, return_counts=True)))}")

        return features_df, labels_array

    @staticmethod
    def _compute_outcome_weight(
        base_weight: float,
        confidence: float,
        return_pct: float,
    ) -> float:
        """Compute per-sample weight for an outcome record.

        Weight = base_weight * confidence * log(1 + |return_pct|)

        High-confidence trades with large returns teach the model the most.
        Low-confidence breakevens teach the least (but still more than market data).
        """
        import math
        conf = max(0.0, min(1.0, confidence or 0.5))
        magnitude = math.log1p(abs(return_pct or 0.0))
        # Floor at 0.5 * base_weight so even low-signal outcomes outweigh market data
        return max(0.5 * base_weight, base_weight * conf * max(magnitude, 0.1))

    async def prepare_outcome_training_data(
        self,
        config: Optional["TrainingConfig"] = None,
    ) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        """Prepare training data blending outcome-labeled and market-labeled records.

        Returns (features_df, labels, sample_weights) where sample_weights
        are per-sample: outcome records get confidence * magnitude weighting,
        market records get 1.0.
        """
        from app.models.training_config import TrainingConfig as _TrainingConfig

        if config is None:
            config = _TrainingConfig(use_outcomes=True)

        feature_names = config.get_feature_names()
        outcome_weight = config.outcome_weight

        # --- Outcome-labeled data from closed trades ---
        outcome_records = await self._fetch_outcome_data(window_days=config.lookback_days)

        outcome_features_list = []
        outcome_labels = []
        outcome_weights = []
        for rec in outcome_records:
            features = rec.get("features", {})
            if not features or not all(name in features for name in feature_names):
                continue

            feature_vec = {name: float(features.get(name, 0.0)) for name in feature_names}
            outcome_features_list.append(feature_vec)

            outcome = rec["outcome"]
            return_pct = rec.get("return_pct", 0.0)
            if outcome == "win":
                label = generate_label(abs(return_pct) / 100.0, config.num_classes, config.thresholds)
                if label <= 0:
                    label = 1
            elif outcome == "loss":
                label = generate_label(-abs(return_pct) / 100.0, config.num_classes, config.thresholds)
                if label >= 0:
                    label = -1
            else:
                label = 0
            outcome_labels.append(label)

            # Per-sample weight: confidence * return magnitude
            confidence = rec.get("signal_confidence", 0.5)
            outcome_weights.append(
                self._compute_outcome_weight(outcome_weight, confidence, return_pct)
            )

        # --- Market-labeled data from yfinance forward returns ---
        market_features_df, market_labels = await self.prepare_training_data(
            lookback_days=config.lookback_days, config=config,
        )

        # --- Blend both sources ---
        all_features = []
        all_labels = []
        all_weights = []

        if outcome_features_list:
            outcome_df = pd.DataFrame(outcome_features_list)
            all_features.append(outcome_df)
            all_labels.extend(outcome_labels)
            all_weights.extend(outcome_weights)

        if len(market_features_df) > 0:
            all_features.append(market_features_df)
            all_labels.extend(market_labels.tolist())
            all_weights.extend([1.0] * len(market_labels))

        if not all_features:
            return pd.DataFrame(), np.array([]), np.array([])

        combined_df = pd.concat(all_features, ignore_index=True)
        return combined_df, np.array(all_labels), np.array(all_weights)

    async def _fetch_disclosures(
        self,
        lookback_days: int,
        exclude_recent_days: int,
    ) -> List[Dict[str, Any]]:
        """Fetch trading disclosures from Supabase."""
        end_date = datetime.now(timezone.utc) - timedelta(days=exclude_recent_days)
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

    async def _fetch_outcome_data(self, window_days: int = 90) -> list:
        """Fetch closed trade outcomes from signal_outcomes for training labels."""
        if not self.supabase:
            return []

        cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

        result = (
            self.supabase.table("signal_outcomes")
            .select("ticker, signal_type, signal_confidence, outcome, return_pct, "
                    "entry_price, exit_price, holding_days, features, signal_date")
            .in_("outcome", ["win", "loss", "breakeven"])
            .gte("signal_date", cutoff)
            .execute()
        )

        return result.data or []

    def _aggregate_by_week(
        self,
        disclosures: List[Dict[str, Any]],
        min_politicians: int,
    ) -> List[Dict[str, Any]]:
        """Aggregate disclosures by ticker per week."""
        weekly_data = defaultdict(lambda: defaultdict(list))

        for d in disclosures:
            ticker = d.get('asset_ticker', '').upper()
            if not ticker or len(ticker) > 10:
                continue

            tx_date = datetime.fromisoformat(d['transaction_date'].replace('Z', '+00:00'))
            week_key = tx_date.isocalendar()[:2]

            weekly_data[(ticker, week_key)]['disclosures'].append(d)

        aggregations = []

        for (ticker, week_key), data in weekly_data.items():
            disclosures_list = data['disclosures']
            if not disclosures_list:
                continue

            buys = 0
            sells = 0
            buy_volume = 0
            sell_volume = 0
            politicians = set()
            parties = set()
            party_counts = Counter()
            chambers = set()
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

                politician_data = d.get('politician') or {}
                party = politician_data.get('party')
                if party:
                    parties.add(party)
                    party_counts[party] += 1

                chamber = politician_data.get('chamber')
                if chamber:
                    chambers.add(chamber.lower() if isinstance(chamber, str) else chamber)

                if d.get('transaction_date') and d.get('disclosure_date'):
                    tx_dt = datetime.fromisoformat(d['transaction_date'].replace('Z', '+00:00'))
                    disc_dt = datetime.fromisoformat(d['disclosure_date'].replace('Z', '+00:00'))
                    delay = (disc_dt - tx_dt).days
                    if delay >= 0:
                        disclosure_delays.append(delay)

            if len(politicians) < min_politicians:
                continue

            year, week_num = week_key
            week_start = datetime.fromisocalendar(year, week_num, 1)

            # Real party_alignment: consensus measure (0.5 = split, 1.0 = all same party)
            total_party_trades = sum(party_counts.values())
            if total_party_trades > 0:
                party_alignment = max(party_counts.values()) / total_party_trades
            else:
                party_alignment = 0.5

            # Real committee_relevance: chamber-based proxy
            has_house = 'house' in chambers
            has_senate = 'senate' in chambers
            if has_house and not has_senate:
                committee_relevance = 0.7
            elif has_senate and not has_house:
                committee_relevance = 0.4
            elif has_house and has_senate:
                committee_relevance = 0.5
            else:
                committee_relevance = 0.5

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
                'party_alignment': party_alignment,
                'committee_relevance': committee_relevance,
                'avg_disclosure_delay': np.mean(disclosure_delays) if disclosure_delays else 30,
                'disclosure_count': len(disclosures_list),
            })

        return aggregations

    async def _add_stock_returns(
        self,
        aggregations: List[Dict[str, Any]],
        config: Optional[TrainingConfig] = None,
    ) -> List[Dict[str, Any]]:
        """Add forward stock returns and market regime data to aggregations."""
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed - skipping stock returns")
            return aggregations

        if config is None:
            config = TrainingConfig()

        tickers = list(set(a['ticker'] for a in aggregations))
        logger.info(f"Fetching stock data for {len(tickers)} tickers...")

        all_dates = [datetime.fromisoformat(a['week_start']) for a in aggregations]
        min_date = min(all_dates) - timedelta(days=30)
        max_date = max(all_dates) + timedelta(days=40)

        # Add market regime tickers to download
        extra_tickers = []
        if config.features.enable_market_regime:
            extra_tickers.extend(MARKET_TICKERS)
        if config.features.enable_sector:
            extra_tickers.extend(SECTOR_ETFS)

        all_tickers = tickers + [t for t in extra_tickers if t not in tickers]

        # Fetch in batches
        price_data = {}
        batch_size = 100

        for i in range(0, len(all_tickers), batch_size):
            batch = all_tickers[i:i + batch_size]
            try:
                data = yf.download(
                    batch,
                    start=min_date.strftime('%Y-%m-%d'),
                    end=max_date.strftime('%Y-%m-%d'),
                    progress=False,
                    group_by='ticker',
                )

                if len(batch) == 1:
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
                agg['forward_return_14d'] = None
                agg['forward_return_30d'] = None
                continue

            prices = price_data[ticker]

            try:
                start_prices = prices[prices.index >= week_start.strftime('%Y-%m-%d')]
                if len(start_prices) == 0:
                    agg['forward_return_7d'] = None
                    agg['forward_return_14d'] = None
                    agg['forward_return_30d'] = None
                    continue

                price_start = start_prices.iloc[0]

                if price_start == 0:
                    agg['forward_return_7d'] = None
                    agg['forward_return_14d'] = None
                    agg['forward_return_30d'] = None
                    agg['market_momentum'] = 0
                    continue

                # Forward returns for all windows
                for days in (7, 14, 30):
                    date_fwd = week_start + timedelta(days=days)
                    prices_fwd = prices[prices.index >= date_fwd.strftime('%Y-%m-%d')]
                    if len(prices_fwd) > 0:
                        price_fwd = prices_fwd.iloc[0]
                        agg[f'forward_return_{days}d'] = (price_fwd - price_start) / price_start
                    else:
                        agg[f'forward_return_{days}d'] = None

                # Market momentum (20-day lookback)
                date_20d_back = week_start - timedelta(days=20)
                prices_20d_back = prices[prices.index <= week_start.strftime('%Y-%m-%d')]
                prices_20d_back = prices_20d_back[prices_20d_back.index >= date_20d_back.strftime('%Y-%m-%d')]
                if len(prices_20d_back) >= 2:
                    momentum_base = prices_20d_back.iloc[0]
                    if momentum_base != 0:
                        agg['market_momentum'] = (prices_20d_back.iloc[-1] - momentum_base) / momentum_base
                    else:
                        agg['market_momentum'] = 0
                else:
                    agg['market_momentum'] = 0

            except Exception as e:
                logger.warning(f"Error calculating returns for {ticker}: {e}")
                agg['forward_return_7d'] = None
                agg['forward_return_14d'] = None
                agg['forward_return_30d'] = None

        # Add market regime features from ^VIX and SPY
        if config.features.enable_market_regime:
            self._add_market_regime_features(aggregations, price_data)

        return aggregations

    def _add_market_regime_features(
        self,
        aggregations: List[Dict[str, Any]],
        price_data: Dict[str, Any],
    ):
        """Add VIX level, SPY return, and market breadth features."""
        vix_prices = price_data.get("^VIX")
        spy_prices = price_data.get("SPY")

        for agg in aggregations:
            week_start = datetime.fromisoformat(agg['week_start'])
            ws_str = week_start.strftime('%Y-%m-%d')

            # VIX level (normalized by /30)
            if vix_prices is not None:
                try:
                    vix_at = vix_prices[vix_prices.index <= ws_str]
                    if len(vix_at) > 0:
                        agg['vix_level'] = float(vix_at.iloc[-1]) / 30.0
                    else:
                        agg['vix_level'] = 0.5
                except Exception:
                    agg['vix_level'] = 0.5
            else:
                agg['vix_level'] = 0.5

            # SPY 20-day return
            if spy_prices is not None:
                try:
                    date_20d_back = week_start - timedelta(days=20)
                    spy_window = spy_prices[spy_prices.index >= date_20d_back.strftime('%Y-%m-%d')]
                    spy_window = spy_window[spy_window.index <= ws_str]
                    if len(spy_window) >= 2 and spy_window.iloc[0] != 0:
                        agg['market_return_20d'] = (spy_window.iloc[-1] - spy_window.iloc[0]) / spy_window.iloc[0]
                    else:
                        agg['market_return_20d'] = 0.0
                except Exception:
                    agg['market_return_20d'] = 0.0
            else:
                agg['market_return_20d'] = 0.0

            # Market breadth: fraction of sector ETFs with positive 20-day returns
            positive_sectors = 0
            total_sectors = 0
            for etf in SECTOR_ETFS:
                etf_prices = price_data.get(etf)
                if etf_prices is None:
                    continue
                try:
                    date_20d_back = week_start - timedelta(days=20)
                    etf_window = etf_prices[etf_prices.index >= date_20d_back.strftime('%Y-%m-%d')]
                    etf_window = etf_window[etf_window.index <= ws_str]
                    if len(etf_window) >= 2 and etf_window.iloc[0] != 0:
                        ret = (etf_window.iloc[-1] - etf_window.iloc[0]) / etf_window.iloc[0]
                        total_sectors += 1
                        if ret > 0:
                            positive_sectors += 1
                except Exception:
                    pass

            agg['market_breadth'] = positive_sectors / total_sectors if total_sectors > 0 else 0.5

    def _add_sector_performance(self, aggregations: List[Dict[str, Any]]):
        """Add sector ETF performance for each ticker's sector."""
        from app.services.sector_cache import get_sector_cache

        cache = get_sector_cache()
        tickers = list(set(a['ticker'] for a in aggregations))
        cache.batch_resolve(tickers)

        for agg in aggregations:
            sector_etf = cache.get_sector(agg['ticker'])
            if sector_etf and f'_sector_return_{sector_etf}' in agg:
                agg['sector_performance'] = agg[f'_sector_return_{sector_etf}']
            else:
                # Use market_return_20d as fallback if available
                agg.setdefault('sector_performance', agg.get('market_return_20d', 0.0))

    def _extract_features(
        self,
        aggregation: Dict[str, Any],
        config: Optional[TrainingConfig] = None,
    ) -> Dict[str, float]:
        """Extract feature vector from aggregation based on config."""
        if config is None:
            config = TrainingConfig()

        features: Dict[str, float] = {
            'politician_count': aggregation.get('politician_count', 0),
            'buy_sell_ratio': min(aggregation.get('buy_sell_ratio', 1.0), 10.0),
            'recent_activity_30d': aggregation.get('disclosure_count', 0),
            'bipartisan': 1.0 if aggregation.get('bipartisan', False) else 0.0,
            'net_volume': aggregation.get('net_volume', 0),
            'volume_magnitude': np.log1p(abs(aggregation.get('total_volume', 0))),
            'party_alignment': aggregation.get('party_alignment', 0.5),
            'disclosure_delay': aggregation.get('avg_disclosure_delay', 30),
            'market_momentum': aggregation.get('market_momentum', 0.0),
        }

        if config.features.enable_sector:
            features['committee_relevance'] = aggregation.get('committee_relevance', 0.5)
            features['sector_performance'] = aggregation.get('sector_performance', 0.0)

        if config.features.enable_market_regime:
            features['vix_level'] = aggregation.get('vix_level', 0.5)
            features['market_return_20d'] = aggregation.get('market_return_20d', 0.0)
            features['market_breadth'] = aggregation.get('market_breadth', 0.5)

        if config.features.enable_sentiment:
            features['sentiment_score'] = aggregation.get('sentiment_score', 0.0)

        return features

    async def extract_sentiment(
        self,
        ticker: str,
        news_text: str,
    ) -> float:
        """
        Use Ollama to extract sentiment score from news text.

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

                try:
                    score = float(answer)
                    return max(-1.0, min(1.0, score))
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
        triggered_by: str = 'api',
        config: Optional[TrainingConfig] = None,
    ):
        self.job_id = job_id
        self.lookback_days = lookback_days
        self.model_type = model_type
        self.triggered_by = triggered_by
        self.config = config or TrainingConfig(
            lookback_days=lookback_days,
            model_type=model_type,
            triggered_by=triggered_by,
        )
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
            "triggered_by": self.triggered_by,
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
        self.started_at = datetime.now(timezone.utc)
        self.current_step = "Preparing training data..."
        self.progress = 10

        try:
            supabase = get_supabase()

            config = self.config
            hyperparams_dict = config.to_hyperparameters_dict()

            # Create model record in database
            model_result = supabase.table('ml_models').insert({
                'model_name': f'congress_signal_{self.job_id}',
                'model_version': '1.0.0',
                'model_type': self.model_type,
                'status': 'training',
                'training_started_at': self.started_at.isoformat(),
                'hyperparameters': hyperparams_dict,
            }).execute()

            self.model_id = model_result.data[0]['id']

            # Prepare training data with config
            pipeline = FeaturePipeline()
            sample_weights = None
            if config.use_outcomes:
                features_df, labels, sample_weights = await pipeline.prepare_outcome_training_data(
                    config=config,
                )
            else:
                features_df, labels = await pipeline.prepare_training_data(
                    lookback_days=config.lookback_days,
                    config=config,
                )

            if len(features_df) < 100:
                raise ValueError(f"Insufficient training data: {len(features_df)} samples")

            self.current_step = "Training model..."
            self.progress = 50

            # Train model with config
            model = CongressSignalModel()
            training_result = model.train(
                features_df,
                labels,
                hyperparams=config.hyperparams,
                config=config,
                sample_weights=sample_weights,
            )

            self.current_step = "Saving model..."
            self.progress = 80

            model_path = f"{MODEL_STORAGE_PATH}/{self.model_id}.pkl"
            model.save(model_path)

            self.current_step = "Uploading to storage..."
            self.progress = 85
            storage_path = upload_model_to_storage(self.model_id, model_path)
            if storage_path:
                logger.info(f"[{self.job_id}] Model uploaded to storage: {storage_path}")
            else:
                logger.warning(f"[{self.job_id}] Failed to upload model to storage - model may not persist")

            # Merge config into hyperparameters for storage
            stored_hyperparams = training_result['hyperparameters']
            stored_hyperparams.update(hyperparams_dict)

            supabase.table('ml_models').update({
                'status': 'active',
                'training_completed_at': datetime.now(timezone.utc).isoformat(),
                'metrics': training_result['metrics'],
                'feature_importance': training_result['feature_importance'],
                'hyperparameters': stored_hyperparams,
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
            self.completed_at = datetime.now(timezone.utc)

            logger.info(f"[{self.job_id}] Training completed: {training_result['metrics']}")

        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            self.completed_at = datetime.now(timezone.utc)

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
    triggered_by: str = 'api',
    config: Optional[TrainingConfig] = None,
) -> TrainingJob:
    """Create a new training job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]

    if config is None:
        config = TrainingConfig(
            lookback_days=lookback_days,
            model_type=model_type,
            triggered_by=triggered_by,
        )

    job = TrainingJob(job_id, lookback_days, model_type, triggered_by, config=config)
    _training_jobs[job_id] = job
    return job


async def run_training_job_in_background(job: TrainingJob):
    """Run a training job in the background."""
    await job.run()
