const BLOCK_TYPES = new Set([
    "bestofn", "chainofthought", "codeact", "predict",
    "programofthought", "react", "refine", "rlm", "multichaincomparison"
]);

(function() {
    const serverStart = document.querySelector('meta[name="server-start"]')?.content;
    const lastServerStart = localStorage.getItem('last_server_start');
     
    if (serverStart && lastServerStart !== serverStart) {
        localStorage.removeItem('dspy_blocks_data');
        localStorage.removeItem('dspy_blocks_order');
        localStorage.removeItem('dspy_blocks_text');
        localStorage.removeItem('dspy_block_labels');
        localStorage.removeItem('dspy_block_texts');
        localStorage.removeItem('dspy_table_values');
        localStorage.removeItem('dspy_table_data');
        localStorage.setItem('last_server_start', serverStart);
        console.log('Server restart detected - localStorage cleared');
    }
})();

const Storage = {
    save(data) {
        localStorage.setItem('dspy_blocks_data', JSON.stringify(data));
    },
    
    load() {
        const saved = localStorage.getItem('dspy_blocks_data');
        return saved ? JSON.parse(saved) : { order: [], texts: {} };
    },
    
    saveFromDOM() {
        const blocks = document.querySelectorAll('.workspace-block');
        const order = Array.from(blocks).map(b => b.id);
        const texts = {};
        blocks.forEach(block => {
            const textSpan = block.querySelector('.block-additional-text');
            const text = textSpan?.textContent;
            if (text && text !== "placeholder for dspy module signature input") {
                texts[block.id] = text;
            }
        });
        this.save({ order, texts });
    },
    
    updateText(blockId, text) {
        const data = this.load();
        if (text && text !== "placeholder for dspy module signature input") {
            data.texts[blockId] = text;
        } else {
            delete data.texts[blockId];
        }
        this.save(data);
    },
    
    saveTableValues(values) {
        localStorage.setItem('dspy_table_values', JSON.stringify(values));
    },
    
    loadTableValues() {
        const saved = localStorage.getItem('dspy_table_values');
        return saved ? JSON.parse(saved) : null;
    },
    
    saveTableData(data) {
        localStorage.setItem('dspy_table_data', JSON.stringify(data));
    },
    
    loadTableData() {
        const saved = localStorage.getItem('dspy_table_data');
        return saved ? JSON.parse(saved) : null;
    },
    
    clearTableData() {
        localStorage.removeItem('dspy_table_values');
        localStorage.removeItem('dspy_table_data');
    }
};

const UI = {
    restore() {
        const data = Storage.load();
        const blocks = document.querySelectorAll('.workspace-block');
        blocks.forEach(block => {
            const text = data.texts[block.id];
            if (text) {
                const textSpan = block.querySelector('.block-additional-text');
                if (textSpan) textSpan.textContent = text;
            }
        });
    },
    
    saveTableValues() {
        const values = {};
        document.querySelectorAll('.inline-input').forEach(input => {
            values[input.name] = input.value;
        });
        Storage.saveTableValues(values);
    },
    
    restoreTableValues() {
        const values = Storage.loadTableValues();
        if (!values) return;
        
        document.querySelectorAll('.inline-input').forEach(input => {
            if (values[input.name] !== undefined) {
                input.value = values[input.name];
            }
        });
    },
    
    saveTableState() {
        const inputs = document.querySelectorAll('.inline-input');
        if (inputs.length === 0) return;
        
        const tableState = {
            inputs: {
                columns: [],
                rows: []
            },
            outputs: {
                columns: [],
                rows: []
            }
        };
        
        const inputColumns = [];
        document.querySelectorAll('#input-table-body .table-header').forEach(th => {
            const colName = th.textContent.trim();
            if (colName !== '#') inputColumns.push(colName);
        });
        
        const outputColumns = [];
        document.querySelectorAll('#output-table-body .table-header').forEach(th => {
            const colName = th.textContent.trim();
            if (colName !== '#') outputColumns.push(colName);
        });
        
        tableState.inputs.columns = inputColumns;
        tableState.outputs.columns = outputColumns;
        
        const inputRows = new Map();
        const outputRows = new Map();
        
        inputs.forEach(input => {
            const name = input.name;
            const value = input.value;
            
            if (name.startsWith('input_')) {
                const match = name.match(/input_(\d+)_(.+)/);
                if (match) {
                    const rowId = parseInt(match[1]);
                    const colName = match[2];
                    if (!inputRows.has(rowId)) {
                        inputRows.set(rowId, { id: rowId });
                    }
                    inputRows.get(rowId)[colName] = value;
                }
            } else if (name.startsWith('output_')) {
                const match = name.match(/output_(\d+)_(.+)/);
                if (match) {
                    const rowId = parseInt(match[1]);
                    const colName = match[2];
                    if (!outputRows.has(rowId)) {
                        outputRows.set(rowId, { id: rowId });
                    }
                    outputRows.get(rowId)[colName] = value;
                }
            }
        });
        
        tableState.inputs.rows = Array.from(inputRows.values());
        tableState.outputs.rows = Array.from(outputRows.values());
        
        Storage.saveTableData(tableState);
        
        fetch('/table/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(tableState)
        }).catch(err => console.error('Error saving table state:', err));
    },
    
    restoreTableState() {
        const tableState = Storage.loadTableData();
        if (!tableState) return;
        
        fetch('/table/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(tableState)
        }).then(() => {
            htmx.ajax('GET', '/table-section', {
                target: '#table-section',
                swap: 'outerHTML'
            });
        }).catch(err => console.error('Error restoring table state:', err));
    },
    
    clearTableState() {
        Storage.clearTableData();
        fetch('/table/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }).then(() => {
            htmx.ajax('GET', '/table-section', {
                target: '#table-section',
                swap: 'outerHTML'
            });
        }).catch(err => console.error('Error clearing table state:', err));
    }
};

// ==================== THEME ====================
function initTheme() {
    const savedTheme = localStorage.getItem('dspy_theme');
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

function setupThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (btn && !btn._hasListener) {
        btn.onclick = function() {
            if (document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
                localStorage.setItem('dspy_theme', 'light');
            } else {
                document.documentElement.classList.add('dark');
                localStorage.setItem('dspy_theme', 'dark');
            }
        };
        btn._hasListener = true;
    }
}

initTheme();
setupThemeToggle();

document.body.addEventListener('htmx:afterSwap', () => {
    setupThemeToggle();
});

// ==================== CONTEXT MENU ====================
let currentMenu = null;

function closeMenu() {
    if (currentMenu) {
        currentMenu.remove();
        currentMenu = null;
    }
}

function showContextMenu(event, blockId) {
    event.preventDefault();
    event.stopPropagation();
    closeMenu();
    
    const block = document.getElementById(blockId);
    const textSpan = block?.querySelector('.block-additional-text');
    const currentText = textSpan?.textContent === "placeholder for dspy module signature input" ? '' : (textSpan?.textContent || '');
    
    const menu = document.createElement('div');
    menu.className = 'block-menu';
    menu.innerHTML = `
        <div class="menu-item">
            <textarea rows="3" placeholder="Enter dspy module settings" class="menu-textarea">${currentText.replace(/"/g, '&quot;')}</textarea>
            <button class="menu-save-btn">Save</button>
        </div>
    `;
    
    menu.style.position = 'fixed';
    menu.style.left = event.clientX + 'px';
    menu.style.top = event.clientY + 'px';
    
    const textarea = menu.querySelector('textarea');
    const saveBtn = menu.querySelector('.menu-save-btn');
    
    menu.addEventListener('click', (e) => {
        e.stopPropagation();
    });
    
    saveBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const newText = textarea.value.trim();
        const textSpan = block.querySelector('.block-additional-text');
        if (textSpan) textSpan.textContent = newText;
        Storage.updateText(blockId, newText);
        fetch(`/update-text/${blockId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `text=${encodeURIComponent(newText)}`
        });
        closeMenu();
    });
    
    textarea.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveBtn.click();
        }
    });
    
    textarea.addEventListener('click', (e) => {
        e.stopPropagation();
    });
    
    function onClickOutside(e) {
        if (!menu.contains(e.target)) {
            closeMenu();
            document.removeEventListener('click', onClickOutside);
            document.removeEventListener('contextmenu', onClickOutside);
        }
    }
    
    document.body.appendChild(menu);
    currentMenu = menu;
    textarea.focus();
    setTimeout(() => {
        document.addEventListener('click', onClickOutside);
        document.addEventListener('contextmenu', onClickOutside);
    }, 0);
}

window.showContextMenu = showContextMenu;

// ==================== DRAG & DROP ====================
document.addEventListener('dragstart', e => {
    const item = e.target.closest('[draggable="true"]');
    if (item && item.dataset.blockType) {
        e.dataTransfer.setData('text/plain', item.dataset.blockType);
        e.dataTransfer.effectAllowed = 'copy';
    }
});

document.addEventListener('dragover', e => e.preventDefault());

let isDropping = false;
document.addEventListener('drop', e => {
    const zone = e.target.closest('#working-area');
    if (!zone) return;
    e.preventDefault();
    if (isDropping) return;
    
    const type = e.dataTransfer.getData('text/plain');
    if (BLOCK_TYPES.has(type)) {
        isDropping = true;
        htmx.ajax('POST', `/add/${type}`, {
            target: '#ws',
            swap: 'outerHTML'
        }).finally(() => { isDropping = false; });
    }
});

function initSortable() {
    const area = document.getElementById('working-area');
    if (!area) return;
    if (area._sortable) area._sortable.destroy();
    
    area._sortable = new Sortable(area, {
        animation: 200,
        handle: '.workspace-block',
        onEnd: () => {
            const order = Array.from(area.children).map(c => c.id);
            Storage.saveFromDOM();
            htmx.ajax('POST', '/reorder', {
                target: '#ws',
                values: {order: JSON.stringify(order)},
                swap: 'outerHTML'
            });
        }
    });
}

// ==================== TABLE ====================
let saveTimeout;
function debouncedSaveTableState() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        UI.saveTableState();
    }, 500);
}

document.body.addEventListener('input', (e) => {
    if (e.target.classList && e.target.classList.contains('inline-input')) {
        UI.saveTableValues();
        debouncedSaveTableState();
    }
});

document.body.addEventListener('htmx:afterSwap', (evt) => {
    if (evt.detail.target?.id === 'table-section') {
        setTimeout(() => {
            UI.restoreTableValues();
            if (!window._tableRestored) {
                const tableState = Storage.loadTableData();
                if (tableState && (tableState.inputs.rows.length > 0 || tableState.outputs.rows.length > 0)) {
                    UI.restoreTableState();
                }
                window._tableRestored = true;
            }
        }, 100);
    }
    
    if (evt.detail.target?.id === 'ws') {
        setTimeout(() => {
            UI.restore();
            initSortable();
        }, 10);
    }
    
    if (evt.detail.target?.querySelectorAll) {
        const inputs = evt.detail.target.querySelectorAll('.inline-input');
        inputs.forEach(input => {
            if (!input._hasListener) {
                input._hasListener = true;
                input.addEventListener('input', () => {
                    UI.saveTableValues();
                    debouncedSaveTableState();
                });
            }
        });
    }
});

window.addEventListener('beforeunload', () => {
    UI.saveTableValues();
    UI.saveTableState();
});

function initialize() {
    initSortable();
    
    const data = Storage.load();
    if (data.order && data.order.length > 0 && !window.initialLoadDone) {
        window.initialLoadDone = true;
        htmx.ajax('POST', '/reorder', {
            target: '#ws',
            values: {order: JSON.stringify(data.order)},
            swap: 'outerHTML'
        });
    } else {
        UI.restore();
    }
    
    setTimeout(() => {
        UI.restoreTableValues();
        const tableState = Storage.loadTableData();
        if (tableState && (tableState.inputs.rows.length > 0 || tableState.outputs.rows.length > 0)) {
            UI.restoreTableState();
        }
    }, 200);
}

initialize();