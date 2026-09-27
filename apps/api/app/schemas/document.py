from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentType, ExtractionStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    document_type: DocumentType
    original_filename: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    extraction_status: ExtractionStatus
    extraction_error: str | None
    extraction_pages_done: int | None = None
    created_at: datetime


class DocumentPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    text: str
    char_count: int
    extraction_method: str
    low_text_warning: bool
