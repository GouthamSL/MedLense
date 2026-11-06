
"""Medicine identification and normalization module.

Matches extracted medicine candidates against the reference database
using exact case-insensitive matching and carefully controlled fuzzy matching.

Ambiguous medicine or strength matches require verification.
"""

import csv
import difflib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("prescription_intelligence.identifier")


@dataclass
class DrugRecord:
    """Drug definition from the reference database."""

    name: str
    active_ingredient: Optional[str] = None
    strength: Optional[str] = None


@dataclass
class IdentificationResult:
    """Outcome of identifying a candidate medicine against reference data."""

    medicine_name: str
    active_ingredient: Optional[str]
    strength: Optional[str]
    identification_status: str
    identification_confidence: Optional[float]


class MedicineIdentifier:
    """Engine for identifying medicines against reference data."""

    FUZZY_ACCEPTANCE_THRESHOLD = 0.80
    LOW_OCR_CONFIDENCE_THRESHOLD = 0.55

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "DRUGS_DB_PATH", "database/drugs.csv"
        )
        self._records: list[DrugRecord] = []
        self._exact_index: dict[str, list[DrugRecord]] = {}
        self.reload_database()

    @property
    def is_database_empty(self) -> bool:
        return len(self._records) == 0

    @property
    def record_count(self) -> int:
        """Return the number of medicine records loaded."""
        return len(self._records)

    def get_known_drug_names(self) -> set[str]:
        """Return lowercase set of all known drug names."""
        return set(self._exact_index.keys())

    def reload_database(self) -> None:
        """Load or reload the reference drug dataset from CSV."""

        self._records.clear()
        self._exact_index.clear()

        csv_file = Path(self.db_path)

        if not csv_file.exists() or csv_file.stat().st_size == 0:
            logger.info(
                "Reference drug database at '%s' is empty or absent.",
                self.db_path,
            )
            return

        try:
            with open(
                csv_file,
                mode="r",
                encoding="utf-8",
                errors="replace",
            ) as file:
                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    return

                name_col = self._find_column(
                    reader.fieldnames,
                    ["name", "drug_name", "brand_name", "medicine_name"],
                )

                active_col = self._find_column(
                    reader.fieldnames,
                    [
                        "active_ingredient",
                        "generic_name",
                        "composition",
                        "ingredient",
                    ],
                )

                strength_col = self._find_column(
                    reader.fieldnames,
                    ["strength", "dosage", "dose_strength"],
                )

                if not name_col:
                    logger.warning(
                        "No medicine name column recognized in '%s'.",
                        self.db_path,
                    )
                    return

                for row in reader:
                    raw_name = (row.get(name_col) or "").strip()

                    if not raw_name:
                        continue

                    active = (
                        (row.get(active_col) or "").strip() or None
                        if active_col
                        else None
                    )

                    strength = (
                        (row.get(strength_col) or "").strip() or None
                        if strength_col
                        else None
                    )

                    record = DrugRecord(
                        name=raw_name,
                        active_ingredient=active,
                        strength=strength,
                    )

                    self._records.append(record)

                    key = raw_name.lower()
                    self._exact_index.setdefault(key, []).append(record)

            logger.info(
                "Loaded %d drug records from '%s'.",
                len(self._records),
                self.db_path,
            )

        except Exception as exc:
            logger.error(
                "Error reading drug database '%s': %s",
                self.db_path,
                exc,
            )

    def load_custom_records(self, records: list[DrugRecord]) -> None:
        """Inject custom drug records for testing or runtime customization."""

        self._records = list(records)
        self._exact_index.clear()

        for record in self._records:
            key = record.name.lower()
            self._exact_index.setdefault(key, []).append(record)

    @staticmethod
    def _find_column(
        fieldnames: list[str],
        candidates: list[str],
    ) -> Optional[str]:
        """Find a matching CSV column name."""

        lookup = {
            col.lower().strip(): col
            for col in fieldnames
        }

        for candidate in candidates:
            if candidate in lookup:
                return lookup[candidate]

        return None

    @staticmethod
    def _normalize_strength(
        strength: Optional[str],
    ) -> Optional[str]:
        """Normalize strength text for comparison."""

        if not strength:
            return None

        return "".join(strength.lower().split())

    def identify_medicine(
        self,
        candidate_name: str,
        extracted_strength: Optional[str] = None,
        ocr_confidence: Optional[float] = None,
    ) -> IdentificationResult:
        """Identify a medicine while avoiding ambiguous assignments."""

        clean_cand = candidate_name.strip()
        cand_lower = clean_cand.lower()

        # CASE 1: Low OCR confidence.
        if (
            ocr_confidence is not None
            and ocr_confidence < self.LOW_OCR_CONFIDENCE_THRESHOLD
        ):
            return IdentificationResult(
                medicine_name=clean_cand,
                active_ingredient=None,
                strength=extracted_strength,
                identification_status="requires_verification",
                identification_confidence=None,
            )

        # CASE 2: Empty reference database.
        if self.is_database_empty:
            return IdentificationResult(
                medicine_name=clean_cand,
                active_ingredient=None,
                strength=extracted_strength,
                identification_status="unverified",
                identification_confidence=None,
            )

        # CASE 3: Exact medicine-name matching.
        if cand_lower in self._exact_index:
            candidates = self._exact_index[cand_lower]

            if extracted_strength:
                target = self._normalize_strength(extracted_strength)

                matching = [
                    record
                    for record in candidates
                    if self._normalize_strength(record.strength) == target
                ]

                if len(matching) == 1:
                    selected = matching[0]

                    return IdentificationResult(
                        medicine_name=selected.name,
                        active_ingredient=selected.active_ingredient,
                        strength=extracted_strength,
                        identification_status="verified",
                        identification_confidence=1.0,
                    )

            elif len(candidates) == 1:
                selected = candidates[0]

                return IdentificationResult(
                    medicine_name=selected.name,
                    active_ingredient=selected.active_ingredient,
                    strength=selected.strength,
                    identification_status="verified",
                    identification_confidence=1.0,
                )

            # Missing or mismatched strength, or ambiguous records.
            return IdentificationResult(
                medicine_name=clean_cand,
                active_ingredient=None,
                strength=extracted_strength,
                identification_status="requires_verification",
                identification_confidence=None,
            )

        # CASE 4: Controlled fuzzy matching with tie detection.
        scored_matches = []

        for record in self._records:
            ratio = difflib.SequenceMatcher(
                None,
                cand_lower,
                record.name.lower(),
            ).ratio()

            if ratio >= self.FUZZY_ACCEPTANCE_THRESHOLD:
                scored_matches.append((ratio, record))

        if scored_matches:
            best_ratio = max(score for score, _ in scored_matches)

            best_candidates = [
                record
                for score, record in scored_matches
                if score == best_ratio
            ]

            # Do not arbitrarily select between different medicine names.
            best_names = {
                record.name.lower()
                for record in best_candidates
            }

            if len(best_names) > 1:
                return IdentificationResult(
                    medicine_name=clean_cand,
                    active_ingredient=None,
                    strength=extracted_strength,
                    identification_status="requires_verification",
                    identification_confidence=None,
                )

            best_match = best_candidates[0]

            same_name_records = [
                record
                for record in self._records
                if record.name.lower() == best_match.name.lower()
            ]

            if extracted_strength:
                target = self._normalize_strength(extracted_strength)

                matching = [
                    record
                    for record in same_name_records
                    if self._normalize_strength(record.strength) == target
                ]

                if len(matching) != 1:
                    return IdentificationResult(
                        medicine_name=clean_cand,
                        active_ingredient=None,
                        strength=extracted_strength,
                        identification_status="requires_verification",
                        identification_confidence=None,
                    )

                best_match = matching[0]

            elif len(same_name_records) != 1:
                return IdentificationResult(
                    medicine_name=clean_cand,
                    active_ingredient=None,
                    strength=None,
                    identification_status="requires_verification",
                    identification_confidence=None,
                )

            return IdentificationResult(
                medicine_name=best_match.name,
                active_ingredient=best_match.active_ingredient,
                strength=extracted_strength or best_match.strength,
                identification_status="fuzzy_matched",
                identification_confidence=round(best_ratio, 3),
            )

        # CASE 5: No sufficiently reliable match.
        return IdentificationResult(
            medicine_name=clean_cand,
            active_ingredient=None,
            strength=extracted_strength,
            identification_status="requires_verification",
            identification_confidence=None,
        )
