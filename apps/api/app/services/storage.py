import hashlib
from pathlib import Path

from app.core.config import get_settings

_data_dir = get_settings().data_dir
STORAGE_ROOT = (
    Path(_data_dir) / "storage"
    if _data_dir
    else Path(__file__).resolve().parent.parent.parent / "storage"
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB — documented assumption for the MVP

# A PDF rendering of a non-PDF upload (e.g. a Word file converted by
# LibreOffice), stored beside the original so page links can open it.
RENDITION_FILENAME = "_rendition.pdf"


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_document_file(
    *, organization_id: str, project_id: str, document_id: str, filename: str, content: bytes
) -> str:
    directory = STORAGE_ROOT / organization_id / project_id / document_id
    directory.mkdir(parents=True, exist_ok=True)
    # Stored under a fixed short name, not the client's: three ID folders
    # plus a long original name ("Commercial clarification - Discount rate
    # - ENI Frac.pdf") overflow Windows' 260-character path limit under a
    # user profile. The original name is kept on the Document row. The
    # extension is kept so the file still opens by type if browsed to.
    suffix = Path(filename).suffix.lower()
    safe_suffix = suffix if suffix[1:].isalnum() and len(suffix) <= 6 else ""
    file_path = directory / f"source{safe_suffix}"
    file_path.write_bytes(content)
    return str(file_path.relative_to(STORAGE_ROOT))


def read_document_file(storage_path: str) -> bytes:
    full_path = STORAGE_ROOT / storage_path
    return full_path.read_bytes()


def resolve_document_path(storage_path: str) -> Path:
    return STORAGE_ROOT / storage_path


def save_rendition(storage_path: str, content: bytes) -> None:
    (STORAGE_ROOT / storage_path).parent.joinpath(RENDITION_FILENAME).write_bytes(content)


def find_rendition(storage_path: str) -> Path | None:
    path = (STORAGE_ROOT / storage_path).parent / RENDITION_FILENAME
    return path if path.is_file() else None
