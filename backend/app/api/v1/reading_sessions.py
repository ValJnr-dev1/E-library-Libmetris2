from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_student
from app.core.responses import success_response
from app.database import get_db
from app.schemas.reading import EndSessionRequest, StartSessionRequest
from app.services import reading_sessions as session_service

router = APIRouter(prefix="/reading-sessions", tags=["Reading Sessions"])


@router.post("/start")
def start_session(
    data: StartSessionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    session = session_service.start_session(db, current_user.id, data.book_id)
    return success_response(
        data={"session_id": session.id},
        message="Reading session started",
        status_code=201,
    )


@router.post("/end")
def end_session(
    data: EndSessionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    session = session_service.end_session(db, current_user.id, data.session_id)
    return success_response(
        data={
            "session_id": session.id,
            "duration_minutes": session.duration_minutes,
            "status": session.status,
        },
        message="Reading session completed",
    )
