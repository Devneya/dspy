const DSPY_MODULE_SCHEMAS = window.DSPY_MODULE_SCHEMAS || {};
const BLOCK_TYPES = new Set(Object.keys(DSPY_MODULE_SCHEMAS));

(function () {
  const serverStart = document.querySelector(
    'meta[name="server-start"]',
  )?.content;
  const lastServerStart = localStorage.getItem("last_server_start");

  if (serverStart && lastServerStart !== serverStart) {
    const keysToClear = ["dspy_blocks_data", "dspy_table_data"];
    keysToClear.forEach((key) => localStorage.removeItem(key));
    localStorage.setItem("last_server_start", serverStart);
    console.log("Server restart detected - localStorage cleared");
  }
})();

const Storage = {
  _get(key) {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : null;
  },
  _set(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
  },
  _remove(key) {
    localStorage.removeItem(key);
  },

  saveBlocks(data) {
    this._set("dspy_blocks_data", data);
  },
  loadBlocks() {
    return (
      this._get("dspy_blocks_data") || { order: [], signatures: {}, params: {} }
    );
  },
  clearBlocks() {
    this._remove("dspy_blocks_data");
  },

  saveTable(data) {
    this._set("dspy_table_data", data);
  },
  loadTableData() {
    return this._get("dspy_table_data") || { columns: [], rows: [] };
  },
  clearTable() {
    this._remove("dspy_table_data");
  },
};

const UI = {
  restoreBlocks() {
    const data = Storage.loadBlocks();
    const blocks = document.querySelectorAll(".workspace-block");
    blocks.forEach((block) => {
      const signature = data.signatures[block.id];
      const params = data.params[block.id];
      if (signature) {
        block.setAttribute("data-signature", signature);
        const signatureSpan = block.querySelector(".font-mono");
        if (signatureSpan) signatureSpan.textContent = signature;
      }
      if (params) {
        block.setAttribute("data-params", JSON.stringify(params));
      }
    });
  },

  updateBlockConfig(blockId, signature, params) {
    const data = Storage.loadBlocks();
    if (signature) {
      data.signatures[blockId] = signature;
    } else {
      delete data.signatures[blockId];
    }
    if (params && Object.keys(params).length > 0) {
      data.params[blockId] = params;
    } else {
      delete data.params[blockId];
    }
    Storage.saveBlocks(data);

    const block = document.getElementById(blockId);
    if (block) {
      block.setAttribute("data-signature", signature);
      block.setAttribute("data-params", JSON.stringify(params));
      const signatureSpan = block.querySelector(".font-mono");
      if (signatureSpan)
        signatureSpan.textContent = signature || "Click to configure";
    }
  },

  saveBlocksState() {
    const blocks = document.querySelectorAll(".workspace-block");
    const order = Array.from(blocks).map((b) => b.id);
    const signatures = {};
    const params = {};

    blocks.forEach((block) => {
      const signatureAttr = block.getAttribute("data-signature");
      const paramsAttr = block.getAttribute("data-params");
      if (signatureAttr) {
        signatures[block.id] = signatureAttr;
      }
      if (paramsAttr) {
        try {
          params[block.id] = JSON.parse(paramsAttr);
        } catch (e) {}
      }
    });

    Storage.saveBlocks({ order, signatures, params });
  },

  saveTableState() {
    const tableState = this.captureTableState();
    if (tableState && tableState.rows.length > 0) {
      Storage.saveTable(tableState);
    }
    htmx
      .ajax("POST", "/table/restore", {
        values: { data: JSON.stringify(tableState) },
        swap: "none",
      })
      .catch((err) => console.error("Error saving table state:", err));
  },

  captureTableState() {
    const cells = document.querySelectorAll('input[name^="cell_"]');
    if (cells.length === 0) return null;

    const tableState = { columns: [], rows: [] };

    const headers = document.querySelectorAll("#table-section th");
    headers.forEach((th, idx) => {
      if (idx > 0 && idx < headers.length - 1) {
        tableState.columns.push(th.textContent.trim());
      }
    });

    const rowsMap = new Map();
    cells.forEach((cell) => {
      const match = cell.name.match(/^cell_(\d+)_(.+)$/);
      if (match) {
        const [, rowId, colName] = match;
        const rowIdNum = parseInt(rowId);
        if (!rowsMap.has(rowIdNum)) {
          rowsMap.set(rowIdNum, { id: rowIdNum });
        }
        rowsMap.get(rowIdNum)[colName] = cell.value;
      }
    });

    tableState.rows = Array.from(rowsMap.values());
    return tableState;
  },

  restoreTableValues() {
    const data = Storage.loadTableData();
    if (!data || !data.rows) return;

    data.rows.forEach((row) => {
      Object.keys(row).forEach((col) => {
        if (col !== "id") {
          const input = document.querySelector(
            `input[name="cell_${row.id}_${col}"]`,
          );
          if (input) {
            input.value = row[col];
          }
        }
      });
    });
  },

  clearTable() {
    Storage.clearTable();
    htmx.ajax("POST", "/table/clear", {
      target: "#table-section",
      swap: "outerHTML",
    });
  },
};

// ==================== THEME ====================
function initTheme() {
  const savedTheme = localStorage.getItem("dspy_theme");
  if (savedTheme === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

function setupThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (btn && !btn._hasListener) {
    btn.onclick = function () {
      if (document.documentElement.classList.contains("dark")) {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("dspy_theme", "light");
      } else {
        document.documentElement.classList.add("dark");
        localStorage.setItem("dspy_theme", "dark");
      }
    };
    btn._hasListener = true;
  }
}

initTheme();
setupThemeToggle();

document.body.addEventListener("htmx:afterSwap", () => {
  setupThemeToggle();
});

// ==================== CONTEXT MENU ====================
let currentMenu = null;

function closeMenu() {
  currentMenu?.remove();
  currentMenu = null;
}

window.showContextMenu = async (event, blockId) => {
  event.preventDefault();
  closeMenu();

  try {
    const res = await fetch(`/context-menu/${blockId}`);
    const html = await res.text();
    if (!html?.length) return;

    const div = document.createElement("div");
    div.innerHTML = html;
    const menu = div.firstElementChild;
    if (!menu) return;

    Object.assign(menu.style, {
      position: "fixed",
      left: `${Math.min(event.clientX + 10, window.innerWidth - 320)}px`,
      top: `${Math.min(event.clientY + 10, window.innerHeight - 400)}px`,
      zIndex: "100000",
    });

    document.body.appendChild(menu);
    currentMenu = menu;

    const signatureTab = document.getElementById("signature-tab");
    const paramsTab = document.getElementById("params-tab");
    const sigBtn = document.getElementById("tab-signature-btn");
    const paramsBtn = document.getElementById("tab-params-btn");

    if (sigBtn && paramsBtn) {
      sigBtn.onclick = () => {
        sigBtn.className =
          "bg-primary text-primary-foreground hover:bg-primary/90 text-sm px-4 py-2 rounded";
        paramsBtn.className =
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 text-sm px-4 py-2 rounded";
        signatureTab.classList.remove("hidden");
        paramsTab.classList.add("hidden");
      };
      paramsBtn.onclick = () => {
        paramsBtn.className =
          "bg-primary text-primary-foreground hover:bg-primary/90 text-sm px-4 py-2 rounded";
        sigBtn.className =
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 text-sm px-4 py-2 rounded";
        paramsTab.classList.remove("hidden");
        signatureTab.classList.add("hidden");
      };
    }

    menu
      .querySelector(".menu-save-btn")
      ?.addEventListener("click", async (e) => {
        e.preventDefault();
        const signature =
          document.getElementById("signature-input")?.value || "";
        const params = {};
        menu
          .querySelectorAll(
            "#params-tab input, #params-tab select, #params-tab textarea",
          )
          .forEach((input) => {
            if (input.id) {
              const paramName = input.id.replace("param-", "");
              params[paramName] = input.value;
            }
          });

        UI.updateBlockConfig(blockId, signature, params);

        const formData = new FormData();
        formData.append("signature", signature);
        Object.keys(params).forEach((key) => {
          formData.append(key, params[key]);
        });

        await htmx.ajax("POST", `/update-config/${blockId}`, {
          values: Object.fromEntries(formData),
          target: "#main-container",
          swap: "outerHTML",
        });

        closeMenu();
      });
  } catch (err) {
    console.error("Context menu error:", err);
  }
};

document.body.addEventListener("contextmenu", (e) => {
  const block = e.target.closest(".workspace-block");
  if (block) {
    e.preventDefault();
    window.showContextMenu(e, block.id);
  }
});

document.body.addEventListener("click", (e) => {
  if (currentMenu && !currentMenu.contains(e.target)) closeMenu();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && currentMenu) closeMenu();
});

// ==================== DRAG & DROP ====================
document.addEventListener("dragstart", (e) => {
  const item = e.target.closest('[draggable="true"]');
  if (item && item.dataset.blockType) {
    e.dataTransfer.setData("text/plain", item.dataset.blockType);
    e.dataTransfer.effectAllowed = "copy";
  }
});

document.addEventListener("dragover", (e) => e.preventDefault());

let isDropping = false;
document.addEventListener("drop", (e) => {
  const zone = e.target.closest("#working-area");
  if (!zone) return;
  e.preventDefault();
  if (isDropping) return;

  const type = e.dataTransfer.getData("text/plain");
  if (BLOCK_TYPES.has(type)) {
    isDropping = true;
    htmx
      .ajax("POST", `/add/${type}`, {
        target: "#main-container",
        swap: "outerHTML",
      })
      .finally(() => {
        isDropping = false;
      });
  }
});

function initSortable() {
  const area = document.getElementById("working-area");
  if (!area) return;
  if (area._sortable) area._sortable.destroy();

  area._sortable = new Sortable(area, {
    animation: 200,
    handle: ".workspace-block",
    draggable: ".workspace-block",
    onEnd: () => {
      const order = Array.from(area.children).map((c) => c.id);
      UI.saveBlocksState();
      htmx.ajax("POST", "/reorder", {
        target: "#main-container",
        values: { order: JSON.stringify(order) },
        swap: "outerHTML",
      });
    },
  });
}

document.body.addEventListener("input", (e) => {
  if (e.target.name && e.target.name.startsWith("cell_")) {
    UI.saveTableState();
  }
});

document.body.addEventListener("htmx:afterSwap", (evt) => {
  if (evt.detail.target?.id === "table-section") {
    setTimeout(() => {
      UI.restoreTableValues();
    }, 50);
  }
  if (evt.detail.target?.id === "main-container") {
    setTimeout(() => {
      UI.restoreBlocks();
      initSortable();
      UI.restoreTableValues();
    }, 50);
  }
});

function initialize() {
  initSortable();

  const blocksData = Storage.loadBlocks();
  if (
    blocksData.order &&
    blocksData.order.length > 0 &&
    !window.initialBlockLoadDone
  ) {
    window.initialBlockLoadDone = true;
    htmx
      .ajax("POST", "/reorder", {
        target: "#main-container",
        values: { order: JSON.stringify(blocksData.order) },
        swap: "outerHTML",
      })
      .then(() => {
        setTimeout(() => UI.restoreBlocks(), 100);
      });
  } else {
    UI.restoreBlocks();
  }

  const tableData = Storage.loadTableData();
  if (tableData && tableData.rows.length > 0 && !window.initialTableLoadDone) {
    window.initialTableLoadDone = true;
    htmx
      .ajax("POST", "/table/restore", {
        target: "#table-section",
        swap: "outerHTML",
        values: { data: JSON.stringify(tableData) },
      })
      .then(() => {
        setTimeout(() => UI.restoreTableValues(), 100);
      });
  } else {
    UI.restoreTableValues();
  }
}

window.addEventListener("beforeunload", () => {
  UI.saveTableState();
  UI.saveBlocksState();
});

initialize();
