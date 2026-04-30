(function () {
  var loaderEl = null;
  var loaderTextEl = null;
  var loaderCancelButtonEl = null;
  var isLoading = false;
  var downloadPollIntervalId = null;
  var downloadFallbackTimeoutId = null;

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
    if (downloadPollIntervalId) {
      window.clearInterval(downloadPollIntervalId);
      downloadPollIntervalId = null;
    }
    if (downloadFallbackTimeoutId) {
      window.clearTimeout(downloadFallbackTimeoutId);
      downloadFallbackTimeoutId = null;
    }
  }

  function handleCancel() {
    if (!isLoading) return;
    // Stops browser navigation/waiting for the current response.
    // Server-side processing may continue until job cancellation is implemented.
    window.stop();
    hideLoader();
  }

  function readCookie(name) {
    var prefix = name + "=";
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var i = 0; i < cookies.length; i += 1) {
      var c = cookies[i].trim();
      if (c.indexOf(prefix) === 0) {
        return decodeURIComponent(c.substring(prefix.length));
      }
    }
    return null;
  }

  function startDownloadCompletionWatcher(form) {
    if (!form || form.dataset.loaderDownload !== "true") return;
    var token = "dl_" + Date.now() + "_" + Math.random().toString(36).slice(2, 10);
    var tokenField = form.querySelector("input[name='download_token']");
    if (!tokenField) {
      tokenField = document.createElement("input");
      tokenField.type = "hidden";
      tokenField.name = "download_token";
      form.appendChild(tokenField);
    }
    tokenField.value = token;

    if (downloadPollIntervalId) {
      window.clearInterval(downloadPollIntervalId);
      downloadPollIntervalId = null;
    }
    if (downloadFallbackTimeoutId) {
      window.clearTimeout(downloadFallbackTimeoutId);
      downloadFallbackTimeoutId = null;
    }

    downloadPollIntervalId = window.setInterval(function () {
      var doneToken = readCookie("unleashed_download_token");
      if (doneToken && doneToken === token) {
        document.cookie = "unleashed_download_token=; Max-Age=0; path=/";
        hideLoader();
      }
    }, 500);

    // Safety fallback so the UI does not remain locked forever.
    downloadFallbackTimeoutId = window.setTimeout(function () {
      hideLoader();
    }, 10 * 60 * 1000);
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

    form.dataset.loadingSubmitted = "true";
    startDownloadCompletionWatcher(form);
    showLoader(message, submitter);
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
