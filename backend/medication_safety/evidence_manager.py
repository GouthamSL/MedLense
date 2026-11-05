"""Evidence manager loads reference CSV files and provides lookup utilities.

The manager is deliberately lightweight â€“ it only reads the CSVs once at
initialisation and caches the resulting pandas DataFrames.  All lookâ€‘ups are
caseâ€‘insensitive and return ``None`` when a record cannot be found, allowing
callers to emit a limitation rather than fabricate data.
"""

import pathlib
from typing import Optional, Tuple
import pandas as pd

# Resolve the projectâ€‘root ``database`` directory relative to this file.
BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "database"

class EvidenceManager:
    """Centralised access to the CSVâ€‘based knowledge base.

    The class loads three CSV files:
    * ``drugs.csv`` â€“ basic drug properties and dosage limits.
    * ``interactions.csv`` â€“ known pairwise drug interactions.
    * ``safety_rules.csv`` â€“ ruleâ€‘based contraindications (e.g. disease rules).
    """

    def __init__(self, base_dir: pathlib.Path | None = None) -> None:
        """Create an EvidenceManager.

        The constructor loads all CSV knowledge bases and records whether optional
        datasets are missing or empty.  This information is later used by the
        ``MedicationSafetyEngine`` to surface transparent limitations to the user.
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
        """Create an EvidenceManager.

        The constructor loads all CSV knowledge bases and records whether optional
        datasets are missing or empty.  This information is later used by the
        ``MedicationSafetyEngine`` to surface transparent limitations to the user.
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

        """Create an EvidenceManager.

        Parameters
        ----------
        base_dir: pathlib.Path | None
            Optional directory that contains the ``database`` folder.  If omitted,
            the manager falls back to the projectâ€‘root ``database`` directory.
        """
        # Resolve to the provided base directory or the default project root.
        if base_dir is None:
            base_dir = pathlib.Path(__file__).resolve().parents[2]
        db_dir = base_dir / "database"
        # Load CSVs lazily â€“ if a file is missing we keep an empty DataFrame.
        self.drugs_df = self._load_csv(db_dir / "drugs.csv")
        self.interactions_df = self._load_csv(db_dir / "interactions.csv")
        self.safety_rules_df = self._load_csv(db_dir / "safety_rules.csv")
        # Load adverse effects dataset (optional). If missing, an empty DataFrame is used.
        self.adverse_effects_df = self._load_csv(db_dir / "adverse_effects.csv")

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
    # Drug lookâ€‘ups
    # ---------------------------------------------------------------------
    def get_drug_record(self, medicine_name: str) -> Optional[pd.Series]:
        """Return the drug row matching *medicine_name* (caseâ€‘insensitive).

        The function returns ``None`` when the drug is not present in the CSV.
        """
        if self.drugs_df.empty:
            return None
        mask = self.drugs_df["medicine_name"].str.lower() == medicine_name.lower()
        matches = self.drugs_df[mask]
        if matches.empty:
            return None
        # Return the first match â€“ duplicate rows are unexpected but harmless.
        return matches.iloc[0]

    # ---------------------------------------------------------------------
    # Interaction lookâ€‘ups
    # ---------------------------------------------------------------------
    def get_interaction(self, med_a: str, med_b: str) -> Optional[Tuple[str, str, str]]:
        """Lookup a known interaction between *med_a* and *med_b*.

        Returns a tuple ``(severity, explanation, evidence_source)`` or ``None``
        if the pair is not recorded.  The CSV is considered orderâ€‘independent.
        """
        if self.interactions_df.empty:
            return None
        a = med_a.lower()
        b = med_b.lower()
        mask = (
            ((self.interactions_df["medicine_a"].str.lower() == a) & (self.interactions_df["medicine_b"].str.lower() == b)) |
            ((self.interactions_df["medicine_a"].str.lower() == b) & (self.interactions_df["medicine_b"].str.lower() == a))
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
    # Safety rule lookâ€‘ups (disease contraindications, etc.)
    # ---------------------------------------------------------------------
    def get_adverse_effects(self, active_ingredient: str, symptom: str) -> pd.DataFrame:
        """Return rows from ``adverse_effects.csv`` matching *active_ingredient* and *symptom*.

        Matching is caseâ€‘insensitive and uses straightforward normalisation (lowerâ€‘casing
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

        mask_type = self.safety_rules_df["rule_type"].fillna("").str.strip().str.lower() == "disease_contraindication"
        mask_name = self.safety_rules_df["medicine_name"].fillna("").str.strip().str.lower() == medicine_name.strip().lower()

        return self.safety_rules_df[mask_type & mask_name].copy()

