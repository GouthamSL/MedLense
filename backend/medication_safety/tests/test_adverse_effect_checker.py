"""Unit tests for the Adverse Effect Checker (Phase 2).

These tests cover the essential behaviours required for the hackathon sprint.
They use temporary CSV files so that no real clinical data is created.
"""

import unittest
import tempfile
import pathlib
import pandas as pd
from datetime import datetime

from backend.common.schemas import PrescriptionResult, MedicineRecord
from backend.medication_safety.adverse_effect_checker import AdverseEffectChecker
from backend.medication_safety.evidence_manager import EvidenceManager
from backend.medication_safety.symptom_timeline import SymptomRecord


class TestAdverseEffectChecker(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary workspace with a ``database`` sub‑folder.
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        (self.tmp_dir / "database").mkdir()

    def _make_manager(self) -> EvidenceManager:
        return EvidenceManager(base_dir=self.tmp_dir)

    def _make_prescription(self, med_name: str, active_ing: str | None = None) -> PrescriptionResult:
        med = MedicineRecord(
            medicine_name=med_name,
            active_ingredient=active_ing,
            prescription_id="RX_1",
            identification_status="identified",
        )
        return PrescriptionResult(prescription_id="RX_1", medicines=[med])

    def test_exact_match(self):
        # Write a single adverse‑effect row.
        df = pd.DataFrame([
            {
                "active_ingredient": "penicillin",
                "symptom": "rash",
                "severity": "high",
                "frequency": "",
                "evidence_source": "FDA",
                "reference_url": "http://example.com",
                "verified_date": "2023-01-01",
                "notes": "",
                "explanation": "Documented rash risk",
            }
        ])
        df.to_csv(self.tmp_dir / "database" / "adverse_effects.csv", index=False)
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("Penicillin", "penicillin")
        symptom = SymptomRecord(symptom_name="rash", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.finding_type, "possible_adverse_effect")
        self.assertEqual(f.medicine_a, "Penicillin")
        self.assertEqual(f.source_a, "RX_1")
        self.assertEqual(f.severity, "high")
        self.assertIn("rash", f.explanation.lower())
        self.assertEqual(f.evidence_source, "FDA")

    def test_no_match(self):
        # Same CSV but symptom that does not exist.
        df = pd.DataFrame([
            {
                "active_ingredient": "penicillin",
                "symptom": "rash",
                "severity": "high",
                "frequency": "",
                "evidence_source": "FDA",
                "reference_url": "http://example.com",
                "verified_date": "2023-01-01",
                "notes": "",
                "explanation": "Documented rash risk",
            }
        ])
        df.to_csv(self.tmp_dir / "database" / "adverse_effects.csv", index=False)
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("Penicillin", "penicillin")
        symptom = SymptomRecord(symptom_name="headache", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")
        self.assertIn("no matching adverse-effect record", findings[0].explanation.lower())

    def test_unknown_active_ingredient(self):
        # No adverse_effects rows, ingredient not known to the system.
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("UnknownDrug", None)
        symptom = SymptomRecord(symptom_name="rash", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "information_missing")
        self.assertIn("active ingredient unknown", findings[0].explanation.lower())

    def test_missing_active_ingredient(self):
        # Provide a medicine without an active ingredient; drug record also missing.
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("Aspirin", None)
        symptom = SymptomRecord(symptom_name="nausea", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        self.assertIn("active ingredient unknown", findings[0].explanation.lower())

    def test_missing_symptom(self):
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("Penicillin", "penicillin")
        # Symptom name is empty string
        symptom = SymptomRecord(symptom_name="", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        self.assertIn("symptom description missing", findings[0].explanation.lower())

    def test_empty_dataset(self):
        # Create an empty CSV (header only).
        (self.tmp_dir / "database" / "adverse_effects.csv").touch()
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("Penicillin", "penicillin")
        symptom = SymptomRecord(symptom_name="rash", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        self.assertIn("adverse-effect dataset not available", findings[0].explanation.lower())

    def test_prescription_source_attribution(self):
        df = pd.DataFrame([
            {
                "active_ingredient": "penicillin",
                "symptom": "rash",
                "severity": "high",
                "frequency": "",
                "evidence_source": "FDA",
                "reference_url": "http://example.com",
                "verified_date": "2023-01-01",
                "notes": "",
                "explanation": "Doc",
            }
        ])
        df.to_csv(self.tmp_dir / "database" / "adverse_effects.csv", index=False)
        manager = self._make_manager()
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = PrescriptionResult(
            prescription_id="RX_9",
            medicines=[MedicineRecord(medicine_name="Penicillin", active_ingredient="penicillin", prescription_id="RX_9", identification_status="identified")],
        )
        symptom = SymptomRecord(symptom_name="rash", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(findings[0].source_a, "RX_9")

    def test_missing_csv_file(self):
        # Do NOT create adverse_effects.csv at all.
        manager = self._make_manager()  # will load an empty DataFrame
        checker = AdverseEffectChecker(evidence_manager=manager)
        presc = self._make_prescription("Penicillin", "penicillin")
        symptom = SymptomRecord(symptom_name="rash", onset=datetime.now())
        findings = checker.check([presc], [symptom])
        self.assertEqual(len(findings), 1)
        self.assertIn("adverse-effect dataset not available", findings[0].explanation.lower())


if __name__ == "__main__":
    unittest.main()

