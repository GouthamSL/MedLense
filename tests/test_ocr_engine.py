"""Unit tests for Tesseract OCR engine."""

from unittest.mock import patch
import numpy as np
import pytest

from backend.prescription_intelligence.image_processor import preprocess_image
from backend.prescription_intelligence.ocr_engine import (
    OCREngine,
    OCRExecutionError,
    TesseractNotFoundError,
)
from tests.conftest import create_synthetic_prescription_image


def test_tesseract_not_found():
    # Deterministically mock missing Tesseract executable
    with patch("os.path.isfile", return_value=False), patch("shutil.which", return_value=None):
        engine = OCREngine(tesseract_cmd=r"C:\non_existent_dir\tesseract_fake.exe")
        assert engine.is_available() is False
        assert engine.get_version() is None

        dummy_img = np.zeros((100, 100), dtype=np.uint8)
        with pytest.raises(TesseractNotFoundError) as exc_info:
            engine.extract_text(dummy_img)
        assert "executable not found" in str(exc_info.value)


def test_ocr_engine_available():
    engine = OCREngine()
    # On this machine, Tesseract is installed at C:\Program Files\Tesseract-OCR\tesseract.exe
    assert engine.is_available() is True
    version = engine.get_version()
    assert version is not None
    assert "5." in version


def test_ocr_extraction_on_synthetic_prescription(synthetic_prescription_png):
    engine = OCREngine()
    proc_img, _ = preprocess_image(synthetic_prescription_png, target_binarize=False)

    result = engine.extract_text(proc_img)
    assert result.latency_ms > 0
    assert result.average_confidence > 0.5
    assert len(result.lines) > 0
    assert "Amoxicillin" in result.raw_text or "amoxicillin" in result.raw_text.lower()
