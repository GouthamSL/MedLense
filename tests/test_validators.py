"""Unit tests for prescription image validators."""

import io
from PIL import Image
import pytest

from backend.prescription_intelligence.validators import (
    ImageValidationError,
    validate_image_extension,
    validate_image_payload,
    validate_magic_bytes,
)
from tests.conftest import create_synthetic_prescription_image


def test_validate_image_extension_valid():
    assert validate_image_extension("rx.png") == ".png"
    assert validate_image_extension("scan.jpg") == ".jpg"
    assert validate_image_extension("DOC.JPEG") == ".jpeg"


def test_validate_image_extension_invalid():
    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_extension("prescription.pdf")
    assert exc_info.value.status_code == 415
    assert "Unsupported file extension" in exc_info.value.message

    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_extension("prescription.gif")
    assert exc_info.value.status_code == 415

    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_extension("")
    assert exc_info.value.status_code == 400


def test_validate_magic_bytes_valid_png(synthetic_prescription_png):
    assert validate_magic_bytes(synthetic_prescription_png) == "png"


def test_validate_magic_bytes_valid_jpeg(synthetic_prescription_jpeg):
    assert validate_magic_bytes(synthetic_prescription_jpeg) == "jpeg"


def test_validate_magic_bytes_empty():
    with pytest.raises(ImageValidationError) as exc_info:
        validate_magic_bytes(b"")
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.message.lower()


def test_validate_magic_bytes_corrupted():
    with pytest.raises(ImageValidationError) as exc_info:
        validate_magic_bytes(b"NOT_AN_IMAGE_FILE_HEADER_XYZ")
    assert exc_info.value.status_code == 415


def test_validate_image_payload_success(synthetic_prescription_png):
    width, height, fmt = validate_image_payload(
        data=synthetic_prescription_png,
        filename="rx.png",
        content_type="image/png",
    )
    assert width == 1200
    assert height == 800
    assert fmt == "png"


def test_validate_image_payload_too_small():
    img = Image.new("RGB", (20, 20), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    small_bytes = buf.getvalue()

    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_payload(small_bytes, filename="tiny.png")
    assert "too small" in exc_info.value.message.lower()

