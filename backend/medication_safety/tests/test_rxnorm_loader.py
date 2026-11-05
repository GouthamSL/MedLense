"""RxNorm loader unit tests for MEDLENSE.

The tests verify that the CSV‑based loader works correctly, that it records
metadata in the evidence manifest, and that it does not interfere with the
existing EvidenceManager public API.
"""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from backend.medication_safety.evidence_manager import EvidenceManager
from backend.medication_safety.rxnorm_loader import RxNormLoader


class TestRxNormLoader(unittest.TestCase):
    def setUp(self):
        # Create a temporary workspace that mimics the project layout.
        self.tmp_root = Path(tempfile.mkdtemp())
        # Database folder and required sub‑folders.
        self.db_dir = self.tmp_root / "database"
        self.db_dir.mkdir(parents=True)
        (self.db_dir / "metadata").mkdir(parents=True)
        (self.db_dir / "public_sources" / "rxnorm").mkdir(parents=True)
        self.rxnorm_dir = self.db_dir / "public_sources" / "rxnorm"
        # Manifest path that EvidenceManager will use.
        self.manifest_path = self.db_dir / "metadata" / "evidence_manifest.json"

        # Build a valid CSV with intentional duplicate RxCUI and ambiguous names.
        self.valid_csv = self.rxnorm_dir / "rxnorm_medicines.csv"
        pd.DataFrame(
            [
                {
                    "rxnorm_id": "12345",
                    "medicine_name": "Paracetamol",
                    "normalized_name": "acetaminophen",
                    "active_ingredient": "acetaminophen",
                },
                {
                    "rxnorm_id": "67890",
                    "medicine_name": "Ibuprofen",
                    "normalized_name": "ibuprofen",
                    "active_ingredient": "ibuprofen",
                },
                # Duplicate RxCUI – should be deduplicated.
                {
                    "rxnorm_id": "12345",
                    "medicine_name": "Paracetamol Duplicate",
                    "normalized_name": "acetaminophen",
                    "active_ingredient": "acetaminophen",
                },
                # Same medicine name, different RxCUI – creates ambiguity.
                {
                    "rxnorm_id": "54321",
                    "medicine_name": "Paracetamol",
                    "normalized_name": "acetaminophen",
                    "active_ingredient": "acetaminophen",
                },
            ]
        ).to_csv(self.valid_csv, index=False)

    def _make_manager(self) -> EvidenceManager:
        """Instantiate an EvidenceManager that points at the temporary DB root."""
        return EvidenceManager(base_dir=self.tmp_root)

    # -----------------------------------------------------------------
    # 1. Valid CSV loading and duplicate RxCUI removal
    # -----------------------------------------------------------------
    def test_valid_csv_loading_and_deduplication(self):
        loader = RxNormLoader(csv_path=self.valid_csv)
        mgr = self._make_manager()
        loader.load(mgr)

        self.assertTrue(hasattr(mgr, "rxnorm_df"))
        df = mgr.rxnorm_df
        # Duplicate RxCUI (12345) should be removed → 3 rows total.
        self.assertEqual(len(df), 3)
        self.assertIn("12345", set(df["rxnorm_id"]))
        self.assertIn("67890", set(df["rxnorm_id"]))
        self.assertIn("54321", set(df["rxnorm_id"]))

    # -----------------------------------------------------------------
    # 2. Missing CSV handling
    # -----------------------------------------------------------------
    def test_missing_csv(self):
        missing_path = self.rxnorm_dir / "does_not_exist.csv"
        loader = RxNormLoader(csv_path=missing_path)
        mgr = self._make_manager()
        loader.load(mgr)
        self.assertTrue(hasattr(mgr, "rxnorm_df"))
        self.assertTrue(mgr.rxnorm_df.empty)

    # -----------------------------------------------------------------
    # 3. Missing required columns
    # -----------------------------------------------------------------
    def test_missing_required_columns(self):
        bad_csv = self.rxnorm_dir / "bad.csv"
        pd.DataFrame([
            {"rxnorm_id": "111", "medicine_name": "Aspirin"}  # missing normalized_name
        ]).to_csv(bad_csv, index=False)
        loader = RxNormLoader(csv_path=bad_csv)
        mgr = self._make_manager()
        with self.assertRaises(ValueError) as ctx:
            loader.load(mgr)
        self.assertIn("missing required columns", str(ctx.exception).lower())

    # -----------------------------------------------------------------
    # 4. Case‑insensitive medicine‑name lookup and ambiguity detection
    # -----------------------------------------------------------------
    def test_lookup_by_name_case_insensitive_and_ambiguous(self):
        loader = RxNormLoader(csv_path=self.valid_csv)
        mgr = self._make_manager()
        loader.load(mgr)

        # Exact name (case‑insensitive) – two rows share "Paracetamol"
        matches = loader.lookup_by_name("paracetamol")
        self.assertEqual(len(matches), 2)
        # Ensure each returned dict contains the required fields.
        for rec in matches:
            self.assertIn("rxnorm_id", rec)
            self.assertIn("medicine_name", rec)

    # -----------------------------------------------------------------
    # 5. Evidence manifest creation
    # -----------------------------------------------------------------
    def test_manifest_creation(self):
        loader = RxNormLoader(csv_path=self.valid_csv)
        mgr = self._make_manager()
        loader.load(mgr)
        # Manifest file should have been created.
        self.assertTrue(self.manifest_path.is_file())
        data = json.loads(self.manifest_path.read_text())
        self.assertIn("rxnorm", data)
        entry = data["rxnorm"]
        self.assertEqual(entry["path"], str(self.valid_csv))
        self.assertEqual(entry["version"], "1.0")
        self.assertIn("import_date", entry)

    # -----------------------------------------------------------------
    # 6. Manifest preservation of unrelated entries
    # -----------------------------------------------------------------
    def test_manifest_preserves_existing_entries(self):
        # Pre‑populate a dummy entry.
        dummy = {"dummy": {"path": "dummy.csv", "version": "0.1", "import_date": "2020-01-01"}}
        self.manifest_path.write_text(json.dumps(dummy), encoding="utf-8")

        loader = RxNormLoader(csv_path=self.valid_csv)
        mgr = self._make_manager()
        loader.load(mgr)

        data = json.loads(self.manifest_path.read_text())
        self.assertIn("rxnorm", data)
        self.assertIn("dummy", data)
        self.assertEqual(data["dummy"], dummy["dummy"])

    # -----------------------------------------------------------------
    # 7. Compatibility with existing EvidenceManager methods
    # -----------------------------------------------------------------
    def test_existing_manager_methods_unchanged(self):
        mgr = self._make_manager()
        # All core CSVs are empty in this temporary DB, so look‑ups should return
        # None or empty DataFrames as per the original contract.
        self.assertIsNone(mgr.get_drug_record("Anything"))
        self.assertIsNone(mgr.get_interaction("A", "B"))
        self.assertTrue(mgr.get_adverse_effects("ing", "sym").empty)
        self.assertTrue(mgr.get_disease_contraindications("Med").empty)


if __name__ == "__main__":
    unittest.main()
