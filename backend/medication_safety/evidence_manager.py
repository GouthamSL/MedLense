"""Evidence manager loads reference CSV files and provides lookup utilities.

The manager is deliberately lightweight – it only reads the CSVs once at
initialisation and caches the resulting pandas DataFrames.  All look‑ups are
case‑insensitive and return ``None`` when a record cannot be found, allowing
callers to emit a limitation rather than fabricate data.
"""

import pathlib
from typing import Optional, Tuple
import pandas as pd

# Resolve the project‑root ``database`` directory relative to this file.
BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
DB_DIR = BASE_DIR / "database"

class EvidenceManager:
    """Centralised access to the CSV‑based knowledge base.

    The class loads three CSV files:
    * ``drugs.csv`` – basic drug properties and dosage limits.
    * ``interactions.csv`` – known pairwise drug interactions.
    * ``safety_rules.csv`` – rule‑based contraindications (e.g. disease rules).
    """

    def __init__(self, base_dir: pathlib.Path | None = None) -> None:
        """Create an EvidenceManager.

        Parameters
        ----------
        base_dir: pathlib.Path | None
            Optional directory that contains the ``database`` folder.  If omitted,
            the manager falls back to the project‑root ``database`` directory.
        """
        # Resolve to the provided base directory or the default project root.
        if base_dir is None:
            base_dir = pathlib.Path(__file__).resolve().parents[2]
        db_dir = base_dir / "database"
        # Load CSVs lazily – if a file is missing we keep an empty DataFrame.
        self.drugs_df = self._load_csv(db_dir / "drugs.csv")
        self.interactions_df = self._load_csv(db_dir / "interactions.csv")
        self.safety_rules_df = self._load_csv(db_dir / "safety_rules.csv")

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
    # Safety rule look‑ups (disease contraindications, etc.)
    # ---------------------------------------------------------------------
    def get_disease_contraindications(self, medicine_name: str) -> pd.DataFrame:
        """Return all rows from ``safety_rules.csv`` that apply to *medicine_name*.

        The CSV is expected to have a ``rule_type`` column.  Only rows where
        ``rule_type == "disease_contraindication"`` are returned.  Matching is
        case‑insensitive on the ``medicine_name`` column.
        """
        if self.safety_rules_df.empty:
            return pd.DataFrame()
        mask_type = self.safety_rules_df["rule_type"].str.lower() == "disease_contraindication"
        mask_name = self.safety_rules_df["medicine_name"].str.lower() == medicine_name.lower()
        return self.safety_rules_df[mask_type & mask_name]
