# LibMetrics — E-Library & Reading Intelligence

This document describes the LibMetrics project (backend, frontend, database, and deployment). It is tailored to the code in this repository and intended for study and presentation.

---

## 1. Project Overview

- **Project name:** LibMetrics (E-Library & Reading Intelligence)
- **Purpose:** Provide a simple e-library allowing librarians to upload PDF books and students to read, track progress, and view analytics.
- **What it does:** Users can register/login (students & librarians), librarians upload books (PDFs stored in DB), students open books in an e-reader, track reading sessions and progress, and librarians view dashboards & activity logs.
- **Target users:** Students and Librarians (admin-like functions provided to librarians).
- **Core features:**
  - User registration & authentication (students, librarians)
  - Book upload (PDF) and storage as binary (`file_data` / BYTEA)
  - Serving PDF files for viewing/downloading
  - Reading sessions tracking and progress updates
  - Student and librarian analytics and activity logs

---

## 2. System Architecture

High-level (text) architecture:

- Client (static frontend HTML/Tailwind/JS) <-> Backend API (FastAPI) <-> Database (PostgreSQL)
- The backend runs under Gunicorn + Uvicorn worker. Migrations are applied on startup via Alembic.

Tech stack (as used in this repo):

- **Backend:** FastAPI, Python, SQLAlchemy ORM, Alembic migrations. See `backend/app/main.py` and router at `backend/app/api/v1/router.py`.
- **Frontend:** Static HTML files with Tailwind CSS and vanilla JS (no React). See `frontend/README.md` and entry script `frontend/src/app.js`.
- **Database:** PostgreSQL (configured via `DATABASE_URL` / `database_url` setting). Connection code in `backend/app/database.py`.
- **Deployment:** Render (web service) recommended; Dockerfile and `entrypoint.sh` present to run migrations then start the app. See `backend/Dockerfile` and `backend/entrypoint.sh`.
- **Other tools:** Gunicorn with UvicornWorker, pypdf for page counting, bcrypt & jose for JWTs.

Why these choices (short):

- FastAPI: Modern, fast, async-ready, automatic OpenAPI docs, compact code for APIs.
- SQLAlchemy + Alembic: Mature ORM and migrations for relational DB.
- Static frontend: Simple, easy to host on Render or static hosts. Tailwind for rapid UI.
- Postgres: Production-ready RDBMS for relational data and BYTEA storage.

System flow (example upload -> read):

1. Librarian submits upload form (multipart/form-data) to `/api/v1/librarian/books`.
2. Backend validates PDF bytes (`app/services/files.py`), counts pages via `pypdf`, writes bytes into `books.file_data` and metadata into `books` table (`app/models/book.py`).
3. Student requests `/api/v1/books` to list books; sees metadata (via `app/schemas/book.py`).
4. Student opens reader and fetches `/api/v1/books/{id}/file` (or `/download`), streaming PDF bytes from DB into response.

---

## 3. Database Design

Entity tables (high-level ER):

- **students** (1) —< **reading_sessions** >— (many) **books**
- **librarians** (1) —< **books**
- **reading_progress** links students to books (one per student/book)
- **activity_logs** reference students and books for events

Tables and columns (current models):

- `students` (see `backend/app/models/student.py`)
  - id: Integer PK
  - first_name: String(100)
  - last_name: String(100)
  - matric_number: String(50) UNIQUE
  - email: String(255) UNIQUE
  - password: String(255) (hashed)
  - role: String(20)
  - created_at: DateTime

- `librarians` (see `backend/app/models/librarian.py`)
  - id: Integer PK
  - first_name, last_name, school_id_number (unique), email (unique), password, role, created_at
  - relationship: `books` (uploaded books)

- `books` (see `backend/app/models/book.py`)
  - id: Integer PK
  - title: String(255)
  - author: String(255)
  - description: Text nullable
  - file_data: LargeBinary / BYTEA nullable
  - original_filename: String(255)
  - total_pages: Integer
  - uploaded_by: FK -> librarians.id
  - is_deleted: Boolean
  - deleted_at: DateTime nullable
  - created_at: DateTime

- `reading_sessions` (see `backend/alembic/versions/001_initial_schema.py`)
  - id: Integer PK
  - student_id: FK -> students.id
  - book_id: FK -> books.id
  - started_at, ended_at: DateTime
  - duration_minutes: Integer
  - status: String(20)

- `reading_progress`
  - id: Integer PK
  - student_id, book_id: FKs
  - current_page: Integer
  - completion_percentage: Float
  - last_read_at: DateTime
  - unique constraint on (student_id, book_id)

- `activity_logs`
  - id: Integer PK
  - student_id nullable FK, book_id nullable FK
  - action: String(50)
  - notes: Text
  - created_at: DateTime

Primary / Foreign keys and indexes are declared in model files and initial migration. See `backend/alembic/versions/001_initial_schema.py`.

Schema design decisions:

- Books store PDF bytes directly in the DB (column `file_data` / LargeBinary). This simplifies deployment (no shared filesystem) and atomicity between metadata and file.
- `is_deleted` soft-delete flag for books to preserve history and avoid expensive deletes.

Migrations (Alembic):

- Migrations are located in `backend/alembic/versions`. Example migration adding `file_data`: `002_add_file_data.py`.
- The repository includes a migration that drops `file_path` (`003_drop_file_path.py`). Alembic is configured to run `upgrade head` at container startup in `backend/entrypoint.sh`.

---

## 4. API Endpoints

All API routes are under `/api/v1` (see `backend/app/api/v1/router.py`). The API returns JSON wrapped with `{ success, message, data }` for typical responses (`app/core/responses.py`).

List of primary endpoints (summary table):

| Method | Path | Auth | Purpose | Request | Response |
|---|---:|---:|---|---|---|
| POST | /api/v1/auth/student/register | No | Register student | StudentRegisterRequest JSON | success + { id, email, role } |
| POST | /api/v1/auth/librarian/register | No | Register librarian | LibrarianRegisterRequest JSON | success + { id, email, role } |
| POST | /api/v1/auth/login | No | Login (get JWT) | LoginRequest JSON (email, password, role) | success + TokenResponse ({ access_token, token_type, role, account_type }) |
| GET | /api/v1/books | Optional | List books | - | success + [BookResponse] |
| GET | /api/v1/books/{id} | Optional | Get book metadata | - | success + BookResponse |
| GET | /api/v1/books/{id}/reader | Requires student | Reader state (book + progress + active session) | - | success + ReaderStateResponse |
| GET | /api/v1/books/{id}/file (alias /download) | Requires student | Stream PDF bytes for a book | - | application/pdf stream (or 404/error) |
| POST | /api/v1/librarian/books | Requires librarian | Upload book (multipart) | multipart: title, author, file (PDF), description?, total_pages? | success + BookResponse (201) |
| DELETE | /api/v1/librarian/books/{id} | Requires librarian | Soft-delete book | - | success + {id, is_deleted} |
| POST | /api/v1/reading-sessions/start | Requires student | Start reading session | { book_id } | success + { session_id } (201) |
| POST | /api/v1/reading-sessions/end | Requires student | End session | { session_id } | success + session data |
| PATCH | /api/v1/reading-progress/{book_id} | Requires student | Update progress | { current_page } | success + ReadingProgressResponse |
| GET | /api/v1/students/analytics | Requires student | Personal analytics | - | success + analytics object |
| GET | /api/v1/librarian/dashboard/overview | Requires librarian | Librarian overview | - | success + overview data |
| GET | /api/v1/librarian/students/all | Requires librarian | List all students | ?search= | success + [students] |
| DELETE | /api/v1/librarian/students/{id} | Requires librarian | Delete student | - | success |
| GET | /api/v1/librarian/activity-logs/export | Requires librarian | Export logs as CSV | ?search= | CSV response |

For exact request bodies and response models see the `backend/app/schemas` directory.

Authentication flow:

- Login endpoint returns a JWT (see `app/core/security.py`). The token contains `sub` (user id), `email`, `role`, `account_type`, and `exp` claims.
- Protected endpoints use HTTP Bearer token validated by `app/core/deps.py` via `get_current_user`, `require_student`, and `require_librarian`.

Example login request (curl):

```bash
curl -X POST https://your-api/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"jane@school.edu","password":"password123","role":"LIBRARIAN"}'
```

Example upload (curl):

```bash
curl -X POST https://your-api/api/v1/librarian/books \
  -H "Authorization: Bearer $TOKEN" \
  -F title="My Book" -F author="Author" -F file=@book.pdf
```

---

## 5. Key Features Explained

- **User Registration & Login**
  - Passwords hashed with `bcrypt` in `app/core/security.py` via `hash_password`.
  - Login verifies hashed password then issues a JWT via `create_access_token`.
  - Tokens validated in `app/core/deps.py` with `HTTPBearer` dependency.

- **Book Upload**
  - Upload handled in `backend/app/api/v1/librarian_books.py` as multipart form with `file` field.
  - `app/services/books.py` calls `app/services/files.validate_and_save_pdf` which validates PDF signature and size, and returns bytes + original filename.
  - File bytes are stored in `books.file_data` (LargeBinary). Pages are auto-counted with `pypdf.PdfReader` via `count_pdf_pages`.

- **Book Download/View**
  - Endpoint `/api/v1/books/{id}/file` streams bytes from `books.file_data` using `StreamingResponse` with media_type `application/pdf` in `backend/app/api/v1/books.py`.

- **Search/Filter**
  - Basic search for librarian student listing uses `search` query parameters in librarian endpoints and shown in frontend pages.

- **Admin/Librarian Features**
  - Librarians can upload and soft-delete books, view popular books analytics, list students, export activity logs, and view activity analytics (endpoints in `backend/app/api/v1/librarian.py`).

---

## 6. File Storage Strategy

- Files are stored in the database column `books.file_data` (LargeBinary / BYTEA). Code: `backend/app/models/book.py` and migration `backend/alembic/versions/002_add_file_data.py`.

Why store in DB:
- Pros:
  - Simplifies deployment: no shared file-system needed across replicas.
  - Atomicity: metadata and file stored together in same transaction.
  - Backups via DB include files.
- Cons:
  - Database bloat and potential performance issues for very large files.
  - Bytea retrieval can be memory intensive.

File handling notes:
- Upload is validated in memory (`validate_and_save_pdf`) and the bytes are saved.
- There is a max upload size (configured via `max_upload_size_mb` in `backend/app/config.py`).

Size limitations and recommendations:
- Default `max_upload_size_mb` is 25MB; adjust via environment or `.env`.
- For larger scale, consider object storage (S3) or a dedicated file service.

---

## 7. Deployment Process

Deployment notes (Render or Docker):

- Environment variables: configured by pydantic `Settings` in `backend/app/config.py`. Important variables:
  - `DATABASE_URL` / `database_url` (Postgres connection)
  - `JWT_SECRET` / `jwt_secret`
  - `JWT_EXPIRY_MINUTES` / `jwt_expiry_minutes`
  - `UPLOAD_DIRECTORY` (kept for back-compat but no longer required)

- Automatic migrations: `entrypoint.sh` runs `python -m alembic upgrade head` before starting Gunicorn, so migration files in `backend/alembic/versions` are applied on deploy.

- Dockerfile: `backend/Dockerfile`. It installs requirements, copies project, ensures `entrypoint.sh` is executable and creates `/app/uploads` for compatibility. Gunicorn is started by `entrypoint.sh`.

Render specifics:
- Configure a Web Service using the Dockerfile or by pointing to `backend` service.
- Add a managed PostgreSQL instance and set `DATABASE_URL` environment variable in Render service settings.

---

## 8. Challenges & Solutions

- Docker permission issues: ensure `entrypoint.sh` is executable (`chmod +x`) - handled in Dockerfile.
- Database connection differences (local vs Render): use `DATABASE_URL` env to switch between local SQLite test (`sqlite://`) for tests and Postgres for production. See `backend/app/database.py` and `frontend/README.md`.
- NOT NULL `file_path`: historical migrations created `file_path` as NOT NULL in the initial migration. To remove this column we generated a migration that drops it: `backend/alembic/versions/003_drop_file_path.py`.
- File storage design: migrated from filesystem `file_path` to storing bytes (`file_data`) to simplify deployments and remove filesystem dependencies.
- Mobile responsiveness: fixed in frontend CSS (`frontend/src/input.css`) and templates to ensure wrapping and prevent overflow.

Lessons learned:
- Avoid coupling files to filesystem when deploying to platforms without shared volumes.
- Keep migrations incremental and careful about NOT NULL constraints when changing columns.

---

## 9. Code Structure

Backend:

- `backend/app/main.py` — FastAPI app setup and exception handlers.
- `backend/app/api/v1/*` — API routers for auth, books, librarians, students, reading sessions, reading progress.
- `backend/app/models/*` — SQLAlchemy models (Book, Student, Librarian, ReadingSession, ReadingProgress, ActivityLog).
- `backend/app/schemas/*` — Pydantic schemas for requests/responses.
- `backend/app/services/*` — Business logic (auth, books, files, reading_progress, reading_sessions, students, activity).
- `backend/app/core/*` — Reusable utilities: `security.py` (JWT + bcrypt), `deps.py` (auth deps), `responses.py`, `exceptions.py`.
- `backend/alembic` — Migrations and Alembic config.
- `backend/entrypoint.sh`, `backend/Dockerfile`, `backend/gunicorn.conf.py` — deployment and process management.

Frontend:

- `frontend/src/*.html` — Static pages: login, register, student-dashboard, student-library, e-reader, librarian pages.
- `frontend/src/app.js` — Client-side JS wrapper and `api` helper functions.
- `frontend/src/input.css` — Tailwind/Tailwind components and custom styles (we added responsive fixes here).

Key modules:
- `app/services/books.py` — upload_book, list_books, get_active_book, soft_delete_book.
- `app/api/v1/librarian_books.py` — upload and delete endpoints for librarian uploads.

---

## 10. Security Considerations

- **Authentication:** JWT tokens created by `app/core/security.create_access_token` and validated in `app/core/deps.get_current_user` (HTTP Bearer).
- **Password Hashing:** bcrypt used via `hash_password` and `verify_password` in `app/core/security.py`.
- **Input validation:** Pydantic schemas validate requests (`backend/app/schemas`).
- **CORS:** Configured in `backend/app/main.py` with permissive `allow_origins=["*"]` (consider tightening for production).
- **Secrets:** `jwt_secret` should be set via environment and kept secret.

Recommendations:
- Use HTTPS in production, rotate JWT secrets, limit token expiry, and implement refresh tokens if needed.
- Tighten CORS to allowed origins in production.

---

## 11. Testing

- Unit & integration tests: `backend/tests/test_integration.py` exercises major flows. Run via `./scripts/run_tests.sh` in `backend`.
- Swagger/OpenAPI docs: available at `/api/docs` when backend is running.
- Manual testing: start backend locally and serve frontend (see `frontend/README.md`). Ensure `API_BASE` in `frontend/src/app.js` is pointed to backend.

---

## 12. Future Improvements

- Move file storage to cloud object storage (S3) for scaling and reduce DB size.
- Add pagination for books listing and searching.
- Add refresh tokens and role-based admin features.
- Improve frontend with a SPA framework (React/Vue) for better UX and state management.
- Add CI/CD pipeline with tests and Docker image publishing.

---

## 13. User Guide (concise)

- **Student:** Sign up at `/register.html`, sign in, go to `student-library.html` to browse books, click `Open Reader` to view PDF and track progress.
- **Librarian:** Register and sign in, go to `book-management.html` to upload books (title, author, PDF). Use librarian dashboard to view students and export logs.

---

## 14. Technical Glossary

- API: Application Programming Interface.
- BYTEA: Postgres binary type for storing byte arrays.
- ORM: Object-Relational Mapper (SQLAlchemy) maps Python classes to DB tables.
- JWT: JSON Web Token, used for stateless authentication.
- Alembic: DB migration tool for SQLAlchemy.

---

## Defense Q&A Preparation (selected questions & answers)

1. **Why choose FastAPI over Django/Flask?**
   - FastAPI provides automatic OpenAPI docs, simple async support, concise route definitions, and great dev ergonomics. Django is heavier (full-stack) while Flask requires more boilerplate for validation and docs.

2. **Why store files in DB instead of cloud storage?**
   - In this project storing files in DB simplifies deployment (single data store, atomic writes). For production scale, cloud storage (S3) is preferable because of cost, performance, and serving capabilities.

3. **How did you handle the `file_path` NOT NULL error?**
   - The initial migration had a `file_path` column. We added a migration to drop that column (`backend/alembic/versions/003_drop_file_path.py`) and updated the model to remove the attribute. Migrations run on startup.

4. **How does authentication work?**
   - Passwords hashed with bcrypt. Login returns a JWT with `sub` and role claims. Protected endpoints validate the JWT and enforce role-specific access via dependency functions.

5. **How scalable is the system?**
   - Application servers can be scaled horizontally behind a load balancer. Database must be scaled or moved to managed Postgres; storing files in DB affects DB scalability (recommend S3 for large scale).

6. **How did you ensure data integrity?**
   - DB constraints (unique keys, foreign keys), transactions when creating records, and Alembic migrations to manage schema changes ensure integrity.

7. **What was the most challenging part?**
   - File handling and deployment: switching from filesystem storage to DB storage to make the app cloud-friendly and ensure migrations and startup behavior are robust.

8. **What would you do differently next time?**
   - Use object storage for files, implement streaming uploads for very large files, add RBAC and rate-limiting per endpoint, and write more unit tests for services.

9. **How do you serve PDFs efficiently from the DB?**
   - The backend streams bytes using `StreamingResponse`. For heavy traffic, cache or a CDN in front of S3/object storage is recommended.

10. **Why did you choose SQLAlchemy + Alembic?**
    - SQLAlchemy is a mature ORM with flexibility and Alembic integrates for safe migrations.

11. **How are migrations handled in CI/CD?**
    - Migrations run on service startup via `entrypoint.sh` which executes `alembic upgrade head`.

12. **How secure is JWT usage here?**
    - JWTs use a shared secret `jwt_secret`. For production, set a strong secret, shorter expiry, and consider refresh tokens & revocation.

13. **How to handle large files beyond DB limits?**
    - Switch to S3 or a dedicated file service, store object URL in DB, and stream from S3 with proper access-control.

14. **How does mobile responsiveness work now?**
    - Frontend CSS was updated (`frontend/src/input.css`) and templates adjusted to use wrapping utility `.text-break` and remove fixed `min-width` values.

15. **How to add new features safely?**
    - Add migration files for DB changes, write tests for new endpoints, and follow feature-branch PR workflow.

---

## Justification for Major Technologies

- FastAPI: quick API development, auto docs, async-first.
- Postgres: ACID compliant RDBMS, supports BYTEA.
- Tailwind + static HTML: lightweight and easy to host.
- Docker & Gunicorn: containers for consistent deployment and process management.

---

## Strengths & Weaknesses

- Strengths:
  - Simple, focused codebase.
  - Atomic file storage in DB simplifies consistency.
  - Clear API and small frontend surface.

- Weaknesses:
  - Files in DB may not scale for many large PDFs.
  - Frontend is static, limited interactivity compared to SPA.

---

## Appendix — Useful file references

- Backend entrypoint and Docker: `backend/entrypoint.sh`, `backend/Dockerfile`
- Models: `backend/app/models/book.py`, `backend/app/models/student.py`, `backend/app/models/librarian.py`
- Services: `backend/app/services/books.py`, `backend/app/services/files.py`
- Frontend: `frontend/src/app.js`, `frontend/src/input.css`

---

If you'd like, I can also:

- Commit this `README.md` into the repo (I can add it now),
- Generate diagrams in Mermaid syntax for the architecture and ER diagram,
- Produce a short defense slide deck (outline + key answers), or
- Expand API documentation with full example requests/responses for each endpoint.

Would you like me to commit this file to the repository now? (I can add it as `README.md` at project root.)
