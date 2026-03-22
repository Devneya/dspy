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
    }
};

// ==================== THEME PERSISTENCE ====================
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
        UI.updateBlockText(blockId, newText);
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

UI.updateBlockText = function(blockId, text) {
    const block = document.getElementById(blockId);
    const textSpan = block?.querySelector('.block-additional-text');
    if (textSpan) {
        textSpan.textContent = text;
    }
};

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
}

document.body.addEventListener('htmx:afterSwap', (evt) => {
    if (evt.detail.target?.id === 'ws') {
        setTimeout(() => {
            UI.restore();
            initSortable();
        }, 10);
    }
});

initialize();