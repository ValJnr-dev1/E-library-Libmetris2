from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.utils.time import minutes_between

from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.enums import ActivityAction, SessionStatus
from app.models.reading_progress import ReadingProgress
from app.models.reading_session import ReadingSession


def _completed_session_dates(db: Session, student_id: int) -> list[date]:
    rows = (
        db.query(ReadingSession.ended_at)
        .filter(
            ReadingSession.student_id == student_id,
            ReadingSession.status == SessionStatus.COMPLETED.value,
            ReadingSession.ended_at.isnot(None),
        )
        .all()
    )
    return sorted({r[0].date() for r in rows if r[0]}, reverse=True)


def calculate_streak(db: Session, student_id: int) -> int:
    dates = _completed_session_dates(db, student_id)
    if not dates:
        return 0

    today = date.today()
    streak = 0
    expected = today

    if dates[0] < today - timedelta(days=1):
        return 0

    if dates[0] == today - timedelta(days=1):
        expected = today - timedelta(days=1)
    elif dates[0] != today:
        return 0

    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    return streak


def _compute_minutes_per_page(db: Session, student_id: int) -> float:
    logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.student_id == student_id,
            ActivityLog.action == ActivityAction.PAGE_CHANGED.value,
        )
        .order_by(ActivityLog.created_at.asc())
        .all()
    )
    if len(logs) < 2:
        return 0.0

    total_minutes = 0.0
    transitions = 0
    for prev, curr in zip(logs, logs[1:], strict=False):
        if prev.book_id != curr.book_id:
            continue
        delta = minutes_between(prev.created_at, curr.created_at)
        if 0 < delta <= 120:
            total_minutes += delta
            transitions += 1

    if transitions == 0:
        return 0.0
    return round(total_minutes / transitions, 2)


def get_student_analytics(db: Session, student_id: int) -> dict:
    books_read = (
        db.query(func.count(ReadingProgress.id))
        .filter(
            ReadingProgress.student_id == student_id,
            ReadingProgress.completion_percentage >= 100.0,
        )
        .scalar()
        or 0
    )

    total_minutes = (
        db.query(func.coalesce(func.sum(ReadingSession.duration_minutes), 0))
        .filter(
            ReadingSession.student_id == student_id,
            ReadingSession.status == SessionStatus.COMPLETED.value,
        )
        .scalar()
    )

    streak = calculate_streak(db, student_id)

    last_opened = (
        db.query(ActivityLog, Book)
        .join(Book, ActivityLog.book_id == Book.id)
        .filter(
            ActivityLog.student_id == student_id,
            ActivityLog.action == ActivityAction.BOOK_OPENED.value,
            Book.is_deleted.is_(False),
        )
        .order_by(ActivityLog.created_at.desc())
        .first()
    )

    last_opened_book = None
    if last_opened:
        log, book = last_opened
        last_opened_book = {
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "opened_at": log.created_at.isoformat(),
        }

    progress_rows = (
        db.query(ReadingProgress, Book)
        .join(Book, ReadingProgress.book_id == Book.id)
        .filter(
            ReadingProgress.student_id == student_id,
            Book.is_deleted.is_(False),
        )
        .all()
    )

    book_progress = []
    books_in_progress = []
    for prog, book in progress_rows:
        entry = {
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "current_page": prog.current_page,
            "total_pages": book.total_pages,
            "completion_percentage": prog.completion_percentage,
            "last_read_at": prog.last_read_at.isoformat(),
        }
        book_progress.append(entry)
        if prog.completion_percentage < 100.0:
            books_in_progress.append(entry)

    books_in_progress.sort(key=lambda b: b["last_read_at"], reverse=True)
    minutes_per_page = _compute_minutes_per_page(db, student_id)

    return {
        "total_books_read": books_read,
        "total_reading_time_minutes": int(total_minutes),
        "current_streak_days": streak,
        "minutes_per_page": minutes_per_page,
        "last_opened_book": last_opened_book,
        "book_progress": book_progress,
        "books_in_progress": books_in_progress,
    }
