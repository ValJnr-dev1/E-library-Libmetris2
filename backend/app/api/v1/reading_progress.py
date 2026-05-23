from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_student
from app.core.responses import success_response
from app.database import get_db
from app.schemas.book import ProgressUpdateRequest, ReadingProgressResponse
from app.services import reading_progress as progress_service

router = APIRouter(prefix="/reading-progress", tags=["Reading Progress"])


@router.patch("/{book_id}")
def update_progress(
    book_id: int,
    data: ProgressUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_student)],
):
    progress = progress_service.update_progress(
        db, current_user.id, book_id, data.current_page
    )
    return success_response(
        data=ReadingProgressResponse.model_validate(progress).model_dump(mode="json"),
        message="Reading progress updated",
    )
