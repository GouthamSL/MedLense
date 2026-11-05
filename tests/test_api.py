"""Integration tests for FastAPI endpoints."""

from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app import app
from backend.prescription_intelligence.ocr_engine import OCREngine, TesseractNotFoundError
from backend.prescription_intelligence.router import set_service
from backend.prescription_intelligence.service import PrescriptionIntelligenceService
from tests.conftest import create_synthetic_prescription_image

client = TestClient(app)


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"] == "MedLense"
    assert "/api/v1/prescription/extract" in data["endpoints"]["prescription_extract"]


def test_health_endpoints():
    # Overall health
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "healthy"

    # Module health
    resp2 = client.get("/api/v1/prescription/health")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "healthy"
    assert data["module"] == "prescription_intelligence"
    assert data["ocr_available"] is True
    assert "tesseract_version" in data


def test_extract_endpoint_success(synthetic_prescription_png):
    files = {
        "file": ("prescription.png", synthetic_prescription_png, "image/png"),
    }
    resp = client.post("/api/v1/prescription/extract", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "prescription_id" in data
    assert data["prescription_id"].startswith("rx-")
    assert "medicines" in data
    assert isinstance(data["medicines"], list)
    assert len(data["medicines"]) > 0


def test_upload_alias_endpoint_success(synthetic_prescription_jpeg):
    files = {
        "file": ("prescription.jpeg", synthetic_prescription_jpeg, "image/jpeg"),
    }
    resp = client.post("/api/v1/prescription/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "prescription_id" in data
    assert len(data["medicines"]) > 0


def test_extract_with_audit_endpoint(synthetic_prescription_png):
    files = {
        "file": ("prescription.png", synthetic_prescription_png, "image/png"),
    }
    resp = client.post("/api/v1/prescription/extract-with-audit", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "raw_ocr_text" in data
    assert "ocr_latency_ms" in data
    assert data["ocr_latency_ms"] > 0


def test_invalid_extension_rejected():
    files = {
        "file": ("prescription.txt", b"Invalid text file", "text/plain"),
    }
    resp = client.post("/api/v1/prescription/extract", files=files)
    assert resp.status_code == 415
    assert "Unsupported file extension" in resp.json()["detail"]


def test_corrupted_image_rejected():
    files = {
        "file": ("prescription.png", b"CORRUPTED_BYTES_NOT_PNG", "image/png"),
    }
    resp = client.post("/api/v1/prescription/extract", files=files)
    assert resp.status_code in (400, 415)


def test_empty_file_rejected():
    files = {
        "file": ("prescription.png", b"", "image/png"),
    }
    resp = client.post("/api/v1/prescription/extract", files=files)
    assert resp.status_code in (400, 422)


def test_tesseract_unavailable_returns_503(synthetic_prescription_png):
    # Deterministically mock Tesseract as unavailable
    mock_engine = OCREngine(tesseract_cmd=r"C:\fake\path\tesseract.exe")
    with patch.object(mock_engine, "is_available", return_value=False):
        mock_service = PrescriptionIntelligenceService(ocr_engine=mock_engine)
        set_service(mock_service)
        try:
            files = {
                "file": ("prescription.png", synthetic_prescription_png, "image/png"),
            }
            resp = client.post("/api/v1/prescription/extract", files=files)
            assert resp.status_code == 503
            assert "Tesseract OCR executable not found" in resp.json()["detail"]
        finally:
            # Restore working service
            set_service(PrescriptionIntelligenceService())
