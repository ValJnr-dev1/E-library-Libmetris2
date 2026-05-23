from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    book_id: int = Field(..., gt=0)


class EndSessionRequest(BaseModel):
    session_id: int = Field(..., gt=0)


class SessionStartResponse(BaseModel):
    session_id: int
