/* E3 reads processes and one category page at a time; forms remain unavailable.
 * The input is a draft; applied.search/category/page describe the current request.
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
  const select = get("process-category");
  const categoryPanel = get("categories-panel");
  let endpoint, applied = { search: "", category: null, page: 1 };
  let draftCategory = null, appliedCategory = null;
  // Retain only the current category page and the two selections, never all pages.
  let categoryRows = [], categoryLabels = [];
  const categories = {
    endpoint: null, page: 1, valid: false, pending: false, generation: 0,
    controller: null, previous: null, next: null,
  };
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
    select.disabled = needsLogin;
    apply.disabled = needsLogin;
    clear.disabled = needsLogin;
    previous.disabled = pending || needsLogin || previousPage === null;
    next.disabled = pending || needsLogin || nextPage === null;
    retry.disabled = pending || needsLogin;
  }

  function clearResults() {
    results.replaceChildren();
    categoryLabels = [];
    count.textContent = "";
    count.hidden = true;
    pageLabel.textContent = "";
    previousPage = nextPage = null;
  }

  function requestURL(query) {
    const url = new URL(endpoint.href);
    if (query.search) url.searchParams.set("search", query.search);
    if (query.category !== null) url.searchParams.set("category", String(query.category));
    url.searchParams.set("page", String(query.page));
    return url.href;
  }

  function paginationPage(value, query, base = endpoint, categoryOnly = false) {
    if (value === null) return null;
    if (typeof value !== "string" || !value.trim() || value.includes("#")) throw invalid("invalid_pagination");
    let url;
    try { url = new URL(value, base); }
    catch (_) { throw invalid("invalid_pagination"); }
    if (url.origin !== base.origin || url.pathname !== base.pathname
        || url.username || url.password || url.hash) throw invalid("invalid_pagination");
    const keys = [...url.searchParams.keys()];
    const allowed = categoryOnly ? ["page"] : ["search", "category", "page"];
    if (keys.some((key) => !allowed.includes(key)) || new Set(keys).size !== keys.length) throw invalid("invalid_pagination");
    if (!categoryOnly && ((url.searchParams.get("search") || "") !== query.search
        || url.searchParams.get("category") !== (query.category === null ? null : String(query.category)))) throw invalid("invalid_pagination");
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
    const before = paginationPage(data.previous, query);
    const after = paginationPage(data.next, query);
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
      const label = element("p", "small text-secondary mb-2", categoryName(row.category));
      categoryLabels.push({ id: row.category, node: label });
      card.append(label);
      card.append(element("p", "small text-secondary mb-1", `ایجاد: ${row.created}`));
      card.append(element("p", "small text-secondary mb-0", `ویرایش: ${row.updated}`));
      item.append(card);
      fragment.append(item);
    }
    results.append(fragment);
    count.textContent = `تعداد کل ${query.search || query.category !== null ? "نتایج فیلتر" : "فرایندها"}: ${data.count}`;
    count.hidden = false;
    pageLabel.textContent = `صفحهٔ ${query.page}`;
    previousPage = data.before;
    nextPage = data.after;
    status.textContent = data.rows.length
      ? (query.search || query.category !== null ? "نتایج فیلتر دریافت شد." : "فهرست فرایندها دریافت شد.")
      : (query.search || query.category !== null ? "نتیجه‌ای برای فیلتر اعمال‌شده پیدا نشد." : "هنوز فرایندی ندارید.");
  }

  async function load(query, focus = false) {
    if (needsLogin || (pending && query.search === applied.search && query.page === applied.page && query.category === applied.category)) return;
    const ticket = ++generation;
    controller?.abort();
    controller = new AbortController();
    applied = { ...query };
    appliedCategory = query.category === null ? null : knownCategory(query.category);
    rebuildOptions();
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
        requireLogin(focus ? status : null);
      } else if (error.kind !== "abort") {
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
    const selected = select.value === "" ? null : knownCategory(Number(select.value));
    if (select.value !== "" && (!selected || String(selected.id) !== select.value)) {
      api.showError({ message: "دسته را از گزینه‌های دریافت‌شده انتخاب کنید." }, errors);
      select.focus();
      return;
    }
    draftCategory = selected;
    load({ search: input.value.trim(), category: selected?.id ?? null, page: 1 }, true);
  });
  clear.addEventListener("click", () => {
    input.value = "";
    draftCategory = null;
    select.value = "";
    load({ search: "", category: null, page: 1 }, true);
  });
  previous.addEventListener("click", () => {
    if (!previous.disabled) load({ ...applied, page: previousPage }, true);
  });
  next.addEventListener("click", () => {
    if (!next.disabled) load({ ...applied, page: nextPage }, true);
  });
  retry.addEventListener("click", () => {
    if (!retry.disabled && !retry.hidden) load(applied, true);
  });
  function knownCategory(id) {
    return categoryRows.find((row) => row.id === id)
      || (draftCategory?.id === id ? draftCategory : null)
      || (appliedCategory?.id === id ? appliedCategory : null);
  }

  function categoryName(id) {
    return id === null ? "بدون دسته" : knownCategory(id)?.name || "نام دسته هنوز در دسترس نیست";
  }

  function rebuildOptions() {
    const options = new Map(categoryRows.map((row) => [row.id, row]));
    for (const row of [draftCategory, appliedCategory]) if (row && !options.has(row.id)) options.set(row.id, row);
    select.replaceChildren();
    const all = element("option", "", "همهٔ دسته‌ها");
    all.value = "";
    select.append(all);
    for (const row of options.values()) {
      const option = element("option", "", row.name);
      option.value = String(row.id);
      select.append(option);
    }
    select.value = draftCategory ? String(draftCategory.id) : "";
    for (const label of categoryLabels) label.node.textContent = categoryName(label.id);
  }

  function categoryControls() {
    if (!categoryPanel) return;
    categoryPanel.setAttribute("aria-busy", String(categories.pending));
    get("category-previous").disabled = needsLogin || categories.pending || categories.previous === null;
    get("category-next").disabled = needsLogin || categories.pending || categories.next === null;
    get("category-retry").disabled = needsLogin || categories.pending;
  }

  function clearCategories() {
    categoryRows = [];
    categories.valid = false;
    categories.previous = categories.next = null;
    get("category-results").replaceChildren();
    get("category-count").textContent = "";
    get("category-count").hidden = true;
    get("category-page").textContent = "";
    rebuildOptions();
  }

  function requireLogin(focusTarget) {
    needsLogin = true;
    ++generation;
    ++categories.generation;
    controller?.abort();
    categories.controller?.abort();
    controller = categories.controller = null;
    pending = categories.pending = false;
    input.value = "";
    draftCategory = appliedCategory = null;
    applied = { search: "", category: null, page: 1 };
    clearResults();
    if (categoryPanel) {
      clearCategories();
      api.clearError(get("category-errors"));
      get("category-retry").hidden = true;
      get("category-status").textContent = "برای مشاهدهٔ دسته‌ها باید دوباره وارد حساب شوید.";
      categoryControls();
    }
    api.clearError(errors);
    retry.hidden = true;
    rebuildOptions();
    status.textContent = "برای مشاهدهٔ اطلاعات خود باید دوباره وارد حساب شوید.";
    controls();
    focusTarget?.focus();
  }

  async function loadCategories(page, focus = false, retrying = false) {
    if (needsLogin || (categories.page === page && (categories.pending || (categories.valid && !retrying)))) return;
    const ticket = ++categories.generation;
    categories.controller?.abort();
    categories.controller = new AbortController();
    categories.page = page;
    categories.pending = true;
    clearCategories();
    api.clearError(get("category-errors"));
    get("category-retry").hidden = true;
    get("category-status").textContent = "در حال دریافت دسته‌ها…";
    categoryControls();
    try {
      const url = new URL(categories.endpoint.href);
      url.searchParams.set("page", String(page));
      const data = await api.request(url.href, { method: "GET", signal: categories.controller.signal });
      if (ticket !== categories.generation || needsLogin) return;
      if (!data || !Array.isArray(data.results) || !Number.isSafeInteger(data.count)
          || data.count < data.results.length || (data.count > 0 && data.results.length === 0)) throw invalid();
      const before = paginationPage(data.previous, {}, categories.endpoint, true);
      const after = paginationPage(data.next, {}, categories.endpoint, true);
      const ids = new Set();
      const rows = data.results.map((row) => {
        if (!row || !positiveInteger(row.id) || ids.has(row.id) || typeof row.name !== "string" || !row.name.trim()) throw invalid();
        ids.add(row.id);
        return { id: row.id, name: row.name };
      });
      categoryRows = rows;
      for (const row of rows) {
        if (draftCategory?.id === row.id) draftCategory = row;
        if (appliedCategory?.id === row.id) appliedCategory = row;
        get("category-results").append(element("li", "list-group-item", row.name));
      }
      categories.previous = before;
      categories.next = after;
      categories.valid = true;
      get("category-count").textContent = `تعداد کل دسته‌ها: ${data.count}`;
      get("category-count").hidden = false;
      get("category-page").textContent = `صفحهٔ ${page}`;
      get("category-status").textContent = rows.length ? "دسته‌های این صفحه دریافت شدند." : "هنوز دسته‌بندی ندارید.";
      rebuildOptions();
    } catch (error) {
      if (ticket !== categories.generation || needsLogin) return;
      if (error.status === 401) requireLogin(focus ? get("category-status") : null);
      else if (error.kind !== "abort") {
        get("category-status").textContent = "بارگذاری دسته‌ها ناموفق بود.";
        api.showError({ message: error.status === 403 ? "اجازهٔ مشاهدهٔ دسته‌ها را ندارید."
          : error.status === 429 ? "درخواست‌ها محدود شده‌اند؛ کمی بعد دوباره تلاش کنید." : error.message }, get("category-errors"));
        get("category-retry").hidden = false;
      }
    } finally {
      if (ticket === categories.generation && !needsLogin) {
        categories.pending = false;
        categories.controller = null;
        categoryControls();
        if (focus) get("category-status").focus();
      }
    }
  }

  select.addEventListener("change", () => {
    draftCategory = select.value === "" ? null : knownCategory(Number(select.value));
    rebuildOptions();
  });
  function endpointURL(value) {
    const url = new URL(value, window.location.href);
    if (url.origin !== window.location.origin || !["http:", "https:"].includes(url.protocol)
        || url.username || url.password || url.hash || url.search) throw invalid("invalid_pagination");
    return url;
  }
  if (categoryPanel) {
    get("category-previous").addEventListener("click", () => {
      if (!get("category-previous").disabled) loadCategories(categories.previous, true);
    });
    get("category-next").addEventListener("click", () => {
      if (!get("category-next").disabled) loadCategories(categories.next, true);
    });
    get("category-retry").addEventListener("click", () => {
      if (!get("category-retry").disabled && !get("category-retry").hidden) loadCategories(categories.page, true, true);
    });
    try {
      categories.endpoint = endpointURL(categoryPanel.dataset.listUrl);
      loadCategories(1);
    } catch (error) {
      api.showError(error, get("category-errors"));
      get("category-status").textContent = "دسته‌ها در دسترس نیستند.";
    }
  }
  try {
    endpoint = endpointURL(panel.dataset.listUrl);
    load(applied);
  } catch (error) {
    api.showError(error, errors);
    status.textContent = "فهرست در دسترس نیست.";
  }
})();
