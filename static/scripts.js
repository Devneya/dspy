const BLOCK_TYPES = new Set([
    "bestofn", "chainofthought", "codeact", "predict",
    "programofthought", "react", "refine", "rlm", "multichaincomparison"
]);

(function() {
    const serverStart = document.querySelector('meta[name="server-start"]')?.content;
    const lastServerStart = localStorage.getItem('last_server_start');
     
    if (serverStart && lastServerStart !== serverStart) {
        const keysToClear = [
            'dspy_blocks_data', 'dspy_blocks_order', 'dspy_blocks_text',
            'dspy_block_labels', 'dspy_block_texts', 'dspy_table_values', 'dspy_table_data'
        ];
        keysToClear.forEach(key => localStorage.removeItem(key));
        localStorage.setItem('last_server_start', serverStart);
        console.log('Server restart detected - localStorage cleared');
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
        this._set('dspy_blocks_data', data);
    },
    loadBlocks() {
        return this._get('dspy_blocks_data') || { order: [], texts: {} };
    },
    clearBlocks() {
        const keysToClear = [
            'dspy_blocks_data', 'dspy_blocks_order', 'dspy_blocks_text',
            'dspy_block_labels', 'dspy_block_texts'
        ];
        keysToClear.forEach(key => this._remove(key));
    },

    saveTable(data) {
        console.log('Saving table data:', data);
        this._set('dspy_table_data', data);
    },
    loadTableData() {
        return this._get('dspy_table_data') || { 
            inputs: { 
                columns: ["default"], 
                rows: [] 
            }, 
            outputs: { 
                columns: ["default"], 
                rows: [] 
            } 
        };
    },
    saveTableValues(values) {
        this._set('dspy_table_values', values);
    },
    loadTableValues() {
        return this._get('dspy_table_values');
    },
    clearTable() {
        this._remove('dspy_table_data');
        this._remove('dspy_table_values');
    }
};

const UI = {
    restoreBlocks() {
        const data = Storage.loadBlocks();
        const blocks = document.querySelectorAll('.workspace-block');
        blocks.forEach(block => {
            const text = data.texts[block.id];
            if (text) {
                const textSpan = block.querySelector('.block-additional-text');
                if (textSpan) textSpan.textContent = text;
            }
        });
    },

    updateBlockText(blockId, text) {
        const data = Storage.loadBlocks();
        if (text && text !== "placeholder for dspy module signature input") {
            data.texts[blockId] = text;
        } else {
            delete data.texts[blockId];
        }
        Storage.saveBlocks(data);
    },

    saveBlocksState() {
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
        Storage.saveBlocks({ order, texts });
    },
    
    saveTableState() {
        const tableState = this.captureTableState();
        if (tableState && (tableState.inputs.rows.length > 0 || tableState.outputs.rows.length > 0)) {
            Storage.saveTable(tableState);
        }
        this.saveTableValues();
        htmx.ajax('POST', '/table/restore', {
            values: { data: JSON.stringify(tableState) },
            swap: 'none'
        }).catch(err => console.error('Error saving table state:', err));
    },
    
    captureTableState() {
        const inputs = document.querySelectorAll('.inline-input');
        if (inputs.length === 0) return null;
        
        const tableState = {
            inputs: { columns: [], rows: [] },
            outputs: { columns: [], rows: [] }
        };
        
        document.querySelectorAll('#inputs-table-body .table-header, #input-table-body .table-header').forEach(th => {
            const colName = th.textContent.trim();
            if (colName !== '#') tableState.inputs.columns.push(colName);
        });
        
        document.querySelectorAll('#outputs-table-body .table-header, #output-table-body .table-header').forEach(th => {
            const colName = th.textContent.trim();
            if (colName !== '#') tableState.outputs.columns.push(colName);
        });
        
        const inputRows = new Map();
        const outputRows = new Map();
        
        inputs.forEach(input => {
            const name = input.name;
            const value = input.value;
            
            const match = name.match(/^(inputs|outputs)_(\d+)_(.+)$/);
            if (match) {
                const [, type, rowId, colName] = match;
                const rowIdNum = parseInt(rowId);
                
                if (type === 'inputs') {
                    if (!inputRows.has(rowIdNum)) inputRows.set(rowIdNum, { id: rowIdNum });
                    inputRows.get(rowIdNum)[colName] = value;
                } else if (type === 'outputs') {
                    if (!outputRows.has(rowIdNum)) outputRows.set(rowIdNum, { id: rowIdNum });
                    outputRows.get(rowIdNum)[colName] = value;
                }
            }
        });
        
        tableState.inputs.rows = Array.from(inputRows.values());
        tableState.outputs.rows = Array.from(outputRows.values());
        
        console.log('Captured table state:', tableState);
        return tableState;
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
        
        console.log('Restoring table values:', values);
        document.querySelectorAll('.inline-input').forEach(input => {
            if (values[input.name] !== undefined) {
                input.value = values[input.name];
            }
        });
    },
    
    clearTable() {
        Storage.clearTable();
        htmx.ajax('POST', '/table/clear', {
            target: '#table-section',
            swap: 'outerHTML'
        });
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
        UI.updateBlockText(blockId, newText);
    
        htmx.ajax('POST', `/update-text/${blockId}`, {
            values: { text: newText },
            swap: 'none'
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
            UI.saveBlocksState();
            htmx.ajax('POST', '/reorder', {
                target: '#ws',
                values: {order: JSON.stringify(order)},
                swap: 'outerHTML'
            });
        }
    });
}

document.body.addEventListener('input', (e) => {
    if (e.target.classList && e.target.classList.contains('inline-input')) {
        UI.saveTableValues();
        UI.saveTableState();
    }
});

document.body.addEventListener('htmx:afterSwap', (evt) => {
    if (evt.detail.target?.id === 'table-section') {
        setTimeout(() => {
            UI.restoreTableValues();
        }, 50);
    }
    if (evt.detail.target?.id === 'ws') {
        setTimeout(() => {
            UI.restoreBlocks();
            initSortable();
        }, 50);
    }
});

function initialize() {
    initSortable();
    
    const blocksData = Storage.loadBlocks();
    if (blocksData.order && blocksData.order.length > 0 && !window.initialBlockLoadDone) {
        window.initialBlockLoadDone = true;
        htmx.ajax('POST', '/reorder', {
            target: '#ws',
            values: {order: JSON.stringify(blocksData.order)},
            swap: 'outerHTML'
        }).then(() => {
            setTimeout(() => UI.restoreBlocks(), 100);
        });
    } else {
        UI.restoreBlocks();
    }
    
    const tableData = Storage.loadTableData();
    if (tableData && (tableData.inputs.rows.length > 0 || tableData.outputs.rows.length > 0) && !window.initialTableLoadDone) {
        window.initialTableLoadDone = true;
        htmx.ajax('POST', '/table/restore', {
            target: '#table-section',
            swap: 'outerHTML',
            values: { data: JSON.stringify(tableData) }
        }).then(() => {
            setTimeout(() => UI.restoreTableValues(), 100);
        });
    } else {
        UI.restoreTableValues();
    }
}

window.addEventListener('beforeunload', () => {
    UI.saveTableState();
    UI.saveBlocksState();
});

initialize();