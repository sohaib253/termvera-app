import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentPage, DocumentType, ExtractionStatus
from app.services import storage
from app.services.extraction import UnsupportedDocumentError, extract_document

logger = logging.getLogger("tenderguard.documents")


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
    if mime_type not in storage.ALLOWED_MIME_TYPES:
        raise InvalidUploadError("Only PDF files are supported at this time.")
    if len(content) == 0:
        raise InvalidUploadError("The uploaded file is empty.")
    if len(content) > storage.MAX_UPLOAD_BYTES:
        limit_mb = storage.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise InvalidUploadError(f"The uploaded file exceeds the {limit_mb}MB limit.")

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
    request-scoped session is gone by the time this executes."""
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document is None:
            logger.warning("Extraction requested for missing document %s", document_id)
            return

        document.extraction_status = ExtractionStatus.PROCESSING
        await db.commit()

        try:
            content = storage.read_document_file(document.storage_path)
            result = extract_document(content)
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

        document.page_count = result.page_count
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
        document.extraction_status = ExtractionStatus.COMPLETED
        await db.commit()


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
