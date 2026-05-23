from fastapi import APIRouter

from app.api.v1 import (
    auth,
    books,
    librarian,
    librarian_books,
    reading_progress,
    reading_sessions,
    students,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(books.router)
api_router.include_router(librarian_books.router)
api_router.include_router(reading_sessions.router)
api_router.include_router(reading_progress.router)
api_router.include_router(students.router)
api_router.include_router(librarian.router)
