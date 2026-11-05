"""Unit tests for clinical entities and dosage extraction."""

import pytest

from backend.prescription_intelligence.dosage_extractor import (
    clean_medicine_name,
    extract_dose,
    extract_duration,
    extract_frequency,
    extract_prescription_items,
    extract_strength,
    is_header_or_footer_line,
    parse_prescription_line,
)


def test_extract_strength_single_and_compound():
    # 5mg and 500mg
    s, _ = extract_strength("Prednisolone 5mg")
    assert s == "5 mg"

    s, _ = extract_strength("Amoxicillin 500mg")
    assert s == "500 mg"

    # 5mg/5ml and 250mg/5ml
    s, _ = extract_strength("Cetirizine 5mg/5ml syrup")
    assert s == "5 mg/5 ml"

    s, _ = extract_strength("Amoxicillin 250mg/5ml oral suspension")
    assert s == "250 mg/5 ml"

    # 500 mg/125 mg compound
    s, _ = extract_strength("Augmentin 500 mg/125 mg tablets")
    assert s == "500 mg/125 mg"

    s, _ = extract_strength("Amoxicillin and Clavulanate 500/125 mg")
    assert s == "500/125 mg"

    # Other units
    s, _ = extract_strength("Vitamin D 1000 IU")
    assert s == "1000 iu"

    s, _ = extract_strength("Hydrocortisone 0.5% cream")
    assert s == "0.5 %"

    s, _ = extract_strength("Medicine without strength")
    assert s is None


def test_extract_dose():
    d, _ = extract_dose("Take 1 tablet BD")
    assert d == "1 tablet"

    d, _ = extract_dose("2 capsules OD")
    assert d == "2 capsules"

    d, _ = extract_dose("5 ml TDS")
    assert d == "5 ml"

    d, _ = extract_dose("1-2 tabs PRN")
    assert d == "1-2 tablets"

    d, _ = extract_dose("No dose specified here")
    assert d is None


def test_extract_frequency_matrix():
    f, _ = extract_frequency("Paracetamol 650mg 1-0-1 for 3 days")
    assert f == "Twice daily (1-0-1)"

    f, _ = extract_frequency("Metformin 500mg 1-1-1")
    assert f == "Three times daily (1-1-1)"

    f, _ = extract_frequency("Thyroxine 50mcg 1-0-0")
    assert f == "Once daily - Morning (1-0-0)"

    f, _ = extract_frequency("Atorvastatin 20mg 0-0-1")
    assert f == "Once daily - Night (0-0-1)"

    f, _ = extract_frequency("Drug 1-1-1-1")
    assert f == "Four times daily (1-1-1-1)"


def test_extract_frequency_latin():
    f, _ = extract_frequency("Amoxicillin 500mg BD for 5 days")
    assert f == "Twice daily (BD)"

    f, _ = extract_frequency("Azithromycin 500mg OD")
    assert f == "Once daily (OD)"

    f, _ = extract_frequency("Ibuprofen 400mg TDS")
    assert f == "Three times daily (TDS)"

    f, _ = extract_frequency("Tramadol 50mg PRN")
    assert f == "As needed (PRN/SOS)"

    f, _ = extract_frequency("Alprazolam 0.25mg HS")
    assert f == "At bedtime (HS)"

    f, _ = extract_frequency("Antibiotic Q8H")
    assert f == "Every 8 hours"


def test_extract_frequency_natural():
    f, _ = extract_frequency("Take once daily with breakfast")
    assert f == "Once daily"

    f, _ = extract_frequency("Twice a day after food")
    assert f == "Twice daily"


def test_extract_duration():
    dur, _ = extract_duration("1 tablet BD for 5 days")
    assert dur == "5 days"

    dur, _ = extract_duration("1 cap OD x 2 weeks")
    assert dur == "2 weeks"

    dur, _ = extract_duration("Take for 1 month")
    assert dur == "1 month"

    dur, _ = extract_duration("No duration mentioned")
    assert dur is None


def test_clean_medicine_name():
    assert clean_medicine_name("1. Tab Amoxicillin") == "Amoxicillin"
    assert clean_medicine_name("2) Cap Omeprazole") == "Omeprazole"
    assert clean_medicine_name("• Syr Cetirizine") == "Cetirizine"
    assert clean_medicine_name("Tab. Paracetamol") == "Paracetamol"
    assert clean_medicine_name("CapOmeprazole") == "Omeprazole"


def test_regression_header_footer_filtering():
    # Clinic and Hospital headers
    assert is_header_or_footer_line("City Healthcare Clinic, Medical Center") is True
    assert is_header_or_footer_line("Apollo Multispeciality Hospital") is True
    assert is_header_or_footer_line("St. Jude Memorial Hospital") is True

    # Doctor credentials and titles
    assert is_header_or_footer_line("Dr. Jane Doe, MD - General Medicine") is True
    assert is_header_or_footer_line("Dr. Robert Smith, MBBS, MD, Consultant Physician") is True
    assert is_header_or_footer_line("Surgeon Dr. Alan Brown") is True

    # Patient demographics
    assert is_header_or_footer_line("Patient: Alex Johnson   Age: 38   Date: 2026-11-05") is True
    assert is_header_or_footer_line("Pt Name: Maria Garcia, Age: 42, Sex: Female") is True
    assert is_header_or_footer_line("DOB: 14/08/1982, Weight: 70 kg, BP: 120/80") is True

    # Addresses and Contacts
    assert is_header_or_footer_line("124 Healthcare Boulevard, Suite 400, New York, NY") is True
    assert is_header_or_footer_line("Phone: +1-234-567-8900 Email: info@healthclinic.org") is True
    assert is_header_or_footer_line("Pincode: 560001, Ph: 9876543210") is True

    # Dividers and Prescription Markers
    assert is_header_or_footer_line("--------------------------------------------------") is True
    assert is_header_or_footer_line("==================================================") is True
    assert is_header_or_footer_line("Rx:") is True
    assert is_header_or_footer_line("Diagnosis: Acute Pharyngitis") is True
    assert is_header_or_footer_line("Signature: Dr. Jane Doe") is True
    assert is_header_or_footer_line("Follow up after 1 week") is True

    # Legitimate medicine lines must NOT be filtered
    assert is_header_or_footer_line("1. Tab Amoxicillin 500mg 1 tablet BD for 5 days") is False
    assert is_header_or_footer_line("Paracetamol 650mg 1-0-1 for 3 days") is False


def test_regression_rejects_arbitrary_non_medication_text():
    # Arbitrary non-medication lines lacking clinical context must not be parsed as medicines
    assert parse_prescription_line("Drink plenty of warm water throughout the day") is None
    assert parse_prescription_line("Avoid cold drinks and ice cream") is None
    assert parse_prescription_line("General instruction: Complete bed rest") is None
    assert parse_prescription_line("Random short text") is None


def test_parse_prescription_line_preserves_explicit_instructions():
    line = "1. Tab Amoxicillin 500mg 1 tablet BD for 5 days"
    parsed = parse_prescription_line(line, confidence=0.95)
    assert parsed is not None
    assert parsed.raw_medicine_name == "Amoxicillin"
    assert parsed.strength == "500 mg"
    assert parsed.dose == "1 tablet"
    assert parsed.frequency == "Twice daily (BD)"
    assert parsed.duration == "5 days"
    assert parsed.ocr_confidence == 0.95


def test_parse_prescription_line_never_infers_missing_clinical_instructions():
    line = "Paracetamol 650mg"
    parsed = parse_prescription_line(line)
    assert parsed is not None
    assert parsed.raw_medicine_name == "Paracetamol"
    assert parsed.strength == "650 mg"
    assert parsed.dose is None  # Never inferred!
    assert parsed.frequency is None  # Never inferred!
    assert parsed.duration is None  # Never inferred!


def test_extract_prescription_items_multiline():
    lines = [
        ("Dr. John Clinic, Medical Center", 0.9),
        ("Patient: Alex Smith, Age: 34", 0.95),
        ("Rx:", 0.9),
        ("1. Tab Amoxicillin 500mg 1-0-1 for 5 days", 0.92),
        ("2. Cap Omeprazole 20mg OD for 14 days", 0.91),
        ("Signature: Dr. John", 0.8),
    ]
    items = extract_prescription_items(lines)
    assert len(items) == 2
    assert items[0].raw_medicine_name == "Amoxicillin"
    assert items[1].raw_medicine_name == "Omeprazole"
