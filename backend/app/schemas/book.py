from datetime import datetime

from pydantic import BaseModel, Field


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    description: str | None
    original_filename: str
    total_pages: int
    uploaded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReadingProgressResponse(BaseModel):
    current_page: int
    completion_percentage: float
    last_read_at: datetime

    model_config = {"from_attributes": True}


class ActiveSessionResponse(BaseModel):
    session_id: int
    started_at: datetime
    status: str

    model_config = {"from_attributes": True}


class ReaderStateResponse(BaseModel):
    book: BookResponse
    progress: ReadingProgressResponse | None
    active_session: ActiveSessionResponse | None


class ProgressUpdateRequest(BaseModel):
    current_page: int = Field(..., ge=1)
