"""Shared test fixtures and synthetic image generators for MedLense tests."""

import io
from PIL import Image, ImageDraw, ImageFont
import pytest


def create_synthetic_prescription_image(
    lines: list[str] = None,
    width: int = 1200,
    height: int = 800,
    format: str = "PNG",
) -> bytes:
    """Generate a clean synthetic prescription image in memory."""
    if lines is None:
        lines = [
            "Dr. Jane Doe, MD - General Medicine",
            "City Healthcare Clinic, Medical Center",
            "Patient: Alex Johnson   Age: 38   Date: 2026-11-05",
            "--------------------------------------------------",
            "Rx:",
            "1. Tab Amoxicillin 500mg 1 tablet BD for 5 days",
            "2. Paracetamol 650mg 1-0-1 for 3 days",
            "3. Cap Omeprazole 20mg 1 cap OD for 14 days",
            "--------------------------------------------------",
            "Signature: Dr. Jane Doe",
        ]

    # White background image
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Use clean default vector font with proper size
    try:
        font = ImageFont.load_default(size=20)
    except TypeError:
        # Fallback for older Pillow
        font = ImageFont.load_default()

    y_offset = 40
    line_spacing = 38

    for line in lines:
        draw.text((60, y_offset), line, fill=(0, 0, 0), font=font)
        y_offset += line_spacing

    buf = io.BytesIO()
    image.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def synthetic_prescription_png() -> bytes:
    """Return synthetic PNG prescription image bytes."""
    return create_synthetic_prescription_image(format="PNG")


@pytest.fixture
def synthetic_prescription_jpeg() -> bytes:
    """Return synthetic JPEG prescription image bytes."""
    return create_synthetic_prescription_image(format="JPEG")
