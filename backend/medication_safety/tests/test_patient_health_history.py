"""Tests for the PatientHealthHistory module and integration with the safety engine.

These tests verify that conditions can be added, resolved, retrieved, and that the
DiseaseChecker respects the active‑condition list supplied by the history.
"""

import unittest
from datetime import datetime, timedelta

from backend.medication_safety.patient_health_history import PatientHealthHistory
from backend.common.schemas import PrescriptionResult, MedicineRecord
from backend.medication_safety.safety_engine import MedicationSafetyEngine
from backend.medication_safety.evidence_manager import EvidenceManager
import pandas as pd
import pathlib, tempfile


class TestPatientHealthHistory(unittest.TestCase):
    def setUp(self) -> None:
        # Minimal temporary database (same as other tests) – disease contraindication data will be added.
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        db_dir = self.tmp_dir / "database"
        db_dir.mkdir()
        # Empty CSVs for modules we don't need.
        pd.DataFrame([]).to_csv(db_dir / "drugs.csv", index=False)
        pd.DataFrame([]).to_csv(db_dir / "interactions.csv", index=False)
        # safety_rules.csv will contain a disease contraindication for "Flu" against "Penicillin".
        safety_rules = pd.DataFrame([
            {
                "rule_type": "disease_contraindication",
                "medicine_name": "Penicillin",
                "disease": "Flu",
                "severity": "high",
                "explanation": "Risk of severe reaction.",
                "evidence_source": "Guidelines",
            }
        ])
        safety_rules.to_csv(db_dir / "safety_rules.csv", index=False)
        pd.DataFrame([]).to_csv(db_dir / "adverse_effects.csv", index=False)
        self.evidence = EvidenceManager(base_dir=self.tmp_dir)
        # Simple prescription containing Penicillin.
        med = MedicineRecord(
            medicine_name="Penicillin",
            active_ingredient="penicillin",
            strength="250 mg",
            dose="1",
            frequency="once daily",
            duration="5",
            prescription_id="RX_1",
            identification_status="identified",
        )
        self.prescription = PrescriptionResult(prescription_id="RX_1", medicines=[med])

    def test_add_new_active_disease(self):
        ph = PatientHealthHistory()
        ph.add_condition(
            name="Flu",
            reported_date=datetime.now() - timedelta(days=2),
            source="PATIENT_REPORTED",
        )
        self.assertIn("Flu", ph.active_condition_names())
        self.assertEqual(len(ph.get_active_conditions()), 1)

    def test_add_second_active_disease_while_first_active(self):
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime.now() - timedelta(days=5), "PATIENT_REPORTED")
        ph.add_condition("Asthma", datetime.now() - timedelta(days=3), "HEALTHCARE_PROVIDER_CONFIRMED")
        active = ph.active_condition_names()
        self.assertCountEqual(active, ["Flu", "Asthma"])
        self.assertEqual(len(ph.get_active_conditions()), 2)

    def test_resolve_existing_disease(self):
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime.now() - timedelta(days=5), "PATIENT_REPORTED")
        ph.resolve_condition(
            name="Flu",
            resolution_date=datetime.now() - timedelta(days=1),
            source="HEALTHCARE_PROVIDER_CONFIRMED",
        )
        self.assertEqual(len(ph.get_active_conditions()), 0)
        self.assertEqual(len(ph.get_resolved_conditions()), 1)
        self.assertEqual(ph.get_resolved_conditions()[0].status, "RESOLVED")

    def test_preserve_resolved_history(self):
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime.now() - timedelta(days=10), "PATIENT_REPORTED")
        ph.resolve_condition("Flu", datetime.now() - timedelta(days=2), "PATIENT_REPORTED")
        # Add a new active disease
        ph.add_condition("Allergy", datetime.now() - timedelta(days=1), "PATIENT_REPORTED")
        self.assertEqual(len(ph.get_resolved_conditions()), 1)
        self.assertEqual(ph.get_resolved_conditions()[0].name, "Flu")
        self.assertIn("Allergy", ph.active_condition_names())

    def test_multiple_simultaneous_active_diseases(self):
        ph = PatientHealthHistory()
        for i in range(3):
            ph.add_condition(
                name=f"Condition{i}",
                reported_date=datetime.now() - timedelta(days=5 - i),
                source="PATIENT_REPORTED",
            )
        self.assertEqual(len(ph.get_active_conditions()), 3)
        self.assertCountEqual(ph.active_condition_names(), ["Condition0", "Condition1", "Condition2"])

    def test_chronological_history_retrieval(self):
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime(2023, 1, 1), "PATIENT_REPORTED")
        ph.add_condition("Asthma", datetime(2023, 2, 1), "HEALTHCARE_PROVIDER_CONFIRMED")
        ph.resolve_condition("Flu", datetime(2023, 3, 1), "HEALTHCARE_PROVIDER_CONFIRMED")
        history = ph.get_history()
        self.assertEqual([r.name for r in history], ["Flu", "Asthma", "Flu"])
        # The first Flu entry remains ACTIVE? Actually after resolution we replaced it with RESOLVED record.
        self.assertEqual(history[0].status, "RESOLVED")
        self.assertEqual(history[1].status, "ACTIVE")
        self.assertEqual(history[2].status, "RESOLVED")

    def test_invalid_status_transition(self):
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime.now(), "PATIENT_REPORTED")
        # Attempt to resolve with a date before reported_date – should raise ValueError from pydantic validation.
        with self.assertRaises(ValueError):
            ph.resolve_condition(
                name="Flu",
                resolution_date=datetime.now() - timedelta(days=1),
                source="PATIENT_REPORTED",
            )

    def test_source_preservation(self):
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime.now(), "PATIENT_REPORTED", notes="Mild symptoms")
        ph.resolve_condition("Flu", datetime.now() + timedelta(days=2), "HEALTHCARE_PROVIDER_CONFIRMED", notes="Doctor confirmed recovery")
        resolved = ph.get_resolved_conditions()[0]
        self.assertEqual(resolved.source, "HEALTHCARE_PROVIDER_CONFIRMED")
        self.assertEqual(resolved.notes, "Doctor confirmed recovery")

    def test_safety_reassessment_after_condition_change(self):
        # Build engine with temporary evidence manager.
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        # No diseases – should produce no disease contraindication findings.
        result_no_disease = engine.run([self.prescription], patient_diseases=[])
        self.assertFalse(any(f.finding_type == "disease_contraindication" for f in result_no_disease.findings))
        # Add active Flu condition via history and run again.
        ph = PatientHealthHistory()
        ph.add_condition("Flu", datetime.now() - timedelta(days=1), "PATIENT_REPORTED")
        result_with_flu = engine.run([self.prescription], patient_diseases=ph.active_condition_names())
        self.assertTrue(any(f.finding_type == "disease_contraindication" for f in result_with_flu.findings))
        # Resolve Flu – should remove contraindication.
        ph.resolve_condition("Flu", datetime.now(), "HEALTHCARE_PROVIDER_CONFIRMED")
        result_after_resolve = engine.run([self.prescription], patient_diseases=ph.active_condition_names())
        self.assertFalse(any(f.finding_type == "disease_contraindication" for f in result_after_resolve.findings))

if __name__ == '__main__':
    unittest.main()
