"""Interaction checker for medication safety.

Provides utilities to detect known drug‑drug interactions within a single
prescription and across multiple prescriptions.
"""

from typing import List
import itertools
from backend.common.schemas import PrescriptionResult, SafetyFinding
from .evidence_manager import EvidenceManager


class InteractionChecker:
    """Detect interactions using the ``interactions.csv`` dataset.

    The checker is order‑independent: a pair (A, B) is the same as (B, A).
    """

    def __init__(self, evidence_manager: EvidenceManager | None = None):
        self.evidence = evidence_manager or EvidenceManager()

    def _pairwise(self, meds: List[str]):
        """Yield unique unordered pairs of medicine names.
        """
        for a, b in itertools.combinations(meds, 2):
            yield a, b

    def check(self, prescriptions: List[PrescriptionResult]) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        # Build a mapping from prescription_id to list of medicine names.
        presc_map = {p.prescription_id: [m.medicine_name for m in p.medicines] for p in prescriptions}
        # Within‑prescription checks
        for pid, meds in presc_map.items():
            for med_a, med_b in self._pairwise(meds):
                interaction = self.evidence.get_interaction(med_a, med_b)
                if interaction:
                    severity, explanation, evidence_src = interaction
                    findings.append(
                        SafetyFinding(
                            finding_type="drug_interaction",
                            medicine_a=med_a,
                            medicine_b=med_b,
                            source_a=pid,
                            source_b=pid,
                            severity=severity,
                            explanation=explanation,
                            evidence_source=evidence_src,
                        )
                    )
        # Cross‑prescription checks
        presc_ids = list(presc_map.keys())
        for i in range(len(presc_ids)):
            for j in range(i + 1, len(presc_ids)):
                pid_a, pid_b = presc_ids[i], presc_ids[j]
                for med_a in presc_map[pid_a]:
                    for med_b in presc_map[pid_b]:
                        interaction = self.evidence.get_interaction(med_a, med_b)
                        if interaction:
                            severity, explanation, evidence_src = interaction
                            findings.append(
                                SafetyFinding(
                                    finding_type="drug_interaction",
                                    medicine_a=med_a,
                                    medicine_b=med_b,
                                    source_a=pid_a,
                                    source_b=pid_b,
                                    severity=severity,
                                    explanation=explanation,
                                    evidence_source=evidence_src,
                                )
                            )
        return findings

