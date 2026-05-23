from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.enums import ActivityAction


def log_activity(
    db: Session,
    action: ActivityAction,
    *,
    student_id: int | None = None,
    book_id: int | None = None,
    notes: str | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        student_id=student_id,
        book_id=book_id,
        action=action.value,
        notes=notes,
    )
    db.add(entry)
    return entry
