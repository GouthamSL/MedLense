"""Validation module for uploaded prescription images.

Ensures only valid image formats (PNG, JPG, JPEG) are processed,
rejects oversized, empty, or corrupted image payloads, and verifies image headers.
"""

from pathlib import Path
from typing import Optional
import io
from PIL import Image, UnidentifiedImageError


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/pjpeg",
    "image/jpg",
}

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MIN_IMAGE_DIMENSION = 30  # pixels


class ImageValidationError(Exception):
    """Exception raised when an image fails validation checks."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_image_extension(filename: Optional[str]) -> str:
    """Validate that filename has an accepted extension."""
    if not filename:
        raise ImageValidationError(
            "Missing filename. An image file name with extension is required.",
            status_code=400,
        )

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            status_code=415,
        )
    return ext


def validate_magic_bytes(data: bytes) -> str:
    """Validate image magic bytes to verify PNG or JPEG header format."""
    if not data:
        raise ImageValidationError("Uploaded image file is empty.", status_code=400)

    if len(data) > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise ImageValidationError(
            f"File size exceeds maximum permitted size of {max_mb:.0f} MB.",
            status_code=400,
        )

    # PNG magic bytes: \x89PNG\r\n\x1a\n
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    # JPEG magic bytes: \xff\xd8\xff
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    raise ImageValidationError(
        "Invalid file header. Content does not match supported PNG or JPEG signature.",
        status_code=415,
    )


def validate_image_payload(
    data: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size: int = MAX_FILE_SIZE_BYTES,
) -> tuple[int, int, str]:
    """Perform end-to-end image validation.

    Returns:
        tuple[int, int, str]: (width, height, format_name)

    Raises:
        ImageValidationError: If validation fails.
    """
    if filename:
        validate_image_extension(filename)

    if content_type:
        normalized_ct = content_type.lower().split(";")[0].strip()
        if normalized_ct not in ALLOWED_CONTENT_TYPES:
            raise ImageValidationError(
                f"Unsupported content type '{normalized_ct}'. Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
                status_code=415,
            )

    detected_format = validate_magic_bytes(data)

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, Exception) as exc:
        raise ImageValidationError(
            f"Corrupted or invalid image payload: {str(exc)}",
            status_code=400,
        ) from exc

    # Re-open to read dimensions since verify() closes/invalidates the stream
    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                raise ImageValidationError(
                    f"Image dimensions ({width}x{height}) are too small for OCR processing (minimum: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}).",
                    status_code=400,
                )
            return width, height, detected_format
    except ImageValidationError:
        raise
    except Exception as exc:
        raise ImageValidationError(
            f"Failed to read image properties: {str(exc)}",
            status_code=400,
        ) from exc

