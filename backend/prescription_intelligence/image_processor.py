"""Image preprocessing pipeline for prescription OCR using OpenCV and Pillow.

Implements grayscale conversion, noise reduction, adaptive thresholding,
and adaptive resizing optimized for CPU-based execution.
"""

from typing import Any, Optional
import cv2
import numpy as np
from PIL import Image
import io


class ImageProcessingError(Exception):
    """Raised when image preprocessing fails."""
    pass


def decode_image_bytes(data: bytes) -> np.ndarray:
    """Decode raw image bytes into an OpenCV BGR numpy array."""
    try:
        np_arr = np.frombuffer(data, dtype=np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            # Fallback to Pillow
            pil_img = Image.open(io.BytesIO(data)).convert("RGB")
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return image
    except Exception as exc:
        raise ImageProcessingError(f"Failed to decode image data: {str(exc)}") from exc


def resize_for_ocr(
    image: np.ndarray,
    min_width: int = 1200,
    max_dimension: int = 2600,
) -> tuple[np.ndarray, float]:
    """Resize image to an optimal resolution for OCR without degrading CPU speed.

    Returns:
        tuple[np.ndarray, float]: (resized_image, scale_factor)
    """
    height, width = image.shape[:2]
    scale_factor = 1.0

    # Upscale low-resolution scans/images
    if width < min_width and width > 0:
        scale_factor = min(2.5, min_width / float(width))
        new_w = int(round(width * scale_factor))
        new_h = int(round(height * scale_factor))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        return resized, scale_factor

    # Downscale overly large high-res camera captures to maintain fast CPU OCR
    max_side = max(height, width)
    if max_side > max_dimension:
        scale_factor = max_dimension / float(max_side)
        new_w = int(round(width * scale_factor))
        new_h = int(round(height * scale_factor))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale_factor

    return image, scale_factor


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert an image to single-channel grayscale."""
    if len(image.shape) == 2:
        return image
    elif len(image.shape) == 3:
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raise ImageProcessingError(f"Unexpected image shape: {image.shape}")


def reduce_noise(gray_image: np.ndarray) -> np.ndarray:
    """Apply bilateral filtering to smooth noise while preserving sharp font edges."""
    return cv2.bilateralFilter(gray_image, d=5, sigmaColor=50, sigmaSpace=50)


def enhance_contrast(gray_image: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for uneven lighting."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray_image)


def apply_adaptive_threshold(gray_image: np.ndarray) -> np.ndarray:
    """Apply Otsu's thresholding for high-contrast binarized text."""
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def preprocess_image(
    image_bytes: bytes,
    target_binarize: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Complete image preprocessing pipeline for prescription OCR.

    Args:
        image_bytes: Raw bytes of the uploaded image file.
        target_binarize: Whether to apply Otsu binarization (True) or enhanced grayscale (False).

    Returns:
        tuple[np.ndarray, dict[str, Any]]:
            - Preprocessed image array suitable for Tesseract OCR.
            - Metadata dictionary describing initial dimensions, resized dimensions, and scale.
    """
    raw_bgr = decode_image_bytes(image_bytes)
    orig_h, orig_w = raw_bgr.shape[:2]

    # Resize adaptively
    scaled_bgr, scale = resize_for_ocr(raw_bgr)
    proc_h, proc_w = scaled_bgr.shape[:2]

    # Grayscale
    gray = convert_to_grayscale(scaled_bgr)

    # Contrast enhancement
    enhanced = enhance_contrast(gray)

    # Noise reduction
    denoised = reduce_noise(enhanced)

    # Thresholding if explicitly requested
    if target_binarize:
        processed = apply_adaptive_threshold(denoised)
    else:
        processed = denoised

    meta = {
        "original_width": orig_w,
        "original_height": orig_h,
        "processed_width": proc_w,
        "processed_height": proc_h,
        "scale_factor": round(scale, 3),
        "binarized": target_binarize,
    }

    return processed, meta
