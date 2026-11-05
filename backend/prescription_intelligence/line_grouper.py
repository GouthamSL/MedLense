
"""Medicine-line grouping module for prescription OCR.

Associates medicine-name lines with their dosage, frequency, and duration
instruction lines while preserving boundaries between medicines.
"""

from dataclasses import dataclass, field
import re
from typing import Optional

from backend.prescription_intelligence.dosage_extractor import (
    FORM_PREFIXES,
    is_header_or_footer_line,
)
from backend.prescription_intelligence.ocr_engine import OCRLine, OCRWord


# Patterns that identify dosage and administration instructions.
CONTINUATION_PATTERNS = [
    # Explicit quantities: 1 tablet, 2 capsules, 5 ml, etc.
    r"^\s*(?:take\s+)?\d+(?:\.\d+)?\s*(?:tab(?:let)?s?|cap(?:sule)?s?|puffs?|drops?|ml|tsp|tbsp|sachets?|patches?)\b",

    # Frequency matrix: 1-0-1, 1-1-1, 0-0-1, etc.
    r"^\s*[012]\s*[-–—/]\s*[012]\s*[-–—/]\s*[012](?:\s*[-–—/]\s*[012])?\b",

    # Medical frequency abbreviations.
    r"^\s*(?:OD|BD|B\.?I\.?D\.?|TDS|T\.?I\.?D\.?|QID|Q\.?I\.?D\.?|PRN|SOS|HS|STAT|Q\d+H)\b",

    # Natural-language frequency.
    r"^\s*(?:once|twice|three\s+times|four\s+times)\s+(?:daily|a\s+day)\b",

    # Duration.
    r"^\s*(?:for\s+|x\s+|\*\s*)\d+\s*(?:days?|weeks?|months?|d|wks?)\b",

    # Food and administration instructions.
    r"^\s*(?:before|after|with)\s+(?:food|meals?|breakfast|lunch|dinner)\b",
    r"^\s*(?:empty\s+stomach|at\s+bedtime|as\s+needed|orally|oral)\b",

    # Dosage form followed by a frequency instruction.
    r"^\s*(?:tab(?:let)?s?|cap(?:sule)?s?)\b.*\b(?:OD|BD|TDS|QID|PRN|SOS)\b",
]


# Patterns that identify the beginning of a new medicine.
NEW_MEDICINE_PATTERNS = [
    # Numbered entries: 1., 2), [3], etc.
    r"^\s*(?:\[\s*\d+\s*\]|\d+\s*[.)]|\*|-|•)\s*",

    # Dosage forms: Tab, Cap, Syr, Inj, etc.
    rf"^\s*{FORM_PREFIXES}\.?\b",
]


# Common OCR symbols appearing before dosage instructions.
LEADING_CONTINUATION_MARKER = re.compile(r"^\s*[/|\\¢]\s*")


@dataclass
class GroupedMedicineLine:
    """A medicine entry with associated OCR instruction lines."""

    text: str
    confidence: float
    words: list[OCRWord] = field(default_factory=list)
    line_numbers: list[int] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


def is_continuation_line(line_text: str) -> bool:
    """Identify dosage, frequency, duration, or instruction lines."""

    stripped = line_text.strip()

    if not stripped or is_header_or_footer_line(stripped):
        return False

    # OCR may add symbols before an instruction.
    if LEADING_CONTINUATION_MARKER.match(stripped):
        return True

    return any(
        re.search(pattern, stripped, re.IGNORECASE)
        for pattern in CONTINUATION_PATTERNS
    )


def is_new_medicine_start(
    line_text: str,
    known_drug_names: Optional[set[str]] = None,
) -> bool:
    """Identify whether a line starts a new medicine entry."""

    stripped = line_text.strip()

    if not stripped or is_header_or_footer_line(stripped):
        return False

    for pattern in NEW_MEDICINE_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True

    if known_drug_names:
        first_word = re.split(r"[\s\-_:;,./]", stripped)[0].strip().lower()
        normalized_names = {
            name.strip().lower() for name in known_drug_names
        }

        if first_word in normalized_names:
            return True

    return False


def _append_line(
    entry: GroupedMedicineLine,
    line: OCRLine,
    text: str,
) -> None:
    """Append a continuation line and update confidence."""

    entry.text = f"{entry.text} {text}"
    entry.words.extend(line.words)
    entry.raw_lines.append(text)
    entry.line_numbers.append(line.line_num)

    if entry.words:
        entry.confidence = round(
            sum(word.confidence for word in entry.words) / len(entry.words),
            4,
        )


def group_ocr_lines(
    lines: list[OCRLine],
    known_drug_names: Optional[set[str]] = None,
) -> list[GroupedMedicineLine]:
    """Group each medicine line with its following instructions."""

    grouped_entries: list[GroupedMedicineLine] = []
    current_entry: Optional[GroupedMedicineLine] = None

    for line in lines:
        text = line.text.strip()

        if not text:
            continue

        # Skip headers and patient/clinic information.
        if is_header_or_footer_line(text):
            if current_entry is not None:
                grouped_entries.append(current_entry)
                current_entry = None
            continue

        new_medicine = is_new_medicine_start(text, known_drug_names)
        continuation = is_continuation_line(text)

        # A new numbered medicine must start a separate entry.
        if new_medicine:
            if current_entry is not None:
                grouped_entries.append(current_entry)

            current_entry = GroupedMedicineLine(
                text=text,
                confidence=line.confidence,
                words=list(line.words),
                line_numbers=[line.line_num],
                raw_lines=[text],
            )
            continue

                # Ignore dosage instructions when no medicine entry exists.
        if current_entry is None and continuation:
            continue

        # Attach recognized instructions to the current medicine.
        if current_entry is not None and continuation:
            _append_line(current_entry, line, text)
            continue

        # Otherwise start a separate entry.
        if current_entry is not None:
            grouped_entries.append(current_entry)

        current_entry = GroupedMedicineLine(
            text=text,
            confidence=line.confidence,
            words=list(line.words),
            line_numbers=[line.line_num],
            raw_lines=[text],
        )

    if current_entry is not None:
        grouped_entries.append(current_entry)

    return grouped_entries
