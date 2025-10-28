"""Political influence features for stock recommendation models"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PoliticalFeatureConfig:
    """Configuration for political feature extraction"""

    # Politician influence scoring
    committee_weights: Dict[str, float] = None
    party_influence_weights: Dict[str, float] = None
    position_weights: Dict[str, float] = None

    # Trading pattern analysis
    influence_lookback_days: int = 180
    insider_threshold_days: int = 30
    cluster_analysis_window: int = 60

    # Policy impact modeling
    sector_policy_mapping: Dict[str, List[str]] = None
    policy_announcement_window: int = 7

    def __post_init__(self):
        if self.committee_weights is None:
            self.committee_weights = {
                "financial_services": 3.0,
                "energy_commerce": 2.5,
                "judiciary": 2.0,
                "appropriations": 2.5,
                "ways_means": 3.0,
                "defense": 2.0,
                "foreign_affairs": 1.5,
                "healthcare": 2.0,
                "technology": 2.5,
            }

        if self.party_influence_weights is None:
            self.party_influence_weights = {
                "majority_party": 1.2,
                "minority_party": 0.8,
                "leadership": 2.0,
                "committee_chair": 1.8,
                "ranking_member": 1.4,
            }

        if self.position_weights is None:
            self.position_weights = {
                "speaker": 3.0,
                "majority_leader": 2.5,
                "minority_leader": 2.0,
                "committee_chair": 2.0,
                "subcommittee_chair": 1.5,
                "ranking_member": 1.3,
                "member": 1.0,
            }

        if self.sector_policy_mapping is None:
            self.sector_policy_mapping = {
                "technology": ["tech_regulation", "data_privacy", "antitrust"],
                "healthcare": ["medicare", "drug_pricing", "healthcare_reform"],
                "energy": ["climate_policy", "renewable_energy", "oil_regulation"],
                "financial": ["banking_regulation", "fintech", "cryptocurrency"],
                "defense": ["defense_spending", "military_contracts", "cybersecurity"],
            }


class PoliticalInfluenceFeatures:
    """Extract features based on political influence and power"""

    def __init__(self, config: Optional[PoliticalFeatureConfig] = None):
        self.config = config or PoliticalFeatureConfig()
        self.politician_influence_cache = {}

    def extract_influence_features(
        self, trading_data: pd.DataFrame, politician_metadata: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Extract political influence features from trading data"""
        df = trading_data.copy()

        # Calculate politician influence scores
        df = self._calculate_politician_influence(df, politician_metadata)

        # Trading timing analysis
        df = self._analyze_trading_timing(df)

        # Committee and sector alignment
        df = self._analyze_committee_sector_alignment(df, politician_metadata)

        # Party clustering analysis
        df = self._analyze_party_clustering(df)

        # Seniority and experience features
        df = self._extract_seniority_features(df, politician_metadata)

        return df

    def _calculate_politician_influence(
        self, df: pd.DataFrame, metadata: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """Calculate comprehensive politician influence scores"""

        # Base influence score from trading frequency and volume
        politician_stats = (
            df.groupby("politician_name_cleaned")
            .agg(
                {
                    "transaction_amount_cleaned": ["count", "sum", "mean", "std"],
                    "asset_name_cleaned": "nunique",
                }
            )
            .round(2)
        )

        politician_stats.columns = [
            "trade_count",
            "total_volume",
            "avg_trade_size",
            "trade_size_std",
            "unique_assets",
        ]

        # Calculate base influence from trading metrics
        # More trades, higher volumes, and diverse assets = higher influence
        politician_stats["trade_influence"] = (
            np.log1p(politician_stats["trade_count"])
            + np.log1p(politician_stats["total_volume"]) / 10
            + np.log1p(politician_stats["unique_assets"]) * 2
        )

        # Normalize to 0-1 scale
        politician_stats["trade_influence"] = (
            politician_stats["trade_influence"] / politician_stats["trade_influence"].max()
        )

        # Add metadata-based influence if available
        if metadata is not None:
            politician_stats = self._add_metadata_influence(politician_stats, metadata)
        else:
            # Use default influence based on trading patterns
            politician_stats["position_influence"] = 1.0
            politician_stats["committee_influence"] = 1.0
            politician_stats["party_influence"] = 1.0

        # Combined influence score
        politician_stats["total_influence"] = (
            politician_stats["trade_influence"] * 0.4
            + politician_stats["position_influence"] * 0.3
            + politician_stats["committee_influence"] * 0.2
            + politician_stats["party_influence"] * 0.1
        )

        # Merge back to main dataframe
        df = df.merge(
            politician_stats[["total_influence", "trade_influence"]],
            left_on="politician_name_cleaned",
            right_index=True,
            how="left",
        )

        return df

    def _add_metadata_influence(
        self, stats_df: pd.DataFrame, metadata: pd.DataFrame
    ) -> pd.DataFrame:
        """Add influence scores based on politician metadata"""

        # Position-based influence
        if "position" in metadata.columns:
            position_influence = metadata["position"].map(self.config.position_weights)
            metadata["position_influence"] = position_influence.fillna(1.0)
        else:
            metadata["position_influence"] = 1.0

        # Committee-based influence
        if "committees" in metadata.columns:

            def calculate_committee_influence(committees_str):
                if pd.isna(committees_str):
                    return 1.0
                committees = str(committees_str).lower().split(",")
                influence = 1.0
                for committee in committees:
                    committee = committee.strip()
                    for key, weight in self.config.committee_weights.items():
                        if key in committee:
                            influence = max(influence, weight)
                return influence

            metadata["committee_influence"] = metadata["committees"].apply(
                calculate_committee_influence
            )
        else:
            metadata["committee_influence"] = 1.0

        # Party-based influence (simplified)
        if "party" in metadata.columns:
            # Assume majority party has more influence (would need current data)
            party_influence = metadata["party"].map({"Republican": 1.1, "Democrat": 1.0})
            metadata["party_influence"] = party_influence.fillna(1.0)
        else:
            metadata["party_influence"] = 1.0

        # Merge metadata influence scores
        influence_cols = ["position_influence", "committee_influence", "party_influence"]
        available_cols = [col for col in influence_cols if col in metadata.columns]

        if available_cols:
            stats_df = stats_df.merge(
                metadata[["politician_name_cleaned"] + available_cols],
                left_index=True,
                right_on="politician_name_cleaned",
                how="left",
            )

        # Fill missing values
        for col in influence_cols:
            if col not in stats_df.columns:
                stats_df[col] = 1.0
            else:
                stats_df[col] = stats_df[col].fillna(1.0)

        return stats_df

    def _analyze_trading_timing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze timing patterns in political trading"""

        # Convert date to datetime if not already
        if "transaction_date_cleaned" in df.columns:
            df["transaction_date_dt"] = pd.to_datetime(df["transaction_date_cleaned"])

        # Days since last trade by politician
        df = df.sort_values(["politician_name_cleaned", "transaction_date_dt"])
        df["days_since_last_trade"] = (
            df.groupby("politician_name_cleaned")["transaction_date_dt"].diff().dt.days
        )

        # Trading frequency score (more frequent = higher score)
        df["trading_frequency_score"] = np.where(
            df["days_since_last_trade"].isna(),
            1.0,
            np.clip(30 / (df["days_since_last_trade"] + 1), 0, 2.0),
        )

        # Cluster trading detection (multiple trades in short timeframe)
        df["cluster_trades"] = (
            df.groupby("politician_name_cleaned")["days_since_last_trade"]
            .rolling(window=5, min_periods=1)
            .apply(lambda x: (x <= 7).sum())
            .values
        )

        # Quarterly timing (end of quarter trading patterns)
        df["quarter_end_trade"] = (
            df["transaction_date_dt"].dt.month.isin([3, 6, 9, 12])
            & (df["transaction_date_dt"].dt.day >= 25)
        ).astype(int)

        # Year-end trading
        df["year_end_trade"] = (
            (df["transaction_date_dt"].dt.month == 12) & (df["transaction_date_dt"].dt.day >= 20)
        ).astype(int)

        # Pre-earnings timing (approximate - would need earnings calendar)
        df["potential_insider_timing"] = (df["days_since_last_trade"] <= 5).astype(int)

        return df

    def _analyze_committee_sector_alignment(
        self, df: pd.DataFrame, metadata: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """Analyze alignment between committee assignments and traded sectors"""

        # Simplified sector classification based on asset names
        def classify_sector(asset_name):
            if pd.isna(asset_name):
                return "unknown"

            asset_lower = str(asset_name).lower()

            # Technology sector
            tech_keywords = [
                "tech",
                "software",
                "microsoft",
                "apple",
                "google",
                "meta",
                "facebook",
                "amazon",
                "netflix",
                "tesla",
                "nvidia",
                "intel",
            ]
            if any(keyword in asset_lower for keyword in tech_keywords):
                return "technology"

            # Healthcare sector
            health_keywords = [
                "health",
                "pharma",
                "medical",
                "bio",
                "johnson",
                "pfizer",
                "merck",
                "abbott",
                "healthcare",
            ]
            if any(keyword in asset_lower for keyword in health_keywords):
                return "healthcare"

            # Financial sector
            finance_keywords = [
                "bank",
                "financial",
                "capital",
                "credit",
                "jpmorgan",
                "bank of america",
                "wells fargo",
                "goldman",
                "morgan stanley",
            ]
            if any(keyword in asset_lower for keyword in finance_keywords):
                return "financial"

            # Energy sector
            energy_keywords = [
                "energy",
                "oil",
                "gas",
                "exxon",
                "chevron",
                "renewable",
                "solar",
                "wind",
                "petroleum",
            ]
            if any(keyword in asset_lower for keyword in energy_keywords):
                return "energy"

            # Defense sector
            defense_keywords = [
                "defense",
                "aerospace",
                "boeing",
                "lockheed",
                "raytheon",
                "general dynamics",
                "northrop",
            ]
            if any(keyword in asset_lower for keyword in defense_keywords):
                return "defense"

            return "other"

        df["sector_classification"] = df["asset_name_cleaned"].apply(classify_sector)

        # Committee-sector alignment score
        if metadata is not None and "committees" in metadata.columns:

            def calculate_alignment_score(politician, sector):
                politician_metadata = metadata[metadata["politician_name_cleaned"] == politician]
                if politician_metadata.empty:
                    return 0.5  # Neutral alignment

                committees = str(politician_metadata.iloc[0]["committees"]).lower()

                # Check for relevant committee memberships
                alignment_score = 0.5  # Base neutral score

                if sector == "technology" and any(
                    keyword in committees for keyword in ["technology", "commerce", "judiciary"]
                ):
                    alignment_score = 0.9
                elif sector == "healthcare" and "health" in committees:
                    alignment_score = 0.9
                elif sector == "financial" and "financial" in committees:
                    alignment_score = 0.9
                elif sector == "energy" and any(
                    keyword in committees for keyword in ["energy", "environment"]
                ):
                    alignment_score = 0.9
                elif sector == "defense" and any(
                    keyword in committees for keyword in ["defense", "armed services"]
                ):
                    alignment_score = 0.9

                return alignment_score

            df["committee_sector_alignment"] = df.apply(
                lambda row: calculate_alignment_score(
                    row["politician_name_cleaned"], row["sector_classification"]
                ),
                axis=1,
            )
        else:
            df["committee_sector_alignment"] = 0.5  # Neutral when no metadata

        return df

    def _analyze_party_clustering(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze clustering of trades by party affiliation"""

        # Mock party assignment based on politician name patterns
        # In real implementation, this would come from metadata
        def assign_party(name):
            # This is a simplified mock assignment
            # In practice, this would come from politician metadata
            republican_indicators = ["mitch", "mcconnell", "cruz", "rubio", "romney"]
            democrat_indicators = ["pelosi", "schumer", "warren", "sanders"]

            name_lower = str(name).lower()
            if any(indicator in name_lower for indicator in republican_indicators):
                return "Republican"
            elif any(indicator in name_lower for indicator in democrat_indicators):
                return "Democrat"
            else:
                return "Independent"  # Default

        df["estimated_party"] = df["politician_name_cleaned"].apply(assign_party)

        # Party-based trading patterns
        party_stats = (
            df.groupby(["estimated_party", "sector_classification"])
            .agg(
                {
                    "transaction_amount_cleaned": ["count", "mean"],
                    "transaction_type_cleaned": lambda x: (x == "buy").mean(),
                }
            )
            .round(3)
        )

        party_stats.columns = ["party_sector_trades", "party_avg_amount", "party_buy_ratio"]

        # Calculate party consensus score for each trade
        df = df.merge(
            party_stats,
            left_on=["estimated_party", "sector_classification"],
            right_index=True,
            how="left",
        )

        # Party divergence score (how much this trade differs from party norm)
        df["party_divergence"] = abs(
            (df["transaction_type_cleaned"] == "buy").astype(int) - df["party_buy_ratio"]
        )

        return df

    def _extract_seniority_features(
        self, df: pd.DataFrame, metadata: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        """Extract features related to politician seniority and experience"""

        # Estimate seniority based on trading patterns (mock implementation)
        politician_first_trade = df.groupby("politician_name_cleaned")["transaction_date_dt"].min()

        # Calculate trading experience (days since first recorded trade)
        df = df.merge(
            politician_first_trade.rename("first_trade_date"),
            left_on="politician_name_cleaned",
            right_index=True,
            how="left",
        )

        df["trading_experience_days"] = (df["transaction_date_dt"] - df["first_trade_date"]).dt.days

        # Experience categories
        df["experience_category"] = pd.cut(
            df["trading_experience_days"],
            bins=[0, 90, 365, 1095, float("inf")],
            labels=["novice", "intermediate", "experienced", "veteran"],
        )

        # Seniority influence score
        df["seniority_influence"] = np.clip(np.log1p(df["trading_experience_days"]) / 10, 0, 2.0)

        return df


class CongressionalTrackingFeatures:
    """Features based on congressional trading disclosure tracking"""

    def __init__(self, config: Optional[PoliticalFeatureConfig] = None):
        self.config = config or PoliticalFeatureConfig()

    def extract_disclosure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features related to disclosure timing and patterns"""

        # Disclosure delay analysis
        if "disclosure_date" in df.columns and "transaction_date_cleaned" in df.columns:
            df["disclosure_date_dt"] = pd.to_datetime(df["disclosure_date"])
            df["disclosure_delay_days"] = (
                df["disclosure_date_dt"] - df["transaction_date_dt"]
            ).dt.days

            # Disclosure compliance scoring
            df["timely_disclosure"] = (df["disclosure_delay_days"] <= 45).astype(int)
            df["late_disclosure"] = (df["disclosure_delay_days"] > 45).astype(int)
            df["very_late_disclosure"] = (df["disclosure_delay_days"] > 90).astype(int)

            # Disclosure pattern analysis
            df["disclosure_compliance_score"] = np.clip(
                1.0 - (df["disclosure_delay_days"] / 90), 0, 1
            )
        else:
            # Default values when disclosure dates not available
            df["disclosure_delay_days"] = 30
            df["timely_disclosure"] = 1
            df["disclosure_compliance_score"] = 0.8

        # Transaction size vs disclosure timing
        df["large_trade_late_disclosure"] = (
            (df["transaction_amount_cleaned"] > df["transaction_amount_cleaned"].quantile(0.9))
            & (df["disclosure_delay_days"] > 45)
        ).astype(int)

        return df

    def extract_reporting_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract patterns in reporting behavior"""

        # Reporting frequency by politician
        politician_reporting = df.groupby("politician_name_cleaned").agg(
            {
                "disclosure_delay_days": ["mean", "std", "max"],
                "timely_disclosure": "mean",
                "transaction_amount_cleaned": "count",
            }
        )

        politician_reporting.columns = [
            "avg_disclosure_delay",
            "disclosure_delay_std",
            "max_disclosure_delay",
            "timely_disclosure_rate",
            "total_disclosures",
        ]

        # Reporting reliability score
        politician_reporting["reporting_reliability"] = (
            politician_reporting["timely_disclosure_rate"] * 0.7
            + np.clip(1.0 - politician_reporting["avg_disclosure_delay"] / 90, 0, 1) * 0.3
        )

        # Merge back to main dataframe
        df = df.merge(
            politician_reporting[["reporting_reliability", "avg_disclosure_delay"]],
            left_on="politician_name_cleaned",
            right_index=True,
            how="left",
        )

        return df


class PolicyImpactFeatures:
    """Features related to policy announcements and their market impact"""

    def __init__(self, config: Optional[PoliticalFeatureConfig] = None):
        self.config = config or PoliticalFeatureConfig()

    def extract_policy_timing_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features related to policy announcement timing"""

        # Mock policy events (in practice, this would come from news/policy databases)
        policy_events = self._generate_mock_policy_events(df)

        if policy_events:
            df = self._analyze_policy_trade_timing(df, policy_events)
        else:
            # Default values when no policy data available
            df["days_to_policy_event"] = 999
            df["pre_policy_trade"] = 0
            df["post_policy_trade"] = 0
            df["policy_relevant_trade"] = 0

        return df

    def _generate_mock_policy_events(self, df: pd.DataFrame) -> List[Dict]:
        """Generate mock policy events for demonstration"""
        # In practice, this would be loaded from external policy/news data

        date_range = pd.date_range(
            start=df["transaction_date_dt"].min(),
            end=df["transaction_date_dt"].max(),
            freq="30D",
        )

        policy_events = []
        sectors = ["technology", "healthcare", "financial", "energy"]

        for date in date_range:
            for sector in sectors:
                if np.random.random() < 0.1:  # 10% chance of policy event
                    policy_events.append(
                        {
                            "date": date,
                            "sector": sector,
                            "event_type": np.random.choice(
                                ["regulation", "legislation", "hearing"]
                            ),
                            "impact_score": np.random.uniform(0.1, 1.0),
                        }
                    )

        return policy_events

    def _analyze_policy_trade_timing(
        self, df: pd.DataFrame, policy_events: List[Dict]
    ) -> pd.DataFrame:
        """Analyze timing of trades relative to policy events"""

        # Convert policy events to DataFrame
        policy_df = pd.DataFrame(policy_events)
        policy_df["date"] = pd.to_datetime(policy_df["date"])

        # For each trade, find the nearest policy event in the same sector
        def find_nearest_policy_event(row):
            sector = row["sector_classification"]
            trade_date = row["transaction_date_dt"]

            # Filter policy events for the same sector
            sector_events = policy_df[policy_df["sector"] == sector]

            if sector_events.empty:
                return 999, 0  # No relevant events

            # Calculate days to each event
            days_diff = (sector_events["date"] - trade_date).dt.days

            # Find nearest event (past or future)
            abs_days = days_diff.abs()
            nearest_idx = abs_days.idxmin()

            nearest_days = days_diff.loc[nearest_idx]
            impact_score = sector_events.loc[nearest_idx, "impact_score"]

            return nearest_days, impact_score

        # Apply to all trades
        policy_analysis = df.apply(find_nearest_policy_event, axis=1, result_type="expand")
        df["days_to_policy_event"] = policy_analysis[0]
        df["policy_impact_score"] = policy_analysis[1]

        # Policy-related trade flags
        df["pre_policy_trade"] = (
            (df["days_to_policy_event"] > 0) & (df["days_to_policy_event"] <= 7)
        ).astype(int)

        df["post_policy_trade"] = (
            (df["days_to_policy_event"] < 0) & (df["days_to_policy_event"] >= -7)
        ).astype(int)

        df["policy_relevant_trade"] = (abs(df["days_to_policy_event"]) <= 7).astype(int)

        # Potential insider trading indicator
        df["potential_insider_policy"] = (
            (df["pre_policy_trade"] == 1)
            & (df["policy_impact_score"] > 0.7)
            & (df["transaction_amount_cleaned"] > df["transaction_amount_cleaned"].quantile(0.8))
        ).astype(int)

        return df
