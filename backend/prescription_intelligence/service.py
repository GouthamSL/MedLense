"""Prescription Intelligence core orchestration service.

Coordinates the complete pipeline:
Validation -> Image Preprocessing -> OCR -> Medicine-Line Grouping ->
Clinical Information Extraction -> Medicine Identification & Normalization ->
Structured Pydantic Response.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Optional
import uuid

from backend.common.schemas import MedicineRecord, PrescriptionResult
from backend.prescription_intelligence.dosage_extractor import (
    extract_prescription_items,
    ParsedPrescriptionItem,
)
from backend.prescription_intelligence.image_processor import preprocess_image
from backend.prescription_intelligence.line_grouper import group_ocr_lines
from backend.prescription_intelligence.medicine_identifier import MedicineIdentifier
from backend.prescription_intelligence.ocr_engine import OCREngine, OCRExtractionResult
from backend.prescription_intelligence.validators import validate_image_payload

logger = logging.getLogger("prescription_intelligence.service")


@dataclass
class ProcessingAuditRecord:
    """Internal audit record preserving raw OCR text, latencies, and metadata."""
    prescription_id: str
    filename: Optional[str]
    raw_ocr_text: str
    cleaned_ocr_text: str
    ocr_latency_ms: float
    total_latency_ms: float
    ocr_confidence: float
    is_low_confidence: bool
    image_metadata: dict[str, Any]
    items_extracted_count: int
    timestamp: float = field(default_factory=time.time)


class PrescriptionIntelligenceService:
    """Orchestrates image processing, OCR, multi-line grouping, and normalization."""

    def __init__(
        self,
        ocr_engine: Optional[OCREngine] = None,
        medicine_identifier: Optional[MedicineIdentifier] = None,
    ):
        self.ocr_engine = ocr_engine or OCREngine()
        self.medicine_identifier = medicine_identifier or MedicineIdentifier()
        self._last_audit_record: Optional[ProcessingAuditRecord] = None

    @property
    def last_audit_record(self) -> Optional[ProcessingAuditRecord]:
        """Internal debugging accessor preserving the most recent OCR and pipeline audit record."""
        return self._last_audit_record

    @staticmethod
    def generate_prescription_id() -> str:
        """Generate a unique prescription identifier with rx- prefix."""
        return f"rx-{uuid.uuid4().hex[:12]}"

    def process_prescription_image(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> tuple[PrescriptionResult, ProcessingAuditRecord]:
        """Process an uploaded prescription image through the complete intelligent pipeline.

        Args:
            image_bytes: Raw bytes of uploaded file.
            filename: Original filename (for extension validation).
            content_type: MIME content type header.

        Returns:
            tuple[PrescriptionResult, ProcessingAuditRecord]:
                - Validated PrescriptionResult with MedicineRecord list.
                - Internal audit record preserving raw OCR text and latencies.
        """
        overall_start = time.perf_counter()

        # Step 1: Image Validation
        validate_image_payload(
            data=image_bytes,
            filename=filename,
            content_type=content_type,
        )

        # Step 2: Image Preprocessing
        preprocessed_img, img_meta = preprocess_image(image_bytes)

        # Step 3: OCR Extraction
        ocr_result: OCRExtractionResult = self.ocr_engine.extract_text(preprocessed_img)

        # Step 4: Medicine-Line Grouping Stage
        # Associate continuation lines (e.g. '1 tab BD x 5 days') with preceding medicine line
        known_drugs = self.medicine_identifier.get_known_drug_names()
        grouped_lines = group_ocr_lines(
            lines=ocr_result.lines,
            known_drug_names=known_drugs,
        )

        # Preserve grouped OCR objects and their original raw_lines.
        # Fall back to text tuples only when grouping returns no entries.
        extraction_inputs = grouped_lines

        if not extraction_inputs and ocr_result.cleaned_text:
            extraction_inputs = [
                (line.strip(), ocr_result.average_confidence)
                for line in ocr_result.cleaned_text.splitlines()
                if line.strip()
            ]

        # Step 5: Clinical Extraction from Grouped Entries
        extracted_items: list[ParsedPrescriptionItem] = extract_prescription_items(
            lines=extraction_inputs,
            known_drug_names=known_drugs,
        )

        # Step 6: Medicine Identification & Normalization
        prescription_id = self.generate_prescription_id()
        medicine_records: list[MedicineRecord] = []

        for item in extracted_items:
            # Match against database / reference data
            ident = self.medicine_identifier.identify_medicine(
                candidate_name=item.raw_medicine_name,
                extracted_strength=item.strength,
                ocr_confidence=item.ocr_confidence,
            )

            # If OCR overall was flagged as low confidence, adjust status
            status = ident.identification_status
            if ocr_result.is_low_confidence and status not in ("requires_verification",):
                status = "requires_verification"

            record = MedicineRecord(
                medicine_name=ident.medicine_name,
                active_ingredient=ident.active_ingredient,
                strength=ident.strength,
                dose=item.dose,
                frequency=item.frequency,
                duration=item.duration,
                prescription_id=prescription_id,
                identification_status=status,
                identification_confidence=ident.identification_confidence,
            )
            medicine_records.append(record)

        overall_end = time.perf_counter()
        total_latency_ms = round((overall_end - overall_start) * 1000, 2)

        # Preserve raw text and diagnostic info internally for debugging
        audit_record = ProcessingAuditRecord(
            prescription_id=prescription_id,
            filename=filename,
            raw_ocr_text=ocr_result.raw_text,
            cleaned_ocr_text=ocr_result.cleaned_text,
            ocr_latency_ms=ocr_result.latency_ms,
            total_latency_ms=total_latency_ms,
            ocr_confidence=ocr_result.average_confidence,
            is_low_confidence=ocr_result.is_low_confidence,
            image_metadata=img_meta,
            items_extracted_count=len(medicine_records),
        )
        self._last_audit_record = audit_record

        result = PrescriptionResult(
            prescription_id=prescription_id,
            medicines=medicine_records,
        )

        return result, audit_record
