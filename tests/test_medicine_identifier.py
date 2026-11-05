"""Unit tests for medicine identification engine."""

import pytest

from backend.prescription_intelligence.medicine_identifier import (
    DrugRecord,
    MedicineIdentifier,
)


def test_empty_database_behavior(tmp_path):
    empty_csv = tmp_path / "empty_drugs.csv"
    empty_csv.write_text("")

    identifier = MedicineIdentifier(db_path=str(empty_csv))
    assert identifier.is_database_empty is True
    assert identifier.record_count == 0

    res = identifier.identify_medicine("Amoxicillin", extracted_strength="500 mg", ocr_confidence=0.92)
    assert res.medicine_name == "Amoxicillin"
    assert res.strength == "500 mg"
    assert res.active_ingredient is None  # Never fabricated!
    assert res.identification_status == "unverified"
    # OCR confidence is kept separate from database identification confidence
    assert res.identification_confidence is None


def test_populated_database_exact_match():
    identifier = MedicineIdentifier(db_path="non_existent_file.csv")
    identifier.load_custom_records([
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin Trihydrate", strength="500 mg"),
        DrugRecord(name="Paracetamol", active_ingredient="Acetaminophen", strength="650 mg"),
    ])

    assert identifier.is_database_empty is False
    assert identifier.record_count == 2

    # Case-insensitive exact match
    res = identifier.identify_medicine("amoxicillin", extracted_strength="500 mg")
    assert res.medicine_name == "Amoxicillin"
    assert res.active_ingredient == "Amoxicillin Trihydrate"
    assert res.identification_status == "verified"
    assert res.identification_confidence == 1.0


def test_strength_disambiguation():
    identifier = MedicineIdentifier(db_path="non_existent.csv")
    identifier.load_custom_records([
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin", strength="250 mg"),
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin", strength="500 mg"),
    ])

    res = identifier.identify_medicine("Amoxicillin", extracted_strength="500 mg")
    assert res.strength == "500 mg"


def test_controlled_fuzzy_match():
    identifier = MedicineIdentifier(db_path="non_existent.csv")
    identifier.load_custom_records([
        DrugRecord(name="Azithromycin", active_ingredient="Azithromycin Dihydrate", strength="500 mg"),
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin Trihydrate", strength="500 mg"),
    ])

    # Slight typo "Azithromicin" (similarity > 0.90)
    res = identifier.identify_medicine("Azithromicin", extracted_strength="500 mg")
    assert res.identification_status == "fuzzy_matched"
    assert res.medicine_name == "Azithromycin"
    assert res.active_ingredient == "Azithromycin Dihydrate"
    assert res.identification_confidence is not None
    assert res.identification_confidence >= 0.80

    # Common OCR typo "Amaxcilin" vs "Amoxicillin"
    res2 = identifier.identify_medicine("Amaxcilin", extracted_strength="500 mg")
    assert res2.identification_status == "fuzzy_matched"
    assert res2.medicine_name == "Amoxicillin"
    assert res2.active_ingredient == "Amoxicillin Trihydrate"


def test_low_similarity_rejected_fuzzy_match():
    identifier = MedicineIdentifier(db_path="non_existent.csv")
    identifier.load_custom_records([
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin", strength="500 mg"),
    ])

    # Distinct unknown name
    res = identifier.identify_medicine("TotallyUnknownChemical123", extracted_strength="100 mg", ocr_confidence=0.88)
    assert res.identification_status in ("unrecognized", "requires_verification")
    assert res.medicine_name == "TotallyUnknownChemical123"
    assert res.active_ingredient is None  # Never fabricated
    assert res.identification_confidence is None


def test_low_ocr_confidence_triggers_verification():
    identifier = MedicineIdentifier(db_path="non_existent.csv")
    identifier.load_custom_records([
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin", strength="500 mg"),
    ])

    # OCR confidence very low (e.g. 0.40)
    res = identifier.identify_medicine("Amoxicillin", extracted_strength="500 mg", ocr_confidence=0.40)
    assert res.identification_status == "requires_verification"
    assert res.identification_confidence is None
