from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_librarian
from app.core.responses import success_response
from app.database import get_db
from app.schemas.book import BookResponse
from app.services import books as book_service

router = APIRouter(prefix="/librarian/books", tags=["Librarian Books"])


@router.post("")
async def upload_book(
    title: Annotated[str, Form()],
    author: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_librarian)],
    file: UploadFile = File(...),
    description: Annotated[str | None, Form()] = None,
    total_pages: Annotated[int | None, Form()] = None,
):
    book = await book_service.upload_book(
        db=db,
        librarian_id=current_user.id,
        title=title,
        author=author,
        description=description,
        file=file,
        total_pages=total_pages,
    )
    return success_response(
        data=BookResponse.model_validate(book).model_dump(mode="json"),
        message="Book uploaded successfully",
        status_code=201,
    )


@router.delete("/{book_id}")
def delete_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_librarian)],
):
    book = book_service.soft_delete_book(db, book_id, current_user.id)
    return success_response(
        data={"id": book.id, "is_deleted": book.is_deleted},
        message="Book soft-deleted successfully",
    )
