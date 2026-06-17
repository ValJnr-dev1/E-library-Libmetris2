from typing import Annotated

from fastapi import APIRouter, Depends
import io
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_student
from app.core.responses import success_response
from app.database import get_db
from app.schemas.book import BookResponse, ReaderStateResponse, ReadingProgressResponse
from app.services import books as book_service
from app.services import reading_progress as progress_service
from app.services import reading_sessions as session_service
from app.services.reading_progress import log_book_opened

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("")
def list_books(db: Annotated[Session, Depends(get_db)]):
    books = book_service.list_books(db)
    return success_response(
        data=[BookResponse.model_validate(b).model_dump(mode="json") for b in books]
    )


@router.get("/{book_id}")
def get_book(book_id: int, db: Annotated[Session, Depends(get_db)]):
    book = book_service.get_active_book(db, book_id)
    return success_response(data=BookResponse.model_validate(book).model_dump(mode="json"))


@router.get("/{book_id}/reader")
def get_reader_state(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    book = book_service.get_active_book(db, book_id)
    log_book_opened(db, current_user.id, book_id)

    progress = progress_service.get_progress(db, current_user.id, book_id)
    active = session_service.get_active_session(db, current_user.id, book_id)

    data = ReaderStateResponse(
        book=BookResponse.model_validate(book),
        progress=ReadingProgressResponse.model_validate(progress) if progress else None,
        active_session={
            "session_id": active.id,
            "started_at": active.started_at,
            "status": active.status,
        }
        if active
        else None,
    )
    return success_response(data=data.model_dump(mode="json"))


@router.get("/{book_id}/progress")
def get_reading_progress(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    book_service.get_active_book(db, book_id)
    progress = progress_service.get_progress(db, current_user.id, book_id)
    if not progress:
        return success_response(
            data={
                "current_page": 1,
                "completion_percentage": 0.0,
                "last_read_at": None,
            },
            message="No reading progress yet",
        )
    return success_response(
        data=ReadingProgressResponse.model_validate(progress).model_dump(mode="json")
    )


@router.get("/{book_id}/download")
@router.get("/{book_id}/file")
def serve_book_file(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    book = book_service.get_active_book(db, book_id)
    # Serve file bytes stored in the database (BYTEA / LargeBinary).
    if not book.file_data:
        raise Exception("Book file not available")

    stream = io.BytesIO(book.file_data)
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{book.original_filename}"'},
    )
