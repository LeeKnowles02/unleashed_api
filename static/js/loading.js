(function () {
  var loaderEl = null;
  var loaderTextEl = null;
  var loaderCancelButtonEl = null;
  var isLoading = false;

  function getLoaderElements() {
    if (!loaderEl) loaderEl = document.getElementById("globalLoader");
    if (!loaderTextEl) loaderTextEl = document.getElementById("loaderText");
    if (!loaderCancelButtonEl) loaderCancelButtonEl = document.getElementById("loaderCancelButton");
  }

  function setButtonLoadingState(button) {
    if (!button || button.dataset.loadingApplied === "true") return;
    button.dataset.loadingApplied = "true";
    button.dataset.originalText = button.textContent;
    button.textContent = button.dataset.loaderButtonText || "Running...";
    button.classList.add("is-loading");
    var spinner = document.createElement("span");
    spinner.className = "btn-inline-spinner";
    spinner.setAttribute("aria-hidden", "true");
    button.prepend(spinner);
  }

  function disableRunButtons(activeButton) {
    var runButtons = document.querySelectorAll(".js-loader-trigger");
    runButtons.forEach(function (button) {
      if (button === activeButton) {
        setButtonLoadingState(button);
        return;
      }
      button.disabled = true;
    });
  }

  function resetRunButtons() {
    var runButtons = document.querySelectorAll(".js-loader-trigger");
    runButtons.forEach(function (button) {
      button.disabled = false;
      if (button.dataset.loadingApplied === "true") {
        button.dataset.loadingApplied = "false";
        button.classList.remove("is-loading");
        var spinner = button.querySelector(".btn-inline-spinner");
        if (spinner) spinner.remove();
        if (button.dataset.originalText) {
          button.textContent = button.dataset.originalText;
        }
      }
    });
  }

  function showLoader(message, activeButton) {
    getLoaderElements();
    if (!loaderEl || !loaderTextEl || isLoading) return;
    isLoading = true;
    loaderTextEl.textContent = message || "Running export...";
    loaderEl.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    disableRunButtons(activeButton || null);
  }

  function hideLoader() {
    getLoaderElements();
    if (!loaderEl || !loaderTextEl) return;
    isLoading = false;
    loaderEl.classList.add("hidden");
    document.body.style.overflow = "";
    resetRunButtons();
  }

  function handleCancel() {
    if (!isLoading) return;
    // Stops browser navigation/waiting for the current response.
    // Server-side processing may continue until job cancellation is implemented.
    window.stop();
    hideLoader();
  }

  function submitWithLoader(event) {
    var form = event.target;
    if (!form) return;
    if (form.dataset.loadingSubmitted === "true") {
      event.preventDefault();
      return;
    }

    var submitter = event.submitter || document.activeElement;
    var message =
      (submitter && submitter.dataset && submitter.dataset.loaderMessage) ||
      form.dataset.loaderMessage ||
      "Running export...";

    event.preventDefault();
    form.dataset.loadingSubmitted = "true";
    showLoader(message, submitter);

    // Allow one paint frame so the loader is visible before request starts.
    requestAnimationFrame(function () {
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit(submitter && submitter.form === form ? submitter : undefined);
      } else {
        form.submit();
      }
    });
  }

  function bindLoaderForms() {
    var forms = document.querySelectorAll("form[data-loader-form='true']");
    forms.forEach(function (form) {
      form.addEventListener("submit", submitWithLoader);
    });
    getLoaderElements();
    if (loaderCancelButtonEl) {
      loaderCancelButtonEl.addEventListener("click", handleCancel);
    }
  }

  window.showLoader = showLoader;
  window.hideLoader = hideLoader;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindLoaderForms);
  } else {
    bindLoaderForms();
  }
})();
