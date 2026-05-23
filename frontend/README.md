# LibMetrics Frontend

Static HTML/Tailwind UI wired to the E-Library API.

## Run locally

1. Start the backend API on port **8000** (see `../backend/README.md`).
2. Serve this folder:

```bash
cd src
python3 -m http.server 8080
```

3. Open http://localhost:8080

## API base URL

By default, `app.js` calls `http://localhost:8000`. To override:

```js
localStorage.setItem("libmetrics_api_base", "http://your-api-host:8000");
```

## Pages

| Page | Role | API usage |
|------|------|-----------|
| `index.html` | All | Sign in |
| `register.html` | All | Create account (student or librarian) |
| `student-dashboard.html` | Student | Analytics, books |
| `student-library.html` | Student | Book catalog |
| `e-reader.html` | Student | Reader state, sessions, progress, PDF |
| `student-analytics.html` | Student | Personal analytics |
| `librarian-dashboard.html` | Librarian | Dashboard, students, logs, export |
| `book-management.html` | Librarian | Upload/delete books |

## Build CSS

```bash
npm install
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch
```
