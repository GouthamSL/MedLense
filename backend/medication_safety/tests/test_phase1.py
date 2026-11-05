"""Unit tests for Phase 1: Symptom Timeline and Treatment Response.

These tests verify that the new checkers correctly handle provided dates,
missing dates, and basic severity trend detection.
"""

import unittest
from datetime import datetime, timedelta

from backend.common.schemas import PrescriptionResult, MedicineRecord
from backend.medication_safety.symptom_timeline import SymptomTimelineChecker, SymptomRecord
from backend.medication_safety.treatment_response import TreatmentResponseChecker, SymptomSeverityRecord


class TestPhase1Checkers(unittest.TestCase):
    def setUp(self) -> None:
        # Simple prescription with a known start date
        self.prescription = PrescriptionResult(
            prescription_id="RX_1",
            medicines=[
                MedicineRecord(
                    medicine_name="Aspirin",
                    active_ingredient="acetylsalicylic acid",
                    strength="500 mg",
                    dose="1",
                    frequency="once daily",
                    duration="5",
                    prescription_id="RX_1",
                    identification_status="identified",
                )
            ],
        )
        # Base start date
        self.start_date = datetime(2023, 1, 1, 9, 0, 0)
        self.prescription_dates = {"RX_1": self.start_date}

    def test_symptom_timeline_with_dates(self):
        checker = SymptomTimelineChecker()
        # Symptom occurring after prescription start
        symptom = SymptomRecord(
            symptom_name="headache",
            onset=self.start_date + timedelta(hours=2),
        )
        findings = checker.check([self.prescription], [symptom], self.prescription_dates)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.finding_type, "symptom_timeline")
        self.assertEqual(f.medicine_a, "headache")
        self.assertEqual(f.source_a, "RX_1")
        self.assertEqual(f.severity, "requires_review")

    def test_symptom_timeline_missing_dates(self):
        checker = SymptomTimelineChecker()
        symptom = SymptomRecord(
            symptom_name="nausea",
            onset=datetime.now(),
        )
        findings = checker.check([self.prescription], [symptom])  # no dates supplied
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")

    def test_treatment_response_improved(self):
        checker = TreatmentResponseChecker()
        # Two symptom observations, severity improves after start
        before = SymptomSeverityRecord(
            symptom_name="headache",
            onset=self.start_date - timedelta(days=1),
            severity=8,
        )
        after = SymptomSeverityRecord(
            symptom_name="headache",
            onset=self.start_date + timedelta(days=2),
            severity=4,
        )
        findings = checker.check([self.prescription], [before, after], self.prescription_dates)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.finding_type, "treatment_response")
        self.assertIn("improved", f.explanation)
        self.assertEqual(f.severity, "requires_review")

    def test_treatment_response_missing_dates(self):
        checker = TreatmentResponseChecker()
        symptom = SymptomSeverityRecord(
            symptom_name="fatigue",
            onset=datetime.now(),
            severity=5,
        )
        findings = checker.check([self.prescription], [symptom])  # missing dates
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")

if __name__ == "__main__":
    unittest.main()

