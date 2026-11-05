"""Dosage, frequency, duration, and medicine entity extraction module.

Parses unstructured OCR prescription text, extracts structured clinical attributes
with strict adherence to non-fabrication rules (unspecified fields remain None)
and filters out clinic headers, doctor details, patient data, addresses, and non-medication text.
"""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass
class ParsedPrescriptionItem:
    """Raw parsed fields extracted from a prescription line."""
    raw_line: str
    raw_medicine_name: str
    strength: Optional[str] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    ocr_confidence: Optional[float] = None


# Prefixes commonly indicating pharmaceutical dosage forms
FORM_PREFIXES = (
    r"(?:tab(?:let)?s?|cap(?:sule)?s?|syr(?:up)?s?|inj(?:ection)?s?|oint(?:ment)?s?|"
    r"susp(?:ension)?s?|creams?|drops?|gels?|sol(?:ution)?s?|inhalers?|sprays?|lotions?|patch(?:es)?)"
)

# Comprehensive patterns identifying non-medication lines:
# Clinic / Hospital / Doctor / Patient / Address / Contact / Dividers / Instructions
HEADER_FOOTER_KEYWORDS = [
    # Doctor / Professional Titles
    r"\bdr\.?\b",
    r"\bdoctor\b",
    r"\bphysician\b",
    r"\bsurgeon\b",
    r"\bconsultant\b",
    r"\bspecialist\b",
    r"\bpractitioner\b",
    r"\bmbbs\b",
    r"\bm\.?d\.?\b",
    r"\bms\b",
    r"\bdm\b",
    r"\bdnb\b",
    r"\bbams\b",
    r"\bbhms\b",
    r"\bfrcs\b",
    r"\bmrcp\b",
    r"\bfacp\b",
    # Clinic / Hospital / Organization
    r"\bhospital\b",
    r"\bclinic\b",
    r"\bmedical\s+cent(?:er|re)\b",
    r"\bhealth\s*care\b",
    r"\bnursing\s+home\b",
    r"\bdispensary\b",
    r"\binfirmary\b",
    r"\binstitute\b",
    r"\bpolyclinic\b",
    r"\bpharmacy\b",
    # Patient Demographics
    r"\bpatient\b",
    r"\bpt\.?\b",
    r"\bpatient\s*name\b",
    r"\bpt\s*name\b",
    r"\b(?:name|age|sex|gender|dob|d\.o\.b)\s*:",
    r"\b(?:male|female)\b.*?\b(?:age|yr|years|y/o)\b",
    r"\b(?:age|years|yrs|y/o)\b.*?\b(?:male|female)\b",
    r"\b(?:weight|height|bp|pulse|temp|spo2|vitals?)\s*:",
    # Addresses / Locations
    r"\b(?:street|st\.|road|rd\.|avenue|ave\.|lane|cross|floor|suite|block|sector|layout|nagar|city|state)\b",
    r"\b(?:pincode|pin|zip|zipcode)\s*:",
    # Contacts
    r"\b(?:tel|phone|ph|mob|mobile|email|web|website|fax)\s*:",
    r"\bwww\.[a-z0-9\-]+\.[a-z]{2,}\b",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    # Clinical Section Headers / Notes / Dividers
    r"^(?:rx|rx\s*:|r/|prescription|prescribed\s+by)\b",
    r"^(?:chief\s+complaint|diagnosis|provisional\s+diagnosis|history)\s*:",
    r"^(?:investigations?|lab\s+tests?|reports?)\s*:",
    r"^(?:advice|general\s+advice|diet\s+advice|instructions?|precautions?)\s*:",
    r"^(?:signature|doctor['’]?s\s+signature|reg(?:istration)?\s*(?:no|number)?|lic(?:ense)?\s*(?:no|number)?)\b",
    r"^(?:follow\s*up|next\s+visit|review\s+(?:in|after|on))\b",
    r"^(?:emergency\s+contact|get\s+well\s+soon|not\s+for\s+medico-legal)\b",
]


def is_header_or_footer_line(line: str) -> bool:
    """Determine whether a line is header/metadata/patient/clinic text rather than a medication."""
    stripped = line.strip().lower()

    # Reject empty or very short lines
    if len(stripped) < 3:
        return True

    # Pure divider or punctuation lines: e.g. "--------------------", "======"
    if re.match(r"^[\s\-_=\*\.·~|/]{3,}$", stripped):
        return True

    # Standalone "Rx" or "Rx:"
    if re.match(r"^r[x/][:\-.]?$", stripped):
        return True

    # Check against header/footer keywords
    for pattern in HEADER_FOOTER_KEYWORDS:
        if re.search(pattern, stripped, re.IGNORECASE):
            return True

    # Phone number pattern (e.g. +1-234-567-8900 or 10-digit number)
    if re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", stripped):
        if not re.search(FORM_PREFIXES, stripped):
            return True

    return False


def normalize_ocr_line_spacing(line: str) -> str:
    """Fix common OCR spatial merges, e.g. '3.CapOmeprazole' -> '3. Cap Omeprazole'."""
    # Insert space between numbering and form prefix, e.g. "3.Cap" -> "3. Cap"
    line = re.sub(r"(\d+[.)\]])([A-Za-z])", r"\1 \2", line)

    # Insert space between form prefix and capital medicine name:
    # Important: Do NOT use re.IGNORECASE here, so words like "tablet" are NOT split into "tab let"!
    line = re.sub(
        r"\b(Tab(?:let)?|Cap(?:sule)?|Syr(?:up)?|Inj(?:ection)?|Oint(?:ment)?|Susp(?:ension)?|Cream|Drops?|Gel|Sol(?:ution)?)([A-Z][a-z])",
        r"\1 \2",
        line,
    )

    # Insert space in merged duration: "for3 days" -> "for 3 days"
    line = re.sub(r"\b(for|x)(\d+)\b", r"\1 \2", line, flags=re.IGNORECASE)

    # Insert space in merged frequency: "capOD" -> "cap OD"
    line = re.sub(r"\b(cap|tab|syr|inj)(OD|BD|TDS|QID|HS|PRN|SOS)\b", r"\1 \2", line, flags=re.IGNORECASE)

    return line


def extract_strength(text: str) -> tuple[Optional[str], str]:
    """Extract medicine strength or compound concentration without truncating units.

    Supports:
      - Compound dual-unit: '500 mg/125 mg', '500mg/125mg', '5 mg/5 ml', '5mg/5ml', '250mg/5ml'
      - Dual-amount single-unit: '500/125 mg'
      - Additive combos: '500 mg + 125 mg'
      - Single strengths: '5 mg', '500 mg', '650mg', '1000 IU', '250 mcg', '0.5%'

    Returns:
        tuple[Optional[str], str]: (normalized_strength, remainder_text)
    """
    # 1. Dual-part with units on both numerator and denominator (e.g. 500 mg/125 mg, 5mg/5ml, 250mg/5ml)
    compound_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(mg|g|gm|mcg|ug|ml|iu|meq|%)\s*([\/|\+])\s*(\d+(?:\.\d+)?)\s*(mg|g|gm|mcg|ug|ml|iu|meq|%)(?!\w)",
        re.IGNORECASE,
    )
    match = compound_pattern.search(text)
    if match:
        v1, u1, op, v2, u2 = match.groups()
        u1_norm = "g" if u1.lower() == "gm" else ("mcg" if u1.lower() == "ug" else u1.lower())
        u2_norm = "g" if u2.lower() == "gm" else ("mcg" if u2.lower() == "ug" else u2.lower())
        separator = " + " if op == "+" else "/"
        normalized = f"{v1} {u1_norm}{separator}{v2} {u2_norm}"
        remainder = text[: match.start()] + " " + text[match.end() :]
        return normalized, remainder

    # 2. Denominator unit only without digits (e.g. 100 mg/ml)
    per_volume_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(mg|g|gm|mcg|ug|iu|meq|%)\s*(\/)\s*(ml|l)\b",
        re.IGNORECASE,
    )
    match = per_volume_pattern.search(text)
    if match:
        v1, u1, op, u2 = match.groups()
        u1_norm = "g" if u1.lower() == "gm" else ("mcg" if u1.lower() == "ug" else u1.lower())
        normalized = f"{v1} {u1_norm}/{u2.lower()}"
        remainder = text[: match.start()] + " " + text[match.end() :]
        return normalized, remainder

    # 3. Dual-part with unit on the right only (e.g. 500/125 mg or 500 + 125 mg)
    dual_val_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*([\/|\+])\s*(\d+(?:\.\d+)?)\s*(mg|g|gm|mcg|ug|ml|iu|meq|%)(?!\w)",
        re.IGNORECASE,
    )
    match = dual_val_pattern.search(text)
    if match:
        v1, op, v2, u = match.groups()
        u_norm = "g" if u.lower() == "gm" else ("mcg" if u.lower() == "ug" else u.lower())
        separator = " + " if op == "+" else "/"
        normalized = f"{v1}{separator}{v2} {u_norm}"
        remainder = text[: match.start()] + " " + text[match.end() :]
        return normalized, remainder

    # 4. Standard single strength (e.g. 500 mg, 5mg, 1000 IU, 0.5%)
    # Use (?!\w) rather than \b so non-word '%' is correctly matched
    single_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(mg|g|gm|mcg|ug|ml|iu|meq|%)(?!\w)",
        re.IGNORECASE,
    )
    match = single_pattern.search(text)
    if match:
        val, u = match.groups()
        u_norm = "g" if u.lower() == "gm" else ("mcg" if u.lower() == "ug" else u.lower())
        normalized = f"{val} {u_norm}"
        remainder = text[: match.start()] + " " + text[match.end() :]
        return normalized, remainder

    return None, text


def extract_frequency(text: str) -> tuple[Optional[str], str]:
    """Extract medication frequency instructions and return remainder text."""
    remainder = text

    # 1. Numeric matrix notation: 1-0-1, 1-1-1, 0-0-1, 1-0-0, 1-1-1-1, etc.
    matrix_match = re.search(
        r"\b([012])\s*[-–—/]\s*([012])\s*[-–—/]\s*([012])(?:\s*[-–—/]\s*([012]))?\b",
        remainder,
    )
    if matrix_match:
        m1, m2, m3, m4 = matrix_match.groups()
        if m4 is not None:
            code = f"{m1}-{m2}-{m3}-{m4}"
            norm = f"Four times daily ({code})"
        else:
            code = f"{m1}-{m2}-{m3}"
            if code == "1-0-1":
                norm = f"Twice daily ({code})"
            elif code == "1-1-1":
                norm = f"Three times daily ({code})"
            elif code == "1-0-0":
                norm = f"Once daily - Morning ({code})"
            elif code == "0-0-1":
                norm = f"Once daily - Night ({code})"
            elif code == "0-1-0":
                norm = f"Once daily - Afternoon ({code})"
            elif code == "1-1-0":
                norm = f"Twice daily ({code})"
            elif code == "0-1-1":
                norm = f"Twice daily ({code})"
            else:
                norm = f"{code}"
        remainder = remainder[: matrix_match.start()] + " " + remainder[matrix_match.end() :]
        return norm, remainder

    # 2. Latin / Medical abbreviation matching
    latin_patterns = [
        (r"\b(?:OD|Q\.?D\.?)\b", "Once daily (OD)"),
        (r"\b(?:BD|B\.?I\.?D\.?)\b", "Twice daily (BD)"),
        (r"\b(?:TDS|T\.?I\.?D\.?)\b", "Three times daily (TDS)"),
        (r"\b(?:QID|Q\.?I\.?D\.?)\b", "Four times daily (QID)"),
        (r"\b(?:SOS|PRN)\b", "As needed (PRN/SOS)"),
        (r"\b(?:HS|QHS)\b", "At bedtime (HS)"),
        (r"\b(?:STAT)\b", "Immediately (STAT)"),
        (r"\bQ(\d+)H\b", "Every \\1 hours"),
    ]

    for pat, desc in latin_patterns:
        match = re.search(pat, remainder, re.IGNORECASE)
        if match:
            if "\\1" in desc:
                desc = desc.replace("\\1", match.group(1))
            remainder = remainder[: match.start()] + " " + remainder[match.end() :]
            return desc, remainder

    # 3. Natural language frequencies
    nat_patterns = [
        (r"\bonce\s+(?:a\s+)?day\b|\bonce\s+daily\b", "Once daily"),
        (r"\btwice\s+(?:a\s+)?day\b|\btwice\s+daily\b", "Twice daily"),
        (r"\bthree\s+times\s+(?:a\s+)?day\b|\bthree\s+times\s+daily\b", "Three times daily"),
        (r"\bfour\s+times\s+(?:a\s+)?day\b|\bfour\s+times\s+daily\b", "Four times daily"),
        (r"\bevery\s+(\d+)\s+hours?\b", "Every \\1 hours"),
        (r"\bat\s+bedtime\b", "At bedtime (HS)"),
        (r"\bas\s+needed\b", "As needed (PRN)"),
    ]

    for pat, desc in nat_patterns:
        match = re.search(pat, remainder, re.IGNORECASE)
        if match:
            if "\\1" in desc:
                desc = desc.replace("\\1", match.group(1))
            remainder = remainder[: match.start()] + " " + remainder[match.end() :]
            return desc, remainder

    return None, text


def extract_duration(text: str) -> tuple[Optional[str], str]:
    """Extract duration specifications (e.g. for 5 days, 1 week, x 10 days)."""
    # Pattern: optional preposition (for, x, *), digits, time unit
    pattern = re.compile(
        r"(?:\bfor\s*|\bx\s*|\*\s*)?(\d+)\s*(days?|weeks?|wks?|months?|mths?|years?|yrs?|d)\b",
        re.IGNORECASE,
    )

    match = pattern.search(text)
    if not match:
        return None, text

    num = match.group(1)
    unit_raw = match.group(2).lower()

    if unit_raw in ("d", "day", "days"):
        unit = "day" if num == "1" else "days"
    elif unit_raw in ("wk", "wks", "week", "weeks"):
        unit = "week" if num == "1" else "weeks"
    elif unit_raw in ("mth", "mths", "month", "months"):
        unit = "month" if num == "1" else "months"
    elif unit_raw in ("yr", "yrs", "year", "years"):
        unit = "year" if num == "1" else "years"
    else:
        unit = unit_raw

    norm = f"{num} {unit}"
    remainder = text[: match.start()] + " " + text[match.end() :]
    return norm, remainder


def extract_dose(text: str) -> tuple[Optional[str], str]:
    """Extract explicit dosage quantities (e.g. 1 tablet, 2 puffs, 5 ml, 1-2 caps).

    Strict rule: Never infers or defaults a dosage unless explicitly present in text.
    """
    pattern = re.compile(
        r"\b(\d+(?:\.\d+)?(?:\s*-\s*\d+)?)\s*(tablets?|tabs?|capsules?|caps?|puffs?|drops?|ml|tsp|tbsp|sachets?|patches?)\b",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None, text

    qty = match.group(1).strip()
    raw_unit = match.group(2).lower()

    if raw_unit in ("tab", "tabs", "tablet", "tablets"):
        unit = "tablet" if qty == "1" else "tablets"
    elif raw_unit in ("cap", "caps", "capsule", "capsules"):
        unit = "capsule" if qty == "1" else "capsules"
    elif raw_unit in ("puff", "puffs"):
        unit = "puff" if qty == "1" else "puffs"
    elif raw_unit in ("drop", "drops"):
        unit = "drop" if qty == "1" else "drops"
    elif raw_unit in ("sachet", "sachets"):
        unit = "sachet" if qty == "1" else "sachets"
    elif raw_unit in ("patch", "patches"):
        unit = "patch" if qty == "1" else "patches"
    else:
        unit = raw_unit

    dose_str = f"{qty} {unit}"
    remainder = text[: match.start()] + " " + text[match.end() :]
    return dose_str, remainder


def clean_medicine_name(candidate_text: str) -> str:
    """Clean isolated candidate medicine string from residual syntax, bullets, and prefixes."""
    # Strip leading numbering like 1., 2), [3], *, -, •
    cleaned = re.sub(r"^\s*(?:\[?\d+[.)\]]|\*|-|•)\s*", "", candidate_text).strip()

    # Strip drug form prefixes
    cleaned = re.sub(
        rf"^\s*{FORM_PREFIXES}\.?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Strip trailing administration instructions, residual forms, or common filler words
    cleaned = re.sub(
        rf"[\s\-,;:]+(?:{FORM_PREFIXES}|take|oral|daily|before|after|with|food|meals?|empty\s+stomach|water|bedtime|pain)?$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Strip residual punctuation
    cleaned = re.sub(r"^[\s\-_:;,./]+|[\s\-_:;,./]+$", "", cleaned).strip()

    return cleaned


def has_clinical_context(
    original_line: str,
    strength: Optional[str],
    frequency: Optional[str],
    duration: Optional[str],
    dose: Optional[str],
) -> bool:
    """Determine whether a candidate line has credible clinical prescription context.

    Prevents arbitrary non-clinical text from being treated as a medicine.
    """
    # 1. Has an explicit dosage form prefix (Tab, Cap, Syr, etc.)
    if re.search(rf"\b{FORM_PREFIXES}\b", original_line, re.IGNORECASE):
        return True

    # 2. Has an explicit strength (e.g. 500 mg, 5mg/5ml)
    if strength is not None:
        return True

    # 3. Has an explicit frequency instruction (e.g. 1-0-1, BD, OD, TDS)
    if frequency is not None:
        return True

    # 4. Has an explicit duration or dose
    if duration is not None or dose is not None:
        return True

    return False


def parse_prescription_line(
    line: str,
    confidence: Optional[float] = None,
    allow_contextless: bool = False,
) -> Optional[ParsedPrescriptionItem]:
    """Parse a single prescription text line into structured components.

    Rejects non-medication headers, clinic info, and lines lacking clinical evidence.
    """
    if is_header_or_footer_line(line):
        return None

    # Pre-normalize spacing for merged OCR tokens
    normalized_line = normalize_ocr_line_spacing(line)

    # Step 1: Extract Strength
    strength, rem1 = extract_strength(normalized_line)

    # Step 2: Extract Duration (before frequency to avoid eating numeric days in matrix)
    duration, rem2 = extract_duration(rem1)

    # Step 3: Extract Frequency
    frequency, rem3 = extract_frequency(rem2)

    # Step 4: Extract explicit dose
    dose, rem4 = extract_dose(rem3)

    # Step 5: Clean candidate medicine name
    med_name = clean_medicine_name(rem4)

    # Validate medicine name candidate length and content
    if not med_name or len(med_name) < 2:
        return None

    # Filter out stopwords, purely numeric text, or single-character noise
    if med_name.isdigit() or med_name.lower() in {
        "and",
        "the",
        "for",
        "tab",
        "cap",
        "mg",
        "ml",
        "take",
        "once",
        "twice",
        "rx",
        "sign",
        "date",
        "daily",
    }:
        return None

    # Filter out common medical advice sentences: e.g. "Drink plenty of water"
    if re.search(r"\b(?:drink|water|rest|diet|exercise|walk|warm|avoid)\b", med_name, re.IGNORECASE):
        if not strength and not dose and not frequency:
            return None

    # Require credible clinical context unless explicitly bypassed (e.g. for database direct match)
    if not allow_contextless and not has_clinical_context(line, strength, frequency, duration, dose):
        return None

    return ParsedPrescriptionItem(
        raw_line=line.strip(),
        raw_medicine_name=med_name,
        strength=strength,
        dose=dose,
        frequency=frequency,
        duration=duration,
        ocr_confidence=confidence,
    )


def extract_prescription_items(
    lines: list,
    known_drug_names: Optional[set[str]] = None,
) -> list[ParsedPrescriptionItem]:
    """Extract medicines from legacy tuples or grouped OCR entries."""

    items: list[ParsedPrescriptionItem] = []
    lower_known = {
        name.lower() for name in known_drug_names
    } if known_drug_names else set()

    for entry in lines:

        # Backwards-compatible tuple input.
        if isinstance(entry, tuple):
            if len(entry) != 2:
                continue

            line_text, conf = entry

            if not line_text or not line_text.strip():
                continue

            words = {
                word.lower()
                for word in re.findall(r"\b[A-Za-z]{3,}\b", line_text)
            }

            parsed = parse_prescription_line(
                line_text,
                confidence=conf,
                allow_contextless=bool(words.intersection(lower_known)),
            )

            if parsed:
                items.append(parsed)

            continue

        # Grouped OCR object.
        combined_text = getattr(entry, "text", "")
        raw_lines = getattr(entry, "raw_lines", None)
        conf = getattr(entry, "confidence", None)

        if not combined_text or not raw_lines:
            continue

        medicine_line = raw_lines[0].strip()

        if not medicine_line or is_header_or_footer_line(medicine_line):
            continue

        # Explicitly reject date-like OCR entries.
        if re.search(
            r"\b(?:date|dob)\b\s*[:\-]?\s*\d",
            medicine_line,
            re.IGNORECASE,
        ):
            continue

        # Parse the complete group for clinical instructions.
        combined_parsed = parse_prescription_line(
            combined_text,
            confidence=conf,
        )

        # Parse only the original medicine line for its candidate name.
        medicine_parsed = parse_prescription_line(
            medicine_line,
            confidence=conf,
            allow_contextless=True,
        )

        if medicine_parsed is None:
            continue

        candidate = medicine_parsed.raw_medicine_name.strip()

        if not candidate:
            continue

        # Reject short OCR noise such as "eee" and "ate".
        alpha_words = re.findall(r"\b[A-Za-z]{2,}\b", candidate)

        if not alpha_words:
            continue

        # Preserve a contextless candidate only when it belongs to a
        # multi-line grouped prescription entry.
        if combined_parsed is None and len(raw_lines) < 2:
            continue

        # Require at least one substantial alphabetic token.
        if max((len(word) for word in alpha_words), default=0) < 5:
            continue

        items.append(
            ParsedPrescriptionItem(
                raw_line=combined_text.strip(),
                raw_medicine_name=candidate,
                strength=(
                    combined_parsed.strength
                    if combined_parsed else medicine_parsed.strength
                ),
                dose=combined_parsed.dose if combined_parsed else None,
                frequency=combined_parsed.frequency if combined_parsed else None,
                duration=combined_parsed.duration if combined_parsed else None,
                ocr_confidence=conf,
            )
        )

    return items

