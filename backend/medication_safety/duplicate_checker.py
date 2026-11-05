"""Duplicate active‑ingredient checker.

Detects medicines that share the same active ingredient within a single
prescription and across multiple prescriptions.
"""

from typing import List, Dict
from collections import defaultdict
from backend.common.schemas import PrescriptionResult, SafetyFinding
from .evidence_manager import EvidenceManager


class DuplicateChecker:
    """Find medicines that contain the same active ingredient.

    The check preserves the source prescription ID for each medicine.  It
    never classifies a duplicate as an overdose; the finding type is
    ``duplicate_ingredient`` and the severity is ``requires_review``.
    """

    def __init__(self, evidence_manager: EvidenceManager | None = None):
        self.evidence = evidence_manager or EvidenceManager()

    def check(self, prescriptions: List[PrescriptionResult]) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        # Map active ingredient -> list of (medicine_name, prescription_id)
        ingredient_map: Dict[str, List[tuple[str, str]]] = defaultdict(list)
        for presc in prescriptions:
            for med in presc.medicines:
                # Resolve active ingredient from the drug record if missing.
                ingredient = med.active_ingredient
                if not ingredient:
                    record = self.evidence.get_drug_record(med.medicine_name)
                    if record is not None:
                        ingredient = record.get("active_ingredient", "")
                if ingredient:
                    ingredient_map[ingredient.lower()].append((med.medicine_name, presc.prescription_id))
        # Identify duplicates (more than one entry for the same ingredient).
        for ing, entries in ingredient_map.items():
            if len(entries) < 2:
                continue
            # Create pairwise findings for every combination.
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    med_a, src_a = entries[i]
                    med_b, src_b = entries[j]
                    findings.append(
                        SafetyFinding(
                            finding_type="duplicate_ingredient",
                            medicine_a=med_a,
                            medicine_b=med_b,
                            source_a=src_a,
                            source_b=src_b,
                            severity="requires_review",
                            explanation="Both medicines share the same active ingredient.",
                            evidence_source=None,
                        )
                    )
        return findings

