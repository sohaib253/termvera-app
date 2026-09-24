import hashlib
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage"

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB — documented assumption for the MVP
ALLOWED_MIME_TYPES = {"application/pdf"}


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_document_file(
    *, organization_id: str, project_id: str, document_id: str, filename: str, content: bytes
) -> str:
    directory = STORAGE_ROOT / organization_id / project_id / document_id
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name  # strip any path components from the client-supplied name
    file_path = directory / safe_name
    file_path.write_bytes(content)
    return str(file_path.relative_to(STORAGE_ROOT))


def read_document_file(storage_path: str) -> bytes:
    full_path = STORAGE_ROOT / storage_path
    return full_path.read_bytes()


def resolve_document_path(storage_path: str) -> Path:
    return STORAGE_ROOT / storage_path
