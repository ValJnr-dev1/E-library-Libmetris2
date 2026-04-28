(() => {
  const ROLE_KEY = "libmetrics_role";

  function getRole() {
    return window.localStorage.getItem(ROLE_KEY) || "";
  }

  function setRole(role) {
    window.localStorage.setItem(ROLE_KEY, role);
  }

  function clearRole() {
    window.localStorage.removeItem(ROLE_KEY);
  }

  function requireRole(allowed) {
    const role = getRole();
    if (!allowed.includes(role)) {
      window.location.href = "./index.html";
      return false;
    }
    return true;
  }

  window.LibMetrics = {
    getRole,
    setRole,
    clearRole,
    requireRole,
  };

  document.addEventListener("click", (e) => {
    const a = e.target && e.target.closest ? e.target.closest("a[data-signout]") : null;
    if (!a) return;
    clearRole();
  });
})();

