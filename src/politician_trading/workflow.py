"""
Main workflow orchestrator for politician trading data collection
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .config import WorkflowConfig
from .database import PoliticianTradingDB
from .models import DataPullJob, Politician, PoliticianRole, TradingDisclosure
from .scrapers import (
    CongressTradingScraper,
    EUParliamentScraper,
    PoliticianMatcher,
    QuiverQuantScraper,
    run_california_workflow,
    run_eu_member_states_workflow,
    run_uk_parliament_workflow,
    run_us_states_workflow,
)

logger = logging.getLogger(__name__)


class PoliticianTradingWorkflow:
    """Main workflow for collecting politician trading data"""

    def __init__(self, config: WorkflowConfig = None):
        self.config = config or WorkflowConfig.default()
        self.db = PoliticianTradingDB(self.config)
        self.politicians: List[Politician] = []

    async def run_full_collection(self) -> Dict[str, Any]:
        """Run complete data collection workflow"""
        logger.info("Starting full politician trading data collection")

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "jobs": {},
            "summary": {"total_new_disclosures": 0, "total_updated_disclosures": 0, "errors": []},
        }

        try:
            # Ensure database schema
            schema_ok = await self.db.ensure_schema()
            if not schema_ok:
                raise Exception("Database schema verification failed")

            # Load existing politicians for matching
            await self._load_politicians()

            # Run US Congress collection
            us_results = await self._collect_us_congress_data()
            results["jobs"]["us_congress"] = us_results
            results["summary"]["total_new_disclosures"] += us_results.get("new_disclosures", 0)
            results["summary"]["total_updated_disclosures"] += us_results.get(
                "updated_disclosures", 0
            )

            # Run EU Parliament collection
            eu_results = await self._collect_eu_parliament_data()
            results["jobs"]["eu_parliament"] = eu_results
            results["summary"]["total_new_disclosures"] += eu_results.get("new_disclosures", 0)
            results["summary"]["total_updated_disclosures"] += eu_results.get(
                "updated_disclosures", 0
            )

            # Run California collection
            ca_results = await self._collect_california_data()
            results["jobs"]["california"] = ca_results
            results["summary"]["total_new_disclosures"] += ca_results.get("new_disclosures", 0)
            results["summary"]["total_updated_disclosures"] += ca_results.get(
                "updated_disclosures", 0
            )

            # Run EU member states collection
            eu_states_results = await self._collect_eu_member_states_data()
            results["jobs"]["eu_member_states"] = eu_states_results
            results["summary"]["total_new_disclosures"] += eu_states_results.get(
                "new_disclosures", 0
            )
            results["summary"]["total_updated_disclosures"] += eu_states_results.get(
                "updated_disclosures", 0
            )

            # Run US states collection
            us_states_results = await self._collect_us_states_data()
            results["jobs"]["us_states"] = us_states_results
            results["summary"]["total_new_disclosures"] += us_states_results.get(
                "new_disclosures", 0
            )
            results["summary"]["total_updated_disclosures"] += us_states_results.get(
                "updated_disclosures", 0
            )

            results["completed_at"] = datetime.utcnow().isoformat()
            results["status"] = "completed"

        except Exception as e:
            logger.error(f"Full collection workflow failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            results["summary"]["errors"].append(str(e))

        logger.info(f"Workflow completed: {results['summary']}")
        return results

    async def _load_politicians(self):
        """Load politicians from database for matching"""
        try:
            # For now, create some sample politicians
            # In production, you'd load from a politicians API or database
            sample_politicians = [
                Politician(
                    id=str(uuid.uuid4()),
                    first_name="Nancy",
                    last_name="Pelosi",
                    full_name="Nancy Pelosi",
                    role=PoliticianRole.US_HOUSE_REP,
                    party="Democratic",
                    state_or_country="CA",
                    district="5",
                    bioguide_id="P000197",
                ),
                Politician(
                    id=str(uuid.uuid4()),
                    first_name="Ted",
                    last_name="Cruz",
                    full_name="Ted Cruz",
                    role=PoliticianRole.US_SENATOR,
                    party="Republican",
                    state_or_country="TX",
                    bioguide_id="C001098",
                ),
            ]

            # Store politicians in database
            for politician in sample_politicians:
                politician_id = await self.db.upsert_politician(politician)
                politician.id = politician_id
                self.politicians.append(politician)

            logger.info(f"Loaded {len(self.politicians)} politicians for matching")

        except Exception as e:
            logger.error(f"Failed to load politicians: {e}")
            self.politicians = []

    async def _collect_us_congress_data(self) -> Dict[str, Any]:
        """Collect US Congress trading data"""
        job_id = await self.db.create_data_pull_job(
            "us_congress", self.config.to_serializable_dict()
        )

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id, job_type="us_congress", status="running", started_at=datetime.utcnow()
        )

        try:
            logger.info("Starting US Congress data collection")

            # Initialize scrapers
            congress_scraper = CongressTradingScraper(self.config.scraping)
            quiver_scraper = QuiverQuantScraper(self.config.scraping)

            all_disclosures = []

            # Scrape official sources
            async with congress_scraper:
                house_disclosures = await congress_scraper.scrape_house_disclosures()
                senate_disclosures = await congress_scraper.scrape_senate_disclosures()
                all_disclosures.extend(house_disclosures)
                all_disclosures.extend(senate_disclosures)

            # Scrape backup sources
            async with quiver_scraper:
                quiver_trades = await quiver_scraper.scrape_congress_trades()
                for trade_data in quiver_trades:
                    disclosure = quiver_scraper.parse_quiver_trade(trade_data)
                    if disclosure:
                        all_disclosures.append(disclosure)

            job.records_found = len(all_disclosures)

            # Process disclosures
            matcher = PoliticianMatcher(self.politicians)

            for disclosure in all_disclosures:
                try:
                    # Find matching politician
                    politician_name = disclosure.raw_data.get("politician_name", "")
                    if not politician_name or politician_name.strip() == "":
                        logger.warning("Skipping disclosure with empty politician name")
                        job.records_failed += 1
                        continue

                    # Filter out obviously invalid politician names
                    if self._is_invalid_politician_name(politician_name):
                        logger.warning(
                            f"Skipping disclosure with invalid politician name: {politician_name}"
                        )
                        job.records_failed += 1
                        continue

                    politician = matcher.find_politician(politician_name)

                    if not politician:
                        # Create new politician with real name from scraper
                        logger.info(f"Creating new politician for: {politician_name}")

                        # Parse real name into first/last components
                        name_parts = politician_name.strip().split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = " ".join(name_parts[1:])
                        else:
                            first_name = politician_name.strip()
                            last_name = ""

                        # Create politician with real name - use generic role for now
                        new_politician = Politician(
                            first_name=first_name,
                            last_name=last_name,
                            full_name=politician_name.strip(),
                            role=PoliticianRole.US_HOUSE_REP,  # Default role
                        )
                        politician_id = await self.db.upsert_politician(new_politician)
                        disclosure.politician_id = politician_id
                    else:
                        disclosure.politician_id = politician.id

                    # Check if disclosure already exists
                    existing = await self.db.find_disclosure_by_transaction(
                        disclosure.politician_id,
                        disclosure.transaction_date,
                        disclosure.asset_name,
                        disclosure.transaction_type.value,
                    )

                    if existing:
                        # Update existing record
                        disclosure.id = existing.id
                        if await self.db.update_disclosure(disclosure):
                            job.records_updated += 1
                            job_result["updated_disclosures"] += 1
                        else:
                            job.records_failed += 1
                    else:
                        # Insert new record
                        disclosure_id = await self.db.insert_disclosure(disclosure)
                        if disclosure_id:
                            job.records_new += 1
                            job_result["new_disclosures"] += 1
                        else:
                            job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"US Congress collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def _collect_eu_parliament_data(self) -> Dict[str, Any]:
        """Collect EU Parliament trading/financial data"""
        job_id = await self.db.create_data_pull_job(
            "eu_parliament", self.config.to_serializable_dict()
        )

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id, job_type="eu_parliament", status="running", started_at=datetime.utcnow()
        )

        try:
            logger.info("Starting EU Parliament data collection")

            scraper = EUParliamentScraper(self.config.scraping)

            async with scraper:
                disclosures = await scraper.scrape_mep_declarations()

            job.records_found = len(disclosures)

            # Process EU disclosures (similar to US processing)
            for disclosure in disclosures:
                try:
                    # For EU, we'd need a different politician matching strategy
                    # For now, create a sample politician
                    if not disclosure.politician_id:
                        # Create placeholder politician
                        eu_politician = Politician(
                            first_name="Sample",
                            last_name="MEP",
                            full_name="Sample MEP",
                            role=PoliticianRole.EU_MEP,
                            state_or_country="EU",
                        )
                        politician_id = await self.db.upsert_politician(eu_politician)
                        disclosure.politician_id = politician_id

                    # Insert disclosure
                    disclosure_id = await self.db.insert_disclosure(disclosure)
                    if disclosure_id:
                        job.records_new += 1
                        job_result["new_disclosures"] += 1
                    else:
                        job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process EU disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"EU Parliament collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def _collect_uk_parliament_data(self) -> Dict[str, Any]:
        """Collect UK Parliament financial interests data"""
        job_id = await self.db.create_data_pull_job(
            "uk_parliament", self.config.to_serializable_dict()
        )

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id,
            job_type="uk_parliament",
            status="running",
            started_at=datetime.utcnow(),
        )

        try:
            # Collect UK Parliament financial interests
            logger.info("Starting UK Parliament financial interests collection")
            uk_disclosures = await run_uk_parliament_workflow(self.config.scraping)

            job.records_found = len(uk_disclosures)

            # Process each disclosure
            matcher = PoliticianMatcher(self.politicians)

            for disclosure in uk_disclosures:
                try:
                    # For UK Parliament, find or create politician using real names from scrapers
                    if not disclosure.politician_id:
                        # Extract real politician name from raw data
                        politician_name = disclosure.raw_data.get("politician_name", "")

                        if not politician_name or politician_name.strip() == "":
                            # Fallback to using member ID if no name available
                            if disclosure.raw_data.get("uk_member_id"):
                                logger.warning(
                                    f"Using member ID as fallback for UK disclosure: {disclosure.raw_data.get('uk_member_id')}"
                                )
                                uk_politician = Politician(
                                    first_name="UK",
                                    last_name="MP",
                                    full_name=f"UK MP {disclosure.raw_data.get('uk_member_id')}",
                                    role=PoliticianRole.UK_MP,
                                    state_or_country="UK",
                                )
                                politician_id = await self.db.upsert_politician(uk_politician)
                                disclosure.politician_id = politician_id
                            else:
                                logger.warning(
                                    "Skipping UK disclosure with no politician name or member ID"
                                )
                                job.records_failed += 1
                                continue
                        else:
                            # Filter out obviously invalid politician names
                            if self._is_invalid_politician_name(politician_name):
                                logger.warning(
                                    f"Skipping UK disclosure with invalid politician name: {politician_name}"
                                )
                                job.records_failed += 1
                                continue

                            # Try to find existing politician
                            politician = matcher.find_politician(politician_name)

                            if not politician:
                                # Create new politician with real name from scraper
                                # Parse real name into first/last components
                                name_parts = politician_name.strip().split()
                                if len(name_parts) >= 2:
                                    first_name = name_parts[0]
                                    last_name = " ".join(name_parts[1:])
                                else:
                                    first_name = politician_name.strip()
                                    last_name = ""

                                # Create politician with REAL name
                                uk_politician = Politician(
                                    first_name=first_name,
                                    last_name=last_name,
                                    full_name=politician_name.strip(),
                                    role=PoliticianRole.UK_MP,
                                    state_or_country="UK",
                                )
                                politician_id = await self.db.upsert_politician(uk_politician)
                                disclosure.politician_id = politician_id
                                logger.info(f"Created new UK MP: {politician_name}")
                            else:
                                disclosure.politician_id = politician.id

                    # Insert disclosure
                    disclosure_id = await self.db.insert_disclosure(disclosure)
                    if disclosure_id:
                        job.records_new += 1
                        job_result["new_disclosures"] += 1
                    else:
                        job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process UK Parliament disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"UK Parliament collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def _collect_california_data(self) -> Dict[str, Any]:
        """Collect California NetFile and state disclosure data"""
        job_id = await self.db.create_data_pull_job(
            "california", self.config.to_serializable_dict()
        )

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id,
            job_type="california",
            status="running",
            started_at=datetime.utcnow(),
        )

        try:
            # Collect California financial disclosures
            logger.info("Starting California financial disclosures collection")
            california_disclosures = await run_california_workflow(self.config.scraping)

            job.records_found = len(california_disclosures)

            # Process each disclosure
            matcher = PoliticianMatcher(self.politicians)

            for disclosure in california_disclosures:
                try:
                    # For California, create politician if needed
                    if not disclosure.politician_id:
                        # Extract politician name from raw data or create placeholder
                        politician_name = disclosure.raw_data.get("politician_name", "")
                        if not politician_name:
                            # Create placeholder for California politician
                            ca_politician = Politician(
                                first_name="California",
                                last_name="Politician",
                                full_name=f"California Politician {disclosure.raw_data.get('jurisdiction', 'Unknown')}",
                                role=PoliticianRole.US_HOUSE_REP,  # Could be state-level role
                                state_or_country="CA",
                            )
                            politician_id = await self.db.upsert_politician(ca_politician)
                            disclosure.politician_id = politician_id

                    # Insert disclosure
                    disclosure_id = await self.db.insert_disclosure(disclosure)
                    if disclosure_id:
                        job.records_new += 1
                        job_result["new_disclosures"] += 1
                    else:
                        job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process California disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"California collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def _collect_eu_member_states_data(self) -> Dict[str, Any]:
        """Collect EU member states financial disclosure data"""
        job_id = await self.db.create_data_pull_job(
            "eu_member_states", self.config.to_serializable_dict()
        )

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id,
            job_type="eu_member_states",
            status="running",
            started_at=datetime.utcnow(),
        )

        try:
            # Collect EU member states financial disclosures
            logger.info("Starting EU member states financial disclosures collection")
            eu_states_disclosures = await run_eu_member_states_workflow(self.config.scraping)

            job.records_found = len(eu_states_disclosures)

            # Process each disclosure
            matcher = PoliticianMatcher(self.politicians)

            for disclosure in eu_states_disclosures:
                try:
                    # For EU member states, create politician if needed
                    if not disclosure.politician_id:
                        # Extract politician details from raw data
                        country = disclosure.raw_data.get("country", "Unknown")
                        source = disclosure.raw_data.get("source", "unknown")

                        # Map country to appropriate role
                        role_map = {
                            "Germany": PoliticianRole.GERMAN_BUNDESTAG,
                            "France": PoliticianRole.FRENCH_DEPUTY,
                            "Italy": PoliticianRole.ITALIAN_DEPUTY,
                            "Spain": PoliticianRole.SPANISH_DEPUTY,
                            "Netherlands": PoliticianRole.DUTCH_MP,
                        }

                        politician_role = role_map.get(country, PoliticianRole.EU_MEP)

                        # Create placeholder politician
                        eu_politician = Politician(
                            first_name=country,
                            last_name="Politician",
                            full_name=f"{country} Politician ({source})",
                            role=politician_role,
                            state_or_country=country,
                        )
                        politician_id = await self.db.upsert_politician(eu_politician)
                        disclosure.politician_id = politician_id

                    # Insert disclosure
                    disclosure_id = await self.db.insert_disclosure(disclosure)
                    if disclosure_id:
                        job.records_new += 1
                        job_result["new_disclosures"] += 1
                    else:
                        job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process EU member state disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"EU member states collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def _collect_us_states_data(self) -> Dict[str, Any]:
        """Collect US states financial disclosure data"""
        job_id = await self.db.create_data_pull_job("us_states", self.config.to_serializable_dict())

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id,
            job_type="us_states",
            status="running",
            started_at=datetime.utcnow(),
        )

        try:
            # Collect US states financial disclosures
            logger.info("Starting US states financial disclosures collection")
            us_states_disclosures = await run_us_states_workflow(self.config.scraping)

            job.records_found = len(us_states_disclosures)

            # Process each disclosure
            matcher = PoliticianMatcher(self.politicians)

            for disclosure in us_states_disclosures:
                try:
                    # For US states, find or create politician using real names from scrapers
                    if not disclosure.politician_id:
                        # Extract real politician name from raw data
                        politician_name = disclosure.raw_data.get("politician_name", "")
                        if not politician_name or politician_name.strip() == "":
                            logger.warning(
                                "Skipping US states disclosure with empty politician name"
                            )
                            job.records_failed += 1
                            continue

                        # Filter out obviously invalid politician names
                        if self._is_invalid_politician_name(politician_name):
                            logger.warning(
                                f"Skipping US states disclosure with invalid politician name: {politician_name}"
                            )
                            job.records_failed += 1
                            continue

                        # Try to find existing politician
                        politician = matcher.find_politician(politician_name)

                        if not politician:
                            # Create new politician with real name from scraper
                            state = disclosure.raw_data.get("state", "Unknown")
                            source = disclosure.raw_data.get("source", "unknown")

                            # Map state to appropriate role
                            role_map = {
                                "Texas": PoliticianRole.TEXAS_STATE_OFFICIAL,
                                "New York": PoliticianRole.NEW_YORK_STATE_OFFICIAL,
                                "Florida": PoliticianRole.FLORIDA_STATE_OFFICIAL,
                                "Illinois": PoliticianRole.ILLINOIS_STATE_OFFICIAL,
                                "Pennsylvania": PoliticianRole.PENNSYLVANIA_STATE_OFFICIAL,
                                "Massachusetts": PoliticianRole.MASSACHUSETTS_STATE_OFFICIAL,
                                "California": PoliticianRole.CALIFORNIA_STATE_OFFICIAL,
                            }

                            politician_role = role_map.get(state, PoliticianRole.US_HOUSE_REP)

                            # Parse real name into first/last components
                            name_parts = politician_name.strip().split()
                            if len(name_parts) >= 2:
                                first_name = name_parts[0]
                                last_name = " ".join(name_parts[1:])
                            else:
                                first_name = politician_name.strip()
                                last_name = ""

                            # Create politician with REAL name
                            state_politician = Politician(
                                first_name=first_name,
                                last_name=last_name,
                                full_name=politician_name.strip(),
                                role=politician_role,
                                state_or_country=state,
                            )
                            politician_id = await self.db.upsert_politician(state_politician)
                            disclosure.politician_id = politician_id
                            logger.info(f"Created new US state politician: {politician_name}")
                        else:
                            disclosure.politician_id = politician.id

                    # Insert disclosure
                    disclosure_id = await self.db.insert_disclosure(disclosure)
                    if disclosure_id:
                        job.records_new += 1
                        job_result["new_disclosures"] += 1
                    else:
                        job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process US state disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"US states collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def get_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        try:
            return await self.db.get_job_status()
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}

    async def run_quick_check(self) -> Dict[str, Any]:
        """Run a quick status check without full data collection"""
        try:
            status = await self.get_status()

            # Add some additional quick checks
            status["database_connection"] = "ok" if self.db.client else "failed"
            status["config_loaded"] = "ok" if self.config else "failed"
            status["timestamp"] = datetime.utcnow().isoformat()

            return status

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat(), "status": "failed"}

    def _is_invalid_politician_name(self, name: str) -> bool:
        """Check if a name is obviously not a politician name"""
        if not name or len(name.strip()) < 2:
            return True

        # Check for proper name structure first (before converting to uppercase)
        original_name = name.strip()
        import re

        if not re.search(r"[A-Za-z]", original_name):  # Should have at least one letter
            return True
        if re.search(r"^\d+", original_name):  # Starting with numbers
            return True

        # Now convert to uppercase for pattern matching
        name = original_name.upper()

        # Filter out obvious non-names
        invalid_patterns = [
            # Asset tickers and financial instruments
            r"^-.*CT$",  # -ETHEREUMCT, -DOGCT patterns
            r"^[A-Z]{2,5}$",  # Short all-caps (likely tickers)
            r"^\$",  # Starting with $
            # Municipal and financial terms
            r"MUNICIPAL",
            r"BOND",
            r"TRUST",
            r"FUND",
            r"CORP",
            r"INC\.$",
            r"LLC$",
            r"LP$",
            # Common non-name patterns
            r"^UNKNOWN",
            r"^TEST",
            r"^SAMPLE",
            # Crypto/financial asset patterns
            r"ETHEREUM",
            r"BITCOIN",
            r"CRYPTO",
        ]

        for pattern in invalid_patterns:
            if re.search(pattern, name):
                return True

        return False


# Standalone functions for cron job usage
async def run_politician_trading_collection() -> Dict[str, Any]:
    """Standalone function for cron job execution"""
    workflow = PoliticianTradingWorkflow()
    return await workflow.run_full_collection()


async def check_politician_trading_status() -> Dict[str, Any]:
    """Standalone function for status checking"""
    workflow = PoliticianTradingWorkflow()
    return await workflow.run_quick_check()
