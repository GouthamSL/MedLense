"""Disease contraindication checker.

Uses ``safety_rules.csv`` where ``rule_type`` is ``disease_contraindication``.
Each row is expected to contain at least:
* ``medicine_name`` – the drug the rule applies to
* ``disease`` – the disease name
* ``severity``
* ``explanation``
* ``evidence_source`` (optional)

The checker receives a mapping of patient diseases (list of strings) and
produces a finding for each rule that matches both the medicine and a patient
disease.
"""

from typing import List
from backend.common.schemas import PrescriptionResult, SafetyFinding
from .evidence_manager import EvidenceManager


class DiseaseChecker:
    """Screen medicines against patient diseases using verified rules.

    If no matching rule exists, the engine reports a limitation rather than
    assuming safety.
    """

    def __init__(self, evidence_manager: EvidenceManager | None = None):
        self.evidence = evidence_manager or EvidenceManager()

    def check(self, prescriptions: List[PrescriptionResult], patient_diseases: List[str] | None = None) -> List[SafetyFinding]:
        if not patient_diseases:
            return []
        disease_set = {d.lower() for d in patient_diseases}
        findings: List[SafetyFinding] = []
        for presc in prescriptions:
            for med in presc.medicines:
                rules_df = self.evidence.get_disease_contraindications(med.medicine_name)
                if rules_df.empty:
                    continue
                for _, row in rules_df.iterrows():
                    rule_disease = str(row.get("disease", "")).lower()
                    if rule_disease in disease_set:
                        findings.append(
                            SafetyFinding(
                                finding_type="disease_contraindication",
                                medicine_a=med.medicine_name,
                                source_a=presc.prescription_id,
                                severity=row.get("severity", "requires_review"),
                                explanation=row.get("explanation", ""),
                                evidence_source=row.get("evidence_source", None),
                            )
                        )
        return findings

