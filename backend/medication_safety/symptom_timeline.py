"""Symptom timeline intelligence.

This module analyses patient‑reported symptom events in relation to medication
prescriptions.  It does **not** infer causation – it only reports temporal
associations and flags missing timing information.
"""

from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, ValidationError

from backend.common.schemas import PrescriptionResult, SafetyFinding


class SymptomRecord(BaseModel):
    """A single patient‑reported symptom event.

    Attributes
    ----------
    symptom_name: str
        Human‑readable name of the symptom (e.g. "headache").
    onset: datetime
        Timestamp when the symptom was first noticed.
    severity: Optional[int]
        Optional severity score (1‑10).  Not required for timeline analysis.
    """

    symptom_name: str
    onset: datetime
    severity: Optional[int] = None


class SymptomTimelineChecker:
    """Detect temporal relationships between symptoms and prescriptions.

    The caller may provide a mapping ``prescription_dates`` that links each
    ``prescription_id`` to a ``datetime`` representing when the medication was
    started.  If no date is supplied for a prescription, the checker records a
    limitation rather than guessing.
    """

    def __init__(self):
        pass

    def check(
        self,
        prescriptions: List[PrescriptionResult],
        symptoms: List[SymptomRecord],
        prescription_dates: Optional[Dict[str, datetime]] = None,
    ) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        # If we have no date information we cannot perform any temporal analysis.
        if not prescription_dates:
            for symptom in symptoms:
                findings.append(
                    SafetyFinding(
                        finding_type="symptom_timeline",
                        medicine_a=None,
                        medicine_b=None,
                        source_a=None,
                        source_b=None,
                        severity="information_missing",
                        explanation="Prescription start dates not provided; cannot assess temporal relationship.",
                        evidence_source=None,
                    )
                )
            return findings

        # Build quick lookup of prescription start dates.
        for symptom in symptoms:
            related_presc_ids = [
                pid for pid, start in prescription_dates.items() if start <= symptom.onset
            ]
            if related_presc_ids:
                # Report the earliest prescription that started before the symptom.
                earliest_id = min(
                    related_presc_ids, key=lambda pid: prescription_dates[pid]
                )
                findings.append(
                    SafetyFinding(
                        finding_type="symptom_timeline",
                        medicine_a=symptom.symptom_name,
                        medicine_b=None,
                        source_a=earliest_id,
                        source_b=None,
                        severity="requires_review",
                        explanation=f"Symptom '{symptom.symptom_name}' reported after prescription '{earliest_id}' start date.",
                        evidence_source=None,
                    )
                )
            else:
                # Symptom occurred before any known prescription start.
                findings.append(
                    SafetyFinding(
                        finding_type="symptom_timeline",
                        medicine_a=symptom.symptom_name,
                        medicine_b=None,
                        source_a=None,
                        source_b=None,
                        severity="information_missing",
                        explanation="Symptom occurred before any documented prescription start date.",
                        evidence_source=None,
                    )
                )
        return findings

