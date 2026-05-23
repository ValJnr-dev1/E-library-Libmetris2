"""End-to-end API integration tests."""

from tests.conftest import MINIMAL_PDF, MULTI_PAGE_PDF


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_student_registration_and_duplicate(client):
    payload = {
        "first_name": "Alex",
        "last_name": "Kim",
        "matric_number": "MAT100",
        "email": "alex@school.edu",
        "password": "password123",
    }
    created = client.post("/api/v1/auth/student/register", json=payload)
    assert created.status_code == 201
    assert created.json()["success"] is True
    assert created.json()["data"]["email"] == "alex@school.edu"

    duplicate = client.post("/api/v1/auth/student/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["success"] is False


def test_librarian_registration(client):
    response = client.post(
        "/api/v1/auth/librarian/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "school_id_number": "LIB100",
            "email": "jane@school.edu",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["role"] == "LIBRARIAN"


def test_login_wrong_password(client, student_headers):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "val@school.edu", "password": "wrongpass", "role": "STUDENT"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_role_authorization(client, student_headers, librarian_headers):
    books = client.get("/api/v1/books", headers=student_headers)
    assert books.status_code == 200

    forbidden = client.get(
        "/api/v1/librarian/dashboard/overview",
        headers=student_headers,
    )
    assert forbidden.status_code == 403

    overview = client.get(
        "/api/v1/librarian/dashboard/overview",
        headers=librarian_headers,
    )
    assert overview.status_code == 200
    assert "active_students" in overview.json()["data"]


def test_book_upload_and_list(client, librarian_headers):
    upload = client.post(
        "/api/v1/librarian/books",
        headers=librarian_headers,
        data={
            "title": "Quiet Planet",
            "author": "M. Rivera",
            "description": "Sci-fi",
        },
        files={"file": ("book.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 201
    book_id = upload.json()["data"]["id"]

    listing = client.get("/api/v1/books")
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = client.get(f"/api/v1/books/{book_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["title"] == "Quiet Planet"


def test_reject_non_pdf_upload(client, librarian_headers):
    response = client.post(
        "/api/v1/librarian/books",
        headers=librarian_headers,
        data={
            "title": "Bad File",
            "author": "Nobody",
            "total_pages": "5",
        },
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400


def test_soft_delete_book(client, librarian_headers, book_id):
    deleted = client.delete(
        f"/api/v1/librarian/books/{book_id}",
        headers=librarian_headers,
    )
    assert deleted.status_code == 200

    hidden = client.get(f"/api/v1/books/{book_id}")
    assert hidden.status_code == 404


def test_reading_session_flow(client, student_headers, book_id):
    reader = client.get(
        f"/api/v1/books/{book_id}/reader",
        headers=student_headers,
    )
    assert reader.status_code == 200
    assert reader.json()["data"]["book"]["id"] == book_id

    started = client.post(
        "/api/v1/reading-sessions/start",
        headers=student_headers,
        json={"book_id": book_id},
    )
    assert started.status_code == 201
    session_id = started.json()["data"]["session_id"]

    duplicate = client.post(
        "/api/v1/reading-sessions/start",
        headers=student_headers,
        json={"book_id": book_id},
    )
    assert duplicate.status_code == 409

    progress = client.patch(
        f"/api/v1/reading-progress/{book_id}",
        headers=student_headers,
        json={"current_page": 1},
    )
    assert progress.status_code == 200
    assert progress.json()["data"]["completion_percentage"] == 33.33

    ended = client.post(
        "/api/v1/reading-sessions/end",
        headers=student_headers,
        json={"session_id": session_id},
    )
    assert ended.status_code == 200
    assert ended.json()["data"]["status"] == "COMPLETED"
    assert ended.json()["data"]["duration_minutes"] >= 0


def test_student_analytics(client, student_headers, book_id):
    client.post(
        "/api/v1/reading-sessions/start",
        headers=student_headers,
        json={"book_id": book_id},
    )
    client.patch(
        f"/api/v1/reading-progress/{book_id}",
        headers=student_headers,
        json={"current_page": 1},
    )

    analytics = client.get("/api/v1/students/analytics", headers=student_headers)
    assert analytics.status_code == 200
    data = analytics.json()["data"]
    assert "total_books_read" in data
    assert "current_streak_days" in data
    assert len(data["book_progress"]) == 1


def test_librarian_dashboard_and_logs(client, librarian_headers, student_headers, book_id):
    client.get(f"/api/v1/books/{book_id}/reader", headers=student_headers)

    overview = client.get(
        "/api/v1/librarian/dashboard/overview",
        headers=librarian_headers,
    )
    assert overview.status_code == 200

    students = client.get(
        "/api/v1/librarian/students?search=val",
        headers=librarian_headers,
    )
    assert students.status_code == 200
    assert students.json()["data"]["total"] >= 1

    popular = client.get(
        "/api/v1/librarian/books/popular",
        headers=librarian_headers,
    )
    assert popular.status_code == 200

    logs = client.get(
        "/api/v1/librarian/activity-logs?page=1&limit=10",
        headers=librarian_headers,
    )
    assert logs.status_code == 200
    assert logs.json()["data"]["total"] >= 1

    export = client.get(
        "/api/v1/librarian/activity-logs/export",
        headers=librarian_headers,
    )
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "BOOK_OPENED" in export.text or "action" in export.text


def test_delete_student(client, librarian_headers, student_headers):
    students = client.get("/api/v1/librarian/students/all", headers=librarian_headers)
    assert students.status_code == 200
    assert len(students.json()["data"]) >= 1

    student_id = students.json()["data"][0]["id"]
    deleted = client.delete(
        f"/api/v1/librarian/students/{student_id}",
        headers=librarian_headers,
    )
    assert deleted.status_code == 200

    again = client.get("/api/v1/librarian/students/all", headers=librarian_headers)
    ids = [s["id"] for s in again.json()["data"]]
    assert student_id not in ids


def test_auto_detect_pdf_pages(client, librarian_headers):
    upload = client.post(
        "/api/v1/librarian/books",
        headers=librarian_headers,
        data={"title": "Auto Pages", "author": "System"},
        files={"file": ("book.pdf", MULTI_PAGE_PDF, "application/pdf")},
    )
    assert upload.status_code == 201
    assert upload.json()["data"]["total_pages"] == 3


def test_serve_book_file(client, student_headers, book_id):
    response = client.get(
        f"/api/v1/books/{book_id}/file",
        headers=student_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
