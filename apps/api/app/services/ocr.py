"""Tesseract OCR for scanned pages.

Most contracts in the field are scans: a photocopied, signed and stamped
paper original run through an office scanner, with no text layer at all.
Two things about those scans drive the design here:

- Pages are frequently sideways or upside down (a landscape rate table
  fed in portrait, a page turned over on the glass). Tesseract reads an
  upside-down page as confident-looking garbage, so a page whose word
  confidence comes back low is run through orientation detection,
  rotated, and read again; the better of the two reads wins.
- Tesseract is a separate executable, not a Python package. Installing it
  without admin rights on Windows puts it outside PATH, so the standard
  install folders are searched as well as PATH and TESSERACT_CMD.
"""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger("tenderguard.ocr")

# Below this mean word confidence (0-100) a page is suspected to be rotated
# and gets an orientation check. Clean upright scans score 85-95.
LOW_CONFIDENCE_THRESHOLD = 60.0
# Words this unsure at the edge of a line are stamp/signature fragments.
EDGE_NOISE_CONFIDENCE = 30.0


@dataclass
class OcrResult:
    text: str
    confidence: float  # mean word confidence, 0-100
    rotated_degrees: int = 0


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env_var)
        if not base:
            continue
        if env_var == "LOCALAPPDATA":
            candidates.append(Path(base) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
        else:
            candidates.append(Path(base) / "Tesseract-OCR" / "tesseract.exe")
    candidates += [
        Path("/usr/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
        Path("/opt/homebrew/bin/tesseract"),
    ]
    return candidates


@lru_cache
def find_tesseract() -> str | None:
    configured = get_settings().tesseract_cmd
    if configured:
        return configured if Path(configured).is_file() else None
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    for candidate in _candidate_paths():
        if candidate.is_file():
            return str(candidate)
    return None


def ocr_available() -> bool:
    return find_tesseract() is not None


def _configure() -> None:
    import pytesseract

    cmd = find_tesseract()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


@dataclass
class _Line:
    block: int
    paragraph: tuple[int, int]
    words: list[str]
    boxes: list[tuple[int, int, int, int]]  # left, top, width, height per word
    marker_prefix: str = ""
    consumed: bool = False

    @property
    def text(self) -> str:
        body = " ".join(self.words)
        return f"{self.marker_prefix} {body}" if self.marker_prefix else body


# A clause or list number standing alone: "5.2", "6.", "(a)", "iv)", "b.".
_MARKER = re.compile(r"^(?:\(?\d{1,3}(?:\.\d{1,3}){0,4}[.)]?|\(?[a-zA-Z][.)]|\(?[ivxIVX]{1,5}[.)])$")


def _read(image: Image.Image) -> OcrResult:
    """One Tesseract pass, rebuilding line/paragraph breaks from the word
    boxes so a single call yields both the text and its confidence."""
    import pytesseract

    data = pytesseract.image_to_data(
        image,
        lang=get_settings().ocr_languages,
        config="--psm 3",
        output_type=pytesseract.Output.DICT,
    )
    lines: list[_Line] = []
    confidences: list[float] = []
    current_key: tuple[int, int, int] | None = None
    words: list[str] = []
    word_confidences: list[float] = []
    boxes: list[tuple[int, int, int, int]] = []

    def flush() -> None:
        if not words or current_key is None:
            return
        kept = _trim_edge_noise(words, word_confidences)
        if not kept or _is_noise_line([w for w, _ in kept], [c for _, c in kept]):
            return
        # Trimming only removes from the ends, so the kept words are a
        # contiguous run; find where it starts to keep boxes aligned.
        offset = next(i for i in range(len(words)) if words[i : i + len(kept)] == [w for w, _ in kept])
        kept_words = [w for w, _ in kept]
        # A tick glued to a clause number ("v5.1") only changes the first word.
        kept_words[0] = _strip_margin_mark(f"{kept_words[0]} x").rsplit(" ", 1)[0]
        lines.append(
            _Line(
                block=current_key[0],
                paragraph=current_key[:2],
                words=kept_words,
                boxes=boxes[offset : offset + len(kept)],
            )
        )

    for i, word in enumerate(data["text"]):
        word = (word or "").strip()
        if not word:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if key != current_key:
            flush()
            current_key = key
            words, word_confidences, boxes = [], [], []
        words.append(word)
        boxes.append((data["left"][i], data["top"][i], data["width"][i], data["height"][i]))
        conf = float(data["conf"][i])
        if conf >= 0:
            confidences.append(conf)
        word_confidences.append(max(conf, 0.0))  # kept aligned with words
    flush()

    _attach_margin_markers(lines)

    out: list[str] = []
    previous_paragraph: tuple[int, int] | None = None
    for line in lines:
        if line.consumed or not line.words:
            continue
        if previous_paragraph is not None and (
            line.paragraph != previous_paragraph or line.marker_prefix
        ):
            out.append("")  # blank line between paragraphs, as image_to_string does
        out.append(line.text)
        previous_paragraph = line.paragraph

    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    text = "\n".join(out)
    # Dropped noise lines can leave runs of blank paragraph separators.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return OcrResult(text=text.strip(), confidence=confidence)


def _attach_margin_markers(lines: list[_Line]) -> None:
    """Rejoin clause numbers set in a hanging-indent margin to their text.

    Formal contracts often print numbers in their own column:

        5.2   Any taxes, duties, fees ...
              future, assessed ...
        5.3   The Contractor shall ...

    Tesseract reads that column as a separate block, so the page came out
    as "5.2 5.3 5.4 ..." followed by unnumbered paragraphs, and clause
    detection found none of them. Each lone marker is put back in front of
    the line level with it to its right. Only list markers move: a stamp or
    signature in the margin is never glued to a clause heading.

    Level is judged between the marker and the first word of the line (not
    the lines' bounding boxes), which keeps it right on a slightly skewed
    scan, where whole-line boxes grow tall and overlap their neighbours.
    """
    markers = [ln for ln in lines if len(ln.words) == 1 and _MARKER.match(ln.words[0])]
    for marker in markers:
        m_left, m_top, m_width, m_height = marker.boxes[0]
        m_right, m_centre = m_left + m_width, m_top + m_height / 2
        best: _Line | None = None
        best_gap = None
        for line in lines:
            if line is marker or line.consumed or line.block == marker.block or line.marker_prefix:
                continue
            if len(line.words) == 1 and _MARKER.match(line.words[0]):
                continue
            left, top, _, height = line.boxes[0]
            if left < m_right:
                continue
            if abs((top + height / 2) - m_centre) > 0.6 * min(height, m_height):
                continue
            gap = left - m_right
            if best_gap is None or gap < best_gap:
                best, best_gap = line, gap
        if best is not None:
            best.marker_prefix = marker.words[0]
            marker.consumed = True


def _is_noise_line(words: list[str], confidences: list[float]) -> bool:
    """Signatures, initials, and rubber stamps on a scanned contract come out
    of Tesseract as short low-confidence gibberish ("att HAM) AD Pa yp",
    "4 ya\""), which clause segmentation can mistake for a clause. Figures
    are never dropped however unsure the read: a smudged "675,000/-" can
    score below 30% and still be the contract value. A lone stray digit
    doesn't count as a figure; signatures often contain one."""
    text = "".join(words)
    digits = sum(ch.isdigit() for ch in text)
    confident_number = any(
        any(ch.isdigit() for ch in word) and conf >= 70
        for word, conf in zip(words, confidences, strict=False)
    )
    if digits >= 2 or confident_number:
        return False
    mean = sum(confidences) / len(confidences) if confidences else 0.0
    alphanumeric = sum(ch.isalnum() for ch in text)
    if alphanumeric <= 3 and mean < 60:
        return True
    return mean < 40


def _trim_edge_noise(words: list[str], confidences: list[float]) -> list[tuple[str, float]]:
    """Drop near-zero-confidence fragments from the start and end of a line.
    A stamp or signature overlapping the margin reads as junk glued onto a
    real line ("ise non 5. TAXES AND DUTIES:"), which hides the clause
    number from segmentation. Anything containing a digit is kept."""
    pairs = list(zip(words, confidences, strict=False))

    def junk(pair: tuple[str, float]) -> bool:
        word, conf = pair
        return conf < EDGE_NOISE_CONFIDENCE and not any(ch.isdigit() for ch in word)

    while pairs and junk(pairs[0]):
        pairs.pop(0)
    while pairs and junk(pairs[-1]):
        pairs.pop()
    return pairs


# A reviewer's tick or a stray pen mark in the margin gets read as a letter
# glued to the clause number ("v5.1 Any taxes..."), which hides the clause
# from segmentation.
_MARGIN_MARK = re.compile(r"^[a-zA-Z/|'`]{1,2}(?=\d{1,2}(?:\.\d{1,2})+\s)")


def _strip_margin_mark(line: str) -> str:
    return _MARGIN_MARK.sub("", line)


def _detect_rotation(image: Image.Image) -> int:
    import pytesseract

    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractError:
        # OSD refuses pages with too few characters to judge orientation.
        return 0
    return int(osd.get("rotate", 0)) % 360


def ocr_image(image: Image.Image) -> OcrResult:
    """OCR one page image, correcting orientation when the first read looks wrong."""
    _configure()
    if image.mode not in ("L", "RGB"):
        image = image.convert("L")

    first = _read(image)
    if first.confidence >= LOW_CONFIDENCE_THRESHOLD and len(first.text) >= 40:
        return first

    rotation = _detect_rotation(image)
    if rotation == 0:
        return first
    # OSD reports the clockwise rotation needed; PIL rotates counter-clockwise.
    second = _read(image.rotate(-rotation, expand=True))
    second.rotated_degrees = rotation
    if second.confidence > first.confidence:
        return second
    return first


def ocr_png_bytes(png: bytes) -> OcrResult:
    from PIL import Image as PILImage

    with PILImage.open(io.BytesIO(png)) as image:
        image.load()
        return ocr_image(image)
