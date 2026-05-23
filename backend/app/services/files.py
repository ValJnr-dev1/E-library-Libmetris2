import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import AppException

settings = get_settings()

PDF_MAGIC = b"%PDF"
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


def ensure_upload_directory() -> Path:
    path = Path(settings.upload_directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def validate_and_save_pdf(file: UploadFile) -> tuple[str, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise AppException("Only PDF files are allowed", 400)

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise AppException(
            f"File exceeds maximum size of {settings.max_upload_size_mb}MB", 413
        )

    if not content.startswith(PDF_MAGIC):
        raise AppException("Invalid PDF file", 400)

    original_filename = file.filename or "document.pdf"
    if not original_filename.lower().endswith(".pdf"):
        raise AppException("Only PDF files are allowed", 400)

    internal_name = f"{uuid.uuid4().hex}.pdf"
    upload_dir = ensure_upload_directory()
    file_path = upload_dir / internal_name

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path), original_filename


def count_pdf_pages(file_path: str | Path) -> int:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(file_path))
        pages = len(reader.pages)
    except PdfReadError as exc:
        raise AppException(
            "Could not read PDF page count. Provide total pages manually.", 400
        ) from exc

    if pages < 1:
        raise AppException("PDF has no readable pages", 400)
    return pages


def get_book_file_path(stored_path: str) -> Path:
    path = Path(stored_path)
    if not path.is_file():
        raise AppException("Book file not found", 404)
    return path
