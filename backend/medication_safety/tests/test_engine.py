"""Unit tests for the medication safety engine.

The tests build a temporary ``database`` directory with minimal CSV files that
exercise each checker.  The temporary directory is passed to ``EvidenceManager``
so the production data on disk is untouched.
"""

import unittest
import tempfile
import pathlib
import pandas as pd

from backend.common.schemas import PrescriptionResult, MedicineRecord
from backend.medication_safety.evidence_manager import EvidenceManager
from backend.medication_safety.safety_engine import MedicationSafetyEngine

class TestMedicationSafetyEngine(unittest.TestCase):
    def setUp(self) -> None:
        # Create temporary database directory with minimal CSVs
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        db_dir = self.tmp_dir / "database"
        db_dir.mkdir()
        # drugs.csv
        drugs = pd.DataFrame([
            {
                "medicine_name": "Aspirin",
                "active_ingredient": "acetylsalicylic acid",
                "strength": "500 mg",
                "max_daily_dose": "4000",
                "max_single_dose": "1000",
                "dose_units": "mg",
                "evidence_source": "DrugBank",
            },
            {
                "medicine_name": "Paracetamol",
                "active_ingredient": "acetaminophen",
                "strength": "500 mg",
                "max_daily_dose": "3000",
                "max_single_dose": "1000",
                "dose_units": "mg",
                "evidence_source": "DrugBank",
            },
            {
                "medicine_name": "Penicillin",
                "active_ingredient": "penicillin",
                "strength": "250 mg",
                "max_daily_dose": "2000",
                "max_single_dose": "500",
                "dose_units": "mg",
                "evidence_source": "DrugBank",
            },
        ])
        drugs.to_csv(db_dir / "drugs.csv", index=False)
        # interactions.csv
        interactions = pd.DataFrame([
            {
                "medicine_a": "Aspirin",
                "medicine_b": "Paracetamol",
                "severity": "moderate",
                "explanation": "Increased risk of bleeding.",
                "evidence_source": "FDA",
            }
        ])
        interactions.to_csv(db_dir / "interactions.csv", index=False)
        # safety_rules.csv
        safety_rules = pd.DataFrame([
            {
                "rule_type": "disease_contraindication",
                "medicine_name": "Penicillin",
                "disease": "mononucleosis",
                "severity": "high",
                "explanation": "Risk of rash.",
                "evidence_source": "ClinicalGuidelines",
            }
        ])
        safety_rules.to_csv(db_dir / "safety_rules.csv", index=False)
        self.evidence = EvidenceManager(base_dir=self.tmp_dir)

    def make_prescription(self, prescription_id: str, medicines: list[dict]) -> PrescriptionResult:
        # Ensure each medicine dict includes the prescription_id field required by the schema
        enriched = []
        for m in medicines:
            med = m.copy()
            med.setdefault('prescription_id', prescription_id)
            enriched.append(med)
        med_records = [MedicineRecord(**m) for m in enriched]
        return PrescriptionResult(prescription_id=prescription_id, medicines=med_records)


    def test_interaction_within_and_cross_prescriptions(self):
        rx_a = self.make_prescription(
            "RX_A",
            [{"medicine_name": "Aspirin", "active_ingredient": "acetylsalicylic acid", "strength": "500 mg", "dose": "1", "frequency": "once daily", "duration": "5", "identification_status": "identified"}],
        )
        rx_b = self.make_prescription(
            "RX_B",
            [{"medicine_name": "Paracetamol", "active_ingredient": "acetaminophen", "strength": "500 mg", "dose": "1", "frequency": "once daily", "duration": "5", "identification_status": "identified"}],
        )
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        result = engine.run([rx_a, rx_b])
        interactions = [f for f in result.findings if f.finding_type == "drug_interaction"]
        self.assertEqual(len(interactions), 1)
        inter = interactions[0]
        self.assertSetEqual({inter.medicine_a, inter.medicine_b}, {"Aspirin", "Paracetamol"})
        self.assertEqual(inter.source_a, "RX_A")
        self.assertEqual(inter.source_b, "RX_B")
        self.assertEqual(inter.severity, "moderate")

    def test_duplicate_active_ingredient(self):
        rx = self.make_prescription(
            "RX_1",
            [
                {"medicine_name": "Aspirin", "active_ingredient": "acetylsalicylic acid", "strength": "500 mg", "dose": "1", "frequency": "once daily", "duration": "5", "identification_status": "identified"},
                {"medicine_name": "Aspirin 500", "active_ingredient": "acetylsalicylic acid", "strength": "500 mg", "dose": "1", "frequency": "once daily", "duration": "5", "identification_status": "identified"},
            ],
        )
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        result = engine.run([rx])
        dupes = [f for f in result.findings if f.finding_type == "duplicate_ingredient"]
        self.assertEqual(len(dupes), 1)
        d = dupes[0]
        self.assertEqual(d.severity, "requires_review")
        self.assertEqual(d.source_a, d.source_b)
        self.assertEqual(d.source_a, "RX_1")

    def test_dosage_exceeds_limit(self):
        # within limit – no finding
        rx = self.make_prescription(
            "RX_D",
            [{"medicine_name": "Paracetamol", "strength": "500 mg", "dose": "3", "frequency": "twice daily", "duration": "5", "identification_status": "identified"}],
        )
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        result = engine.run([rx])
        dosage = [f for f in result.findings if f.finding_type == "dosage_issue"]
        self.assertEqual(len(dosage), 0)
        # exceed limit – high severity
        rx_exceed = self.make_prescription(
            "RX_EX",
            [{"medicine_name": "Paracetamol", "strength": "500 mg", "dose": "4", "frequency": "twice daily", "duration": "5", "identification_status": "identified"}],
        )
        result2 = engine.run([rx_exceed])
        dosage2 = [f for f in result2.findings if f.finding_type == "dosage_issue"]
        self.assertTrue(any(f.severity == "high" for f in dosage2))

    def test_allergy_match(self):
        rx = self.make_prescription(
            "RX_ALL",
            [{"medicine_name": "Penicillin", "identification_status": "identified"}],
        )
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        result = engine.run([rx], allergies=["penicillin"])
        allergy = [f for f in result.findings if f.finding_type == "allergy_match"]
        self.assertEqual(len(allergy), 1)
        self.assertEqual(allergy[0].medicine_a, "Penicillin")

    def test_disease_contraindication(self):
        rx = self.make_prescription(
            "RX_DIS",
            [{"medicine_name": "Penicillin", "identification_status": "identified"}],
        )
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        result = engine.run([rx], patient_diseases=["Mononucleosis"])
        disease = [f for f in result.findings if f.finding_type == "disease_contraindication"]
        self.assertEqual(len(disease), 1)
        self.assertEqual(disease[0].severity, "high")

    def test_unknown_medicine_and_missing_data(self):
        rx = self.make_prescription(
            "RX_U",
            [{"medicine_name": "UnknownDrug", "identification_status": "identified"}],
        )
        engine = MedicationSafetyEngine(evidence_manager=self.evidence)
        result = engine.run([rx])
        dosage = [f for f in result.findings if f.finding_type == "dosage_issue"]
        self.assertTrue(any(f.severity == "information_missing" for f in dosage))

    def test_empty_input(self):
        engine = MedicationSafetyEngine()
        result = engine.run([])
        self.assertEqual(result.analysis_status, "no_input")
        self.assertIn("No prescription data provided.", result.limitations)

if __name__ == "__main__":
    unittest.main()
