from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.analytics import librarian_analytics
from app.core.deps import CurrentUser, require_librarian
from app.core.responses import success_response
from app.database import get_db
from app.services import students as student_service

router = APIRouter(prefix="/librarian", tags=["Librarian"])


@router.get("/dashboard/overview")
def dashboard_overview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
):
    data = librarian_analytics.get_dashboard_overview(db)
    return success_response(data=data)


@router.get("/students/all")
def list_all_students(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
    search: str | None = Query(None),
):
    students = student_service.list_students(db, search=search)
    data = [
        {
            "id": s.id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "matric_number": s.matric_number,
            "email": s.email,
            "created_at": s.created_at.isoformat(),
        }
        for s in students
    ]
    return success_response(data=data)


@router.delete("/students/{student_id}")
def delete_student(
    student_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
):
    student_service.delete_student(db, student_id)
    return success_response(message="Student deleted successfully")


@router.get("/students")
def students_analytics(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    data = librarian_analytics.list_students_analytics(db, search=search, page=page, limit=limit)
    return success_response(data=data)


@router.get("/books/popular")
def popular_books(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
):
    data = librarian_analytics.get_popular_books(db)
    return success_response(data=data)


@router.get("/students/attention")
def low_activity_students(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
):
    data = librarian_analytics.get_low_activity_students(db)
    return success_response(data=data)


@router.get("/activity-logs")
def activity_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    data = librarian_analytics.list_activity_logs(db, search=search, page=page, limit=limit)
    return success_response(data=data)


@router.get("/activity-logs/export")
def export_activity_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_librarian)],
    search: str | None = Query(None),
):
    csv_content = librarian_analytics.export_activity_logs_csv(db, search=search)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_logs.csv"},
    )
