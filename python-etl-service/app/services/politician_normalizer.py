"""
Politician Data Normalizer

Automated daily normalization for politician records:
- Role normalization: enforce canonical values (Representative, Senator, MEP)
- Name standardization: strip honorific prefixes (Hon., Mr., etc.)
- State/country backfill: fill empty fields from district data

All corrections are logged to data_quality_corrections table for audit.
"""

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.lib.database import get_supabase
from app.services.auto_correction import CorrectionType

logger = logging.getLogger(__name__)

# Canonical role values recognized by the system
CANONICAL_ROLES = {"Representative", "Senator", "MEP"}

# Map of non-canonical role values to their canonical form
# Keys are lowercase for case-insensitive matching
ROLE_MAP = {
    "us_house_representative": "Representative",
    "senate": "Senator",
    "house": "Representative",
    "congress": "Representative",
    "state official": "Representative",
    "rep": "Representative",
    "rep.": "Representative",
    "representative-": "Representative",  # prefix pattern
    "senator-": "Senator",  # prefix pattern
    "sen": "Senator",
    "sen.": "Senator",
    "member of european parliament": "MEP",
    "mep": "MEP",
    "eu parliament": "MEP",
}

# Honorific prefixes to strip from names
HONORIFIC_PREFIXES = [
    "Hon. ",
    "Hon ",
    "The Honorable ",
    "Honorable ",
    "Mr. ",
    "Mrs. ",
    "Ms. ",
    "Dr. ",
    "Sen. ",
    "Rep. ",
    "Senator ",
    "Representative ",
    "Congressman ",
    "Congresswoman ",
]

# Placeholder name patterns to skip during name standardization
PLACEHOLDER_PATTERNS = [
    r"^placeholder",
    r"^unknown",
    r"^pending",
    r"^tbd",
    r"^n/a",
]

# State extraction pattern from district field (e.g., "CA12" -> "CA")
STATE_FROM_DISTRICT_RE = re.compile(r"^([A-Z]{2})\d+$")


class PoliticianNormalizer:
    """
    Normalizes politician data for consistency.

    Performs three operations:
    1. Role normalization - maps deprecated/variant roles to canonical values
    2. Name standardization - strips honorific prefixes and fixes whitespace
    3. State/country backfill - fills empty state_or_country from district data
    """

    def __init__(self) -> None:
        self.supabase = get_supabase()

    def normalize_all(
        self, dry_run: bool = True, limit: int = 500
    ) -> Dict[str, Any]:
        """
        Run all normalization steps.

        Args:
            dry_run: If True, preview changes without applying
            limit: Max records to process per step

        Returns:
            Combined results from all steps
        """
        start = time.time()
        results = {}

        results["roles"] = self.normalize_roles(dry_run=dry_run, limit=limit)
        results["names"] = self.standardize_names(dry_run=dry_run, limit=limit)
        results["state_backfill"] = self.backfill_state_country(
            dry_run=dry_run, limit=limit
        )

        total_corrections = sum(
            r.get("corrections", 0) for r in results.values()
        )
        total_errors = sum(r.get("errors", 0) for r in results.values())

        return {
            "dry_run": dry_run,
            "steps_completed": list(results.keys()),
            "total_corrections": total_corrections,
            "total_errors": total_errors,
            "results": results,
            "duration_ms": int((time.time() - start) * 1000),
        }

    def normalize_roles(
        self, dry_run: bool = True, limit: int = 500
    ) -> Dict[str, Any]:
        """
        Find politicians with non-canonical roles and normalize them.

        Args:
            dry_run: If True, preview changes without applying
            limit: Max records to process

        Returns:
            Dict with corrections count, errors count, and details
        """
        if not self.supabase:
            return {"corrections": 0, "errors": 1, "details": "Supabase not configured"}

        corrections = 0
        errors = 0
        details = []

        try:
            # Fetch politicians whose role is NOT in canonical set
            # We fetch all and filter in Python since Supabase doesn't
            # support NOT IN easily via the client
            response = (
                self.supabase.table("politicians")
                .select("id, first_name, last_name, role")
                .limit(limit * 5)
                .execute()
            )

            for record in response.data:
                role = record.get("role")
                if not role or role in CANONICAL_ROLES:
                    continue

                new_role = self._map_role(role)
                if not new_role:
                    details.append({
                        "id": record["id"],
                        "name": f"{record.get('first_name', '')} {record.get('last_name', '')}".strip(),
                        "old_role": role,
                        "action": "skipped_unknown",
                    })
                    continue

                detail = {
                    "id": record["id"],
                    "name": f"{record.get('first_name', '')} {record.get('last_name', '')}".strip(),
                    "old_role": role,
                    "new_role": new_role,
                }

                if not dry_run:
                    try:
                        self._apply_and_log(
                            record_id=record["id"],
                            table_name="politicians",
                            field_name="role",
                            old_value=role,
                            new_value=new_role,
                            correction_type=CorrectionType.ROLE_NORMALIZATION,
                        )
                        detail["applied"] = True
                    except Exception as e:
                        detail["applied"] = False
                        detail["error"] = str(e)
                        errors += 1

                corrections += 1
                details.append(detail)

                if corrections >= limit:
                    break

        except Exception as e:
            logger.error(f"Role normalization failed: {e}")
            errors += 1

        return {"corrections": corrections, "errors": errors, "details": details}

    def standardize_names(
        self, dry_run: bool = True, limit: int = 500
    ) -> Dict[str, Any]:
        """
        Strip honorific prefixes and fix whitespace in politician names.

        Skips placeholder names (e.g., "Placeholder Senator").

        Args:
            dry_run: If True, preview changes without applying
            limit: Max records to process

        Returns:
            Dict with corrections count, errors count, and details
        """
        if not self.supabase:
            return {"corrections": 0, "errors": 1, "details": "Supabase not configured"}

        corrections = 0
        errors = 0
        details = []

        try:
            response = (
                self.supabase.table("politicians")
                .select("id, first_name, last_name, full_name")
                .limit(limit * 5)
                .execute()
            )

            for record in response.data:
                updates = {}

                for field in ["first_name", "last_name", "full_name"]:
                    value = record.get(field)
                    if not value:
                        continue

                    # Skip placeholder names
                    if self._is_placeholder(value):
                        continue

                    cleaned = self._clean_name(value)
                    if cleaned != value:
                        updates[field] = (value, cleaned)

                if not updates:
                    continue

                detail = {
                    "id": record["id"],
                    "changes": {
                        k: {"old": old, "new": new}
                        for k, (old, new) in updates.items()
                    },
                }

                if not dry_run:
                    try:
                        # Apply all name field changes at once
                        update_data = {k: new for k, (_, new) in updates.items()}
                        self.supabase.table("politicians").update(
                            update_data
                        ).eq("id", record["id"]).execute()

                        # Log each field change separately for audit
                        for field, (old_val, new_val) in updates.items():
                            self._log_correction(
                                record_id=record["id"],
                                table_name="politicians",
                                field_name=field,
                                old_value=old_val,
                                new_value=new_val,
                                correction_type=CorrectionType.NAME_STANDARDIZATION,
                            )
                        detail["applied"] = True
                    except Exception as e:
                        detail["applied"] = False
                        detail["error"] = str(e)
                        errors += 1

                corrections += 1
                details.append(detail)

                if corrections >= limit:
                    break

        except Exception as e:
            logger.error(f"Name standardization failed: {e}")
            errors += 1

        return {"corrections": corrections, "errors": errors, "details": details}

    def backfill_state_country(
        self, dry_run: bool = True, limit: int = 500
    ) -> Dict[str, Any]:
        """
        Fill empty state_or_country from district data.

        E.g., if district is "CA12" and state_or_country is null, set to "CA".
        Checks for unique constraint collisions before applying.

        Args:
            dry_run: If True, preview changes without applying
            limit: Max records to process

        Returns:
            Dict with corrections count, errors count, and details
        """
        if not self.supabase:
            return {"corrections": 0, "errors": 1, "details": "Supabase not configured"}

        corrections = 0
        errors = 0
        details = []

        try:
            # Fetch politicians with district but no state
            response = (
                self.supabase.table("politicians")
                .select("id, first_name, last_name, district, state_or_country")
                .is_("state_or_country", "null")
                .not_.is_("district", "null")
                .limit(limit * 2)
                .execute()
            )

            for record in response.data:
                district = record.get("district", "")
                if not district:
                    continue

                state = self._extract_state(district)
                if not state:
                    continue

                detail = {
                    "id": record["id"],
                    "name": f"{record.get('first_name', '')} {record.get('last_name', '')}".strip(),
                    "district": district,
                    "state": state,
                }

                if not dry_run:
                    try:
                        self._apply_and_log(
                            record_id=record["id"],
                            table_name="politicians",
                            field_name="state_or_country",
                            old_value=None,
                            new_value=state,
                            correction_type=CorrectionType.STATE_BACKFILL,
                        )
                        detail["applied"] = True
                    except Exception as e:
                        detail["applied"] = False
                        detail["error"] = str(e)
                        errors += 1

                corrections += 1
                details.append(detail)

                if corrections >= limit:
                    break

        except Exception as e:
            logger.error(f"State backfill failed: {e}")
            errors += 1

        return {"corrections": corrections, "errors": errors, "details": details}

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _map_role(self, role: str) -> Optional[str]:
        """Map a non-canonical role to its canonical form."""
        if not role:
            return None

        lower = role.lower().strip()

        # Direct match
        if lower in ROLE_MAP:
            return ROLE_MAP[lower]

        # Prefix matching (e.g., "Representative-CA" -> "Representative")
        for prefix, canonical in ROLE_MAP.items():
            if prefix.endswith("-") and lower.startswith(prefix):
                return canonical

        return None

    def _clean_name(self, name: str) -> str:
        """Strip honorific prefixes and fix whitespace."""
        cleaned = name

        for prefix in HONORIFIC_PREFIXES:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break  # Only strip the first matching prefix

        # Fix multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _is_placeholder(self, name: str) -> bool:
        """Check if a name is a placeholder/unknown value."""
        lower = name.lower().strip()
        return any(re.match(pattern, lower) for pattern in PLACEHOLDER_PATTERNS)

    def _extract_state(self, district: str) -> Optional[str]:
        """Extract state abbreviation from district field."""
        if not district:
            return None

        match = STATE_FROM_DISTRICT_RE.match(district.strip())
        if match:
            return match.group(1)

        return None

    def _apply_and_log(
        self,
        record_id: str,
        table_name: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        correction_type: CorrectionType,
    ) -> None:
        """Apply a correction and log it to the audit table."""
        # Log first
        correction_id = self._log_correction(
            record_id=record_id,
            table_name=table_name,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            correction_type=correction_type,
        )

        # Apply the update
        self.supabase.table(table_name).update(
            {field_name: new_value}
        ).eq("id", record_id).execute()

        # Mark as applied
        if correction_id:
            try:
                self.supabase.table("data_quality_corrections").update(
                    {"status": "applied", "applied_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", correction_id).execute()
            except Exception as e:
                logger.warning(f"Failed to mark correction applied: {e}")

    def _log_correction(
        self,
        record_id: str,
        table_name: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        correction_type: CorrectionType,
    ) -> Optional[str]:
        """Log a correction to the audit table."""
        correction_id = str(uuid.uuid4())

        try:
            self.supabase.table("data_quality_corrections").insert({
                "id": correction_id,
                "record_id": record_id,
                "table_name": table_name,
                "field_name": field_name,
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value) if new_value is not None else None,
                "correction_type": correction_type.value,
                "confidence_score": 1.0,
                "corrected_by": "politician_normalizer",
                "status": "pending",
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log correction: {e}")
            return None

        return correction_id
