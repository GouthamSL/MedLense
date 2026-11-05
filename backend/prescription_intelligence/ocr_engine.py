"""OCR Engine utilizing Tesseract through pytesseract.

Handles executable path detection, execution time measurement,
word/line-level confidence scoring, and unclear text detection.
"""

from collections import defaultdict
from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import time
from typing import Any, Optional
import numpy as np
import pytesseract


class TesseractNotFoundError(Exception):
    """Raised when the Tesseract OCR executable cannot be found on the system."""
    pass


class OCRExecutionError(Exception):
    """Raised when Tesseract OCR fails during execution."""
    pass


@dataclass
class OCRWord:
    """Individual word extracted by OCR with its positional confidence."""
    text: str
    confidence: float  # Normalized 0.0 to 1.0
    left: int
    top: int
    width: int
    height: int
    line_num: int


@dataclass
class OCRLine:
    """Single line of OCR text containing words and line-average confidence."""
    text: str
    confidence: float  # Normalized 0.0 to 1.0
    words: list[OCRWord] = field(default_factory=list)
    line_num: int = 0


@dataclass
class OCRExtractionResult:
    """Complete result of OCR processing on a prescription image."""
    raw_text: str
    cleaned_text: str
    lines: list[OCRLine]
    average_confidence: float
    is_low_confidence: bool
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


class OCREngine:
    """Tesseract OCR wrapper with auto-detection and confidence analysis."""

    COMMON_WINDOWS_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self._explicit_path_provided = tesseract_cmd is not None
        self.tesseract_cmd = self._resolve_tesseract_path(tesseract_cmd)
        if self.tesseract_cmd and os.path.isfile(self.tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _resolve_tesseract_path(self, explicit_path: Optional[str]) -> Optional[str]:
        """Resolve the Tesseract binary path from args, env, PATH, or common locations."""
        # 1. Explicit argument - if provided, do not fall back to system locations
        if explicit_path is not None:
            return explicit_path

        # 2. Environment variable
        env_path = os.getenv("TESSERACT_CMD")
        if env_path and os.path.isfile(env_path):
            return env_path

        # 3. PATH
        system_cmd = shutil.which("tesseract")
        if system_cmd:
            return system_cmd

        # 4. Standard Windows locations
        for candidate in self.COMMON_WINDOWS_PATHS:
            if candidate and os.path.isfile(candidate):
                return candidate

        return None

    def is_available(self) -> bool:
        """Check whether Tesseract is installed and functional."""
        if not self.tesseract_cmd and not self._explicit_path_provided:
            self.tesseract_cmd = self._resolve_tesseract_path(None)
            if self.tesseract_cmd and os.path.isfile(self.tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        if not self.tesseract_cmd or not os.path.isfile(self.tesseract_cmd):
            return False

        try:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            _ = pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """Return the installed Tesseract version string."""
        if not self.is_available():
            return None
        try:
            return str(pytesseract.get_tesseract_version())
        except Exception:
            return None

    def extract_text(
        self,
        image: np.ndarray,
        psm: int = 6,
        confidence_threshold: float = 0.55,
    ) -> OCRExtractionResult:
        """Run OCR on the given preprocessed image array.

        Args:
            image: Preprocessed numpy image array (grayscale or binarized).
            psm: Page segmentation mode.
            confidence_threshold: Below which text is flagged as low confidence.

        Returns:
            OCRExtractionResult: Structured OCR extraction with confidence metrics and latency.
        """
        if not self.is_available():
            raise TesseractNotFoundError(
                "Tesseract OCR executable not found. Please ensure Tesseract is installed "
                "or configure the path using the TESSERACT_CMD environment variable."
            )

        start_time = time.perf_counter()

        config = f"--oem 3 --psm {psm}"

        try:
            # 1. Full raw text extraction
            raw_text = pytesseract.image_to_string(image, config=config)

            # 2. Detailed word and confidence data
            data = pytesseract.image_to_data(
                image,
                config=config,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            raise OCRExecutionError(f"Tesseract OCR execution failed: {str(exc)}") from exc

        end_time = time.perf_counter()
        latency_ms = round((end_time - start_time) * 1000, 2)

        # Parse word-level confidences into lines grouped by (block_num, par_num, line_num)
        # to ensure lines across different blocks/paragraphs are strictly separated
        grouped_lines: dict[tuple[int, int, int], list[OCRWord]] = defaultdict(list)
        total_conf_sum = 0.0
        word_count = 0

        num_entries = len(data.get("text", []))
        for i in range(num_entries):
            word_str = data["text"][i].strip()
            conf_val = float(data["conf"][i])

            if conf_val < 0 or not word_str:
                continue

            normalized_conf = round(conf_val / 100.0, 4)
            total_conf_sum += normalized_conf
            word_count += 1

            line_key = (
                int(data.get("block_num", [0])[i]),
                int(data.get("par_num", [0])[i]),
                int(data.get("line_num", [0])[i]),
            )

            word_obj = OCRWord(
                text=word_str,
                confidence=normalized_conf,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
                line_num=line_key[2],
            )
            grouped_lines[line_key].append(word_obj)

        lines: list[OCRLine] = []
        for idx, (key, words) in enumerate(grouped_lines.items(), start=1):
            if not words:
                continue
            line_text = " ".join(w.text for w in words)
            avg_line_conf = round(sum(w.confidence for w in words) / len(words), 4)
            lines.append(
                OCRLine(
                    text=line_text,
                    confidence=avg_line_conf,
                    words=words,
                    line_num=idx,
                )
            )

        avg_confidence = round(total_conf_sum / word_count, 4) if word_count > 0 else 0.0
        is_low_conf = avg_confidence < confidence_threshold or word_count == 0

        # Normalization of raw text
        cleaned_text = "\n".join(
            line.strip() for line in raw_text.splitlines() if line.strip()
        )

        return OCRExtractionResult(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            lines=lines,
            average_confidence=avg_confidence,
            is_low_confidence=is_low_conf,
            latency_ms=latency_ms,
            metadata={
                "word_count": word_count,
                "tesseract_cmd": self.tesseract_cmd,
                "psm": psm,
            },
        )
