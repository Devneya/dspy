function handleAutoFocus() {
  document
    .querySelectorAll('.column-name-input[data-auto-focus="true"]')
    .forEach((input) => {
      setTimeout(() => {
        input.focus();
        input.select();
        if (input.dataset.tableType === "inputs") showColumnSuggestions(input);
        delete input.dataset.autoFocus;
      }, 10);
    });
}

// =================== ADD BLOCK ===================
function toggleAddBlockMenu() {
  const menu = document.getElementById("add-block-menu");
  if (menu) {
    menu.classList.toggle("hidden");
  }
}

document.addEventListener("click", (e) => {
  const menu = document.getElementById("add-block-menu");
  const btn = e.target.closest('[onclick="toggleAddBlockMenu()"]');
  if (menu && !menu.contains(e.target) && !btn) {
    menu.classList.add("hidden");
  }
});

// ================= TABS =================
let tabsSortable = null;

function initTabsSortable() {
  const container = document.getElementById("tabs-container");
  if (!container) return;
  if (tabsSortable) tabsSortable.destroy();

  tabsSortable = new Sortable(container, {
    animation: 200,
    handle: ".cursor-grab",
    draggable: "[data-block-id]",
    ghostClass: "opacity-50",
    onEnd: () => {
      const order = Array.from(
        container.querySelectorAll("[data-block-id]"),
      ).map((tab) => tab.dataset.blockId);
      htmx.ajax("POST", "/reorder-tabs", {
        target: "#main-container",
        swap: "outerHTML",
        values: { order: JSON.stringify(order) },
      });
    },
  });
}

// ================= COLUMN SUGGESTIONS =================
function getSuggestionsDiv(input) {
  return input.closest(".relative")?.querySelector(".column-suggestions");
}

function parseJsonData(input, key) {
  try {
    return JSON.parse(input.dataset[key] || "[]");
  } catch {
    return [];
  }
}

function renderSuggestions(suggestionsDiv, columns, input) {
  suggestionsDiv.innerHTML = "";
  columns.forEach((col) => {
    const option = document.createElement("div");
    option.className = "px-3 py-2 text-sm hover:bg-muted cursor-pointer";
    option.textContent = col;
    option.onmousedown = (e) => {
      e.preventDefault();
      input.value = col;
      validateAndSaveColumn(input);
      hideColumnSuggestions(input);
    };
    suggestionsDiv.appendChild(option);
  });
  suggestionsDiv.classList.remove("hidden");
}

function showColumnSuggestions(input) {
  if (input.dataset.tableType !== "inputs") return;
  const available = parseJsonData(input, "availableColumns");
  if (!available.length) return;

  const suggestionsDiv = getSuggestionsDiv(input);
  if (!suggestionsDiv) return;

  const filtered = available.filter((col) =>
    col.toLowerCase().includes(input.value.toLowerCase()),
  );
  filtered.length
    ? renderSuggestions(suggestionsDiv, filtered, input)
    : suggestionsDiv.classList.add("hidden");
}

function filterColumnSuggestions(input) {
  if (input.dataset.tableType !== "inputs") return;
  const available = parseJsonData(input, "availableColumns");
  const suggestionsDiv = getSuggestionsDiv(input);
  if (!suggestionsDiv) return;

  const filtered = available.filter((col) =>
    col.toLowerCase().includes(input.value.toLowerCase()),
  );
  filtered.length
    ? renderSuggestions(suggestionsDiv, filtered, input)
    : suggestionsDiv.classList.add("hidden");
}

function hideColumnSuggestions(input) {
  setTimeout(() => getSuggestionsDiv(input)?.classList.add("hidden"), 200);
}

// ==================== COLUMN VALIDATION ====================
function getErrorDiv(input) {
  return input.closest(".relative")?.querySelector(".column-error");
}

function checkColumnName(input) {
  const value = input.value.trim();
  if (input.dataset.tableType !== "outputs") return;

  const usedColumns = parseJsonData(input, "usedColumns");
  const originalValue = input.dataset.originalValue || "";
  const errorDiv = getErrorDiv(input);
  if (!errorDiv) return;

  const columnsToCheck = usedColumns.filter((col) => col !== originalValue);
  if (value && columnsToCheck.includes(value)) {
    input.classList.add("border-destructive");
    errorDiv.textContent = `"${value}" already exists in this or previous tab(s)`;
    errorDiv.classList.remove("hidden");
  } else {
    input.classList.remove("border-destructive");
    errorDiv.classList.add("hidden");
  }
}

function validateAndSaveColumn(input) {
  const value = input.value.trim();
  const {
    tableType,
    originalValue,
    isNew,
    blockId,
    columnIndex: colIndex,
  } = input.dataset;
  const usedColumns = parseJsonData(input, "usedColumns");

  hideColumnSuggestions(input);
  const errorDiv = getErrorDiv(input);

  if (tableType === "outputs") {
    const columnsToCheck = usedColumns.filter((col) => col !== originalValue);
    if (value && columnsToCheck.includes(value)) {
      input.value = originalValue;
      input.classList.add("border-destructive");
      if (errorDiv) {
        errorDiv.textContent = `Column name "${value}" already exists`;
        errorDiv.classList.remove("hidden");
        setTimeout(() => errorDiv.classList.add("hidden"), 3000);
      }
      return;
    }
  }

  if (!value && isNew === "true") {
    htmx.ajax(
      "DELETE",
      `/block/${blockId}/delete-column/${tableType}/${colIndex}`,
      { target: "#main-container", swap: "outerHTML" },
    );
    return;
  }

  if (!value && isNew !== "true") {
    input.value = originalValue;
    return;
  }

  if (errorDiv) errorDiv.classList.add("hidden");
  input.classList.remove("border-destructive");

  htmx.ajax("POST", "/save-column", {
    swap: "none",
    values: {
      block_id: blockId,
      table_type: tableType,
      col_index: colIndex,
      value,
      original_value: originalValue,
      is_new: isNew,
    },
  });
}

// =================== SAVE ===================
function saveCell(input, rowId, colName) {
  htmx.ajax("POST", "/save-cell", {
    swap: "none",
    values: { row_id: rowId, col_name: colName, value: input.value },
  });
}

function saveParam(input, blockId, paramName) {
  htmx.ajax("POST", "/save-param", {
    swap: "none",
    values: { block_id: blockId, param_name: paramName, value: input.value },
  });
}

// =================== FILE UPLOAD ===================

function uploadInferenceFile(input) {
  const file = input.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  fetch("/inference/upload", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.text())
    .then((html) => {
      const target = document.querySelector(input.dataset.target);
      if (target) target.outerHTML = html;
    })
    .catch((err) => console.error("Upload failed:", err));

  input.value = "";
}

// =================== THEME ===================
function initTheme() {
  const theme = localStorage.getItem("dspy_theme");
  document.documentElement.classList.toggle("dark", theme === "dark");
}

function setupThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn || btn._hasListener) return;
  btn.onclick = () => {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("dspy_theme", isDark ? "dark" : "light");
  };
  btn._hasListener = true;
}

// =================== INIT ===================
initTheme();
setupThemeToggle();

document.body.addEventListener("htmx:afterSwap", (evt) => {
  setupThemeToggle();
  handleAutoFocus();
  if (evt.detail.target?.id === "main-container")
    setTimeout(initTabsSortable, 50);
});

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    initTabsSortable();
    handleAutoFocus();
  }, 100);
});

Object.assign(window, {
  checkColumnName,
  showColumnSuggestions,
  hideColumnSuggestions,
  filterColumnSuggestions,
  validateAndSaveColumn,
  saveCell,
  saveParam,
  toggleAddBlockMenu,
  uploadInferenceFile,
});
