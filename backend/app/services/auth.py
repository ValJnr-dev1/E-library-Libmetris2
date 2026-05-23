from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.librarian import Librarian
from app.models.student import Student
from app.schemas.auth import (
    LibrarianRegisterRequest,
    LoginRequest,
    StudentRegisterRequest,
    TokenResponse,
)


def register_student(db: Session, data: StudentRegisterRequest) -> Student:
    if db.query(Student).filter(Student.email == data.email).first():
        raise AppException("Email already registered", 409)
    if db.query(Student).filter(Student.matric_number == data.matric_number).first():
        raise AppException("Matric number already registered", 409)

    student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        matric_number=data.matric_number,
        email=data.email,
        password=hash_password(data.password),
        role=UserRole.STUDENT.value,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def register_librarian(db: Session, data: LibrarianRegisterRequest) -> Librarian:
    if db.query(Librarian).filter(Librarian.email == data.email).first():
        raise AppException("Email already registered", 409)
    if db.query(Librarian).filter(Librarian.school_id_number == data.school_id_number).first():
        raise AppException("School ID already registered", 409)

    librarian = Librarian(
        first_name=data.first_name,
        last_name=data.last_name,
        school_id_number=data.school_id_number,
        email=data.email,
        password=hash_password(data.password),
        role=UserRole.LIBRARIAN.value,
    )
    db.add(librarian)
    db.commit()
    db.refresh(librarian)
    return librarian


def login(db: Session, data: LoginRequest) -> TokenResponse:
    if data.role == UserRole.STUDENT:
        user = db.query(Student).filter(Student.email == data.email).first()
        account_type = "student"
    else:
        user = db.query(Librarian).filter(Librarian.email == data.email).first()
        account_type = "librarian"

    if not user or not verify_password(data.password, user.password):
        raise AppException("Invalid email or password", 401)

    if user.role != data.role.value:
        raise AppException("Invalid email or password", 401)

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        account_type=account_type,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        account_type=account_type,
    )
