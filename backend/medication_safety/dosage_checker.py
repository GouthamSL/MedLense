"""Dosage checker for medication safety.

The checker validates prescribed dosing against the limits stored in
``drugs.csv``.  It only produces a finding when *all* required data are
available and the units are compatible.  When information is missing or
units differ a ``limitation`` finding is returned instead of a speculative
assessment.
"""

from typing import List, Optional
import re
import math

from backend.common.schemas import PrescriptionResult, SafetyFinding
from .evidence_manager import EvidenceManager

FREQUENCY_MAP = {
    "once daily": 1,
    "qd": 1,
    "daily": 1,
    "bid": 2,
    "twice daily": 2,
    "tid": 3,
    "three times daily": 3,
    "qid": 4,
    "four times daily": 4,
}


def _extract_number(text: str) -> Optional[float]:
    """Return the first numeric value found in *text*.

    Handles integers and decimals. Returns ``None`` if no number is present.
    """
    match = re.search(r"[0-9]+(?:\.[0-9]*)?", text or "")
    return float(match.group()) if match else None


def _parse_strength(strength: str) -> Optional[tuple[float, str]]:
    """Parse a strength string like ``"500 mg"`` → ``(500.0, "mg")``.

    Returns ``None`` if the format cannot be parsed.
    """
    if not strength:
        return None
    parts = strength.strip().split()
    if len(parts) < 2:
        return None
    amount = _extract_number(parts[0])
    unit = parts[1].lower()
    if amount is None:
        return None
    return amount, unit


def _frequency_to_per_day(freq: str) -> Optional[int]:
    """Convert common frequency descriptors to a per‑day integer.

    If the string contains a numeric value we use that.  Otherwise we fall back
    to the ``FREQUENCY_MAP``.  Returns ``None`` when the frequency cannot be
    interpreted.
    """
    if not freq:
        return None
    # Direct numeric e.g. "2 per day"
    num = _extract_number(freq)
    if num is not None:
        return int(num)
    lowered = freq.lower().strip()
    return FREQUENCY_MAP.get(lowered)


class DosageChecker:
    """Validate dosage information against known limits.

    Findings are of type ``dosage_issue`` with severity ``requires_review`` when
    a dose exceeds the recorded maximum, or ``information_missing`` when the
    engine cannot perform a reliable assessment.
    """

    def __init__(self, evidence_manager: EvidenceManager | None = None):
        self.evidence = evidence_manager or EvidenceManager()

    def check(self, prescriptions: List[PrescriptionResult]) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        for presc in prescriptions:
            for med in presc.medicines:
                record = self.evidence.get_drug_record(med.medicine_name)
                if record is None:
                    # No reference data – note the limitation.
                    findings.append(
                        SafetyFinding(
                            finding_type="dosage_issue",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="information_missing",
                            explanation="Drug record not found; cannot evaluate dosage.",
                            evidence_source=None,
                        )
                    )
                    continue

                # Required fields from the drug record.
                max_daily = record.get("max_daily_dose", "")
                dose_unit = record.get("dose_units", "").lower()
                strength = record.get("strength", "")

                # Required prescription fields.
                prescribed_dose = med.dose
                frequency = med.frequency

                # Validate presence.
                if not all([max_daily, dose_unit, strength, prescribed_dose, frequency]):
                    findings.append(
                        SafetyFinding(
                            finding_type="dosage_issue",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="information_missing",
                            explanation="Insufficient dosage information to perform check.",
                            evidence_source=None,
                        )
                    )
                    continue

                # Parse numeric values.
                max_daily_val = _extract_number(max_daily)
                strength_parsed = _parse_strength(strength)
                dose_val = _extract_number(prescribed_dose)
                freq_val = _frequency_to_per_day(frequency)

                if None in (max_daily_val, strength_parsed, dose_val, freq_val):
                    findings.append(
                        SafetyFinding(
                            finding_type="dosage_issue",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="information_missing",
                            explanation="Could not parse numeric dosage components.",
                            evidence_source=None,
                        )
                    )
                    continue

                strength_amount, strength_unit = strength_parsed
                # Units must match for a meaningful comparison.
                if strength_unit != dose_unit:
                    findings.append(
                        SafetyFinding(
                            finding_type="dosage_issue",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="information_missing",
                            explanation=f"Unit mismatch (strength: {strength_unit}, prescribed dose unit: {dose_unit}).",
                            evidence_source=None,
                        )
                    )
                    continue

                # Compute total daily dose.
                total_daily = dose_val * freq_val * strength_amount

                if total_daily > max_daily_val:
                    findings.append(
                        SafetyFinding(
                            finding_type="dosage_issue",
                            medicine_a=med.medicine_name,
                            source_a=presc.prescription_id,
                            severity="high",
                            explanation=f"Prescribed total daily dose {total_daily}{dose_unit} exceeds maximum {max_daily_val}{dose_unit}.",
                            evidence_source=record.get("evidence_source", None),
                        )
                    )
        return findings

