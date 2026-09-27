import asyncio
import logging
import mimetypes

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentPage, DocumentType, ExtractionStatus
from app.services import storage
from app.services.extraction import (
    DocumentExtractionResult,
    UnsupportedDocumentError,
    detect_format,
    extract_document,
)

logger = logging.getLogger("tenderguard.documents")

# How often a long extraction (a few hundred scanned pages takes minutes)
# writes its page progress back for the UI to poll.
PROGRESS_COMMIT_SECONDS = 2.0


class DocumentNotFoundError(Exception):
    pass


class InvalidUploadError(Exception):
    pass


async def create_document(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    uploaded_by_user_id: str,
    document_type: DocumentType,
    filename: str,
    content: bytes,
    mime_type: str,
) -> Document:
    if len(content) == 0:
        raise InvalidUploadError("The uploaded file is empty.")
    if len(content) > storage.MAX_UPLOAD_BYTES:
        limit_mb = storage.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise InvalidUploadError(f"The uploaded file exceeds the {limit_mb}MB limit.")
    try:
        file_format = detect_format(filename, content)
    except UnsupportedDocumentError as exc:
        raise InvalidUploadError(str(exc)) from exc
    if file_format.kind == "pdf":
        mime_type = "application/pdf"
    elif mime_type in ("", "application/octet-stream"):
        mime_type = mimetypes.guess_type(filename)[0] or mime_type

    document = Document(
        project_id=project_id,
        uploaded_by_user_id=uploaded_by_user_id,
        document_type=document_type,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
        file_hash=storage.compute_hash(content),
        storage_path="",
        extraction_status=ExtractionStatus.PENDING,
    )
    db.add(document)
    await db.flush()

    storage_path = storage.save_document_file(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document.id,
        filename=filename,
        content=content,
    )
    document.storage_path = storage_path
    await db.commit()
    await db.refresh(document)
    return document


async def run_extraction(document_id: str) -> None:
    """Runs in a FastAPI BackgroundTask with its own DB session — the
    request-scoped session is gone by the time this executes.

    Extraction itself (PDF parsing, OCR, Word conversion) is CPU- and
    subprocess-bound and can take minutes for a long scan, so it runs on a
    worker thread; running it inline would stall every other request the
    API is serving for the duration."""
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document is None:
            logger.warning("Extraction requested for missing document %s", document_id)
            return

        document.extraction_status = ExtractionStatus.PROCESSING
        document.extraction_pages_done = 0
        await db.commit()

        try:
            content = storage.read_document_file(document.storage_path)
            result = await _extract_with_progress(db, document, content)
        except UnsupportedDocumentError as exc:
            document.extraction_status = ExtractionStatus.FAILED
            document.extraction_error = str(exc)
            await db.commit()
            return
        except Exception:
            logger.exception("Unexpected extraction failure for document %s", document_id)
            document.extraction_status = ExtractionStatus.FAILED
            document.extraction_error = (
                "An unexpected error occurred while processing this document."
            )
            await db.commit()
            return

        if result.rendition_pdf is not None:
            storage.save_rendition(document.storage_path, result.rendition_pdf)

        document.page_count = result.page_count
        document.extraction_pages_done = result.page_count
        for page in result.pages:
            db.add(
                DocumentPage(
                    document_id=document.id,
                    page_number=page.page_number,
                    text=page.text,
                    char_count=page.char_count,
                    extraction_method=page.extraction_method,
                    low_text_warning=page.low_text_warning,
                )
            )
        if not any(page.text for page in result.pages):
            document.extraction_status = ExtractionStatus.FAILED
            document.extraction_error = " ".join(result.notes) or (
                "No readable text was found in this document, even with OCR. Check that the "
                "scan is legible and not blank."
            )
        else:
            document.extraction_status = ExtractionStatus.COMPLETED
            document.extraction_error = None
        await db.commit()


async def _extract_with_progress(
    db: AsyncSession, document: Document, content: bytes
) -> DocumentExtractionResult:
    state = {"done": 0, "total": 0}

    def on_progress(done: int, total: int) -> None:
        state["done"], state["total"] = done, total

    task = asyncio.ensure_future(
        asyncio.to_thread(
            extract_document,
            content,
            filename=document.original_filename,
            progress=on_progress,
        )
    )
    reported = (0, 0)
    while not task.done():
        await asyncio.wait({task}, timeout=PROGRESS_COMMIT_SECONDS)
        current = (state["done"], state["total"])
        if current != reported and current[1] > 0:
            document.page_count = current[1]
            document.extraction_pages_done = current[0]
            await db.commit()
            reported = current
    return task.result()


async def fail_interrupted_extractions(db: AsyncSession) -> int:
    """Extraction runs in a background task, so a server restart leaves
    its document reading "processing" forever. Mark those failed at
    startup, as fail_interrupted_analyses does for contract analysis."""
    interrupted = list(
        await db.scalars(
            select(Document).where(
                Document.extraction_status.in_(
                    [ExtractionStatus.PENDING, ExtractionStatus.PROCESSING]
                )
            )
        )
    )
    for document in interrupted:
        document.extraction_status = ExtractionStatus.FAILED
        document.extraction_error = (
            "Text extraction was interrupted when the server restarted. Upload the file again."
        )
    if interrupted:
        await db.commit()
        logger.warning("Marked %d interrupted document extractions as failed", len(interrupted))
    return len(interrupted)


async def list_documents(db: AsyncSession, *, project_id: str) -> list[Document]:
    result = await db.scalars(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at)
    )
    return list(result)


async def get_document(db: AsyncSession, *, project_id: str, document_id: str) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.project_id == project_id)
    )
    if document is None:
        raise DocumentNotFoundError(document_id)
    return document
