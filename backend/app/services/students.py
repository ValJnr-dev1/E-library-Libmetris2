from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.activity_log import ActivityLog
from app.models.reading_progress import ReadingProgress
from app.models.reading_session import ReadingSession
from app.models.student import Student


def list_students(db: Session, search: str | None = None) -> list[Student]:
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
    return query.order_by(Student.created_at.desc()).all()


def delete_student(db: Session, student_id: int) -> None:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise AppException("Student not found", 404)

    db.query(ActivityLog).filter(ActivityLog.student_id == student_id).delete()
    db.query(ReadingSession).filter(ReadingSession.student_id == student_id).delete()
    db.query(ReadingProgress).filter(ReadingProgress.student_id == student_id).delete()
    db.delete(student)
    db.commit()
