from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip
from app.core.exceptions import AppException
from app.core.rate_limit import check_login_rate_limit
from app.core.responses import error_response, success_response
from app.database import get_db
from app.schemas.auth import (
    LibrarianRegisterRequest,
    LoginRequest,
    StudentRegisterRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/student/register")
def register_student(
    data: StudentRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    student = auth_service.register_student(db, data)
    return success_response(
        data={
            "id": student.id,
            "email": student.email,
            "role": student.role,
        },
        message="Student registered successfully",
        status_code=201,
    )


@router.post("/librarian/register")
def register_librarian(
    data: LibrarianRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    librarian = auth_service.register_librarian(db, data)
    return success_response(
        data={
            "id": librarian.id,
            "email": librarian.email,
            "role": librarian.role,
        },
        message="Librarian registered successfully",
        status_code=201,
    )


@router.post("/login")
def login(
    data: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    client_ip = get_client_ip(request)
    if not check_login_rate_limit(client_ip):
        return error_response("Too many login attempts. Please try again later.", 429)

    token_data = auth_service.login(db, data)
    return success_response(
        data=token_data.model_dump(),
        message="Login successful",
    )
