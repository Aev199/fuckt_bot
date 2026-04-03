const tg = window.Telegram?.WebApp;
const state = {
  initData: "",
  cabinetToken: "",
  currentUser: null,
  canEdit: false,
  categoryTree: [],
  materials: [],
  selectedMaterial: null,
  selectedTopCategoryId: null,
  selectedCategoryId: null,
  activeQuickFilter: "all",
  detailMode: "view",
};

const authStatus = document.getElementById("authStatus");
const accessStatus = document.getElementById("accessStatus");
const globalStatus = document.getElementById("globalStatus");
const refreshButton = document.getElementById("refreshButton");
const categoryTree = document.getElementById("categoryTree");
const rootCategoryForm = document.getElementById("rootCategoryForm");
const rootCategoryName = document.getElementById("rootCategoryName");
const subcategoryForm = document.getElementById("subcategoryForm");
const subcategoryParent = document.getElementById("subcategoryParent");
const subcategoryName = document.getElementById("subcategoryName");
const listContext = document.getElementById("listContext");
const newMaterialButton = document.getElementById("newMaterialButton");
const searchInput = document.getElementById("searchInput");
const quickFilterButtons = [...document.querySelectorAll(".quick-filter")];
const materialsList = document.getElementById("materialsList");
const materialTemplate = document.getElementById("materialTemplate");
const detailEmpty = document.getElementById("detailEmpty");
const detailContent = document.getElementById("detailContent");
const detailTitle = document.getElementById("detailTitle");
const detailMeta = document.getElementById("detailMeta");
const detailSource = document.getElementById("detailSource");
const detailBody = document.getElementById("detailBody");
const detailNotesSection = document.getElementById("detailNotesSection");
const detailNotes = document.getElementById("detailNotes");
const detailTags = document.getElementById("detailTags");
const detailAttachmentsSection = document.getElementById("detailAttachmentsSection");
const detailAttachments = document.getElementById("detailAttachments");
const detailFavoriteButton = document.getElementById("detailFavoriteButton");
const editMaterialButton = document.getElementById("editMaterialButton");
const materialEditor = document.getElementById("materialEditor");
const editorTitle = document.getElementById("editorTitle");
const materialTitleInput = document.getElementById("materialTitle");
const materialContentInput = document.getElementById("materialContent");
const materialSourceUrlInput = document.getElementById("materialSourceUrl");
const materialSourceNameInput = document.getElementById("materialSourceName");
const materialNotesInput = document.getElementById("materialNotes");
const materialTagsInput = document.getElementById("materialTags");
const materialTopCategorySelect = document.getElementById("materialTopCategory");
const materialSubcategorySelect = document.getElementById("materialSubcategory");
const saveMaterialButton = document.getElementById("saveMaterialButton");
const cancelEditButton = document.getElementById("cancelEditButton");
const deleteMaterialButton = document.getElementById("deleteMaterialButton");

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

function getRootCategories() {
  return state.categoryTree;
}

function getCurrentMaterialCategoryId() {
  return Number(materialSubcategorySelect.value || materialTopCategorySelect.value || "") || null;
}

function setQuickFilter(filter) {
  state.activeQuickFilter = filter;
  for (const button of quickFilterButtons) {
    button.classList.toggle("is-active", button.dataset.filter === filter);
  }
}

function updateAccessUi() {
  accessStatus.textContent = state.canEdit
    ? "У тебя есть права редактирования через web."
    : "Режим только для чтения: кабинет работает как справочник.";

  rootCategoryForm.classList.toggle("hidden", !state.canEdit);
  subcategoryForm.classList.toggle("hidden", !state.canEdit);
  newMaterialButton.classList.toggle("hidden", !state.canEdit);
  detailFavoriteButton.classList.toggle("hidden", !state.canEdit);
  editMaterialButton.classList.toggle("hidden", !state.canEdit);
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

  const user = state.initData
    ? await apiRequest("/api/auth/telegram", {
        method: "POST",
        body: JSON.stringify({ init_data: state.initData }),
      })
    : await apiRequest("/api/auth/me");

  state.currentUser = user;
  state.canEdit = Boolean(user.can_edit);
  authStatus.textContent = `Подключено: @${user.username || "user"} (telegram_id: ${user.telegram_id})`;
  updateAccessUi();
}

async function loadCategoryTree() {
  state.categoryTree = await apiRequest("/api/categories/tree");
  renderCategoryTree();
  populateCategoryEditors();
}

async function loadMaterials() {
  const query = new URLSearchParams();

  if (searchInput.value.trim()) {
    query.set("q", searchInput.value.trim());
  }
  if (state.selectedCategoryId) {
    query.set("category_id", String(state.selectedCategoryId));
  } else if (state.selectedTopCategoryId) {
    query.set("top_category_id", String(state.selectedTopCategoryId));
  }
  if (state.activeQuickFilter === "favorites") {
    query.set("favorite", "true");
  }
  if (state.activeQuickFilter === "with-photos") {
    query.set("has_attachments", "true");
  }

  const payload = await apiRequest(`/api/materials?${query.toString()}`);
  state.materials = payload.items;
  renderMaterials();
}

function renderCategoryTree() {
  categoryTree.innerHTML = "";

  const allButton = document.createElement("button");
  allButton.type = "button";
  allButton.className = `tree-button ${!state.selectedTopCategoryId && !state.selectedCategoryId ? "is-active" : ""}`;
  allButton.textContent = "Все материалы";
  allButton.addEventListener("click", async () => {
    state.selectedTopCategoryId = null;
    state.selectedCategoryId = null;
    updateListContext();
    await loadMaterials();
    renderCategoryTree();
  });
  categoryTree.appendChild(allButton);

  for (const root of getRootCategories()) {
    const section = document.createElement("div");
    section.className = "tree-section";

    const rootButton = document.createElement("button");
    rootButton.type = "button";
    rootButton.className = `tree-button ${state.selectedTopCategoryId === root.id && !state.selectedCategoryId ? "is-active" : ""}`;
    rootButton.textContent = `${root.name} (${root.materials_count})`;
    rootButton.addEventListener("click", async () => {
      state.selectedTopCategoryId = root.id;
      state.selectedCategoryId = null;
      updateListContext();
      await loadMaterials();
      renderCategoryTree();
    });
    section.appendChild(rootButton);

    if (root.children?.length) {
      const childList = document.createElement("div");
      childList.className = "tree-children";

      for (const child of root.children) {
        const childButton = document.createElement("button");
        childButton.type = "button";
        childButton.className = `tree-button tree-child ${state.selectedCategoryId === child.id ? "is-active" : ""}`;
        childButton.textContent = `${child.name} (${child.materials_count})`;
        childButton.addEventListener("click", async () => {
          state.selectedTopCategoryId = root.id;
          state.selectedCategoryId = child.id;
          updateListContext();
          await loadMaterials();
          renderCategoryTree();
        });
        childList.appendChild(childButton);
      }

      section.appendChild(childList);
    }

    categoryTree.appendChild(section);
  }
}

function populateCategoryEditors() {
  subcategoryParent.innerHTML = '<option value="">Выбери категорию</option>';
  materialTopCategorySelect.innerHTML = '<option value="">Без категории</option>';
  materialSubcategorySelect.innerHTML = '<option value="">Без подкатегории</option>';

  for (const root of getRootCategories()) {
    const rootOptionForSub = document.createElement("option");
    rootOptionForSub.value = String(root.id);
    rootOptionForSub.textContent = root.name;
    subcategoryParent.appendChild(rootOptionForSub);

    const rootOptionForMaterial = document.createElement("option");
    rootOptionForMaterial.value = String(root.id);
    rootOptionForMaterial.textContent = root.name;
    materialTopCategorySelect.appendChild(rootOptionForMaterial);
  }
}

function populateSubcategoryOptions(topCategoryId, selectedCategoryId = null) {
  materialSubcategorySelect.innerHTML = '<option value="">Без подкатегории</option>';
  const root = getRootCategories().find((item) => item.id === topCategoryId);
  if (!root) {
    return;
  }

  for (const child of root.children || []) {
    const option = document.createElement("option");
    option.value = String(child.id);
    option.textContent = child.name;
    option.selected = selectedCategoryId === child.id;
    materialSubcategorySelect.appendChild(option);
  }
}

function updateListContext() {
  const root = getRootCategories().find((item) => item.id === state.selectedTopCategoryId);
  const child = root?.children?.find((item) => item.id === state.selectedCategoryId);

  if (child) {
    listContext.textContent = `${root.name} → ${child.name}`;
    return;
  }
  if (root) {
    listContext.textContent = root.name;
    return;
  }
  listContext.textContent = "Все материалы";
}

function renderMaterials() {
  materialsList.innerHTML = "";

  if (!state.materials.length) {
    materialsList.innerHTML = '<div class="empty">По текущему фильтру ничего не найдено.</div>';
    return;
  }

  for (const material of state.materials) {
    const node = materialTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".material-title").textContent = material.title;
    node.querySelector(".material-meta").textContent = buildMaterialMeta(material);
    node.querySelector(".material-content").textContent = truncateText(material.content, 160);

    const tagLine = [];
    if (material.tags.length) {
      tagLine.push(`Теги: ${material.tags.join(", ")}`);
    }
    if (material.attachments.length) {
      tagLine.push(`Фото: ${material.attachments.length}`);
    }
    node.querySelector(".material-tags").textContent = tagLine.join(" • ") || "Без тегов и фото";

    const favoriteButton = node.querySelector(".favorite-button");
    favoriteButton.textContent = material.is_favorite ? "★" : "☆";
    favoriteButton.classList.toggle("hidden", !state.canEdit);
    favoriteButton.addEventListener("click", async () => {
      try {
        await apiRequest(`/api/materials/${material.id}/favorite`, { method: "POST" });
        setGlobalStatus("Избранное обновлено.", "success");
        await loadMaterials();
        if (state.selectedMaterial?.id === material.id) {
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

async function openMaterial(materialId) {
  try {
    clearGlobalStatus();
    state.selectedMaterial = await apiRequest(`/api/materials/${materialId}`);
    state.detailMode = "view";
    renderDetailPane();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось открыть материал.", "error");
  }
}

function renderDetailPane() {
  const material = state.selectedMaterial;
  const showView = Boolean(material) && state.detailMode === "view";
  const showEditor = state.detailMode === "edit" && state.canEdit;

  detailEmpty.classList.toggle("hidden", Boolean(material));
  detailContent.classList.toggle("hidden", !showView);
  materialEditor.classList.toggle("hidden", !showEditor);

  if (!material) {
    detailEmpty.textContent = "Выбери материал из списка, чтобы посмотреть детали.";
    return;
  }

  if (showView) {
    detailTitle.textContent = material.title;
    detailMeta.textContent = buildMaterialMeta(material);
    detailSource.innerHTML = material.source_url
      ? `<a href="${escapeAttribute(material.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(material.source_name || material.source_url)}</a>`
      : escapeHtml(material.source_name || "Источник не указан");
    detailBody.textContent = material.content;
    detailTags.textContent = material.tags.length ? material.tags.join(", ") : "Теги не указаны";

    detailNotesSection.classList.toggle("hidden", !material.notes);
    detailNotes.textContent = material.notes || "";

    detailAttachmentsSection.classList.toggle("hidden", !material.attachments.length);
    detailAttachments.innerHTML = material.attachments
      .map(
        (attachment) => `
          <figure class="attachment-card">
            <img
              src="${escapeAttribute(getAttachmentUrl(material.id, attachment.id))}"
              alt="${escapeAttribute(attachment.caption || material.title)}"
              class="attachment-image"
            />
            <figcaption>${escapeHtml(attachment.caption || attachment.file_name || "Фото")}</figcaption>
            ${
              state.canEdit
                ? `<button class="ghost-button danger-button delete-attachment-button" type="button" data-attachment-id="${attachment.id}">Удалить фото</button>`
                : ""
            }
          </figure>
        `,
      )
      .join("");

    for (const button of detailAttachments.querySelectorAll(".delete-attachment-button")) {
      button.addEventListener("click", async () => {
        const attachmentId = Number(button.dataset.attachmentId);
        await deleteAttachment(material.id, attachmentId);
      });
    }

    detailFavoriteButton.textContent = material.is_favorite ? "Убрать из избранного" : "В избранное";
    detailFavoriteButton.classList.toggle("hidden", !state.canEdit);
    editMaterialButton.classList.toggle("hidden", !state.canEdit);
  }

  if (showEditor) {
    fillEditorForm(material);
  }
}

function fillEditorForm(material) {
  editorTitle.textContent = material?.id ? "Редактирование материала" : "Новый материал";
  materialTitleInput.value = material?.title || "";
  materialContentInput.value = material?.content || "";
  materialSourceUrlInput.value = material?.source_url || "";
  materialSourceNameInput.value = material?.source_name || "";
  materialNotesInput.value = material?.notes || "";
  materialTagsInput.value = material?.tags?.join(", ") || "";

  materialTopCategorySelect.value = material?.top_category_id ? String(material.top_category_id) : "";
  populateSubcategoryOptions(material?.top_category_id || null, material?.subcategory_id || null);
  if (!material?.subcategory_id) {
    materialSubcategorySelect.value = "";
  }

  deleteMaterialButton.classList.toggle("hidden", !material?.id);
}

function buildMaterialMeta(material) {
  const parts = [];
  if (material.top_category_name && material.subcategory_name) {
    parts.push(`${material.top_category_name} → ${material.subcategory_name}`);
  } else if (material.top_category_name) {
    parts.push(material.top_category_name);
  } else if (material.category_name) {
    parts.push(material.category_name);
  } else {
    parts.push("Без категории");
  }
  if (material.source_name) {
    parts.push(material.source_name);
  }
  parts.push(new Date(material.updated_at).toLocaleDateString("ru-RU"));
  return parts.join(" • ");
}

function beginCreateMaterial() {
  if (!state.canEdit) {
    setGlobalStatus("У тебя нет прав на создание материалов через web.", "error");
    return;
  }
  state.selectedMaterial = null;
  state.detailMode = "edit";
  detailEmpty.classList.add("hidden");
  detailContent.classList.add("hidden");
  materialEditor.classList.remove("hidden");
  fillEditorForm(null);
}

function beginEditMaterial() {
  if (!state.selectedMaterial || !state.canEdit) {
    return;
  }
  state.detailMode = "edit";
  renderDetailPane();
}

function cancelEdit() {
  state.detailMode = "view";
  renderDetailPane();
}

async function saveMaterial(event) {
  event.preventDefault();
  if (!state.canEdit) {
    setGlobalStatus("У тебя нет прав на редактирование через web.", "error");
    return;
  }

  const payload = {
    title: materialTitleInput.value.trim(),
    content: materialContentInput.value.trim(),
    source_url: materialSourceUrlInput.value.trim() || null,
    source_name: materialSourceNameInput.value.trim() || null,
    notes: materialNotesInput.value.trim() || null,
    category_id: getCurrentMaterialCategoryId(),
    tags: materialTagsInput.value
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
    let material;
    if (state.selectedMaterial?.id) {
      material = await apiRequest(`/api/materials/${state.selectedMaterial.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    } else {
      material = await apiRequest("/api/materials", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    setGlobalStatus("Изменения сохранены.", "success");
    await loadMaterials();
    state.selectedMaterial = material;
    state.detailMode = "view";
    renderDetailPane();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось сохранить материал.", "error");
  } finally {
    saveMaterialButton.disabled = false;
    saveMaterialButton.textContent = "Сохранить";
  }
}

async function deleteSelectedMaterial() {
  if (!state.selectedMaterial?.id || !state.canEdit) {
    return;
  }
  try {
    await apiRequest(`/api/materials/${state.selectedMaterial.id}`, { method: "DELETE" });
    setGlobalStatus("Материал удалён.", "success");
    state.selectedMaterial = null;
    state.detailMode = "view";
    renderDetailPane();
    await loadMaterials();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось удалить материал.", "error");
  }
}

async function deleteAttachment(materialId, attachmentId) {
  if (!state.canEdit) {
    return;
  }
  try {
    await apiRequest(`/api/materials/${materialId}/attachments/${attachmentId}`, { method: "DELETE" });
    setGlobalStatus("Фото удалено.", "success");
    await openMaterial(materialId);
    await loadMaterials();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось удалить фото.", "error");
  }
}

async function createRootCategory(event) {
  event.preventDefault();
  if (!state.canEdit) {
    return;
  }
  const name = rootCategoryName.value.trim();
  if (!name) {
    return;
  }
  try {
    await apiRequest("/api/categories", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    rootCategoryName.value = "";
    setGlobalStatus("Категория создана.", "success");
    await loadCategoryTree();
    await loadMaterials();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось создать категорию.", "error");
  }
}

async function createSubcategory(event) {
  event.preventDefault();
  if (!state.canEdit) {
    return;
  }
  const parentId = Number(subcategoryParent.value || "");
  const name = subcategoryName.value.trim();
  if (!parentId || !name) {
    setGlobalStatus("Выбери категорию и укажи имя подкатегории.", "error");
    return;
  }
  try {
    await apiRequest("/api/categories", {
      method: "POST",
      body: JSON.stringify({ name, parent_id: parentId }),
    });
    subcategoryName.value = "";
    setGlobalStatus("Подкатегория создана.", "success");
    await loadCategoryTree();
    await loadMaterials();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось создать подкатегорию.", "error");
  }
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength).trim()}…`;
}

function escapeHtml(value) {
  return String(value)
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
    await loadCategoryTree();
    updateListContext();
    await loadMaterials();

    const requestedMaterialId = getRequestedMaterialId();
    if (requestedMaterialId) {
      await openMaterial(requestedMaterialId);
    } else {
      renderDetailPane();
    }
  } catch (error) {
    authStatus.textContent = error.message || "Не удалось загрузить данные.";
    setGlobalStatus(error.message || "Не удалось открыть кабинет.", "error");
  }
}

refreshButton.addEventListener("click", async () => {
  clearGlobalStatus();
  await loadCategoryTree();
  updateListContext();
  await loadMaterials();
  if (state.selectedMaterial?.id) {
    await openMaterial(state.selectedMaterial.id);
  }
});
rootCategoryForm.addEventListener("submit", createRootCategory);
subcategoryForm.addEventListener("submit", createSubcategory);
newMaterialButton.addEventListener("click", beginCreateMaterial);
editMaterialButton.addEventListener("click", beginEditMaterial);
cancelEditButton.addEventListener("click", cancelEdit);
materialEditor.addEventListener("submit", saveMaterial);
deleteMaterialButton.addEventListener("click", deleteSelectedMaterial);
materialTopCategorySelect.addEventListener("change", () => {
  const topId = Number(materialTopCategorySelect.value || "") || null;
  populateSubcategoryOptions(topId, null);
});
searchInput.addEventListener("input", loadMaterials);
detailFavoriteButton.addEventListener("click", async () => {
  if (!state.selectedMaterial?.id || !state.canEdit) {
    return;
  }
  try {
    const material = await apiRequest(`/api/materials/${state.selectedMaterial.id}/favorite`, { method: "POST" });
    state.selectedMaterial = material;
    setGlobalStatus("Избранное обновлено.", "success");
    renderDetailPane();
    await loadMaterials();
  } catch (error) {
    setGlobalStatus(error.message || "Не удалось обновить избранное.", "error");
  }
});
for (const button of quickFilterButtons) {
  button.addEventListener("click", async () => {
    setQuickFilter(button.dataset.filter);
    await loadMaterials();
  });
}

bootstrap();
