const tg = window.Telegram?.WebApp;
const state = {
  initData: "",
  cabinetToken: "",
  categories: [],
  materials: [],
  selectedMaterialId: null,
  currentUser: null,
  canEdit: false,
};

const authStatus = document.getElementById("authStatus");
const accessStatus = document.getElementById("accessStatus");
const globalStatus = document.getElementById("globalStatus");
const refreshButton = document.getElementById("refreshButton");
const categoryForm = document.getElementById("categoryForm");
const categoryNameInput = document.getElementById("categoryName");
const categoriesList = document.getElementById("categoriesList");
const materialForm = document.getElementById("materialForm");
const materialFormTitle = document.getElementById("materialFormTitle");
const materialFormSubtitle = document.getElementById("materialFormSubtitle");
const materialTitleInput = document.getElementById("materialTitle");
const materialContentInput = document.getElementById("materialContent");
const materialSourceUrlInput = document.getElementById("materialSourceUrl");
const materialSourceNameInput = document.getElementById("materialSourceName");
const materialNotesInput = document.getElementById("materialNotes");
const materialTagsInput = document.getElementById("materialTags");
const materialCategorySelect = document.getElementById("materialCategory");
const saveMaterialButton = document.getElementById("saveMaterialButton");
const deleteMaterialButton = document.getElementById("deleteMaterialButton");
const resetMaterialButton = document.getElementById("resetMaterialButton");
const materialDetail = document.getElementById("materialDetail");
const searchCategorySelect = document.getElementById("searchCategory");
const materialsList = document.getElementById("materialsList");
const searchInput = document.getElementById("searchInput");
const favoriteOnlyCheckbox = document.getElementById("favoriteOnly");
const materialTemplate = document.getElementById("materialTemplate");

function getInitData() {
  if (tg?.initData) {
    return tg.initData;
  }
  return new URLSearchParams(window.location.search).get("initData") || "";
}

function getRequestedMaterialId() {
  const rawValue = new URLSearchParams(window.location.search).get("material_id");
  return rawValue ? Number(rawValue) : null;
}

function getCabinetToken() {
  const params = new URLSearchParams(window.location.search);
  const tokenFromQuery = params.get("token");
  if (tokenFromQuery) {
    window.localStorage.setItem("webCabinetToken", tokenFromQuery);
    return tokenFromQuery;
  }
  return window.localStorage.getItem("webCabinetToken") || "";
}

function getAttachmentUrl(materialId, attachmentId) {
  const params = new URLSearchParams();
  if (state.cabinetToken) {
    params.set("token", state.cabinetToken);
  } else if (state.initData) {
    params.set("init_data", state.initData);
  }
  return `/api/materials/${materialId}/attachments/${attachmentId}/content?${params.toString()}`;
}

function setGlobalStatus(message, type = "info") {
  globalStatus.textContent = message;
  globalStatus.className = `status-banner ${type}`;
}

function clearGlobalStatus() {
  globalStatus.textContent = "";
  globalStatus.className = "status-banner hidden";
}

function updateEditAccessUi() {
  const formControls = materialForm.querySelectorAll("input, textarea, select, button");
  const categoryControls = categoryForm.querySelectorAll("input, button");

  for (const element of formControls) {
    element.disabled = !state.canEdit;
  }
  for (const element of categoryControls) {
    element.disabled = !state.canEdit;
  }

  saveMaterialButton.classList.toggle("hidden", !state.canEdit);
  deleteMaterialButton.classList.toggle("hidden", !state.canEdit || !state.selectedMaterialId);
  resetMaterialButton.disabled = !state.canEdit;

  accessStatus.textContent = state.canEdit
    ? "У тебя есть права редактирования через web."
    : "Режим только для чтения: смотреть можно, изменять через web нельзя.";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": state.initData,
      "X-Web-Cabinet-Token": state.cabinetToken,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "API error");
  }

  return response.status === 204 ? null : response.json();
}

async function authenticate() {
  state.initData = getInitData();
  state.cabinetToken = getCabinetToken();

  if (!state.initData && !state.cabinetToken) {
    authStatus.textContent = "Для web-кабинета нужен токен доступа или запуск из Telegram.";
    return;
  }

  let user;
  if (state.initData) {
    user = await apiRequest("/api/auth/telegram", {
      method: "POST",
      body: JSON.stringify({ init_data: state.initData }),
    });
  } else {
    user = await apiRequest("/api/auth/me");
  }

  state.currentUser = user;
  state.canEdit = Boolean(user.can_edit);
  authStatus.textContent = `Подключено: @${user.username || "user"} (telegram_id: ${user.telegram_id})`;
  updateEditAccessUi();
}

function renderCategories() {
  categoriesList.innerHTML = "";
  materialCategorySelect.innerHTML = '<option value="">Без категории</option>';
  searchCategorySelect.innerHTML = '<option value="">Все категории</option>';

  if (!state.categories.length) {
    categoriesList.innerHTML = '<div class="empty">Категорий пока нет.</div>';
    return;
  }

  for (const category of state.categories) {
    const item = document.createElement("div");
    item.className = "category-item";
    item.innerHTML = `<strong>${escapeHtml(category.name)}</strong><span>${category.materials_count} материалов</span>`;
    categoriesList.appendChild(item);

    const materialOption = document.createElement("option");
    materialOption.value = String(category.id);
    materialOption.textContent = category.name;
    materialCategorySelect.appendChild(materialOption);

    const searchOption = document.createElement("option");
    searchOption.value = String(category.id);
    searchOption.textContent = category.name;
    searchCategorySelect.appendChild(searchOption);
  }
}

function renderMaterials() {
  materialsList.innerHTML = "";

  if (!state.materials.length) {
    materialsList.innerHTML = '<div class="empty">Материалов пока нет.</div>';
    return;
  }

  for (const material of state.materials) {
    const node = materialTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".material-title").textContent = material.title;
    node.querySelector(".material-meta").textContent =
      `${material.category_name || "Без категории"}${material.source_name ? ` • ${material.source_name}` : ""}`;
    node.querySelector(".material-content").textContent = truncateText(material.content, 180);
    node.querySelector(".material-tags").textContent =
      material.tags.length ? `Теги: ${material.tags.join(", ")}` : "Теги не указаны";

    if (material.attachments?.length) {
      node.querySelector(".material-tags").textContent += ` • Фото: ${material.attachments.length}`;
    }

    const favoriteButton = node.querySelector(".favorite-button");
    favoriteButton.textContent = material.is_favorite ? "★" : "☆";
    favoriteButton.disabled = !state.canEdit;
    favoriteButton.classList.toggle("hidden", !state.canEdit);
    favoriteButton.addEventListener("click", async () => {
      try {
        clearGlobalStatus();
        await apiRequest(`/api/materials/${material.id}/favorite`, { method: "POST" });
        setGlobalStatus("Избранное обновлено.", "success");
        await loadMaterials();
        if (state.selectedMaterialId === material.id) {
          await openMaterial(material.id);
        }
      } catch (error) {
        setGlobalStatus(error.message || "Не удалось обновить избранное.", "error");
      }
    });

    node.querySelector(".open-button").addEventListener("click", async () => {
      await openMaterial(material.id);
    });

    materialsList.appendChild(node);
  }
}

function renderMaterialDetail(material) {
  if (!material) {
    materialDetail.innerHTML = "Выбери материал из списка, чтобы посмотреть детали.";
    materialDetail.className = "detail-empty";
    return;
  }

  const attachmentsHtml = (material.attachments || []).length
    ? `
      <div class="detail-label">Вложения</div>
      <div class="attachment-grid">
        ${material.attachments
          .map(
            (attachment) => `
              <figure class="attachment-card" data-attachment-id="${attachment.id}">
                <img
                  src="${escapeAttribute(getAttachmentUrl(material.id, attachment.id))}"
                  alt="${escapeAttribute(attachment.caption || material.title)}"
                  class="attachment-image"
                />
                <figcaption>${escapeHtml(attachment.caption || attachment.file_name || "Фото")}</figcaption>
                ${
                  state.canEdit
                    ? `<button class="ghost-button danger-button delete-attachment-button" type="button" data-attachment-id="${attachment.id}">
                        Удалить фото
                      </button>`
                    : ""
                }
              </figure>
            `,
          )
          .join("")}
      </div>
    `
    : "";

  materialDetail.className = "detail-card";
  materialDetail.innerHTML = `
    <div class="detail-label">Заголовок</div>
    <h3>${escapeHtml(material.title)}</h3>
    <div class="detail-label">Категория и источник</div>
    <p class="material-meta">${escapeHtml(material.category_name || "Без категории")}${material.source_name ? ` • ${escapeHtml(material.source_name)}` : ""}</p>
    ${material.source_url ? `<p><a href="${escapeAttribute(material.source_url)}" target="_blank" rel="noreferrer">Открыть источник</a></p>` : ""}
    <div class="detail-label">Содержимое</div>
    <p class="detail-content">${escapeHtml(material.content)}</p>
    ${material.notes ? `<div class="detail-label">Заметки</div><p class="detail-notes">${escapeHtml(material.notes)}</p>` : ""}
    <div class="detail-label">Теги</div>
    <p class="material-tags">${material.tags.length ? escapeHtml(material.tags.join(", ")) : "Теги не указаны"}</p>
    ${attachmentsHtml}
  `;

  for (const button of materialDetail.querySelectorAll(".delete-attachment-button")) {
    button.addEventListener("click", async () => {
      const attachmentId = Number(button.dataset.attachmentId);
      await deleteAttachment(material.id, attachmentId);
    });
  }
}

function startCreateMode() {
  state.selectedMaterialId = null;
  materialForm.reset();
  materialFormTitle.textContent = "Добавить материал";
  materialFormSubtitle.textContent = "Сохрани заметку, статью или выдержку.";
  saveMaterialButton.textContent = "Сохранить материал";
  deleteMaterialButton.classList.add("hidden");
  renderMaterialDetail(null);
  updateEditAccessUi();
}

function startEditMode(material) {
  state.selectedMaterialId = material.id;
  materialFormTitle.textContent = "Редактировать материал";
  materialFormSubtitle.textContent = "Измени содержимое, теги, категорию или источник.";
  saveMaterialButton.textContent = "Сохранить изменения";
  deleteMaterialButton.classList.toggle("hidden", !state.canEdit);

  materialTitleInput.value = material.title || "";
  materialContentInput.value = material.content || "";
  materialSourceUrlInput.value = material.source_url || "";
  materialSourceNameInput.value = material.source_name || "";
  materialNotesInput.value = material.notes || "";
  materialTagsInput.value = material.tags.join(", ");
  materialCategorySelect.value = material.category_id ? String(material.category_id) : "";

  renderMaterialDetail(material);
  updateEditAccessUi();
  materialForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openMaterial(materialId) {
  try {
    clearGlobalStatus();
    const material = await apiRequest(`/api/materials/${materialId}`);
    startEditMode(material);
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось открыть материал.", "error");
  }
}

async function loadCategories() {
  state.categories = await apiRequest("/api/categories");
  renderCategories();
}

async function loadMaterials() {
  const query = new URLSearchParams();
  if (searchInput.value.trim()) {
    query.set("q", searchInput.value.trim());
  }
  if (searchCategorySelect.value) {
    query.set("category_id", searchCategorySelect.value);
  }
  if (favoriteOnlyCheckbox.checked) {
    query.set("favorite", "true");
  }

  const payload = await apiRequest(`/api/materials?${query.toString()}`);
  state.materials = payload.items;
  renderMaterials();
}

async function createCategory(event) {
  event.preventDefault();
  if (!state.canEdit) {
    setGlobalStatus("У тебя нет прав на создание категорий через web.", "error");
    return;
  }

  const name = categoryNameInput.value.trim();
  if (!name) {
    return;
  }

  try {
    clearGlobalStatus();
    await apiRequest("/api/categories", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    categoryForm.reset();
    setGlobalStatus("Категория создана.", "success");
    await loadCategories();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось создать категорию.", "error");
  }
}

async function saveMaterial(event) {
  event.preventDefault();
  if (!state.canEdit) {
    setGlobalStatus("У тебя нет прав на редактирование через web.", "error");
    return;
  }

  const formData = new FormData(materialForm);
  const payload = {
    title: String(formData.get("title") || "").trim(),
    content: String(formData.get("content") || "").trim(),
    source_url: String(formData.get("source_url") || "").trim() || null,
    source_name: String(formData.get("source_name") || "").trim() || null,
    notes: String(formData.get("notes") || "").trim() || null,
    category_id: formData.get("category_id") ? Number(formData.get("category_id")) : null,
    tags: String(formData.get("tags") || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };

  if (!payload.title || !payload.content) {
    setGlobalStatus("Заголовок и основной текст обязательны.", "error");
    return;
  }

  saveMaterialButton.disabled = true;
  saveMaterialButton.textContent = "Сохраняю...";

  try {
    clearGlobalStatus();
    let result;
    if (state.selectedMaterialId) {
      result = await apiRequest(`/api/materials/${state.selectedMaterialId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    } else {
      result = await apiRequest("/api/materials", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }

    setGlobalStatus("Изменения сохранены.", "success");
    await loadMaterials();
    await loadCategories();

    if (result?.id) {
      await openMaterial(result.id);
    } else if (state.selectedMaterialId) {
      await openMaterial(state.selectedMaterialId);
    } else {
      startCreateMode();
    }
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось сохранить изменения.", "error");
  } finally {
    saveMaterialButton.disabled = !state.canEdit;
    saveMaterialButton.textContent = state.selectedMaterialId ? "Сохранить изменения" : "Сохранить материал";
  }
}

async function deleteSelectedMaterial() {
  if (!state.selectedMaterialId || !state.canEdit) {
    return;
  }

  try {
    clearGlobalStatus();
    await apiRequest(`/api/materials/${state.selectedMaterialId}`, {
      method: "DELETE",
    });
    setGlobalStatus("Материал удалён.", "success");
    await loadMaterials();
    await loadCategories();
    startCreateMode();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось удалить материал.", "error");
  }
}

async function deleteAttachment(materialId, attachmentId) {
  if (!state.canEdit) {
    setGlobalStatus("У тебя нет прав на удаление вложений.", "error");
    return;
  }

  try {
    clearGlobalStatus();
    await apiRequest(`/api/materials/${materialId}/attachments/${attachmentId}`, {
      method: "DELETE",
    });
    setGlobalStatus("Фото удалено.", "success");
    await loadMaterials();
    await loadCategories();
    await openMaterial(materialId);
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось удалить фото.", "error");
  }
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength).trim()}…`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

async function bootstrap() {
  try {
    tg?.ready();
    tg?.expand();
    await authenticate();
    await loadCategories();
    await loadMaterials();
    startCreateMode();

    const requestedMaterialId = getRequestedMaterialId();
    if (requestedMaterialId) {
      await openMaterial(requestedMaterialId);
    }
  } catch (error) {
    authStatus.textContent = error.message || "Не удалось загрузить данные.";
    setGlobalStatus(error.message || "Не удалось загрузить кабинет.", "error");
  }
}

categoryForm.addEventListener("submit", createCategory);
materialForm.addEventListener("submit", saveMaterial);
deleteMaterialButton.addEventListener("click", deleteSelectedMaterial);
resetMaterialButton.addEventListener("click", startCreateMode);
refreshButton.addEventListener("click", async () => {
  clearGlobalStatus();
  await loadCategories();
  await loadMaterials();
  if (state.selectedMaterialId) {
    await openMaterial(state.selectedMaterialId);
  }
});
searchInput.addEventListener("input", loadMaterials);
searchCategorySelect.addEventListener("change", loadMaterials);
favoriteOnlyCheckbox.addEventListener("change", loadMaterials);

bootstrap();
