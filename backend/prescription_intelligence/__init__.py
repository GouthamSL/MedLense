"""Prescription Intelligence module for MedLense."""

from backend.prescription_intelligence.dosage_extractor import (
    ParsedPrescriptionItem,
    extract_prescription_items,
    parse_prescription_line,
)
from backend.prescription_intelligence.image_processor import preprocess_image
from backend.prescription_intelligence.line_grouper import (
    GroupedMedicineLine,
    group_ocr_lines,
    is_continuation_line,
    is_new_medicine_start,
)
from backend.prescription_intelligence.medicine_identifier import (
    DrugRecord,
    IdentificationResult,
    MedicineIdentifier,
)
from backend.prescription_intelligence.ocr_engine import (
    OCREngine,
    OCRExtractionResult,
    OCRLine,
    OCRWord,
    TesseractNotFoundError,
)
from backend.prescription_intelligence.router import router
from backend.prescription_intelligence.service import (
    PrescriptionIntelligenceService,
    ProcessingAuditRecord,
)
from backend.prescription_intelligence.validators import (
    ImageValidationError,
    validate_image_payload,
)

__all__ = [
    "router",
    "PrescriptionIntelligenceService",
    "ProcessingAuditRecord",
    "OCREngine",
    "OCRExtractionResult",
    "OCRLine",
    "OCRWord",
    "TesseractNotFoundError",
    "preprocess_image",
    "MedicineIdentifier",
    "DrugRecord",
    "IdentificationResult",
    "ParsedPrescriptionItem",
    "extract_prescription_items",
    "parse_prescription_line",
    "GroupedMedicineLine",
    "group_ocr_lines",
    "is_continuation_line",
    "is_new_medicine_start",
    "validate_image_payload",
    "ImageValidationError",
]
