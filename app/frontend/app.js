const tg = window.Telegram?.WebApp;
const state = {
  initData: "",
  cabinetToken: "",
  categories: [],
  materials: [],
  selectedMaterialId: null,
};

const authStatus = document.getElementById("authStatus");
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

function getRequestedView() {
  return new URLSearchParams(window.location.search).get("view");
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

  authStatus.textContent = `Подключено: @${user.username || "user"} (telegram_id: ${user.telegram_id})`;
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
    materialsList.innerHTML = '<div class="empty">Материалов пока нет. Добавь первый.</div>';
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

    const favoriteButton = node.querySelector(".favorite-button");
    favoriteButton.textContent = material.is_favorite ? "★" : "☆";
    favoriteButton.addEventListener("click", async () => {
      await apiRequest(`/api/materials/${material.id}/favorite`, { method: "POST" });
      await loadMaterials();
      if (state.selectedMaterialId === material.id) {
        await openMaterial(material.id);
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
  `;
}

function startCreateMode() {
  state.selectedMaterialId = null;
  materialForm.reset();
  materialFormTitle.textContent = "Добавить материал";
  materialFormSubtitle.textContent = "Сохрани заметку, статью или выдержку.";
  saveMaterialButton.textContent = "Сохранить материал";
  deleteMaterialButton.classList.add("hidden");
  renderMaterialDetail(null);
}

function startEditMode(material) {
  state.selectedMaterialId = material.id;
  materialFormTitle.textContent = "Редактировать материал";
  materialFormSubtitle.textContent = "Измени содержимое, теги, категорию или источник.";
  saveMaterialButton.textContent = "Сохранить изменения";
  deleteMaterialButton.classList.remove("hidden");

  materialTitleInput.value = material.title || "";
  materialContentInput.value = material.content || "";
  materialSourceUrlInput.value = material.source_url || "";
  materialSourceNameInput.value = material.source_name || "";
  materialNotesInput.value = material.notes || "";
  materialTagsInput.value = material.tags.join(", ");
  materialCategorySelect.value = material.category_id ? String(material.category_id) : "";

  renderMaterialDetail(material);
  materialForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openMaterial(materialId) {
  const material = await apiRequest(`/api/materials/${materialId}`);
  startEditMode(material);
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
  const name = categoryNameInput.value.trim();
  if (!name) {
    return;
  }

  await apiRequest("/api/categories", {
    method: "POST",
    body: JSON.stringify({ name }),
  });

  categoryForm.reset();
  await loadCategories();
}

async function saveMaterial(event) {
  event.preventDefault();
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

  if (state.selectedMaterialId) {
    await apiRequest(`/api/materials/${state.selectedMaterialId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  } else {
    await apiRequest("/api/materials", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  await loadMaterials();
  await loadCategories();

  if (state.selectedMaterialId) {
    await openMaterial(state.selectedMaterialId);
  } else {
    startCreateMode();
  }
}

async function deleteSelectedMaterial() {
  if (!state.selectedMaterialId) {
    return;
  }

  await apiRequest(`/api/materials/${state.selectedMaterialId}`, {
    method: "DELETE",
  });

  await loadMaterials();
  await loadCategories();
  startCreateMode();
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
      return;
    }

    if (getRequestedView() === "add") {
      materialTitleInput.focus();
    }
  } catch (error) {
    authStatus.textContent = error.message || "Не удалось загрузить данные.";
  }
}

categoryForm.addEventListener("submit", createCategory);
materialForm.addEventListener("submit", saveMaterial);
deleteMaterialButton.addEventListener("click", deleteSelectedMaterial);
resetMaterialButton.addEventListener("click", startCreateMode);
refreshButton.addEventListener("click", async () => {
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
