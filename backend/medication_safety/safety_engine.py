"""Safety engine that orchestrates all medication safety checks.

The engine is deliberately lightweight – it receives already‑parsed prescription
results (see ``backend.common.schemas``) and produces a ``SafetyAnalysisResult``
containing all findings from the individual checkers.
"""

from typing import List, Optional

from backend.common.schemas import PrescriptionResult, SafetyAnalysisResult, SafetyFinding

from .evidence_manager import EvidenceManager
from .interaction_checker import InteractionChecker
from .duplicate_checker import DuplicateChecker
from .dosage_checker import DosageChecker
from .allergy_checker import AllergyChecker
from .disease_checker import DiseaseChecker


class MedicationSafetyEngine:
    """Central engine that runs the full suite of safety checks.

    Parameters
    ----------
    evidence_manager : EvidenceManager | None
        Allows callers (e.g., tests) to inject a custom ``EvidenceManager`` that
        points at a temporary data directory.  If ``None`` the default manager
        loads the project‑wide CSV files.
    """

    def __init__(self, evidence_manager: Optional[EvidenceManager] = None):
        self.evidence = evidence_manager or EvidenceManager()
        # Initialise individual checkers, sharing the same evidence manager.
        self.interaction_checker = InteractionChecker(self.evidence)
        self.duplicate_checker = DuplicateChecker(self.evidence)
        self.dosage_checker = DosageChecker(self.evidence)
        self.allergy_checker = AllergyChecker(self.evidence)
        self.disease_checker = DiseaseChecker(self.evidence)

    def run(
        self,
        prescriptions: List[PrescriptionResult],
        allergies: Optional[List[str]] = None,
        patient_diseases: Optional[List[str]] = None,
    ) -> SafetyAnalysisResult:
        """Execute all safety checks and return a consolidated result.

        The method never raises on missing data – each checker reports its own
        ``information_missing`` findings.  ``analysis_status`` is set to
        ``"completed"`` unless no prescriptions are supplied, in which case it
        is ``"no_input"``.
        """
        if not prescriptions:
            return SafetyAnalysisResult(
                analysis_status="no_input",
                findings=[],
                limitations=["No prescription data provided."],
            )

        findings: List[SafetyFinding] = []
        findings.extend(self.interaction_checker.check(prescriptions))
        findings.extend(self.duplicate_checker.check(prescriptions))
        findings.extend(self.dosage_checker.check(prescriptions))
        findings.extend(self.allergy_checker.check(prescriptions, allergies))
        findings.extend(self.disease_checker.check(prescriptions, patient_diseases))

        # No additional limitations are collected here – individual checkers emit
        # ``information_missing`` findings where appropriate.
        return SafetyAnalysisResult(
            analysis_status="completed",
            findings=findings,
            limitations=[],
        )

