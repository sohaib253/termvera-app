"""Text extraction for every supported upload format.

Everything is normalised to a list of numbered pages, because every
downstream consumer (requirement evidence, clause segmentation, the
"open at page N" links) cites page numbers:

- PDF: the native text layer where one exists; Tesseract OCR for pages
  that are scanned images (see _page_needs_ocr for what counts).
- Word (.docx), RTF and ODT: read directly in Python, paged at the page
  breaks the file records. Legacy .doc: exported to PDF by Microsoft Word
  (or LibreOffice, if that is what's installed), and that PDF is kept as
  the document's viewable rendition.
- Images (.png, .jpg, .tif incl. multi-page TIFF): OCR, one page per frame.
- Plain text: split into approximate pages.
"""

import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import fitz  # PyMuPDF

from app.core.config import get_settings
from app.services.ocr import ocr_available, ocr_image, ocr_png_bytes

logger = logging.getLogger("tenderguard.extraction")

LOW_TEXT_CHAR_THRESHOLD = 40
# A page this sparse in native text but mostly covered by an image is a
# scan with a small digital overlay (a stamped page number, a Bates label),
# not a text page — its body is only readable by OCR.
SCAN_OVERLAY_CHAR_THRESHOLD = 200
SCAN_IMAGE_COVERAGE = 0.5
# Formats with no physical pages are split into pages of about this size,
# roughly one printed page of contract text.
APPROX_PAGE_CHARS = 3000
PAGE_BREAK = "\f"
_LIBREOFFICE_PROFILE = Path(tempfile.gettempdir()) / "tenderguard-libreoffice-profile"
_LIBREOFFICE_LOCK = threading.Lock()

ProgressCallback = Callable[[int, int], None]


class UnsupportedDocumentError(Exception):
    pass


@dataclass(frozen=True)
class FileFormat:
    kind: str  # "pdf" | "docx" | "doc" | "rtf" | "odt" | "image" | "text"
    label: str


# Extension -> format. Browsers report MIME types for Word files
# inconsistently (often application/octet-stream), so the extension and
# the file's leading bytes decide, not the declared content type.
SUPPORTED_EXTENSIONS: dict[str, FileFormat] = {
    ".pdf": FileFormat("pdf", "PDF"),
    ".docx": FileFormat("docx", "Word document"),
    ".docm": FileFormat("docx", "Word document"),
    ".doc": FileFormat("doc", "Word 97-2003 document"),
    ".rtf": FileFormat("rtf", "Rich Text document"),
    ".odt": FileFormat("odt", "OpenDocument text"),
    ".png": FileFormat("image", "PNG image"),
    ".jpg": FileFormat("image", "JPEG image"),
    ".jpeg": FileFormat("image", "JPEG image"),
    ".tif": FileFormat("image", "TIFF image"),
    ".tiff": FileFormat("image", "TIFF image"),
    ".txt": FileFormat("text", "Text file"),
}

SUPPORTED_FORMATS_DESCRIPTION = (
    "PDF (including scanned), Word (.docx, .doc), RTF, ODT, TXT, "
    "or a scanned image (PNG, JPG, TIFF)"
)


@dataclass
class PageExtractionResult:
    page_number: int
    text: str
    char_count: int
    extraction_method: str
    low_text_warning: bool


@dataclass
class DocumentExtractionResult:
    page_count: int
    pages: list[PageExtractionResult]
    # A PDF rendering of a non-PDF upload (Word via LibreOffice), kept so
    # "open at page N" links work for those files too.
    rendition_pdf: bytes | None = None
    notes: list[str] = field(default_factory=list)


def detect_format(filename: str, content: bytes) -> FileFormat:
    extension = Path(filename).suffix.lower()
    if content.startswith(b"%PDF"):
        return SUPPORTED_EXTENSIONS[".pdf"]
    fmt = SUPPORTED_EXTENSIONS.get(extension)
    if fmt is None:
        raise UnsupportedDocumentError(
            f"'{extension or filename}' files are not supported. Upload a {SUPPORTED_FORMATS_DESCRIPTION}."
        )
    if fmt.kind == "pdf":
        raise UnsupportedDocumentError(
            "The file could not be opened as a PDF. It may be corrupted, "
            "password-protected, or not a real PDF."
        )
    return fmt


@lru_cache
def find_libreoffice() -> str | None:
    configured = get_settings().libreoffice_path
    if configured:
        return configured if Path(configured).is_file() else None
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for env_var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_var)
        if base:
            candidate = Path(base) / "LibreOffice" / "program" / "soffice.exe"
            if candidate.is_file():
                return str(candidate)
    for candidate in (
        Path("/usr/bin/soffice"),
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def extract_document(
    content: bytes, *, filename: str = "document.pdf", progress: ProgressCallback | None = None
) -> DocumentExtractionResult:
    fmt = detect_format(filename, content)
    if fmt.kind == "pdf":
        return _extract_pdf(content, progress=progress)
    if fmt.kind == "docx":
        return _extract_docx(content)
    if fmt.kind == "doc":
        return _extract_legacy_doc(content, progress=progress)
    if fmt.kind == "rtf":
        return _extract_rtf(content)
    if fmt.kind == "odt":
        return _extract_odt(content)
    if fmt.kind == "image":
        return _extract_image(content, progress=progress)
    return _extract_text(content)


# ---------------------------------------------------------------- PDF --


def _page_needs_ocr(page: fitz.Page, native_chars: int) -> bool:
    if native_chars < LOW_TEXT_CHAR_THRESHOLD:
        return True
    if native_chars >= SCAN_OVERLAY_CHAR_THRESHOLD:
        return False
    page_area = abs(page.rect)
    if page_area <= 0:
        return False
    image_area = sum(abs(fitz.Rect(info["bbox"]) & page.rect) for info in page.get_image_info())
    return image_area / page_area >= SCAN_IMAGE_COVERAGE


def _extract_pdf(content: bytes, *, progress: ProgressCallback | None) -> DocumentExtractionResult:
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise UnsupportedDocumentError(
            "The file could not be opened as a PDF. It may be corrupted, "
            "password-protected, or not a real PDF."
        ) from exc

    try:
        if pdf.is_encrypted and not pdf.authenticate(""):
            raise UnsupportedDocumentError(
                "This PDF is password-protected. Remove the password and re-upload."
            )
        return _extract_open_pdf(pdf, progress=progress)
    finally:
        pdf.close()


def _extract_open_pdf(pdf: fitz.Document, *, progress: ProgressCallback | None) -> DocumentExtractionResult:
    total = pdf.page_count
    tesseract_ready = ocr_available()
    dpi = get_settings().ocr_dpi

    texts: list[str] = []
    methods: list[str] = []
    ocr_indices: list[int] = []
    for index in range(total):
        page = pdf.load_page(index)
        text = page.get_text().strip()
        texts.append(text)
        if _page_needs_ocr(page, len(text)):
            ocr_indices.append(index)
            methods.append("ocr_unavailable" if not tesseract_ready else "ocr_pending")
        else:
            methods.append("native")

    done = total - len(ocr_indices)
    if progress:
        progress(done, total)

    if ocr_indices and tesseract_ready:
        # PyMuPDF is not thread-safe, so pages are rendered here on one
        # thread and only the OCR (a Tesseract subprocess per page) runs in
        # the pool. Rendering stays a bounded window ahead of OCR so a
        # 500-page scan never holds more than a few page images in memory.
        workers = get_settings().ocr_workers or min(8, max(1, (os.cpu_count() or 2) // 2))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending: dict[Future, int] = {}

            def collect(future: Future, index: int) -> None:
                nonlocal done
                native = texts[index]
                try:
                    result = future.result()
                except Exception:
                    logger.exception("OCR failed on page %d", index + 1)
                    methods[index] = "ocr_failed"
                else:
                    # Keep whichever of the native layer or OCR read more.
                    if len(result.text) > len(native):
                        texts[index] = result.text
                        methods[index] = "ocr"
                    else:
                        methods[index] = "native"
                done += 1
                if progress:
                    progress(done, total)

            for index in ocr_indices:
                while len(pending) >= workers * 2:
                    oldest = next(iter(pending))
                    collect(oldest, pending.pop(oldest))
                pix = pdf.load_page(index).get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
                pending[pool.submit(ocr_png_bytes, pix.tobytes("png"))] = index
            for future, index in pending.items():
                collect(future, index)

    pages: list[PageExtractionResult] = []
    for i in range(total):
        text = _clean(texts[i])
        read_ok = methods[i] in ("native", "ocr")
        pages.append(
            PageExtractionResult(
                page_number=i + 1,
                text=text,
                char_count=len(text),
                extraction_method=methods[i],
                low_text_warning=not read_ok or len(text) < LOW_TEXT_CHAR_THRESHOLD,
            )
        )
    notes = []
    if ocr_indices and not tesseract_ready:
        notes.append(
            f"{len(ocr_indices)} scanned page(s) could not be read because OCR (Tesseract) is not installed."
        )
    return DocumentExtractionResult(page_count=total, pages=pages, notes=notes)


# --------------------------------------------------------------- Word --
#
# .docx, .rtf and .odt are read directly in Python: no Office install, a
# few milliseconds per file, identical results on every machine. Only the
# legacy binary .doc needs a converter; Microsoft Word is used when it is
# installed (most business laptops), LibreOffice otherwise (e.g. a Linux
# server), and without either the user is asked to save as .docx.

WORD_TIMEOUT_SECONDS = 120
_WORD_LOCK = threading.Lock()

# Runs Word invisibly to export the document as PDF. AutomationSecurity=3
# (force-disable) stops macros in an uploaded file from running, and a
# dummy password makes a protected file fail at once instead of opening a
# password prompt nobody can see.
_WORD_TO_PDF_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
try {
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $doc = $word.Documents.Open($env:TG_SOURCE, $false, $true, $false, 'tg-no-password')
    try { $doc.ExportAsFixedFormat($env:TG_TARGET, 17) } finally { $doc.Close(0) }
} finally {
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
"""

_RTF_PAGE_MARKER = "TGPAGEBREAKMARKER"


@lru_cache
def word_available() -> bool:
    if os.name != "nt":
        return False
    import winreg

    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CurVer").Close()
    except OSError:
        return False
    return True


def _convert_with_word(content: bytes, *, suffix: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="tg-word-") as tmp:
        source = Path(tmp) / f"source{suffix}"
        target = Path(tmp) / "source.pdf"
        source.write_bytes(content)
        env = {**os.environ, "TG_SOURCE": str(source), "TG_TARGET": str(target)}
        # Word runs as one process per user session; serialise conversions.
        with _WORD_LOCK:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", _WORD_TO_PDF_SCRIPT],
                env=env,
                capture_output=True,
                timeout=WORD_TIMEOUT_SECONDS,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        if completed.returncode != 0 or not target.is_file():
            logger.warning(
                "Word conversion failed (%s): %s",
                completed.returncode,
                completed.stderr.decode(errors="replace")[:500],
            )
            raise UnsupportedDocumentError(
                "The document could not be converted. It may be corrupted or password-protected."
            )
        return target.read_bytes()


def _convert_with_libreoffice(content: bytes, *, suffix: str) -> bytes:
    soffice = find_libreoffice()
    if soffice is None:
        raise UnsupportedDocumentError("LibreOffice is not installed.")
    with tempfile.TemporaryDirectory(prefix="tg-convert-") as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / f"source{suffix}"
        source.write_bytes(content)
        # A dedicated profile, separate from the user's own LibreOffice (a
        # running desktop copy would otherwise swallow the request), and
        # reused across conversions: building a fresh profile costs over a
        # minute per file on Windows. One instance can use a profile at a
        # time, hence the lock.
        profile = _LIBREOFFICE_PROFILE.as_uri()
        with _LIBREOFFICE_LOCK:
            completed = subprocess.run(
                [
                    soffice,
                    f"-env:UserInstallation={profile}",
                    "--headless",
                    "--norestore",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(source),
                ],
                capture_output=True,
                timeout=WORD_TIMEOUT_SECONDS,
                check=False,
            )
        output = tmp_path / "source.pdf"
        if completed.returncode != 0 or not output.is_file():
            logger.warning(
                "LibreOffice conversion failed (%s): %s",
                completed.returncode,
                completed.stderr.decode(errors="replace")[:500],
            )
            raise UnsupportedDocumentError(
                "The document could not be converted. It may be corrupted or password-protected."
            )
        return output.read_bytes()


def _extract_legacy_doc(
    content: bytes, *, progress: ProgressCallback | None
) -> DocumentExtractionResult:
    converters: list[Callable[..., bytes]] = []
    if word_available():
        converters.append(_convert_with_word)
    if find_libreoffice() is not None:
        converters.append(_convert_with_libreoffice)
    if not converters:
        raise UnsupportedDocumentError(
            "Old-style Word files (.doc) can only be read on a computer with Microsoft Word "
            "installed. Open the file in Word, save it as .docx or PDF, and upload that instead."
        )
    for convert in converters:
        try:
            pdf_bytes = convert(content, suffix=".doc")
        except (UnsupportedDocumentError, subprocess.TimeoutExpired, OSError):
            continue
        # The converted PDF gives real page numbers, may contain scanned
        # page images needing OCR, and is kept as the viewable rendition.
        result = _extract_pdf(pdf_bytes, progress=progress)
        result.rendition_pdf = pdf_bytes
        return result
    raise UnsupportedDocumentError(
        "This .doc file could not be converted for reading. Open it in Word, save it as .docx "
        "or PDF, and upload that instead."
    )


def _extract_docx(content: bytes) -> DocumentExtractionResult:
    import docx
    from docx.oxml.ns import qn

    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as exc:
        raise UnsupportedDocumentError(
            "The file could not be opened as a Word document. It may be corrupted, "
            "password-protected, or saved in an older format."
        ) from exc

    numbering = _WordNumbering(document)

    # Walk the body in document order so tables stay where they sit in the
    # contract (schedules of rates are usually tables). Word records where
    # it last broke pages (lastRenderedPageBreak) as well as manual breaks,
    # so page numbers match what the author saw in Word.
    last_rendered = f".//{qn('w:lastRenderedPageBreak')}"
    textbox_paragraphs = f".//{qn('w:txbxContent')}//{qn('w:p')}"
    blocks: list[str] = []

    def walk(container: Iterable) -> None:  # type: ignore[type-arg]
        for element in container:
            if element.tag == qn("w:p"):
                paragraph = docx.text.paragraph.Paragraph(element, document)
                starts_new_page = any(
                    br.get(qn("w:type")) == "page" for br in element.iter(qn("w:br"))
                ) or element.find(last_rendered) is not None
                if starts_new_page:
                    blocks.append(PAGE_BREAK)
                label = numbering.label_for(element, paragraph.style)
                blocks.append(f"{label} {paragraph.text}" if label else paragraph.text)
                # Text boxes hang off a paragraph but aren't part of its text.
                for inner in element.iterfind(textbox_paragraphs):
                    blocks.append(docx.text.paragraph.Paragraph(inner, document).text)
            elif element.tag == qn("w:tbl"):
                table = docx.table.Table(element, document)
                if element.find(last_rendered) is not None:
                    blocks.append(PAGE_BREAK)
                blocks.extend(
                    _table_rows([cell.text for cell in row.cells] for row in table.rows)
                )
            elif element.tag == qn("w:sdt"):
                # Content controls: contract templates often wrap whole
                # sections in them.
                content = element.find(qn("w:sdtContent"))
                if content is not None:
                    walk(content.iterchildren())

    walk(document.element.body.iterchildren())
    return _paginate_text("\n".join(blocks), method="docx")


class _WordNumbering:
    """Renders Word's automatic list numbering ("4.1", "(a)", "iii.").

    Contracts almost always number clauses this way, and the numbers live
    in numbering.xml as formatting, not in the paragraph text, so without
    this every clause number vanishes and clause segmentation, which keys
    on those numbers, finds almost nothing. Counters follow Word's rules
    closely enough for clause numbering: one sequence per abstract list,
    deeper levels restart when a shallower one advances, and each level's
    number format and label pattern ("%1.%2") come from the list
    definition. Bullets are dropped; they carry no clause identity.
    """

    def __init__(self, document) -> None:  # type: ignore[no-untyped-def]
        from docx.oxml.ns import qn

        self._qn = qn
        # abstractNumId -> ilvl -> (start, numFmt, lvlText)
        self._abstract: dict[str, dict[int, tuple[int, str, str]]] = {}
        # numId -> (abstractNumId, {ilvl: startOverride})
        self._nums: dict[str, tuple[str, dict[int, int]]] = {}
        self._counters: dict[str, list[int | None]] = {}
        self._overrides_applied: set[str] = set()
        try:
            root = document.part.numbering_part.element
        except (KeyError, NotImplementedError, AttributeError):
            return

        def val(element, tag: str, default: str | None = None) -> str | None:  # type: ignore[no-untyped-def]
            child = element.find(qn(tag))
            return child.get(qn("w:val")) if child is not None else default

        for abstract in root.findall(qn("w:abstractNum")):
            levels: dict[int, tuple[int, str, str]] = {}
            for lvl in abstract.findall(qn("w:lvl")):
                levels[int(lvl.get(qn("w:ilvl"), "0"))] = (
                    int(val(lvl, "w:start", "1") or 1),
                    val(lvl, "w:numFmt", "decimal") or "decimal",
                    val(lvl, "w:lvlText", "") or "",
                )
            self._abstract[abstract.get(qn("w:abstractNumId"))] = levels
        for num in root.findall(qn("w:num")):
            overrides: dict[int, int] = {}
            for override in num.findall(qn("w:lvlOverride")):
                start = val(override, "w:startOverride")
                if start is not None:
                    overrides[int(override.get(qn("w:ilvl"), "0"))] = int(start)
            self._nums[num.get(qn("w:numId"))] = (val(num, "w:abstractNumId", "") or "", overrides)

    def _num_pr(self, element, style) -> tuple[str, int] | None:  # type: ignore[no-untyped-def]
        qn = self._qn
        num_id: str | None = None
        ilvl: int | None = None
        pr = element.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
        if pr is not None:
            node = pr.find(qn("w:numId"))
            num_id = node.get(qn("w:val")) if node is not None else None
            node = pr.find(qn("w:ilvl"))
            ilvl = int(node.get(qn("w:val"))) if node is not None else None
        # Heading and list styles usually carry the numbering themselves.
        while style is not None and (num_id is None or ilvl is None):
            pr = style.element.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
            if pr is not None:
                node = pr.find(qn("w:numId"))
                if num_id is None and node is not None:
                    num_id = node.get(qn("w:val"))
                node = pr.find(qn("w:ilvl"))
                if ilvl is None and node is not None:
                    ilvl = int(node.get(qn("w:val")))
            style = style.base_style
        if not num_id or num_id == "0" or num_id not in self._nums:
            return None
        return num_id, ilvl or 0

    def label_for(self, element, style) -> str:  # type: ignore[no-untyped-def]
        found = self._num_pr(element, style)
        if found is None:
            return ""
        num_id, ilvl = found
        abstract_id, overrides = self._nums[num_id]
        levels = self._abstract.get(abstract_id)
        if not levels or ilvl not in levels:
            return ""
        counters = self._counters.setdefault(abstract_id, [None] * 9)
        if num_id not in self._overrides_applied:
            # A list that restarts numbering (startOverride) does so the
            # first time it is used.
            self._overrides_applied.add(num_id)
            for level, start in overrides.items():
                if level < 9:
                    counters[level] = start - 1
        start, fmt, pattern = levels[ilvl]
        current = counters[ilvl]
        counters[ilvl] = start if current is None else current + 1
        for deeper in range(ilvl + 1, 9):
            counters[deeper] = None
        if fmt in ("bullet", "none"):
            return ""

        def render(match: re.Match[str]) -> str:
            level = int(match.group(1)) - 1
            level_start, level_fmt, _ = levels.get(level, (1, "decimal", ""))
            value = counters[level] if counters[level] is not None else level_start
            return _format_list_number(int(value), level_fmt)  # type: ignore[arg-type]

        return re.sub(r"%([1-9])", render, pattern).strip()


def _format_list_number(value: int, fmt: str) -> str:
    if fmt in ("lowerLetter", "upperLetter"):
        letters = ""
        n = value
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            letters = chr(ord("a") + remainder) + letters
        return letters.upper() if fmt == "upperLetter" else letters
    if fmt in ("lowerRoman", "upperRoman"):
        numerals = [
            (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
        ]
        roman, n = "", value
        for amount, numeral in numerals:
            while n >= amount:
                roman, n = roman + numeral, n - amount
        return roman.upper() if fmt == "upperRoman" else roman
    if fmt == "decimalZero":
        return f"{value:02d}"
    return str(value)


def _table_rows(rows: Iterable[Iterable[str]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        cells: list[str] = []
        for value in row:
            value = value.strip()
            if value and (not cells or cells[-1] != value):  # merged cells repeat
                cells.append(value)
        if cells:
            lines.append(" | ".join(cells))
    return lines


def _extract_rtf(content: bytes) -> DocumentExtractionResult:
    from striprtf.striprtf import rtf_to_text

    raw = content.decode("latin-1")
    if not raw.lstrip().startswith("{\\rtf"):
        raise UnsupportedDocumentError("The file could not be opened as an RTF document.")
    # striprtf drops \page; mark it so explicit page breaks survive.
    raw = re.sub(r"\\page(?![a-z])", lambda _: f"\\par {_RTF_PAGE_MARKER}\\par ", raw)
    text = rtf_to_text(raw, errors="ignore").replace(_RTF_PAGE_MARKER, PAGE_BREAK)
    return _paginate_text(text, method="rtf")


def _extract_odt(content: bytes) -> DocumentExtractionResult:
    import zipfile
    from xml.etree import ElementTree

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            root = ElementTree.fromstring(archive.read("content.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise UnsupportedDocumentError(
            "The file could not be opened as an OpenDocument text file. It may be corrupted "
            "or password-protected."
        ) from exc

    text_ns = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    table_ns = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
    office_ns = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"

    def inline_text(element: ElementTree.Element) -> str:
        parts = [element.text or ""]
        for child in element:
            tag = child.tag.removeprefix(text_ns)
            if tag == "s":
                parts.append(" " * int(child.get(f"{text_ns}c", "1")))
            elif tag == "tab":
                parts.append("\t")
            elif tag == "line-break":
                parts.append("\n")
            elif tag not in ("note", "annotation"):
                parts.append(inline_text(child))
            parts.append(child.tail or "")
        return "".join(parts)

    blocks: list[str] = []

    def walk(element: ElementTree.Element) -> None:
        # LibreOffice records where it broke pages (soft-page-break), the
        # ODF equivalent of Word's lastRenderedPageBreak.
        for child in element:
            if child.tag == f"{text_ns}soft-page-break":
                blocks.append(PAGE_BREAK)
            elif child.tag in (f"{text_ns}p", f"{text_ns}h"):
                if child.find(f"{text_ns}soft-page-break") is not None:
                    blocks.append(PAGE_BREAK)
                blocks.append(inline_text(child))
            elif child.tag == f"{table_ns}table":
                rows = [
                    [
                        "\n".join(inline_text(p) for p in cell.iter(f"{text_ns}p"))
                        for cell in row.findall(f"{table_ns}table-cell")
                    ]
                    for row in child.iter(f"{table_ns}table-row")
                ]
                blocks.extend(_table_rows(rows))
            else:
                walk(child)

    body = root.find(f"{office_ns}body")
    walk(body if body is not None else root)
    return _paginate_text("\n".join(blocks), method="odt")


# ------------------------------------------------------ image and text --


def _extract_image(content: bytes, *, progress: ProgressCallback | None) -> DocumentExtractionResult:
    from PIL import Image, ImageSequence, UnidentifiedImageError

    if not ocr_available():
        raise UnsupportedDocumentError(
            "Reading scanned images requires OCR (Tesseract), which is not installed on the server."
        )
    try:
        image = Image.open(io.BytesIO(content))
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedDocumentError("The image could not be opened. It may be corrupted.") from exc

    with image:
        frames = [frame.convert("L") for frame in ImageSequence.Iterator(image)]
    pages: list[PageExtractionResult] = []
    for index, frame in enumerate(frames):
        result = ocr_image(frame)
        text = _clean(result.text)
        pages.append(
            PageExtractionResult(
                page_number=index + 1,
                text=text,
                char_count=len(text),
                extraction_method="ocr",
                low_text_warning=len(text) < LOW_TEXT_CHAR_THRESHOLD,
            )
        )
        if progress:
            progress(index + 1, len(frames))
    return DocumentExtractionResult(page_count=len(pages), pages=pages)


def _extract_text(content: bytes) -> DocumentExtractionResult:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("latin-1")
    return _paginate_text(text, method="text")


def _paginate_text(raw: str, *, method: str) -> DocumentExtractionResult:
    """Split page-less text into pages. Explicit breaks (\\f, from Word's own
    page breaks and last-rendered page positions) are used when present;
    otherwise a page ends at the first paragraph boundary after about
    APPROX_PAGE_CHARS."""
    if PAGE_BREAK in raw:
        pages_text = raw.split(PAGE_BREAK)
    else:
        pages_text = []
        current: list[str] = []
        size = 0
        for paragraph in raw.split("\n"):
            if size >= APPROX_PAGE_CHARS and paragraph.strip():
                pages_text.append("\n".join(current))
                current, size = [], 0
            current.append(paragraph)
            size += len(paragraph) + 1
        pages_text.append("\n".join(current))

    pages_text = [p for p in (_clean(p) for p in pages_text) if p] or [""]
    pages = [
        PageExtractionResult(
            page_number=i + 1,
            text=text,
            char_count=len(text),
            extraction_method=method,
            low_text_warning=len(text) < LOW_TEXT_CHAR_THRESHOLD,
        )
        for i, text in enumerate(pages_text)
    ]
    if all(not p.text for p in pages):
        raise UnsupportedDocumentError("No text could be found in this document.")
    return DocumentExtractionResult(page_count=len(pages), pages=pages)


def _clean(text: str) -> str:
    # Postgres TEXT rejects NUL bytes, which some scanners' text layers contain.
    return text.replace("\x00", "").strip()
