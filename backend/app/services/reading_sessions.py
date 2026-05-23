from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.enums import ActivityAction, SessionStatus
from app.models.reading_session import ReadingSession
from app.services.activity import log_activity
from app.services.books import get_active_book
from app.utils.time import minutes_between, utc_now

STALE_SESSION_HOURS = 2


def _abandon_stale_sessions(db: Session, student_id: int) -> None:
    cutoff = utc_now() - timedelta(hours=STALE_SESSION_HOURS)
    stale = (
        db.query(ReadingSession)
        .filter(
            ReadingSession.student_id == student_id,
            ReadingSession.status == SessionStatus.ACTIVE.value,
            ReadingSession.started_at < cutoff,
        )
        .all()
    )
    for session in stale:
        session.status = SessionStatus.ABANDONED.value
        session.ended_at = utc_now()
        log_activity(
            db,
            ActivityAction.SESSION_ABANDONED,
            student_id=student_id,
            book_id=session.book_id,
            notes=f"Auto-abandoned stale session {session.id}",
        )


def get_active_session(
    db: Session, student_id: int, book_id: int
) -> ReadingSession | None:
    return (
        db.query(ReadingSession)
        .filter(
            ReadingSession.student_id == student_id,
            ReadingSession.book_id == book_id,
            ReadingSession.status == SessionStatus.ACTIVE.value,
        )
        .first()
    )


def start_session(db: Session, student_id: int, book_id: int) -> ReadingSession:
    get_active_book(db, book_id)
    _abandon_stale_sessions(db, student_id)

    existing = get_active_session(db, student_id, book_id)
    if existing:
        raise AppException("An active reading session already exists for this book", 409)

    session = ReadingSession(
        student_id=student_id,
        book_id=book_id,
        started_at=utc_now(),
        status=SessionStatus.ACTIVE.value,
    )
    db.add(session)
    db.flush()

    log_activity(
        db,
        ActivityAction.SESSION_STARTED,
        student_id=student_id,
        book_id=book_id,
        notes=f"Session {session.id} started",
    )
    db.commit()
    db.refresh(session)
    return session


def end_session(db: Session, student_id: int, session_id: int) -> ReadingSession:
    session = (
        db.query(ReadingSession)
        .filter(
            ReadingSession.id == session_id,
            ReadingSession.student_id == student_id,
        )
        .first()
    )
    if not session:
        raise AppException("Reading session not found", 404)

    if session.status != SessionStatus.ACTIVE.value:
        raise AppException("Session is not active", 400)

    now = utc_now()
    session.ended_at = now
    session.duration_minutes = minutes_between(session.started_at, now)
    session.status = SessionStatus.COMPLETED.value

    log_activity(
        db,
        ActivityAction.SESSION_COMPLETED,
        student_id=student_id,
        book_id=session.book_id,
        notes=f"Session {session.id} completed, duration {session.duration_minutes} min",
    )
    db.commit()
    db.refresh(session)
    return session
