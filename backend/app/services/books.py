from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.enums import ActivityAction
from app.services.activity import log_activity
from app.services.files import count_pdf_pages, validate_and_save_pdf
from app.utils.time import utc_now


def get_active_book(db: Session, book_id: int) -> Book:
    book = (
        db.query(Book)
        .filter(Book.id == book_id, Book.is_deleted.is_(False))
        .first()
    )
    if not book:
        raise AppException("Book not found", 404)
    return book


def list_books(db: Session) -> list[Book]:
    return (
        db.query(Book)
        .filter(Book.is_deleted.is_(False))
        .order_by(Book.created_at.desc())
        .all()
    )


async def upload_book(
    db: Session,
    librarian_id: int,
    title: str,
    author: str,
    description: str | None,
    file: UploadFile,
    total_pages: int | None = None,
) -> Book:
    file_bytes, original_filename = await validate_and_save_pdf(file)

    if not total_pages or total_pages < 1:
        total_pages = count_pdf_pages(file_bytes)

    book = Book(
        title=title,
        author=author,
        description=description,
        file_path=None,
        file_data=file_bytes,
        original_filename=original_filename,
        total_pages=total_pages,
        uploaded_by=librarian_id,
    )
    db.add(book)
    db.flush()

    log_activity(
        db,
        ActivityAction.BOOK_UPLOADED,
        book_id=book.id,
        notes=f"Uploaded by librarian {librarian_id}",
    )
    db.commit()
    db.refresh(book)
    return book


def soft_delete_book(db: Session, book_id: int, librarian_id: int) -> Book:
    book = db.query(Book).filter(Book.id == book_id, Book.is_deleted.is_(False)).first()
    if not book:
        raise AppException("Book not found", 404)

    book.is_deleted = True
    book.deleted_at = utc_now()

    log_activity(
        db,
        ActivityAction.BOOK_DELETED,
        book_id=book.id,
        notes=f"Soft-deleted by librarian {librarian_id}",
    )
    db.commit()
    db.refresh(book)
    return book
