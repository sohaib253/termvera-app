import shutil
from dataclasses import dataclass

import fitz  # PyMuPDF

LOW_TEXT_CHAR_THRESHOLD = 40


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


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


class UnsupportedDocumentError(Exception):
    pass


def extract_document(content: bytes) -> DocumentExtractionResult:
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise UnsupportedDocumentError(
            "The file could not be opened as a PDF. It may be corrupted, "
            "password-protected, or not a real PDF."
        ) from exc

    if pdf.is_encrypted:
        pdf.close()
        raise UnsupportedDocumentError(
            "This PDF is password-protected. Remove the password and re-upload."
        )

    pages: list[PageExtractionResult] = []
    tesseract_ready = ocr_available()

    for index in range(pdf.page_count):
        page = pdf.load_page(index)
        text = page.get_text().strip()
        char_count = len(text)
        low_text = char_count < LOW_TEXT_CHAR_THRESHOLD

        method = "native"
        if low_text:
            if tesseract_ready:
                ocr_text = _ocr_page(page)
                if ocr_text:
                    text = ocr_text
                    char_count = len(text)
                    method = "ocr"
                else:
                    method = "ocr_failed"
            else:
                method = "ocr_unavailable"

        pages.append(
            PageExtractionResult(
                page_number=index + 1,
                text=text,
                char_count=char_count,
                extraction_method=method,
                low_text_warning=low_text and method != "ocr",
            )
        )

    page_count = pdf.page_count
    pdf.close()
    return DocumentExtractionResult(page_count=page_count, pages=pages)


def _ocr_page(page: "fitz.Page") -> str:
    import io

    import pytesseract
    from PIL import Image

    pix = page.get_pixmap(dpi=200)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""
