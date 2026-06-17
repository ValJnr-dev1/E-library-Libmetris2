import io
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import AppException

settings = get_settings()

PDF_MAGIC = b"%PDF"
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


async def validate_and_save_pdf(file: UploadFile) -> tuple[bytes, str]:
    """Validate an uploaded PDF and return its bytes and original filename.

    Returns bytes so callers can persist them in the database.
    """
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

    return content, original_filename


def count_pdf_pages(file_source: str | bytes) -> int:
    """Count pages from bytes or from a file path string.

    When given bytes, it reads from memory; when given a path string, it will
    attempt to read the path via pypdf (caller responsibility).
    """
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        if isinstance(file_source, (bytes, bytearray)):
            reader = PdfReader(io.BytesIO(file_source))
        else:
            reader = PdfReader(str(file_source))
        pages = len(reader.pages)
    except PdfReadError as exc:
        raise AppException(
            "Could not read PDF page count. Provide total pages manually.", 400
        ) from exc

    if pages < 1:
        raise AppException("PDF has no readable pages", 400)
    return pages
