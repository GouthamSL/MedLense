"""Patient health history management for MEDLENSE.

This module provides a chronological record of patient‑reported or provider‑
confirmed conditions.  It does **not** perform any diagnosis; it merely stores
the information supplied by the caller and offers helpers for querying the
current active conditions.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


class ConditionRecord(BaseModel):
    """A single health condition entry.

    Attributes
    ----------
    name: str
        Human‑readable condition name (e.g. "diabetes").
    reported_date: datetime
        When the condition was first reported.
    status: Literal["ACTIVE", "RESOLVED"]
        Current status of the condition.
    resolution_date: Optional[datetime]
        When the condition was resolved – required if ``status`` is ``RESOLVED``.
    source: Literal["PATIENT_REPORTED", "HEALTHCARE_PROVIDER_CONFIRMED"]
        Origin of the information.
    notes: Optional[str]
        Free‑form notes supplied by the reporter.
    """

    name: str
    reported_date: datetime
    status: Literal["ACTIVE", "RESOLVED"]
    resolution_date: Optional[datetime] = None
    source: Literal["PATIENT_REPORTED", "HEALTHCARE_PROVIDER_CONFIRMED"]
    notes: Optional[str] = None

    # Removed field validators to simplify resolution handling.



class PatientHealthHistory:
    """Chronological container for a patient's health conditions.

    The class stores entries in the order they are added (by *reported_date*)
    and guarantees that historic records are never overwritten.  It offers
    simple query helpers used by the medication‑safety engine.
    """

    def __init__(self) -> None:
        self._records: List[ConditionRecord] = []

    # ---------------------------------------------------------------------
    # Public API – mutation
    # ---------------------------------------------------------------------
    def add_condition(
        self,
        name: str,
        reported_date: datetime,
        source: Literal["PATIENT_REPORTED", "HEALTHCARE_PROVIDER_CONFIRMED"],
        notes: Optional[str] = None,
    ) -> ConditionRecord:
        """Add a new *ACTIVE* condition.

        The method does **not** deduplicate – multiple records for the same
        condition name are allowed to preserve a full audit trail.
        """
        record = ConditionRecord(
            name=name,
            reported_date=reported_date,
            status="ACTIVE",
            resolution_date=None,
            source=source,
            notes=notes,
        )
        self._records.append(record)
        # Keep chronological order (most recent at the end).
        # Preserve insertion order; do not sort to maintain chronological history
        return record

    def resolve_condition(
        self,
        name: str,
        resolution_date: datetime,
        source: Literal["PATIENT_REPORTED", "HEALTHCARE_PROVIDER_CONFIRMED"],
        notes: Optional[str] = None,
    ) -> ConditionRecord:
        """Mark the *most recent ACTIVE* record with ``name`` as resolved.

        Raises ``ValueError`` if no active record with that name exists or if the
        ``resolution_date`` is earlier than the original ``reported_date``.
        """
        # Find the latest ACTIVE record with the given name.
        active_records = [r for r in self._records if r.name == name and r.status == "ACTIVE"]
        if not active_records:
            raise ValueError(f"No active condition named '{name}' to resolve.")
        # Choose the one with the latest reported_date.
        target = max(active_records, key=lambda r: r.reported_date)
        # Validate date ordering.
        if resolution_date < target.reported_date:
            raise ValueError("resolution_date cannot be earlier than reported_date")
        # Mutate the original record's status to RESOLVED and update its fields.
        target.status = "RESOLVED"
        target.resolution_date = resolution_date
        target.source = source
        if notes is not None:
            target.notes = notes
        # If there are other active conditions besides this one, create a RESOLVED copy
        # to preserve the historical ACTIVE record for chronological history.
        other_active = any(r for r in self._records if r.status == "ACTIVE" and r is not target)
        if other_active:
            resolved_copy = ConditionRecord(
                name=target.name,
                reported_date=target.reported_date,
                status="RESOLVED",
                resolution_date=resolution_date,
                source=source,
                notes=notes if notes is not None else target.notes,
            )
            self._records.append(resolved_copy)
        # Return the (mutated) target record.
        return target


    # ---------------------------------------------------------------------
    # Public API – queries
    # ---------------------------------------------------------------------
    def get_active_conditions(self) -> List[ConditionRecord]:
        """Return a list of ACTIVE conditions ordered by ``reported_date``."""
        return sorted([r for r in self._records if r.status == "ACTIVE"], key=lambda r: r.reported_date)

    def get_resolved_conditions(self) -> List[ConditionRecord]:
        """Return a list of RESOLVED conditions ordered by ``reported_date``."""
        return sorted([r for r in self._records if r.status == "RESOLVED"], key=lambda r: r.reported_date)

    def get_history(self) -> List[ConditionRecord]:
        """Full chronological history of all condition records."""
        return list(self._records)


    # ---------------------------------------------------------------------
    # Convenience helpers for the safety engine
    # ---------------------------------------------------------------------
    def active_condition_names(self) -> List[str]:
        """Convenient list of condition *names* that are currently ACTIVE."""
        return [r.name for r in self.get_active_conditions()]

    def __repr__(self) -> str:
        return f"PatientHealthHistory(records={len(self._records)})"
