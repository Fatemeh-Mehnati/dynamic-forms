/* Shared session-based API helper; no endpoint or application state is stored.
 * request(url, {method, headers, signal, json}) serializes JSON (including null).
 * request(url, {method, headers, signal, body: formData}) sends FormData.
 * Omit both json and body for no request body. Other fetch options are ignored.
 * Resolves to parsed JSON or null for 204/empty bodies. Rejects with Error carrying
 * kind (local/http/response/network/abort), status, code, message and details.
 * request never changes UI. Pages choose when to call showError / clearError,
 * and handle any field-specific details themselves.
 */
(() => {
  "use strict";

  function failure(kind, status, code, message, details = null) {
    const error = new Error(message);
    Object.assign(error, { kind, status, code, details });
    return error;
  }

  function csrfToken() {
    // Current settings use Django defaults: csrftoken, X-CSRFToken,
    // CSRF_COOKIE_HTTPONLY=False, CSRF_USE_SESSIONS=False. Read on every write.
    const cookie = document.cookie.split(";").map((item) => item.trim())
      .find((item) => item.startsWith("csrftoken="));
    if (cookie) {
      try {
        const token = decodeURIComponent(cookie.slice("csrftoken=".length));
        if (token) return token;
      } catch (_) { /* A malformed cookie may fall back to the rendered token. */ }
    }
    // This fallback becomes stale after token rotation until the page rerenders.
    return document.querySelector("#web-csrf-token [name=csrfmiddlewaretoken]")?.value || "";
  }

  async function request(url, options = {}) {
    let target;
    try { target = new URL(url, window.location.href); }
    catch (_) { throw failure("local", null, "invalid_url", "نشانی درخواست معتبر نیست."); }
    if (target.origin !== window.location.origin || !["http:", "https:"].includes(target.protocol)
        || target.username || target.password) {
      throw failure("local", null, "external_url", "درخواست باید به همین مبدأ ارسال شود.");
    }
    const method = (options.method || "GET").toUpperCase();
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");
    // Prevent a caller-supplied stale CSRF token even on safe requests.
    headers.delete("X-CSRFToken");
    const hasJSON = Object.prototype.hasOwnProperty.call(options, "json");
    const hasBody = options.body !== undefined;
    if ((hasJSON && hasBody) || (hasBody && !(options.body instanceof FormData))) {
      throw failure("local", null, "invalid_body", "بدنه باید json یا FormData باشد.");
    }
    if (["GET", "HEAD"].includes(method) && (hasJSON || hasBody)) {
      throw failure("local", null, "invalid_body", "این روش درخواست بدنه نمی‌پذیرد.");
    }
    let body;
    if (hasJSON) {
      headers.set("Content-Type", "application/json");
      try {
        body = JSON.stringify(options.json);
        if (body === undefined) throw new TypeError("Undefined JSON");
      } catch (_) {
        throw failure("local", null, "invalid_json_body", "بدنهٔ JSON معتبر نیست.");
      }
    } else if (hasBody) {
      body = options.body;
      headers.delete("Content-Type"); // Browser supplies multipart boundary.
    }
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
      const token = csrfToken();
      if (!token) throw failure("local", null, "csrf_missing", "توکن امنیتی موجود نیست؛ صفحه را دوباره بارگذاری کنید.");
      headers.set("X-CSRFToken", token);
    }
    let response, text;
    try {
      response = await fetch(target.href, {
        method, headers, body, signal: options.signal,
        credentials: "same-origin", mode: "same-origin", redirect: "error",
      });
      text = response.status === 204 ? "" : await response.text();
    } catch (error) {
      const aborted = error.name === "AbortError" || options.signal?.aborted;
      throw failure(aborted ? "abort" : "network", null,
        aborted ? "request_aborted" : "network_error",
        aborted ? "درخواست لغو شد." : "ارتباط با سرور برقرار نشد.");
    }
    const contentType = (response.headers.get("Content-Type") || "").split(";")[0].trim().toLowerCase();
    const isJSON = contentType === "application/json" || /^application\/[\w.-]+\+json$/.test(contentType);
    let data = null;
    if (text.trim()) {
      if (!isJSON) {
        throw failure(response.ok ? "response" : "http", response.status,
          response.ok ? "unexpected_content_type" : "http_error",
          response.ok ? "پاسخ سرور از نوع JSON نیست." : "درخواست ناموفق بود.");
      }
      try { data = JSON.parse(text); }
      catch (_) {
        throw failure("response", response.status, "invalid_json", "پاسخ JSON سرور معتبر نیست.");
      }
    }
    if (response.ok) return data;
    const envelope = data && typeof data.error === "object" && data.error !== null ? data.error : null;
    throw failure("http", response.status,
      typeof envelope?.code === "string" ? envelope.code : "http_error",
      typeof envelope?.message === "string" ? envelope.message
        : typeof data?.detail === "string" ? data.detail : "درخواست ناموفق بود.",
      envelope ? (envelope.details ?? null) : data);
  }

  function errorContainer(container) {
    return container || document.getElementById("web-api-errors");
  }

  function clearError(container) {
    const region = errorContainer(container);
    if (!region) return;
    region.replaceChildren();
    region.hidden = true;
  }

  function showError(error, container) {
    const region = errorContainer(container);
    if (!region) return;
    clearError(region);
    region.setAttribute("role", "alert");
    region.setAttribute("aria-live", "assertive");
    region.setAttribute("aria-atomic", "true");
    const box = document.createElement("div");
    box.className = "alert alert-danger d-flex flex-wrap align-items-center gap-3";
    const message = document.createElement("span");
    message.className = "flex-grow-1";
    message.textContent = typeof error?.message === "string" ? error.message : "درخواست ناموفق بود.";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn btn-outline-danger btn-sm";
    close.textContent = "پاک کردن پیام";
    close.addEventListener("click", () => clearError(region));
    box.append(message, close);
    region.append(box);
    region.hidden = false;
  }

  document.querySelectorAll("[data-web-dismiss-message]").forEach((button) => {
    button.addEventListener("click", () => button.closest("[data-web-message]")?.remove());
  });

  window.WebAPI = Object.freeze({ request, showError, clearError });
})();
