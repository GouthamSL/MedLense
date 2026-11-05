"""Unit tests for OCR medicine-line grouping module."""

import pytest

from backend.prescription_intelligence.line_grouper import (
    GroupedMedicineLine,
    group_ocr_lines,
    is_continuation_line,
    is_new_medicine_start,
)
from backend.prescription_intelligence.ocr_engine import OCRLine, OCRWord


def make_ocr_line(text: str, line_num: int = 1, conf: float = 0.95) -> OCRLine:
    words = [
        OCRWord(
            text=w,
            confidence=conf,
            left=10,
            top=10 * line_num,
            width=50,
            height=20,
            line_num=line_num,
        )
        for w in text.split()
    ]
    return OCRLine(text=text, confidence=conf, words=words, line_num=line_num)


def test_medicine_line_followed_by_instruction_line():
    # User's exact example:
    # Medicine line: "1. Amoxicillin 500 mg"
    # Continuation: "1 tab BD x 5 days"
    lines = [
        make_ocr_line("1. Amoxicillin 500 mg", line_num=1, conf=0.96),
        make_ocr_line("1 tab BD x 5 days", line_num=2, conf=0.92),
    ]

    grouped = group_ocr_lines(lines)
    assert len(grouped) == 1
    assert grouped[0].text == "1. Amoxicillin 500 mg 1 tab BD x 5 days"
    assert len(grouped[0].raw_lines) == 2
    assert grouped[0].line_numbers == [1, 2]
    # Weighted confidence check
    assert 0.90 <= grouped[0].confidence <= 0.96


def test_multiple_consecutive_medicines_with_continuations():
    lines = [
        make_ocr_line("1. Amoxicillin 500 mg", line_num=1),
        make_ocr_line("1 tab BD x 5 days", line_num=2),
        make_ocr_line("2. Paracetamol 650 mg", line_num=3),
        make_ocr_line("1-0-1 for 3 days", line_num=4),
        make_ocr_line("3. Cap Omeprazole 20mg", line_num=5),
        make_ocr_line("1 cap OD before food x 14 days", line_num=6),
    ]

    grouped = group_ocr_lines(lines)
    assert len(grouped) == 3

    assert grouped[0].text == "1. Amoxicillin 500 mg 1 tab BD x 5 days"
    assert grouped[1].text == "2. Paracetamol 650 mg 1-0-1 for 3 days"
    assert grouped[2].text == "3. Cap Omeprazole 20mg 1 cap OD before food x 14 days"


def test_clinic_headers_and_unrelated_text_filtered():
    lines = [
        make_ocr_line("City Healthcare Clinic, Medical Center", line_num=1),
        make_ocr_line("Dr. Jane Doe, MD - Consultant Physician", line_num=2),
        make_ocr_line("Patient: Alex Johnson   Age: 38   Date: 2026-11-05", line_num=3),
        make_ocr_line("--------------------------------------------------", line_num=4),
        make_ocr_line("Rx:", line_num=5),
        make_ocr_line("1. Amoxicillin 500 mg", line_num=6),
        make_ocr_line("1 tab BD x 5 days", line_num=7),
        make_ocr_line("Signature: Dr. Jane Doe", line_num=8),
        make_ocr_line("Follow up after 1 week", line_num=9),
    ]

    grouped = group_ocr_lines(lines)
    assert len(grouped) == 1
    assert grouped[0].text == "1. Amoxicillin 500 mg 1 tab BD x 5 days"


def test_low_confidence_preservation():
    lines = [
        make_ocr_line("1. Tab Azithromycin 500mg", line_num=1, conf=0.45),
        make_ocr_line("1 tab OD x 3 days", line_num=2, conf=0.40),
    ]

    grouped = group_ocr_lines(lines)
    assert len(grouped) == 1
    # Average confidence should reflect the low OCR confidence
    assert grouped[0].confidence < 0.50
    assert len(grouped[0].words) > 0


def test_standalone_dosage_instruction_not_treated_as_medicine():
    # If an instruction line appears with no preceding medicine line
    lines = [
        make_ocr_line("City Healthcare Clinic", line_num=1),
        make_ocr_line("Take 1 tablet twice daily with water", line_num=2),
    ]

    # Clinic line is filtered. The orphan instruction line has no medicine name.
    grouped = group_ocr_lines(lines)
    # Even if captured into a candidate line, dosage_extractor will reject it because it has no medicine name
    from backend.prescription_intelligence.dosage_extractor import extract_prescription_items
    items = extract_prescription_items([(g.text, g.confidence) for g in grouped])
    assert len(items) == 0


def test_is_continuation_and_new_medicine_helpers():
    assert is_continuation_line("1 tab BD x 5 days") is True
    assert is_continuation_line("1-0-1 for 3 days") is True
    assert is_continuation_line("Take 1 cap OD before meals") is True
    assert is_continuation_line("1. Amoxicillin 500mg") is False

    assert is_new_medicine_start("1. Amoxicillin 500mg") is True
    assert is_new_medicine_start("Tab Paracetamol 650mg") is True
    assert is_new_medicine_start("1 tab BD x 5 days") is False

