"""Additional tests for Phase 2 covering symptom timeline and treatment response edge cases.

These tests do NOT modify existing behavior; they only verify that the modules
handle missing data and correctly identify trend directions.
"""

import unittest
import tempfile
import pathlib
import pandas as pd
from datetime import datetime, timedelta

from backend.common.schemas import PrescriptionResult, MedicineRecord
from backend.medication_safety.evidence_manager import EvidenceManager
from backend.medication_safety.symptom_timeline import SymptomTimelineChecker, SymptomRecord
from backend.medication_safety.treatment_response import TreatmentResponseChecker, SymptomSeverityRecord


class TestSymptomTimelineAndTreatmentResponse(unittest.TestCase):
    def setUp(self) -> None:
        # Build a minimal temporary database (same as in test_engine) – only the
        # required CSVs for the checkers to load without errors.
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        db_dir = self.tmp_dir / "database"
        db_dir.mkdir()
        # Minimal drugs.csv (empty is fine for these checkers)
        pd.DataFrame([]).to_csv(db_dir / "drugs.csv", index=False)
        pd.DataFrame([]).to_csv(db_dir / "interactions.csv", index=False)
        pd.DataFrame([]).to_csv(db_dir / "safety_rules.csv", index=False)
        # No adverse_effects.csv – intentional empty dataset.
        pd.DataFrame([]).to_csv(db_dir / "adverse_effects.csv", index=False)
        self.evidence = EvidenceManager(base_dir=self.tmp_dir)

    def make_prescription(self, prescription_id: str, medicines: list[dict]) -> PrescriptionResult:
        enriched = []
        for m in medicines:
            med = m.copy()
            med.setdefault('prescription_id', prescription_id)
            enriched.append(med)
        med_records = [MedicineRecord(**m) for m in enriched]
        return PrescriptionResult(prescription_id=prescription_id, medicines=med_records)

    def test_symptom_timeline_missing_dates(self):
        checker = SymptomTimelineChecker()
        prescription = self.make_prescription(
            "RX_1",
            [{"medicine_name": "Aspirin", "identification_status": "identified"}],
        )
        symptom = SymptomRecord(symptom_name="headache", onset=datetime.now())
        findings = checker.check([prescription], [symptom])  # no dates supplied
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")
        self.assertIn("Prescription start dates not provided", findings[0].explanation)

    def test_treatment_response_missing_dates(self):
        checker = TreatmentResponseChecker()
        prescription = self.make_prescription(
            "RX_1",
            [{"medicine_name": "Paracetamol", "identification_status": "identified"}],
        )
        symptom = SymptomSeverityRecord(
            symptom_name="fatigue",
            onset=datetime.now(),
            severity=5,
        )
        findings = checker.check([prescription], [symptom])  # missing dates
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")
        self.assertIn("Prescription start dates not supplied", findings[0].explanation)

    def test_treatment_response_missing_severity(self):
        checker = TreatmentResponseChecker()
        prescription = self.make_prescription(
            "RX_1",
            [{"medicine_name": "Penicillin", "identification_status": "identified"}],
        )
        start_date = datetime(2023, 1, 1)
        dates = {"RX_1": start_date}
        # One record before start with severity, one after without severity
        before = SymptomSeverityRecord(
            symptom_name="nausea",
            onset=start_date - timedelta(days=1),
            severity=7,
        )
        after = SymptomSeverityRecord(
            symptom_name="nausea",
            onset=start_date + timedelta(days=2),
            severity=None,
        )
        findings = checker.check([prescription], [before, after], dates)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")
        self.assertIn("Insufficient severity data", findings[0].explanation)

    def test_treatment_response_trends(self):
        checker = TreatmentResponseChecker()
        prescription = self.make_prescription(
            "RX_1",
            [{"medicine_name": "Ibuprofen", "identification_status": "identified"}],
        )
        start_date = datetime(2023, 5, 1)
        dates = {"RX_1": start_date}
        # Improved trend
        before = SymptomSeverityRecord(
            symptom_name="pain",
            onset=start_date - timedelta(days=1),
            severity=8,
        )
        after = SymptomSeverityRecord(
            symptom_name="pain",
            onset=start_date + timedelta(days=2),
            severity=4,
        )
        findings = checker.check([prescription], [before, after], dates)
        self.assertEqual(len(findings), 1)
        self.assertIn("improved", findings[0].explanation)
        self.assertEqual(findings[0].severity, "requires_review")

        # Worsened trend
        before.severity = 3
        after.severity = 6
        findings = checker.check([prescription], [before, after], dates)
        self.assertIn("worsened", findings[0].explanation)

        # No change trend
        before.severity = 5
        after.severity = 5
        findings = checker.check([prescription], [before, after], dates)
        self.assertIn("no_change", findings[0].explanation)

    def test_symptom_timeline_multiple_prescriptions(self):
        checker = SymptomTimelineChecker()
        # Two prescriptions with different start dates
        presc_a = self.make_prescription(
            "RX_A",
            [{"medicine_name": "DrugA", "identification_status": "identified"}],
        )
        presc_b = self.make_prescription(
            "RX_B",
            [{"medicine_name": "DrugB", "identification_status": "identified"}],
        )
        dates = {"RX_A": datetime(2023, 1, 1, 8, 0), "RX_B": datetime(2023, 1, 5, 9, 0)}
        symptom = SymptomRecord(symptom_name="dizziness", onset=datetime(2023, 1, 3, 12, 0))
        findings = checker.check([presc_a, presc_b], [symptom], dates)
        # Should associate with earliest prescription that started before the symptom (RX_A)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].source_a, "RX_A")
        self.assertEqual(findings[0].severity, "requires_review")

if __name__ == "__main__":
    unittest.main()

