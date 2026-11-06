
"""Unit tests for PrescriptionIntelligenceService orchestration."""

import pytest

from backend.common.schemas import MedicineRecord, PrescriptionResult
from backend.prescription_intelligence.medicine_identifier import DrugRecord, MedicineIdentifier
from backend.prescription_intelligence.ocr_engine import OCREngine
from backend.prescription_intelligence.service import PrescriptionIntelligenceService
from backend.prescription_intelligence.validators import ImageValidationError
from tests.conftest import create_synthetic_prescription_image


def test_service_end_to_end_empty_db(synthetic_prescription_png):
    # Explicitly use an empty database for this test.
    identifier = MedicineIdentifier(db_path="non_existent_test_drugs.csv")
    service = PrescriptionIntelligenceService(medicine_identifier=identifier)

    result, audit = service.process_prescription_image(
        image_bytes=synthetic_prescription_png,
        filename="rx_sample.png",
        content_type="image/png",
    )

    # Validates PrescriptionResult schema
    assert isinstance(result, PrescriptionResult)
    assert result.prescription_id.startswith("rx-")
    assert len(result.medicines) > 0

    # Ensure no clinic or doctor or patient headers leaked into medicines
    med_names = [m.medicine_name.lower() for m in result.medicines]
    assert not any("clinic" in n for n in med_names)
    assert not any("doctor" in n or "jane doe" in n for n in med_names)
    assert not any("alex johnson" in n or "patient" in n for n in med_names)

    # Validate each medicine record adheres to Pydantic schema
    for med in result.medicines:
        assert isinstance(med, MedicineRecord)
        assert med.prescription_id == result.prescription_id
        assert med.identification_status in ("unverified", "requires_verification")
        assert med.medicine_name
        # Active ingredient must never be fabricated when database is empty
        assert med.active_ingredient is None

    # Validate internal audit record is preserved for debugging
    assert audit.raw_ocr_text
    assert audit.ocr_latency_ms > 0
    assert audit.total_latency_ms >= audit.ocr_latency_ms
    assert service.last_audit_record == audit


def test_service_with_populated_database(synthetic_prescription_png):
    identifier = MedicineIdentifier(db_path="non_existent.csv")
    identifier.load_custom_records([
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin Trihydrate", strength="500 mg"),
        DrugRecord(name="Paracetamol", active_ingredient="Acetaminophen", strength="650 mg"),
        DrugRecord(name="Omeprazole", active_ingredient="Omeprazole Magnesium", strength="20 mg"),
    ])

    service = PrescriptionIntelligenceService(medicine_identifier=identifier)
    result, audit = service.process_prescription_image(
        image_bytes=synthetic_prescription_png,
        filename="rx_sample.png",
    )

    names = [m.medicine_name for m in result.medicines]
    assert any("Amoxicillin" in n for n in names)

    # Check verified / matched status for reference drugs
    amox_records = [m for m in result.medicines if "Amoxicillin" in m.medicine_name]
    assert len(amox_records) > 0
    amox = amox_records[0]
    assert amox.identification_status in ("verified", "fuzzy_matched")
    assert amox.active_ingredient == "Amoxicillin Trihydrate"
    assert amox.strength == "500 mg"
    assert amox.dose == "1 tablet"
    assert amox.frequency == "Twice daily (BD)"
    assert amox.duration == "5 days"


def test_service_unknown_medicine_flagged_for_verification():
    # Synthetic prescription with an unlisted drug
    custom_lines = [
        "Dr. Jane Doe, MD",
        "City Clinic",
        "-------------------",
        "Rx:",
        "1. Tab ExperimentalCompoundX 25mg 1 tab OD for 7 days",
    ]
    img_bytes = create_synthetic_prescription_image(lines=custom_lines)

    identifier = MedicineIdentifier(db_path="non_existent.csv")
    identifier.load_custom_records([
        DrugRecord(name="Amoxicillin", active_ingredient="Amoxicillin", strength="500 mg"),
    ])

    service = PrescriptionIntelligenceService(medicine_identifier=identifier)
    result, _ = service.process_prescription_image(img_bytes, filename="rx.png")

    assert len(result.medicines) == 1
    med = result.medicines[0]
    # Unknown medicine must NOT be marked verified
    assert med.identification_status in ("requires_verification", "unrecognized")
    assert med.active_ingredient is None  # Never fabricated


def test_service_invalid_file_rejected():
    service = PrescriptionIntelligenceService()
    with pytest.raises(ImageValidationError):
        service.process_prescription_image(
            image_bytes=b"not_an_image",
            filename="bad.txt",
        )
