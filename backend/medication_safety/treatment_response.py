"""Treatment response analysis.

This module evaluates changes in symptom severity before and after a given
prescription start date.  It never claims causation – it only reports whether
the observed trend could be relevant and flags the result for pharmacist
review.
"""

from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel

from backend.common.schemas import PrescriptionResult, SafetyFinding


class SymptomSeverityRecord(BaseModel):
    """A symptom observation with an optional severity score.

    ``onset`` is the timestamp of the observation. ``severity`` is an integer
    (typically 1‑10) where higher values indicate a worse symptom.
    """

    symptom_name: str
    onset: datetime
    severity: Optional[int] = None


class TreatmentResponseChecker:
    """Compare symptom severity before and after a prescription start.

    The method requires *prescription_dates* – a mapping of ``prescription_id``
    to ``datetime``.  When dates are missing the checker reports a limitation.
    """

    def __init__(self):
        pass

    def _average_severity(self, records: List[SymptomSeverityRecord]) -> Optional[float]:
        vals = [r.severity for r in records if r.severity is not None]
        return sum(vals) / len(vals) if vals else None

    def check(
        self,
        prescriptions: List[PrescriptionResult],
        symptoms: List[SymptomSeverityRecord],
        prescription_dates: Optional[Dict[str, datetime]] = None,
    ) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        if not prescription_dates:
            findings.append(
                SafetyFinding(
                    finding_type="treatment_response",
                    medicine_a=None,
                    medicine_b=None,
                    source_a=None,
                    source_b=None,
                    severity="information_missing",
                    explanation="Prescription start dates not supplied; cannot evaluate treatment response.",
                    evidence_source=None,
                )
            )
            return findings

        # For each prescription, split symptoms into before/after groups
        for presc in prescriptions:
            start = prescription_dates.get(presc.prescription_id)
            if not start:
                findings.append(
                    SafetyFinding(
                        finding_type="treatment_response",
                        medicine_a=None,
                        medicine_b=None,
                        source_a=presc.prescription_id,
                        source_b=None,
                        severity="information_missing",
                        explanation="Start date for prescription not provided.",
                        evidence_source=None,
                    )
                )
                continue
            before = [s for s in symptoms if s.onset < start]
            after = [s for s in symptoms if s.onset >= start]
            avg_before = self._average_severity(before)
            avg_after = self._average_severity(after)
            if avg_before is None or avg_after is None:
                findings.append(
                    SafetyFinding(
                        finding_type="treatment_response",
                        medicine_a=None,
                        medicine_b=None,
                        source_a=presc.prescription_id,
                        source_b=None,
                        severity="information_missing",
                        explanation="Insufficient severity data to assess response.",
                        evidence_source=None,
                    )
                )
                continue
            # Determine trend
            if avg_after < avg_before:
                trend = "improved"
            elif avg_after > avg_before:
                trend = "worsened"
            else:
                trend = "no_change"
            findings.append(
                SafetyFinding(
                    finding_type="treatment_response",
                    medicine_a=None,
                    medicine_b=None,
                    source_a=presc.prescription_id,
                    source_b=None,
                    severity="requires_review",
                    explanation=f"Symptoms {trend} after prescription start (avg severity {avg_before:.1f} → {avg_after:.1f}).",
                    evidence_source=None,
                )
            )
        return findings

