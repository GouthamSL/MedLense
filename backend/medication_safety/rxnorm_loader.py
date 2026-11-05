"""RxNorm data loader for MEDLENSE.

This module provides a small, offline‑only loader that reads a curated CSV file
containing a subset of RxNorm concepts useful for the medication‑safety engine.

The CSV is expected to live under ``database/public_sources/rxnorm/`` and must
contain at least the following columns:

- ``rxnorm_id`` – the RxCUI identifier (string).
- ``medicine_name`` – the brand / trade name as it appears on a prescription.
- ``normalized_name`` – the generic name or normalized representation.
- ``active_ingredient`` – the principal active ingredient (optional).

The loader is deliberately defensive: missing columns raise a clear ``ValueError``
and duplicate rows are silently dropped to keep the knowledge base idempotent.
"""

import pathlib
import pandas as pd
from typing import Optional


class RxNormLoader:
    """Load RxNorm reference data into an ``EvidenceManager`` instance.

    The loader does **not** download data from the internet – that step is expected
    to be performed by an external script.  It only reads a local CSV and injects
    the resulting :class:`pandas.DataFrame` into the manager.
    """

    REQUIRED_COLUMNS = {"rxnorm_id", "medicine_name", "normalized_name"}

    def __init__(self, csv_path: pathlib.Path | None = None):
        """Create a loader.

        Parameters
        ----------
        csv_path:
            Path to the RxNorm CSV.  If ``None`` the loader defaults to the
            ``database/public_sources/rxnorm/rxnorm_medicines.csv`` location.
        """
        if csv_path is None:
            base = pathlib.Path(__file__).resolve().parents[2]
            self.csv_path = base / "database" / "public_sources" / "rxnorm" / "rxnorm_medicines.csv"
        else:
            self.csv_path = pathlib.Path(csv_path)
        self.rxnorm_df: pd.DataFrame = pd.DataFrame()

    def load(self, evidence_manager) -> None:
        """Load the CSV and attach it to *evidence_manager*.

        The manager will gain a new attribute ``rxnorm_df`` containing the parsed
        data.  If the CSV is missing or empty an empty ``DataFrame`` is attached.
        Duplicate rows (identical ``rxnorm_id``) are dropped to keep the import
        idempotent.
        """
        df = self._read_csv(self.csv_path)
        if not df.empty:
            # Drop duplicate rows based on the primary identifier.
            df = df.drop_duplicates(subset=["rxnorm_id"]).reset_index(drop=True)
        # Store on loader instance and attach to manager.
        self.rxnorm_df = df
        evidence_manager.rxnorm_df = df
        # Record import status in the manifest (handled by the manager).
        if hasattr(evidence_manager, "_record_manifest_entry"):
            evidence_manager._record_manifest_entry(
                name="rxnorm",
                path=str(self.csv_path),
                version="1.0",
                import_date=pd.Timestamp.now().isoformat(),
                source="UMLS RxNorm",
                license="UMLS License",
            )

    def lookup_by_name(self, name: str) -> list[dict]:
        """Case‑insensitive lookup of medicine names.

        Returns a list of dictionaries representing matching records. Each dict
        contains the original columns from the CSV, preserving the ``rxnorm_id``
        identifier. An empty list is returned when no matches are found.
        """
        if not hasattr(self, "rxnorm_df") or self.rxnorm_df is None or self.rxnorm_df.empty:
            return []
        if not name or "medicine_name" not in self.rxnorm_df.columns:
            return []
        query = str(name).strip().lower()
        mask = self.rxnorm_df["medicine_name"].astype(str).str.strip().str.lower() == query
        matches = self.rxnorm_df[mask]
        if matches.empty:
            return []
        return matches.to_dict(orient="records")


    # ---------------------------------------------------------------------
    # Placeholder for future RRF parsing
    # ---------------------------------------------------------------------
    @staticmethod
    def parse_rrf(rrf_path: pathlib.Path) -> pd.DataFrame:
        """Parse the official RxNorm RRF files.

        The official RxNorm distribution provides a set of pipe‑delimited
        ``*.RRF`` files (e.g. ``RXNCONSO.RRF``).  Required fields for this
        project are:

        * ``RXCUI`` – the RxNorm Concept Unique Identifier.
        * ``STR``   – the term string (brand name, generic name, etc.).
        * ``TTY``   – term type (e.g. ``IN`` for ingredient, ``BN`` for brand name).
        * ``RGROUP`` – optional grouping information for synonyms.

        This stub documents the expected columns and returns a ``DataFrame``
        with at least the columns used by the CSV loader:
        ``rxnorm_id``, ``medicine_name``, ``normalized_name``, ``active_ingredient``.
        Implementing full parsing is out of scope for the current phase.
        """
        raise NotImplementedError("RRF parsing is not implemented in this version.")

    @staticmethod
    def _read_csv(path: pathlib.Path) -> pd.DataFrame:
        try:
            df = pd.read_csv(path, dtype=str)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return pd.DataFrame()
        # Normalise column names (strip whitespace, lower case).
        df.columns = [c.strip().lower() for c in df.columns]
        missing = RxNormLoader.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"RxNorm CSV is missing required columns: {missing}")
        # Fill NaN for optional fields.
        df = df.fillna("")
        return df
