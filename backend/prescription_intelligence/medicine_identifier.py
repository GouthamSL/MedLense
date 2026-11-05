"""Medicine identification and normalization module.

Matches extracted medicine candidates against the reference database (drugs.csv)
using exact case-insensitive matching and carefully controlled fuzzy matching.
Maintains strict separation between OCR quality and database identification confidence.
Gracefully handles an empty database without fabricating drugs or active ingredients.
"""

import csv
from dataclasses import dataclass
import difflib
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("prescription_intelligence.identifier")


@dataclass
class DrugRecord:
    """Drug definition from reference database."""
    name: str
    active_ingredient: Optional[str] = None
    strength: Optional[str] = None


@dataclass
class IdentificationResult:
    """Outcome of identifying a candidate medicine against reference data."""
    medicine_name: str
    active_ingredient: Optional[str]
    strength: Optional[str]
    identification_status: str  # "verified", "fuzzy_matched", "unverified", "unrecognized", "requires_verification"
    identification_confidence: Optional[float]  # Strictly reference-matching confidence (0.0 to 1.0)


class MedicineIdentifier:
    """Engine for identifying medicines against reference data with strict confidence boundaries."""

    FUZZY_ACCEPTANCE_THRESHOLD = 0.80  # Minimum similarity ratio to accept a fuzzy match (handles common OCR typos like Amaxcilin)
    LOW_OCR_CONFIDENCE_THRESHOLD = 0.55  # Below which items require human verification

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DRUGS_DB_PATH", "database/drugs.csv")
        self._records: list[DrugRecord] = []
        self._exact_index: dict[str, list[DrugRecord]] = {}
        self.reload_database()

    @property
    def record_count(self) -> int:
        """Return the number of loaded drug records."""
        return len(self._records)

    @property
    def is_database_empty(self) -> bool:
        """Whether the reference database contains any records."""
        return len(self._records) == 0

    def get_known_drug_names(self) -> set[str]:
        """Return lowercase set of all known drug names in reference database."""
        return set(self._exact_index.keys())

    def reload_database(self) -> None:
        """Load or reload reference drug dataset from CSV file."""
        self._records.clear()
        self._exact_index.clear()

        csv_file = Path(self.db_path)
        if not csv_file.exists() or csv_file.stat().st_size == 0:
            logger.info("Reference drug database at '%s' is empty or absent (0 records).", self.db_path)
            return

        try:
            with open(csv_file, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return

                # Map column variations
                name_col = self._find_column(reader.fieldnames, ["name", "drug_name", "brand_name", "medicine_name"])
                active_col = self._find_column(reader.fieldnames, ["active_ingredient", "generic_name", "composition", "ingredient"])
                strength_col = self._find_column(reader.fieldnames, ["strength", "dosage", "dose_strength"])

                if not name_col:
                    logger.warning("No medicine name column recognized in '%s'.", self.db_path)
                    return

                for row in reader:
                    raw_name = (row.get(name_col) or "").strip()
                    if not raw_name:
                        continue
                    active = (row.get(active_col) or "").strip() or None if active_col else None
                    strength = (row.get(strength_col) or "").strip() or None if strength_col else None

                    rec = DrugRecord(name=raw_name, active_ingredient=active, strength=strength)
                    self._records.append(rec)
                    key = raw_name.lower()
                    if key not in self._exact_index:
                        self._exact_index[key] = []
                    self._exact_index[key].append(rec)

            logger.info("Loaded %d drug records from '%s'.", len(self._records), self.db_path)
        except Exception as exc:
            logger.error("Error reading drug database '%s': %s", self.db_path, exc)

    def load_custom_records(self, records: list[DrugRecord]) -> None:
        """Inject custom drug records for testing or runtime customization."""
        self._records = list(records)
        self._exact_index.clear()
        for rec in self._records:
            key = rec.name.lower()
            if key not in self._exact_index:
                self._exact_index[key] = []
            self._exact_index[key].append(rec)

    @staticmethod
    def _find_column(fieldnames: list[str], candidates: list[str]) -> Optional[str]:
        lookup = {col.lower().strip(): col for col in fieldnames}
        for cand in candidates:
            if cand in lookup:
                return lookup[cand]
        return None

    def identify_medicine(
        self,
        candidate_name: str,
        extracted_strength: Optional[str] = None,
        ocr_confidence: Optional[float] = None,
    ) -> IdentificationResult:
        """Identify a candidate medicine against reference data.

        Applies exact matching, controlled fuzzy matching, and handles empty reference data
        without fabricating drugs. Separates OCR quality from database match confidence.
        """
        clean_cand = candidate_name.strip()
        cand_lower = clean_cand.lower()

        # If OCR confidence is exceptionally low, flag for human verification
        if ocr_confidence is not None and ocr_confidence < self.LOW_OCR_CONFIDENCE_THRESHOLD:
            return IdentificationResult(
                medicine_name=clean_cand,
                active_ingredient=None,
                strength=extracted_strength,
                identification_status="requires_verification",
                identification_confidence=None,  # OCR confidence kept separate
            )

        # CASE 1: Database is empty (as in default repository state)
        if self.is_database_empty:
            # Preserve extracted name, do NOT fabricate active ingredients or claim verified status
            # Flag unknown candidate for verification
            return IdentificationResult(
                medicine_name=clean_cand,
                active_ingredient=None,
                strength=extracted_strength,
                identification_status="unverified",
                identification_confidence=None,  # Not verified against DB
            )

        # CASE 2: Populated database - Exact case-insensitive matching
        if cand_lower in self._exact_index:
            candidates = self._exact_index[cand_lower]
            selected = self._select_best_by_strength(candidates, extracted_strength)
            return IdentificationResult(
                medicine_name=selected.name,
                active_ingredient=selected.active_ingredient,
                strength=extracted_strength or selected.strength,
                identification_status="verified",
                identification_confidence=1.0,  # Exact database match
            )

        # CASE 3: Populated database - Controlled Fuzzy Matching
        best_match: Optional[DrugRecord] = None
        best_ratio = 0.0

        for rec in self._records:
            ratio = difflib.SequenceMatcher(None, cand_lower, rec.name.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = rec

        if best_ratio >= self.FUZZY_ACCEPTANCE_THRESHOLD and best_match:
            # Controlled fuzzy match accepted with similarity score
            conf = round(best_ratio, 3)
            return IdentificationResult(
                medicine_name=best_match.name,
                active_ingredient=best_match.active_ingredient,
                strength=extracted_strength or best_match.strength,
                identification_status="fuzzy_matched",
                identification_confidence=conf,
            )

        # CASE 4: No match above strict threshold
        # Preserve original extracted text and flag as requires_verification / unrecognized
        return IdentificationResult(
            medicine_name=clean_cand,
            active_ingredient=None,
            strength=extracted_strength,
            identification_status="requires_verification",
            identification_confidence=None,
        )

    @staticmethod
    def _select_best_by_strength(
        candidates: list[DrugRecord],
        target_strength: Optional[str],
    ) -> DrugRecord:
        """Select best candidate when multiple entries have same name but differing strengths."""
        if len(candidates) == 1 or not target_strength:
            return candidates[0]

        target_norm = target_strength.lower().replace(" ", "")
        for cand in candidates:
            if cand.strength:
                cand_norm = cand.strength.lower().replace(" ", "")
                if cand_norm == target_norm:
                    return cand

        return candidates[0]
