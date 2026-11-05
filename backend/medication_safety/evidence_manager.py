"""Evidence manager loads reference CSV files and provides lookup utilities.

The manager is deliberately lightweight – it only reads the CSVs once at
initialisation and caches the resulting pandas DataFrames.  All look‑ups are
case‑insensitive and return ``None`` when a record cannot be found, allowing
callers to emit a limitation rather than fabricate data.
"""

import pathlib
import json
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd

# Resolve the project‑root ``database`` directory relative to this file.
BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "database"


class EvidenceManager:
    """Centralised access to the CSV‑based knowledge base.

    The class loads three core CSV files (drugs, interactions, safety rules) and
    an optional adverse‑effects file.  It also supports a manifest that records
    metadata about imported public‑source datasets (e.g. RxNorm).
    """

    def __init__(self, base_dir: pathlib.Path | None = None) -> None:
        """Create an EvidenceManager.

        The constructor loads all CSV knowledge bases and records whether optional
        datasets are missing or empty.  It also prepares the manifest handling.
        """
        # Resolve to the provided base directory or the default project root.
        if base_dir is None:
            base_dir = pathlib.Path(__file__).resolve().parents[2]
        db_dir = base_dir / "database"

        # Load CSVs lazily – if a file is missing we keep an empty DataFrame.
        self.drugs_df = self._load_csv(db_dir / "drugs.csv")
        self.interactions_df = self._load_csv(db_dir / "interactions.csv")
        self.safety_rules_df = self._load_csv(db_dir / "safety_rules.csv")
        # Load adverse effects dataset (optional). If missing, an empty DataFrame is used.
        self.adverse_effects_df = self._load_csv(db_dir / "adverse_effects.csv")

        # Flags for optional knowledge sources – used for transparent reporting.
        self._missing_adverse_effects = self.adverse_effects_df.empty

        # Manifest handling – ensure the manifest file exists and is a dict.
        self._manifest_path = base_dir / "database" / "metadata" / "evidence_manifest.json"
        self._ensure_manifest()

    # ---------------------------------------------------------------------
    # Private helpers for manifest handling
    # ---------------------------------------------------------------------
    def _ensure_manifest(self) -> None:
        """Guarantee that the manifest file exists and contains a JSON object.

        If the file does not exist, it is created with an empty JSON object.
        If the file is malformed or does not contain a JSON object (e.g. a list, string, or number),
        it is overwritten with an empty JSON object.
        """
        manifest_dir = self._manifest_path.parent
        manifest_dir.mkdir(parents=True, exist_ok=True)
        if not self._manifest_path.is_file():
            self._manifest_path.write_text(json.dumps({}), encoding="utf-8")
            self._manifest_data = {}
            return
        try:
            content = self._manifest_path.read_text(encoding="utf-8")
            data = json.loads(content) if content.strip() else {}
        except (json.JSONDecodeError, OSError):
            data = {}
        # Ensure the manifest data is a dict; otherwise reset.
        if not isinstance(data, dict):
            data = {}
        self._manifest_data = data
        # Write back in case we fixed malformed or wrong‑type content.
        self._manifest_path.write_text(json.dumps(self._manifest_data, indent=2), encoding="utf-8")

    def _record_manifest_entry(
        self,
        name: str,
        path: str,
        version: str,
        import_date: str | None = None,
        source: str | None = None,
        license: str | None = None,
    ) -> None:
        """Record (or update) a manifest entry for a public‑source dataset.

        The manifest is stored as a JSON object where each top‑level key is the
        dataset ``name`` (e.g. ``"rxnorm"``).  Existing entries for other datasets
        are preserved.
        """
        if import_date is None:
            import_date = datetime.utcnow().isoformat()
        entry = {
            "path": path,
            "version": version,
            "import_date": import_date,
        }
        if source:
            entry["source"] = source
        if license:
            entry["license"] = license
        # Update in‑memory manifest and write back to disk.
        self._manifest_data[name] = entry
        try:
            self._manifest_path.write_text(
                json.dumps(self._manifest_data, indent=2), encoding="utf-8"
            )
        except OSError:
            # In a production setting we would log this; for now we silently ignore.
            pass

    # ---------------------------------------------------------------------
    # CSV loader
    # ---------------------------------------------------------------------
    @staticmethod
    def _load_csv(path: pathlib.Path) -> pd.DataFrame:
        """Load a CSV safely.
        Returns an empty DataFrame if the file does not exist or is empty.
        """
        try:
            df = pd.read_csv(path, dtype=str)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            df = pd.DataFrame()
        # Fill NaN with empty strings for uniform handling
        if not df.empty:
            df = df.fillna("")
        return df

    # ---------------------------------------------------------------------
    # Drug look‑ups
    # ---------------------------------------------------------------------
    def get_drug_record(self, medicine_name: str) -> Optional[pd.Series]:
        """Return the drug row matching *medicine_name* (case‑insensitive).

        The function returns ``None`` when the drug is not present in the CSV.
        """
        if self.drugs_df.empty:
            return None
        mask = self.drugs_df["medicine_name"].str.lower() == medicine_name.lower()
        matches = self.drugs_df[mask]
        if matches.empty:
            return None
        # Return the first match – duplicate rows are unexpected but harmless.
        return matches.iloc[0]

    # ---------------------------------------------------------------------
    # Interaction look‑ups
    # ---------------------------------------------------------------------
    def get_interaction(self, med_a: str, med_b: str) -> Optional[Tuple[str, str, str]]:
        """Lookup a known interaction between *med_a* and *med_b*.

        Returns a tuple ``(severity, explanation, evidence_source)`` or ``None``
        if the pair is not recorded.  The CSV is considered order‑independent.
        """
        if self.interactions_df.empty:
            return None
        a = med_a.lower()
        b = med_b.lower()
        mask = (
            ((self.interactions_df["medicine_a"].str.lower() == a) & (self.interactions_df["medicine_b"].str.lower() == b))
            | ((self.interactions_df["medicine_a"].str.lower() == b) & (self.interactions_df["medicine_b"].str.lower() == a))
        )
        matches = self.interactions_df[mask]
        if matches.empty:
            return None
        row = matches.iloc[0]
        severity = row.get("severity", "") or "unknown"
        explanation = row.get("explanation", "") or "No explanation provided"
        evidence = row.get("evidence_source", "") or None
        return severity, explanation, evidence

    # ---------------------------------------------------------------------
    # Safety rule look‑ups (disease contraindications, etc.)
    # ---------------------------------------------------------------------
    def get_adverse_effects(self, active_ingredient: str, symptom: str) -> pd.DataFrame:
        """Return rows from ``adverse_effects.csv`` matching *active_ingredient* and *symptom*.

        Matching is case‑insensitive and uses straightforward normalisation (lower‑casing
        and stripping surrounding whitespace).  The caller may apply additional
        synonym handling if desired.
        """
        if self.adverse_effects_df.empty:
            return pd.DataFrame()
        ing_mask = self.adverse_effects_df["active_ingredient"].str.lower() == active_ingredient.lower()
        sym_mask = self.adverse_effects_df["symptom"].str.lower() == symptom.lower()
        return self.adverse_effects_df[ing_mask & sym_mask]

    def get_disease_contraindications(self, medicine_name: str) -> pd.DataFrame:
        """Return disease contraindication rules for a medicine."""
        if self.safety_rules_df.empty:
            return pd.DataFrame()
        required = {"rule_type", "medicine_name", "disease"}
        if not required.issubset(self.safety_rules_df.columns):
            return pd.DataFrame()
        mask_type = (
            self.safety_rules_df["rule_type"].fillna("").str.strip().str.lower()
            == "disease_contraindication"
        )
        mask_name = (
            self.safety_rules_df["medicine_name"].fillna("").str.strip().str.lower()
            == medicine_name.strip().lower()
        )
        return self.safety_rules_df[mask_type & mask_name].copy()
