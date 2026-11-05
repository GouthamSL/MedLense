"""Unit tests for image preprocessing module."""

import numpy as np
import pytest

from backend.prescription_intelligence.image_processor import (
    apply_adaptive_threshold,
    convert_to_grayscale,
    decode_image_bytes,
    enhance_contrast,
    preprocess_image,
    reduce_noise,
    resize_for_ocr,
)
from tests.conftest import create_synthetic_prescription_image


def test_decode_image_bytes(synthetic_prescription_png):
    img = decode_image_bytes(synthetic_prescription_png)
    assert isinstance(img, np.ndarray)
    assert len(img.shape) == 3
    assert img.shape[2] == 3  # BGR


def test_convert_to_grayscale(synthetic_prescription_png):
    img = decode_image_bytes(synthetic_prescription_png)
    gray = convert_to_grayscale(img)
    assert len(gray.shape) == 2


def test_resize_for_ocr_upscale():
    # Small image width 400
    small_img = np.zeros((300, 400, 3), dtype=np.uint8)
    resized, scale = resize_for_ocr(small_img, min_width=1200)
    assert resized.shape[1] >= 1000
    assert scale > 1.0


def test_resize_for_ocr_downscale():
    # Massive image 4000x3500
    large_img = np.zeros((3500, 4000, 3), dtype=np.uint8)
    resized, scale = resize_for_ocr(large_img, max_dimension=2600)
    assert max(resized.shape[:2]) <= 2600
    assert scale < 1.0


def test_noise_reduction_and_contrast(synthetic_prescription_png):
    img = decode_image_bytes(synthetic_prescription_png)
    gray = convert_to_grayscale(img)
    enhanced = enhance_contrast(gray)
    denoised = reduce_noise(enhanced)
    assert denoised.shape == gray.shape


def test_apply_adaptive_threshold(synthetic_prescription_png):
    img = decode_image_bytes(synthetic_prescription_png)
    gray = convert_to_grayscale(img)
    thresh = apply_adaptive_threshold(gray)
    assert thresh.shape == gray.shape
    # Binarized should only contain 0 or 255
    unique_vals = set(np.unique(thresh))
    assert unique_vals.issubset({0, 255})


def test_preprocess_image_pipeline(synthetic_prescription_png):
    proc_img, meta = preprocess_image(synthetic_prescription_png)
    assert isinstance(proc_img, np.ndarray)
    assert meta["original_width"] == 1200
    assert meta["original_height"] == 800
    assert "scale_factor" in meta
    assert meta["binarized"] is True

