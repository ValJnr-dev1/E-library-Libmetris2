import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Environment must be set before application imports.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-integration-tests-only")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")
os.environ.setdefault("UPLOAD_DIRECTORY", "/tmp/libmetrics-test-uploads")
os.environ.setdefault("MAX_UPLOAD_SIZE_MB", "25")

from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _build_test_pdf(page_count: int = 1) -> bytes:
    import io

    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


MINIMAL_PDF = _build_test_pdf(1)
MULTI_PAGE_PDF = _build_test_pdf(3)


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    from app.core.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(autouse=True)
def _reset_settings(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setenv("UPLOAD_DIRECTORY", str(upload_dir))
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-integration-tests-only")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def librarian_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v1/auth/librarian/register",
        json={
            "first_name": "Lib",
            "last_name": "Rarian",
            "school_id_number": "LIB001",
            "email": "lib@school.edu",
            "password": "password123",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "lib@school.edu", "password": "password123", "role": "LIBRARIAN"},
    )
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v1/auth/student/register",
        json={
            "first_name": "Val",
            "last_name": "Student",
            "matric_number": "MAT001",
            "email": "val@school.edu",
            "password": "password123",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "val@school.edu", "password": "password123", "role": "STUDENT"},
    )
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def book_id(client: TestClient, librarian_headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/librarian/books",
        headers=librarian_headers,
        data={
            "title": "Test Book",
            "author": "Test Author",
            "description": "A test book",
        },
        files={"file": ("test.pdf", MULTI_PAGE_PDF, "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]
