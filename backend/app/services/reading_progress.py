from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.enums import ActivityAction
from app.models.reading_progress import ReadingProgress
from app.services.activity import log_activity
from app.services.books import get_active_book
from app.utils.time import utc_now


def compute_completion(current_page: int, total_pages: int) -> float:
    if total_pages <= 0:
        return 0.0
    percentage = (current_page / total_pages) * 100
    return round(min(100.0, percentage), 2)


def get_progress(
    db: Session, student_id: int, book_id: int
) -> ReadingProgress | None:
    return (
        db.query(ReadingProgress)
        .filter(
            ReadingProgress.student_id == student_id,
            ReadingProgress.book_id == book_id,
        )
        .first()
    )


def update_progress(
    db: Session, student_id: int, book_id: int, current_page: int
) -> ReadingProgress:
    book = get_active_book(db, book_id)

    if current_page > book.total_pages:
        raise AppException(
            f"Current page cannot exceed total pages ({book.total_pages})", 400
        )

    progress = get_progress(db, student_id, book_id)
    completion = compute_completion(current_page, book.total_pages)
    now = utc_now()

    if progress:
        progress.current_page = current_page
        progress.completion_percentage = completion
        progress.last_read_at = now
    else:
        progress = ReadingProgress(
            student_id=student_id,
            book_id=book_id,
            current_page=current_page,
            completion_percentage=completion,
            last_read_at=now,
        )
        db.add(progress)

    log_activity(
        db,
        ActivityAction.PAGE_CHANGED,
        student_id=student_id,
        book_id=book_id,
        notes=f"Page {current_page}, {completion}% complete",
    )
    db.commit()
    db.refresh(progress)
    return progress


def log_book_opened(db: Session, student_id: int, book_id: int) -> None:
    get_active_book(db, book_id)
    log_activity(
        db,
        ActivityAction.BOOK_OPENED,
        student_id=student_id,
        book_id=book_id,
    )
    db.commit()
