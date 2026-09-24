from pydantic import BaseModel


class SampleDocumentRead(BaseModel):
    key: str
    filename: str
    title: str
    description: str
    module: str
    document_type: str
    size_bytes: int
