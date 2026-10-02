/* E3 reads only processes. Missing form/category APIs are not substituted.
 * The input is a draft; applied.search/page describe the current request.
 * Pagination URLs are validated then rebuilt, never forwarded blindly.
 */
(() => {
  "use strict";
  const panel = document.getElementById("processes-panel");
  if (!panel) return; // Anonymous template has no active panel.
  const api = window.WebAPI;
  const get = (id) => document.getElementById(id);
  const input = get("process-search"), form = get("process-search-form");
  const apply = get("process-apply"), clear = get("process-clear");
  const previous = get("process-previous"), next = get("process-next");
  const retry = get("process-retry"), status = get("process-status");
  const results = get("process-results"), count = get("process-count");
  const pageLabel = get("process-page"), errors = get("process-errors");
  let endpoint, applied = { search: "", page: 1 };
  let generation = 0, controller = null, pending = false, needsLogin = false;
  let previousPage = null, nextPage = null;
  const positiveInteger = (value) => Number.isSafeInteger(value) && value > 0;
  const invalid = (code = "invalid_list") => Object.assign(
    new Error(code === "invalid_pagination"
      ? "نشانی صفحه‌بندی معتبر نیست؛ فهرست دریافت نشد."
      : "پاسخ فهرست معتبر نیست؛ دوباره تلاش کنید."), { kind: "response", code });
  const dateFormat = new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Tehran",
  });

  function controls() {
    panel.setAttribute("aria-busy", String(pending));
    input.disabled = needsLogin;
    apply.disabled = needsLogin;
    clear.disabled = needsLogin;
    previous.disabled = pending || needsLogin || previousPage === null;
    next.disabled = pending || needsLogin || nextPage === null;
    retry.disabled = pending || needsLogin;
  }

  function clearResults() {
    results.replaceChildren();
    count.textContent = "";
    count.hidden = true;
    pageLabel.textContent = "";
    previousPage = nextPage = null;
  }

  function requestURL(query) {
    const url = new URL(endpoint.href);
    if (query.search) url.searchParams.set("search", query.search);
    url.searchParams.set("page", String(query.page));
    return url.href;
  }

  function paginationPage(value, search) {
    if (value === null) return null;
    if (typeof value !== "string" || !value.trim() || value.includes("#")) throw invalid("invalid_pagination");
    let url;
    try { url = new URL(value, endpoint); }
    catch (_) { throw invalid("invalid_pagination"); }
    if (url.origin !== endpoint.origin || url.pathname !== endpoint.pathname
        || url.username || url.password || url.hash) throw invalid("invalid_pagination");
    const keys = [...url.searchParams.keys()];
    if (keys.some((key) => !["search", "page"].includes(key))
        || new Set(keys).size !== keys.length
        || (url.searchParams.get("search") || "") !== search) throw invalid("invalid_pagination");
    const rawPage = url.searchParams.get("page");
    if (rawPage !== null && !/^[1-9][0-9]*$/.test(rawPage)) throw invalid("invalid_pagination");
    const page = rawPage === null ? 1 : Number(rawPage);
    if (!positiveInteger(page)) throw invalid("invalid_pagination");
    return page;
  }

  function readableDate(value) {
    // Reject invalid calendar dates as well as non-ISO/Invalid Date values.
    if (typeof value !== "string") throw invalid();
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/.exec(value);
    if (!match) throw invalid();
    const [, year, month, day, hour, minute, second, zone] = match;
    const calendar = new Date(0);
    calendar.setUTCFullYear(Number(year), Number(month), 0);
    if (Number(month) < 1 || Number(month) > 12 || Number(day) < 1
        || Number(day) > calendar.getUTCDate() || Number(hour) > 23
        || Number(minute) > 59 || Number(second) > 59
        || (zone !== "Z" && (Number(zone.slice(1, 3)) > 23 || Number(zone.slice(4)) > 59))) throw invalid();
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) throw invalid();
    return dateFormat.format(date);
  }

  function validate(data, query) {
    if (!data || !Array.isArray(data.results) || !Number.isSafeInteger(data.count)
        || data.count < 0 || data.count < data.results.length
        || (data.count > 0 && data.results.length === 0)) throw invalid();
    const before = paginationPage(data.previous, query.search);
    const after = paginationPage(data.next, query.search);
    const rows = data.results.map((item) => {
      if (!item || typeof item.title !== "string" || typeof item.description !== "string"
          || typeof item.is_public !== "boolean" || !["linear", "free"].includes(item.mode)
          || !(item.category === null || positiveInteger(item.category))) throw invalid();
      return {
        title: item.title, description: item.description, isPublic: item.is_public,
        mode: item.mode, category: item.category,
        created: readableDate(item.created_at), updated: readableDate(item.updated_at),
      };
    });
    return { rows, count: data.count, before, after };
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function display(data, query) {
    const fragment = document.createDocumentFragment();
    for (const row of data.rows) {
      const item = element("li", "col-12 col-lg-6");
      const card = element("article", "border rounded p-3 h-100");
      card.append(element("h3", "h6", row.title));
      if (row.description.trim()) card.append(element("p", "mb-2", row.description));
      card.append(element("p", "small mb-2", `${row.isPublic ? "عمومی" : "خصوصی"} · ${row.mode === "linear" ? "خطی" : "آزاد"}`));
      card.append(element("p", "small text-secondary mb-2", row.category === null ? "بدون دسته" : "نام دسته در دسترس نیست"));
      card.append(element("p", "small text-secondary mb-1", `ایجاد: ${row.created}`));
      card.append(element("p", "small text-secondary mb-0", `ویرایش: ${row.updated}`));
      item.append(card);
      fragment.append(item);
    }
    results.append(fragment);
    count.textContent = `تعداد کل ${query.search ? "نتایج جستجو" : "فرایندها"}: ${data.count}`;
    count.hidden = false;
    pageLabel.textContent = `صفحهٔ ${query.page}`;
    previousPage = data.before;
    nextPage = data.after;
    status.textContent = data.rows.length
      ? (query.search ? `نتایج جستجوی «${query.search}» دریافت شد.` : "فهرست فرایندها دریافت شد.")
      : (query.search ? `نتیجه‌ای برای جستجوی «${query.search}» پیدا نشد.` : "هنوز فرایندی ندارید.");
  }

  async function load(query, focus = false) {
    if (needsLogin || (pending && query.search === applied.search && query.page === applied.page)) return;
    const ticket = ++generation;
    controller?.abort();
    controller = new AbortController();
    applied = { ...query };
    pending = true;
    clearResults();
    api.clearError(errors);
    retry.hidden = true;
    status.textContent = "در حال دریافت فرایندها…";
    controls();
    try {
      const data = await api.request(requestURL(query), { method: "GET", signal: controller.signal });
      if (ticket !== generation) return;
      display(validate(data, query), query);
    } catch (error) {
      if (ticket !== generation) return;
      clearResults();
      if (error.status === 401) {
        ++generation;
        controller?.abort();
        controller = null;
        pending = false;
        needsLogin = true;
        input.value = "";
        applied = { search: "", page: 1 };
        status.textContent = "برای مشاهدهٔ فرایندها باید دوباره وارد حساب شوید.";
        controls();
        if (focus) status.focus();
      } else {
        status.textContent = "بارگذاری فرایندها ناموفق بود.";
        api.showError({ message: error.status === 403 ? "اجازهٔ مشاهدهٔ این فهرست را ندارید."
          : error.status === 429 ? "درخواست‌ها محدود شده‌اند؛ کمی بعد دوباره تلاش کنید."
            : error.message }, errors);
        retry.hidden = false;
      }
    } finally {
      if (ticket === generation) {
        pending = false;
        controller = null;
        controls();
        if (focus) status.focus();
      }
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load({ search: input.value.trim(), page: 1 }, true);
  });
  clear.addEventListener("click", () => {
    input.value = "";
    load({ search: "", page: 1 }, true);
  });
  previous.addEventListener("click", () => {
    if (!previous.disabled) load({ search: applied.search, page: previousPage }, true);
  });
  next.addEventListener("click", () => {
    if (!next.disabled) load({ search: applied.search, page: nextPage }, true);
  });
  retry.addEventListener("click", () => {
    if (!retry.disabled && !retry.hidden) load(applied, true);
  });
  try {
    endpoint = new URL(panel.dataset.listUrl, window.location.href);
    if (endpoint.origin !== window.location.origin || !["http:", "https:"].includes(endpoint.protocol)
        || endpoint.username || endpoint.password || endpoint.hash || endpoint.search) throw invalid("invalid_pagination");
    load(applied);
  } catch (error) {
    api.showError(error, errors);
    status.textContent = "فهرست در دسترس نیست.";
  }
})();
