"""Allergy checker for medication safety.

Compares each medicine's active ingredient against a provided list of known
allergies.  The checker respects the source prescription ID and does not make
assumptions when allergy information is missing.
"""

from typing import List, Optional
from backend.common.schemas import PrescriptionResult, SafetyFinding
from .evidence_manager import EvidenceManager


class AllergyChecker:
    """Detect potential allergy matches.

    The ``allergies`` argument is a list of active‑ingredient strings supplied
    by the user (e.g. ``["penicillin", "sulfa"]``).  If the list is empty or
    ``None`` the checker produces no findings.
    """

    def __init__(self, evidence_manager: EvidenceManager | None = None):
        self.evidence = evidence_manager or EvidenceManager()

    def check(self, prescriptions: List[PrescriptionResult], allergies: Optional[List[str]] = None) -> List[SafetyFinding]:
        if not allergies:
            return []
        lowered_allergies = {a.lower() for a in allergies if a}
        findings: List[SafetyFinding] = []
        for presc in prescriptions:
            for med in presc.medicines:
                ingredient = med.active_ingredient
                if not ingredient:
                    # Fallback to drug record if missing.
                    record = self.evidence.get_drug_record(med.medicine_name)
                    if record is not None:
                        ingredient = record.get("active_ingredient", "")
                if ingredient and ingredient.lower() in lowered_allergies:
                    findings.append(
                        SafetyFinding(
                            finding_type="allergy_match",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="requires_review",
                            explanation=f"Active ingredient '{ingredient}' matches a reported allergy.",
                            evidence_source=None,
                        )
                    )
        return findings

