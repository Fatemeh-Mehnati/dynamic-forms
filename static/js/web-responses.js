(() => {
  "use strict";

  const formSelect = document.getElementById("form-select");
  const submissionsList = document.getElementById("submissions-list");
  const detail = document.getElementById("submission-detail");
  const loading = document.getElementById("submissions-loading");
  const previousButton = document.getElementById("previous-page");
  const nextButton = document.getElementById("next-page");
  const errorRegion = document.getElementById("responses-error");

  if (!formSelect || !submissionsList || !detail) return;

  let currentFormId = null;
  let nextUrl = null;
  let previousUrl = null;
  let listRequestId = 0;
  let detailRequestId = 0;

  function element(tag, text, className = "") {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function showError(error) {
    WebAPI.showError(error, errorRegion);
  }

  function clearError() {
    WebAPI.clearError(errorRegion);
  }

  function formatDate(value) {
    if (!value) return "نامشخص";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString("fa-IR");
  }

  function updatePagination() {
    previousButton.disabled = !previousUrl;
    nextButton.disabled = !nextUrl;
  }

  function resetDetail() {
    detail.replaceChildren(
      element("p", "برای مشاهده جزئیات، یک پاسخ را انتخاب کنید.", "text-muted")
    );
  }

  async function loadForms() {
    formSelect.replaceChildren(element("option", "در حال بارگذاری فرم‌ها..."));
    try {
      const data = await WebAPI.request("/api/v1/forms/");
      const forms = Array.isArray(data) ? data : data?.results;

      formSelect.replaceChildren();
      if (!Array.isArray(forms) || forms.length === 0) {
        formSelect.append(element("option", "فرمی وجود ندارد."));
        formSelect.disabled = true;
        return;
      }

      formSelect.append(element("option", "یک فرم انتخاب کنید"));
      forms.forEach((form) => {
        const option = element("option", form.title || `فرم ${form.id}`);
        option.value = form.id;
        formSelect.append(option);
      });
      formSelect.disabled = false;
    } catch (error) {
      formSelect.replaceChildren(element("option", "بارگذاری فرم‌ها ناموفق بود."));
      showError(error);
    }
  }

  async function loadSubmissions(url) {
    if (!currentFormId) return;

    const requestId = ++listRequestId;
    loading.classList.remove("d-none");
    submissionsList.replaceChildren();
    resetDetail();
    detailRequestId++;
    clearError();

    try {
      const data = await WebAPI.request(url);
      if (requestId !== listRequestId) return;

      const submissions = Array.isArray(data) ? data : data?.results;
      nextUrl = data?.next || null;
      previousUrl = data?.previous || null;
      updatePagination();

      if (!Array.isArray(submissions) || submissions.length === 0) {
        submissionsList.append(
          element("p", "هنوز پاسخی برای این فرم ثبت نشده است.", "text-muted")
        );
        return;
      }

      submissions.forEach((submission) => {
        const button = element(
          "button",
          "",
          "list-group-item list-group-item-action text-start"
        );
        button.type = "button";
        button.append(
          element("strong", `پاسخ شماره ${submission.id}`),
          element(
            "span",
            ` — تاریخ ثبت: ${formatDate(submission.submitted_at)}`,
            "d-block small text-muted mt-1"
          )
        );
        button.addEventListener("click", () => loadDetail(submission.id));
        submissionsList.append(button);
      });
    } catch (error) {
      if (requestId === listRequestId) {
        nextUrl = null;
        previousUrl = null;
        updatePagination();
        showError(error);
      }
    } finally {
      if (requestId === listRequestId) loading.classList.add("d-none");
    }
  }

  async function loadDetail(submissionId) {
    if (!currentFormId) return;

    const requestId = ++detailRequestId;
    detail.replaceChildren(element("p", "در حال بارگذاری جزئیات...", "text-muted"));
    clearError();

    try {
      const data = await WebAPI.request(
        `/api/v1/forms/${encodeURIComponent(currentFormId)}/submissions/${encodeURIComponent(submissionId)}/`
      );
      if (requestId !== detailRequestId) return;

      const content = document.createDocumentFragment();
      const metadata = element("p", `پاسخ شماره ${data.id}`);
      metadata.className = "fw-bold";
      content.append(metadata);
      content.append(
        element("p", `تاریخ ثبت: ${formatDate(data.submitted_at)}`)
      );

      const answers = Array.isArray(data.answers) ? data.answers : [];
      if (answers.length === 0) {
        content.append(element("p", "این پاسخ، جواب ثبت‌شده‌ای ندارد.", "text-muted"));
      }

      answers.forEach((answer, index) => {
        const card = element("div", undefined, "card mb-3");
        const body = element("div", undefined, "card-body");
        body.append(
          element("h3", `سؤال ${index + 1}: ${answer.question_text || "بدون عنوان"}`, "h6")
        );
        body.append(
          element("p", `نوع سؤال: ${answer.type || "نامشخص"}`, "small text-muted")
        );

        if (answer.text_value !== null && answer.text_value !== undefined) {
          body.append(element("p", `پاسخ: ${answer.text_value}`));
        }
        if (answer.number_value !== null && answer.number_value !== undefined) {
          body.append(element("p", `پاسخ عددی: ${answer.number_value}`));
        }

        const choices = Array.isArray(answer.choices) ? answer.choices : [];
        if (choices.length) {
          const list = element("ul", undefined, "mb-0");
          choices.forEach((choice) => list.append(element("li", choice.label)));
          body.append(element("p", "گزینه‌های انتخاب‌شده:", "mb-1"));
          body.append(list);
        }

        card.append(body);
        content.append(card);
      });

      detail.replaceChildren(content);
    } catch (error) {
      if (requestId === detailRequestId) {
        detail.replaceChildren();
        showError(error);
      }
    }
  }

  formSelect.addEventListener("change", () => {
    currentFormId = formSelect.value || null;
    nextUrl = null;
    previousUrl = null;
    updatePagination();
    submissionsList.replaceChildren();
    resetDetail();

    if (currentFormId) {
      loadSubmissions(`/api/v1/forms/${encodeURIComponent(currentFormId)}/submissions/`);
    }
  });

  previousButton.addEventListener("click", () => {
    if (previousUrl) loadSubmissions(previousUrl);
  });

  nextButton.addEventListener("click", () => {
    if (nextUrl) loadSubmissions(nextUrl);
  });

  updatePagination();
  loadForms();
})();
