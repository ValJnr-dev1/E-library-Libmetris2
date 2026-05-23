from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import validate_token
from app.database import get_db
from app.models.enums import UserRole
from app.models.librarian import Librarian
from app.models.student import Student

security_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    email: str
    role: str
    account_type: str  # "student" or "librarian"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    if not credentials:
        raise AppException("Unauthorized", 401)

    try:
        payload = validate_token(credentials.credentials)
    except ValueError:
        raise AppException("Invalid or expired token", 401) from None

    user_id = int(payload["sub"])
    account_type = payload.get("account_type", "student")

    if account_type == "student":
        user = db.query(Student).filter(Student.id == user_id).first()
    else:
        user = db.query(Librarian).filter(Librarian.id == user_id).first()

    if not user:
        raise AppException("Unauthorized", 401)

    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        account_type=account_type,
    )


def require_student(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != UserRole.STUDENT.value or user.account_type != "student":
        raise AppException("Forbidden", 403)
    return user


def require_librarian(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != UserRole.LIBRARIAN.value or user.account_type != "librarian":
        raise AppException("Forbidden", 403)
    return user


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
