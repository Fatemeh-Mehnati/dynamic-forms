/* E2: page state only. Business rules and session establishment belong to A6.
 * URLs are supplied by Django reverse in the template; all I/O uses WebAPI.
 * Abort abandons browser work, not necessarily server effects. A generation
 * guard prevents abandoned request/resend responses and finally blocks changing UI.
 */
(() => {
  "use strict";
  const form = document.getElementById("otp-auth-form");
  if (!form) return;
  const api = window.WebAPI;
  const get = (id) => document.getElementById(id);
  const fields = {
    purpose: get("auth-purpose"), target: get("auth-target"),
    username: get("auth-username"), code: get("auth-code"),
  };
  const submit = get("auth-submit"), resend = get("auth-resend");
  const edit = get("auth-edit"), check = get("auth-check");
  const status = get("auth-status"), validity = get("validity-info");
  let stage = "entry", pending = null, generation = 0, controller = null;
  let accepted = null, expectedUser = null, canConfirm = true;

  const digits = (value) => value.replace(/[۰-۹٠-٩]/g, (char) =>
    String(char.charCodeAt(0) - (char <= "٩" ? 0x660 : 0x6f0)));
  const invalidResponse = () => Object.assign(new Error("پاسخ سرور برای این مرحله معتبر نیست."), { kind: "response" });
  const isUser = (user) => user && Number.isSafeInteger(user.id) && user.id > 0
    && typeof user.username === "string" && user.username.trim().length > 0
    && typeof user.phone === "string" && /^09[0-9]{9}$/.test(user.phone);

  function render() {
    const locked = pending === "verify" || pending === "session";
    const ended = stage === "success";
    get("auth-fields").disabled = ended;
    form.setAttribute("aria-busy", String(Boolean(pending)));
    fields.purpose.disabled = locked || stage === "uncertain";
    fields.target.disabled = locked || stage === "uncertain";
    fields.target.readOnly = stage !== "entry";
    const registration = fields.purpose.value === "register";
    get("username-group").hidden = !registration;
    fields.username.required = registration;
    fields.username.disabled = !registration || Boolean(pending) || stage === "uncertain";
    get("code-group").hidden = stage !== "code";
    fields.code.disabled = stage !== "code" || Boolean(pending);
    fields.code.required = stage === "code";
    submit.hidden = stage === "uncertain" || ended;
    submit.disabled = Boolean(pending);
    submit.textContent = stage === "entry" ? "درخواست کد" : "تأیید کد";
    resend.hidden = stage !== "code";
    resend.disabled = Boolean(pending);
    edit.hidden = stage === "entry" || ended;
    edit.disabled = locked;
    check.hidden = stage !== "uncertain";
    check.disabled = Boolean(pending);
    if (ended) form.hidden = true;
  }

  function clearErrors() {
    api.clearError();
    for (const [name, field] of Object.entries(fields)) {
      field.setAttribute("aria-invalid", "false");
      const region = get(`${name}-error`);
      region.textContent = "";
      region.hidden = true;
    }
  }

  function fieldError(name, message) {
    fields[name].setAttribute("aria-invalid", "true");
    get(`${name}-error`).textContent = message;
    get(`${name}-error`).hidden = false;
  }

  function focusError() {
    const field = Object.values(fields).find((item) => !item.disabled
      && item.getAttribute("aria-invalid") === "true");
    if (field) field.focus();
    else status.focus();
  }

  // Flatten only for display; keep the original error/details object intact.
  function detailText(value) {
    if (Array.isArray(value)) return value.map(detailText).filter(Boolean).join("؛ ");
    if (value && typeof value === "object") return Object.entries(value)
      .map(([key, item]) => `${key}: ${detailText(item)}`).join("؛ ");
    return value == null ? "" : String(value);
  }

  function displayError(error) {
    const details = error.details;
    let mapped = false;
    const other = [];
    if (details && typeof details === "object" && !Array.isArray(details)) {
      for (const [name, value] of Object.entries(details)) {
        const text = detailText(value);
        if (!text) continue;
        if (Object.hasOwn(fields, name)) { fieldError(name, text); mapped = true; }
        else other.push(`${name}: ${text}`);
      }
    } else if (details != null) other.push(detailText(details));
    let message = mapped ? "اطلاعات مشخص‌شده را بررسی کنید." : error.message;
    if (error.status === 429) message = "درخواست‌ها محدود شده‌اند؛ کمی بعد دوباره تلاش کنید.";
    if (error.status === 401) message = "احراز هویت برای این درخواست تأیید نشد.";
    if (error.status === 403) message = "سرور اجازهٔ انجام این درخواست را نداد.";
    if (other.length) message = `${message}\n${other.join("؛ ")}`;
    api.showError({ message });
    status.textContent = "این مرحله تأیید نشد.";
  }

  function reset() {
    if (pending === "verify" || pending === "session") return;
    generation += 1;
    controller?.abort();
    controller = null;
    pending = null;
    accepted = null;
    expectedUser = null;
    canConfirm = true;
    stage = "entry";
    fields.code.value = "";
    validity.textContent = "";
    status.textContent = "";
    clearErrors();
    render();
  }

  function begin(operation) {
    if (pending) return null;
    pending = operation;
    controller = new AbortController();
    clearErrors();
    render();
    return { generation, signal: controller.signal };
  }

  function current(ticket) { return ticket.generation === generation; }
  function finish(ticket) {
    if (!current(ticket)) return;
    pending = null;
    controller = null;
    render();
    if (stage === "success" || stage === "uncertain") status.focus();
    else focusError();
  }

  function validateEntry() {
    fields.target.value = digits(fields.target.value).trim();
    fields.username.value = fields.username.value.trim();
    if (!["login", "register"].includes(fields.purpose.value)) fieldError("purpose", "نوع درخواست را انتخاب کنید.");
    if (!/^09[0-9]{9}$/.test(fields.target.value)) fieldError("target", "شماره باید ۱۱ رقم باشد و با 09 شروع شود.");
    if (fields.purpose.value === "register" && (!fields.username.value || fields.username.value.length > 150)) {
      fieldError("username", "نام کاربری الزامی است و باید حداکثر ۱۵۰ کاراکتر باشد.");
    }
    return !Object.values(fields).some((field) => field.getAttribute("aria-invalid") === "true");
  }

  async function requestCode(isResend = false) {
    if (pending || (isResend ? stage !== "code" : stage !== "entry")) return;
    clearErrors();
    if (!isResend && !validateEntry()) { focusError(); return; }
    const flow = isResend ? accepted : { target: fields.target.value, purpose: fields.purpose.value };
    const ticket = begin(isResend ? "resend" : "request");
    status.textContent = "در حال درخواست کد…";
    try {
      const data = await api.request(form.dataset.requestUrl, {
        method: "POST", json: { target: flow.target, purpose: flow.purpose }, signal: ticket.signal,
      });
      if (!current(ticket)) return;
      if (!data || typeof data.expires_in !== "number" || !Number.isFinite(data.expires_in)
          || data.expires_in <= 0 || data.expires_in > Number.MAX_SAFE_INTEGER) throw invalidResponse();
      accepted = flow;
      stage = "code";
      fields.code.value = "";
      validity.textContent = `مدت اعتبار اعلام‌شدهٔ سرور: ${data.expires_in} ثانیه.`;
      status.textContent = "درخواست کد پذیرفته شد. کد را برای تأیید وارد کنید.";
    } catch (error) {
      if (current(ticket)) {
        displayError(error);
        if (["network", "abort", "response"].includes(error.kind) || error.status >= 500) {
          status.textContent = "نتیجهٔ درخواست کد مشخص نیست؛ دریافت کد جدید تأیید نشده است.";
        }
      }
    } finally {
      if (current(ticket)) {
        finish(ticket);
        if (stage === "code" && fields.code.getAttribute("aria-invalid") !== "true"
            && status.textContent.startsWith("درخواست کد پذیرفته")) fields.code.focus();
      }
    }
  }

  function matchesTarget(user) {
    return isUser(user) && user.phone === accepted.target
      && (accepted.purpose !== "register" || user.username === fields.username.value.trim());
  }

  async function checkSession(ticket) {
    pending = "session";
    render();
    status.textContent = "در حال بررسی وضعیت ورود…";
    try {
      const user = await api.request(form.dataset.meUrl, { signal: ticket.signal });
      if (!current(ticket)) return;
      if (!canConfirm || !matchesTarget(user) || (expectedUser && user.id !== expectedUser.id)) throw invalidResponse();
      stage = "success";
      fields.code.value = "";
      api.clearError();
      status.textContent = `ورود به حساب ${user.username} در این مرورگر تأیید شد.`;
    } catch (error) {
      if (!current(ticket)) return;
      stage = "uncertain";
      fields.code.value = "";
      // A failed GET cannot prove whether a previous POST took effect.
      status.textContent = "ورود به حساب موردنظر تأیید نشد و نتیجهٔ تأیید کد نامشخص است. می‌توانید وضعیت را دوباره بررسی کنید یا اطلاعات را اصلاح کنید.";
      api.showError({ message: error.kind === "network" || error.kind === "abort"
        ? "ارتباط برای بررسی وضعیت ورود کامل نشد."
        : error.status === 401 || error.status === 403
          ? "ورود قابل استفاده برای حساب موردنظر تأیید نشد."
          : error.status === 429
            ? "بررسی وضعیت محدود شده است؛ کمی بعد به‌صورت دستی دوباره بررسی کنید."
            : error.kind === "http"
              ? "سرور نتوانست وضعیت ورود را تأیید کند."
              : "پاسخ بررسی وضعیت با حساب موردنظر تطابق ندارد یا معتبر نیست." });
    }
  }

  async function verify() {
    if (pending || stage !== "code" || !accepted) return;
    clearErrors();
    fields.code.value = digits(fields.code.value).trim();
    if (!/^[0-9]{1,10}$/.test(fields.code.value)) fieldError("code", "کد باید عددی و بین ۱ تا ۱۰ رقم باشد.");
    fields.username.value = fields.username.value.trim();
    if (accepted.purpose === "register" && (!fields.username.value || fields.username.value.length > 150)) {
      fieldError("username", "نام کاربری الزامی است و باید حداکثر ۱۵۰ کاراکتر باشد.");
    }
    if (Object.values(fields).some((field) => field.getAttribute("aria-invalid") === "true")) { focusError(); return; }
    const ticket = begin("verify");
    expectedUser = null;
    canConfirm = true;
    const payload = { target: accepted.target, purpose: accepted.purpose, code: fields.code.value };
    if (accepted.purpose === "register") payload.username = fields.username.value;
    status.textContent = "در حال تأیید کد…";
    try {
      const data = await api.request(form.dataset.verifyUrl, { method: "POST", json: payload, signal: ticket.signal });
      if (!current(ticket)) return;
      if (!matchesTarget(data?.user)) {
        // A malformed successful verify is not proof of login, even if an old
        // session exists. Inspect it once, but keep the outcome uncertain.
        canConfirm = false;
        throw invalidResponse();
      }
      // Retain only identity evidence, never access/refresh or the full response.
      expectedUser = { id: data.user.id };
      await checkSession(ticket);
    } catch (error) {
      if (!current(ticket)) return;
      const explicitClientError = error.status >= 400 && error.status < 500;
      if (!explicitClientError && (["network", "abort", "response"].includes(error.kind) || error.status >= 500)) {
        // At most one recovery GET; never repeat a possibly consumed OTP POST.
        await checkSession(ticket);
      } else displayError(error);
    } finally { finish(ticket); }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (pending) return;
    if (stage === "entry") requestCode();
    else if (stage === "code") verify();
  });
  resend.addEventListener("click", () => requestCode(true));
  edit.addEventListener("click", () => { reset(); fields.target.focus(); });
  fields.purpose.addEventListener("change", () => { reset(); fields.target.focus(); });
  fields.target.addEventListener("input", () => { if (stage === "entry") reset(); });
  check.addEventListener("click", async () => {
    if (pending || stage !== "uncertain" || !accepted) return;
    const ticket = begin("session");
    try { await checkSession(ticket); } finally { finish(ticket); }
  });
  render();
})();
