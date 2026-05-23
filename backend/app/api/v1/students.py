from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.student_analytics import get_student_analytics
from app.core.deps import CurrentUser, require_student
from app.core.responses import success_response
from app.database import get_db

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/analytics")
def personal_analytics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    data = get_student_analytics(db, current_user.id)
    return success_response(data=data)
