"""Adverse-effect checker for medication safety.

The checker matches patient-reported symptoms against a curated ``adverse_effects``
CSV that links *active ingredients* to documented adverse-effect symptoms.
Only exact, normalised symptom matches are used â€“ no fuzzy matching is performed.
If the dataset is missing, or required fields are unavailable, the checker emits
findings with ``severity="information_missing"`` to indicate a limitation rather
than fabricating a clinical claim.
"""

from typing import List, Optional

from backend.common.schemas import PrescriptionResult, SafetyFinding
from .evidence_manager import EvidenceManager
from .symptom_timeline import SymptomRecord


class AdverseEffectChecker:
    """Detect possible adverse-effect associations.

    Parameters
    ----------
    evidence_manager: EvidenceManager | None
        Allows injection of a custom manager (e.g., pointing at a temporary test
        database). If ``None`` the default manager loads the project-wide CSV files.

    Usage
    -----
    >>> checker = AdverseEffectChecker()
    >>> findings = checker.check(prescriptions, symptoms)
    """

    def __init__(self, evidence_manager: Optional[EvidenceManager] = None):
        self.evidence = evidence_manager or EvidenceManager()

    @staticmethod
    def _normalise(text: str) -> str:
        """Simple normalisation: lower-case and strip surrounding whitespace.
        Punctuation that is not part of the word is stripped.
        """
        return text.lower().strip()

    def _resolve_active_ingredient(self, med_name: str, provided: Optional[str]) -> Optional[str]:
        """Return the active ingredient for a medicine.
        Preference is given to the value supplied on the ``MedicineRecord``.
        If missing, a drug record is looked up via ``EvidenceManager``.
        """
        if provided:
            return provided
        record = self.evidence.get_drug_record(med_name)
        if record is not None:
            return record.get("active_ingredient", "") or None
        return None

    def check(
        self,
        prescriptions: List[PrescriptionResult],
        symptoms: List[SymptomRecord] | None = None,
    ) -> List[SafetyFinding]:
        """Run the adverse-effect analysis.

        Returns a list of ``SafetyFinding`` objects.  When the adverse-effect
        dataset is unavailable a single ``information_missing`` finding is added
        for each medicine-symptom pair to make the limitation explicit.
        """
        findings: List[SafetyFinding] = []
        if not symptoms:
            # No symptom information â€“ nothing to match.
            return findings

        # If the CSV is empty, treat it as a limitation for every pair.
        dataset_empty = self.evidence.adverse_effects_df.empty

        for presc in prescriptions:
            for med in presc.medicines:
                ingredient = self._resolve_active_ingredient(med.medicine_name, med.active_ingredient)
                if not ingredient:
                    # Missing active-ingredient information â€“ report limitation.
                    findings.append(
                        SafetyFinding(
                            finding_type="possible_adverse_effect",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="information_missing",
                            explanation="Active ingredient unknown; cannot check adverse effects.",
                            evidence_source=None,
                        )
                    )
                    continue
                for symptom in symptoms:
                    if not symptom.symptom_name:
                        findings.append(
                            SafetyFinding(
                                finding_type="possible_adverse_effect",
                                medicine_a=med.medicine_name,
                                source_a=presc.prescription_id,
                                severity="information_missing",
                                explanation="Symptom description missing; cannot match adverse effect.",
                                evidence_source=None,
                            )
                        )
                        continue
                    # Normalise strings for exact matching.
                    sym_norm = self._normalise(symptom.symptom_name)
                    ing_norm = self._normalise(ingredient)
                    if dataset_empty:
                        findings.append(
                            SafetyFinding(
                                finding_type="possible_adverse_effect",
                                medicine_a=med.medicine_name,
                                source_a=presc.prescription_id,
                                severity="information_missing",
                                explanation="Adverse-effect dataset not available; cannot evaluate.",
                                evidence_source=None,
                            )
                        )
                        continue
                    matches = self.evidence.get_adverse_effects(ing_norm, sym_norm)
                    if matches.empty:
                        # No recorded adverse effect â€“ report a limitation rather than a safe claim.
                        findings.append(
                            SafetyFinding(
                                finding_type="possible_adverse_effect",
                                medicine_a=med.medicine_name,
                                source_a=presc.prescription_id,
                                severity="information_missing",
                                explanation="No matching adverse-effect record found for this symptom.",
                                evidence_source=None,
                            )
                        )
                    else:
                        # One or more rows â€“ create a finding per row.
                        for _, row in matches.iterrows():
                            findings.append(
                                SafetyFinding(
                                    finding_type="possible_adverse_effect",
                                    medicine_a=med.medicine_name,
                                    source_a=presc.prescription_id,
                                    severity=row.get("severity", "requires_review"),
                                    explanation=row.get("explanation", ""),
                                    evidence_source=row.get("evidence_source", None),
                                )
                            )
        return findings


