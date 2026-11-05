"""FastAPI router for the Prescription Intelligence module.

Provides endpoints for health checks, prescription image upload,
text extraction, and structured JSON normalization.
"""

from typing import Any, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.common.schemas import PrescriptionResult
from backend.prescription_intelligence.ocr_engine import (
    OCRExecutionError,
    TesseractNotFoundError,
)
from backend.prescription_intelligence.service import (
    PrescriptionIntelligenceService,
    ProcessingAuditRecord,
)
from backend.prescription_intelligence.validators import ImageValidationError

router = APIRouter(prefix="/prescription", tags=["Prescription Intelligence"])

# Shared service instance
_service: Optional[PrescriptionIntelligenceService] = None


def get_service() -> PrescriptionIntelligenceService:
    """Dependency / accessor for the PrescriptionIntelligenceService instance."""
    global _service
    if _service is None:
        _service = PrescriptionIntelligenceService()
    return _service


def set_service(service: PrescriptionIntelligenceService) -> None:
    """Allow overriding the service instance for testing or dependency injection."""
    global _service
    _service = service


class HealthResponse(BaseModel):
    status: str
    module: str
    ocr_available: bool
    tesseract_version: Optional[str] = None
    database_records_loaded: int
    database_empty: bool


class AuditPrescriptionResponse(BaseModel):
    result: PrescriptionResult
    raw_ocr_text: str
    ocr_latency_ms: float
    total_latency_ms: float
    ocr_confidence: float
    is_low_confidence: bool
    image_metadata: dict[str, Any]


@router.get("/health", response_model=HealthResponse, summary="Module Health Check")
async def health_check() -> HealthResponse:
    """Check module readiness, Tesseract availability, and reference database status."""
    service = get_service()
    ocr_avail = service.ocr_engine.is_available()
    tess_ver = service.ocr_engine.get_version() if ocr_avail else None
    record_count = service.medicine_identifier.record_count

    return HealthResponse(
        status="healthy",
        module="prescription_intelligence",
        ocr_available=ocr_avail,
        tesseract_version=tess_ver,
        database_records_loaded=record_count,
        database_empty=service.medicine_identifier.is_database_empty,
    )


@router.post(
    "/extract",
    response_model=PrescriptionResult,
    status_code=status.HTTP_200_OK,
    summary="Extract Prescription from Image",
    description="Upload a prescription image (PNG, JPG, JPEG) to extract, identify, and normalize medicines.",
)
async def extract_prescription(
    file: UploadFile = File(..., description="Prescription image file (PNG, JPG, or JPEG)"),
) -> PrescriptionResult:
    """Accept prescription image upload and return structured PrescriptionResult."""
    service = get_service()

    try:
        image_bytes = await file.read()
        result, _ = service.process_prescription_image(
            image_bytes=image_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
        return result
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except TesseractNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OCRExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the prescription image: {str(exc)}",
        ) from exc


@router.post(
    "/upload",
    response_model=PrescriptionResult,
    status_code=status.HTTP_200_OK,
    summary="Upload Prescription Image (Alias)",
)
async def upload_prescription_alias(
    file: UploadFile = File(..., description="Prescription image file (PNG, JPG, or JPEG)"),
) -> PrescriptionResult:
    """Alias for /extract endpoint to support both upload and extraction semantic naming."""
    return await extract_prescription(file=file)


@router.post(
    "/extract-with-audit",
    response_model=AuditPrescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Prescription with Diagnostic Audit Info",
)
async def extract_with_audit(
    file: UploadFile = File(..., description="Prescription image file"),
) -> AuditPrescriptionResponse:
    """Extract prescription and return structured result alongside raw OCR text and latency diagnostics."""
    service = get_service()
    try:
        image_bytes = await file.read()
        result, audit = service.process_prescription_image(
            image_bytes=image_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
        return AuditPrescriptionResponse(
            result=result,
            raw_ocr_text=audit.raw_ocr_text,
            ocr_latency_ms=audit.ocr_latency_ms,
            total_latency_ms=audit.total_latency_ms,
            ocr_confidence=audit.ocr_confidence,
            is_low_confidence=audit.is_low_confidence,
            image_metadata=audit.image_metadata,
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except TesseractNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

