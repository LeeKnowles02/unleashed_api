(function () {
  const KEY = "ur_theme";

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch (e) {}
  }

  // Load saved theme
  try {
    const saved = localStorage.getItem(KEY);
    if (saved) apply(saved);
  } catch (e) {}

  // Wire buttons
  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    btn.addEventListener("click", () => {
      apply(btn.getAttribute("data-theme-btn"));
    });
  });
})();
