(() => {
  const ROLE_KEY = "libmetrics_role";
  const TOKEN_KEY = "libmetrics_token";
  const EMAIL_KEY = "libmetrics_email";
  const API_BASE_KEY = "libmetrics_api_base";

  const DEFAULT_API_BASE = "https://e-library-libmetris.onrender.com";
  const API_BASE =
    window.localStorage.getItem(API_BASE_KEY) ||
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? "http://localhost:8000"
      : DEFAULT_API_BASE);

  function getRole() {
    return window.localStorage.getItem(ROLE_KEY) || "";
  }

  function getToken() {
    return window.localStorage.getItem(TOKEN_KEY) || "";
  }

  function getEmail() {
    return window.localStorage.getItem(EMAIL_KEY) || "";
  }

  function setSession(role, token, email) {
    window.localStorage.setItem(ROLE_KEY, role);
    window.localStorage.setItem(TOKEN_KEY, token);
    if (email) window.localStorage.setItem(EMAIL_KEY, email);
  }

  function setRole(role) {
    window.localStorage.setItem(ROLE_KEY, role);
  }

  function clearRole() {
    window.localStorage.removeItem(ROLE_KEY);
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(EMAIL_KEY);
  }

  function requireRole(allowed) {
    const role = getRole();
    const token = getToken();
    if (!token || !allowed.includes(role)) {
      window.location.href = allowed.includes("librarian")
        ? "./librarian-login.html"
        : "./student-login.html";
      return false;
    }
    if (allowed.includes("librarian") && role !== "librarian") {
      window.location.href = "./student-login.html";
      return false;
    }
    if (allowed.includes("student") && role !== "student") {
      window.location.href = "./librarian-login.html";
      return false;
    }
    return true;
  }

  function showError(el, message) {
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("hidden", !message);
  }

  async function parseResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json();
    }
    return { success: response.ok, message: response.statusText, data: null };
  }

  async function apiRequest(method, path, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const config = { method, headers };
    if (options.body !== undefined) {
      if (options.body instanceof FormData) {
        config.body = options.body;
      } else {
        headers["Content-Type"] = "application/json";
        config.body = JSON.stringify(options.body);
      }
    }

    const response = await fetch(`${API_BASE}${path}`, config);
    const payload = await parseResponse(response);

    if (!response.ok || payload.success === false) {
      const message = payload.message || `Request failed (${response.status})`;
      throw new Error(message);
    }
    return payload.data;
  }

  const api = {
    registerStudent(body) {
      return apiRequest("POST", "/api/v1/auth/student/register", { body });
    },
    registerLibrarian(body) {
      return apiRequest("POST", "/api/v1/auth/librarian/register", { body });
    },
    login(email, password, role) {
      return apiRequest("POST", "/api/v1/auth/login", {
        body: { email, password, role },
      });
    },
    getBooks() {
      return apiRequest("GET", "/api/v1/books");
    },
    getBook(bookId) {
      return apiRequest("GET", `/api/v1/books/${bookId}`);
    },
    getReaderState(bookId) {
      return apiRequest("GET", `/api/v1/books/${bookId}/reader`);
    },
    getProgress(bookId) {
      return apiRequest("GET", `/api/v1/books/${bookId}/progress`);
    },
    startSession(bookId) {
      return apiRequest("POST", "/api/v1/reading-sessions/start", {
        body: { book_id: bookId },
      });
    },
    endSession(sessionId) {
      return apiRequest("POST", "/api/v1/reading-sessions/end", {
        body: { session_id: sessionId },
      });
    },
    updateProgress(bookId, currentPage) {
      return apiRequest("PATCH", `/api/v1/reading-progress/${bookId}`, {
        body: { current_page: currentPage },
      });
    },
    getStudentAnalytics() {
      return apiRequest("GET", "/api/v1/students/analytics");
    },
    getLibrarianOverview() {
      return apiRequest("GET", "/api/v1/librarian/dashboard/overview");
    },
    getLibrarianStudents(search, page, limit) {
      const params = new URLSearchParams({ page: String(page), limit: String(limit) });
      if (search) params.set("search", search);
      return apiRequest("GET", `/api/v1/librarian/students?${params}`);
    },
    getPopularBooks() {
      return apiRequest("GET", "/api/v1/librarian/books/popular");
    },
    getLowActivityStudents() {
      return apiRequest("GET", "/api/v1/librarian/students/attention");
    },
    getActivityLogs(search, page, limit) {
      const params = new URLSearchParams({ page: String(page), limit: String(limit) });
      if (search) params.set("search", search);
      return apiRequest("GET", `/api/v1/librarian/activity-logs?${params}`);
    },
    uploadBook(formData) {
      return apiRequest("POST", "/api/v1/librarian/books", { body: formData });
    },
    deleteBook(bookId) {
      return apiRequest("DELETE", `/api/v1/librarian/books/${bookId}`);
    },
    getAllStudents(search) {
      const params = search ? `?search=${encodeURIComponent(search)}` : "";
      return apiRequest("GET", `/api/v1/librarian/students/all${params}`);
    },
    deleteStudent(studentId) {
      return apiRequest("DELETE", `/api/v1/librarian/students/${studentId}`);
    },
    async fetchBookPdfBlob(bookId) {
      const response = await fetch(`${API_BASE}/api/v1/books/${bookId}/file`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!response.ok) {
        const payload = await parseResponse(response);
        throw new Error(payload.message || "Failed to load PDF");
      }
      return response.blob();
    },
    async exportActivityLogs(search) {
      const params = search ? `?search=${encodeURIComponent(search)}` : "";
      const response = await fetch(
        `${API_BASE}/api/v1/librarian/activity-logs/export${params}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      if (!response.ok) throw new Error("Export failed");
      return response.blob();
    },
  };

  function bookCoverSvg(title) {
    const label = (title || "Book").slice(0, 10).replace(/[<>&'"]/g, "");
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='96' height='128'><rect width='100%' height='100%' fill='#dbeafe'/><text x='48' y='72' text-anchor='middle' font-family='Arial' font-size='12' fill='#1f2937'>${label}</text></svg>`;
    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
  }

  function formatMinutes(minutes) {
    if (!minutes) return "0 min";
    if (minutes < 60) return `${minutes} min`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  }

  function displayNameFromEmail(email) {
    if (!email) return "Reader";
    return email.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  window.LibMetrics = {
    API_BASE,
    getRole,
    getToken,
    getEmail,
    setRole,
    setSession,
    clearRole,
    requireRole,
    showError,
    api,
    bookCoverSvg,
    formatMinutes,
    displayNameFromEmail,
  };

  document.addEventListener("click", (e) => {
    const a = e.target && e.target.closest ? e.target.closest("a[data-signout]") : null;
    if (!a) return;
    clearRole();
  });
})();
