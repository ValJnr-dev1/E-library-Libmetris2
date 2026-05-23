import csv
import io
from datetime import timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.enums import SessionStatus
from app.models.reading_session import ReadingSession
from app.models.student import Student
from app.utils.pagination import paginate
from app.utils.time import utc_now

from app.analytics.student_analytics import get_student_analytics


def get_dashboard_overview(db: Session) -> dict:
    thirty_days_ago = utc_now() - timedelta(days=30)

    active_students = (
        db.query(func.count(func.distinct(ReadingSession.student_id)))
        .filter(ReadingSession.started_at >= thirty_days_ago)
        .scalar()
        or 0
    )

    total_sessions = db.query(func.count(ReadingSession.id)).scalar() or 0

    avg_duration = (
        db.query(func.avg(ReadingSession.duration_minutes))
        .filter(
            ReadingSession.status == SessionStatus.COMPLETED.value,
            ReadingSession.duration_minutes.isnot(None),
        )
        .scalar()
    )

    low_activity_count = len(_get_low_activity_student_ids(db))

    return {
        "active_students": active_students,
        "total_sessions": total_sessions,
        "average_reading_minutes": round(float(avg_duration or 0), 2),
        "low_activity_count": low_activity_count,
    }


def _get_low_activity_student_ids(db: Session) -> list[int]:
    seven_days_ago = utc_now() - timedelta(days=7)

    recent_active = (
        db.query(ReadingSession.student_id)
        .filter(
            ReadingSession.status == SessionStatus.COMPLETED.value,
            ReadingSession.ended_at >= seven_days_ago,
        )
        .distinct()
        .subquery()
    )

    return [
        row[0]
        for row in db.query(Student.id)
        .filter(~Student.id.in_(db.query(recent_active.c.student_id)))
        .all()
    ]


def list_students_analytics(
    db: Session,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    offset, limit = paginate(page, limit)
    query = db.query(Student)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Student.first_name.ilike(term),
                Student.last_name.ilike(term),
                Student.email.ilike(term),
                Student.matric_number.ilike(term),
            )
        )

    total = query.count()
    students = query.order_by(Student.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for student in students:
        analytics = get_student_analytics(db, student.id)
        items.append(
            {
                "student_id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "matric_number": student.matric_number,
                "email": student.email,
                "total_books_read": analytics["total_books_read"],
                "total_reading_time_minutes": analytics["total_reading_time_minutes"],
                "current_streak_days": analytics["current_streak_days"],
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


def get_popular_books(db: Session, limit: int = 10) -> list[dict]:
    rows = (
        db.query(
            Book.id,
            Book.title,
            Book.author,
            func.count(ReadingSession.id).label("session_count"),
        )
        .join(ReadingSession, ReadingSession.book_id == Book.id)
        .filter(Book.is_deleted.is_(False))
        .group_by(Book.id)
        .order_by(func.count(ReadingSession.id).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "book_id": r.id,
            "title": r.title,
            "author": r.author,
            "session_count": r.session_count,
        }
        for r in rows
    ]


def get_low_activity_students(db: Session) -> list[dict]:
    ids = _get_low_activity_student_ids(db)
    if not ids:
        return []

    students = db.query(Student).filter(Student.id.in_(ids)).all()

    result = []
    for student in students:
        last_session = (
            db.query(ReadingSession)
            .filter(
                ReadingSession.student_id == student.id,
                ReadingSession.status == SessionStatus.COMPLETED.value,
            )
            .order_by(ReadingSession.ended_at.desc())
            .first()
        )
        result.append(
            {
                "student_id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "matric_number": student.matric_number,
                "email": student.email,
                "last_completed_session_at": (
                    last_session.ended_at.isoformat() if last_session and last_session.ended_at else None
                ),
                "days_inactive": 7,
            }
        )
    return result


def list_activity_logs(
    db: Session,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    offset, limit = paginate(page, limit)
    query = db.query(ActivityLog)

    if search:
        term = f"%{search}%"
        query = (
            query.outerjoin(Student, ActivityLog.student_id == Student.id)
            .outerjoin(Book, ActivityLog.book_id == Book.id)
            .filter(
                or_(
                    ActivityLog.action.ilike(term),
                    ActivityLog.notes.ilike(term),
                    Student.first_name.ilike(term),
                    Student.last_name.ilike(term),
                    Student.email.ilike(term),
                    Book.title.ilike(term),
                )
            )
        )

    query = query.order_by(ActivityLog.created_at.desc())

    total = query.count()
    logs = query.offset(offset).limit(limit).all()

    items = []
    for log in logs:
        student = db.query(Student).filter(Student.id == log.student_id).first() if log.student_id else None
        book = db.query(Book).filter(Book.id == log.book_id).first() if log.book_id else None
        items.append(
            {
                "id": log.id,
                "student_id": log.student_id,
                "student_name": f"{student.first_name} {student.last_name}" if student else None,
                "book_id": log.book_id,
                "book_title": book.title if book else None,
                "action": log.action,
                "notes": log.notes,
                "created_at": log.created_at.isoformat(),
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


def export_activity_logs_csv(db: Session, search: str | None = None) -> str:
    result = list_activity_logs(db, search=search, page=1, limit=10000)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "student_id",
            "student_name",
            "book_id",
            "book_title",
            "action",
            "notes",
            "created_at",
        ],
    )
    writer.writeheader()
    for item in result["items"]:
        writer.writerow(item)
    return output.getvalue()
