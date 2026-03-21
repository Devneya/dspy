function showContextMenu(event, blockId) {
    event.preventDefault();
    event.stopPropagation();
    
    const existingMenu = document.querySelector('.block-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    const block = document.getElementById(blockId);
    const textSpan = block ? block.querySelector('.block-additional-text') : null;
    const currentText = textSpan ? textSpan.textContent : '';
    
    const menu = document.createElement('div');
    menu.className = 'block-menu';
    menu.innerHTML = `
        <div class="menu-item">
            <textarea id="block-text-input" rows="3" placeholder="Enter additional text..." class="menu-textarea">${currentText === 'No additional text' ? '' : currentText.replace(/"/g, '&quot;')}</textarea>
            <button id="save-text-btn" class="menu-save-btn">Save</button>
        </div>
    `;
    
    menu.style.position = 'fixed';
    menu.style.left = event.clientX + 'px';
    menu.style.top = event.clientY + 'px';
    
    const input = menu.querySelector('#block-text-input');
    input.focus();
    
    const saveBtn = menu.querySelector('#save-text-btn');
    saveBtn.addEventListener('click', () => {
        const newText = input.value.trim();
        if (textSpan) {
            if (newText) {
                textSpan.textContent = newText;
            } else {
                textSpan.textContent = "No additional text";
            }
            
            const savedTexts = localStorage.getItem('dspy_block_texts') || '{}';
            const texts = JSON.parse(savedTexts);
            texts[blockId] = newText;
            localStorage.setItem('dspy_block_texts', JSON.stringify(texts));
            
            fetch(`/update-text/${blockId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `text=${encodeURIComponent(newText)}`
            });
        }
        menu.remove();
    });
    
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveBtn.click();
        }
    });
    
    function closeMenu(e) {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
            document.removeEventListener('contextmenu', closeMenu);
        }
    }
    
    document.body.appendChild(menu);
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
        document.addEventListener('contextmenu', closeMenu);
    }, 0);
}

window.showContextMenu = showContextMenu;

function saveBlocksToLocalStorage(blockIds) {
    localStorage.setItem('dspy_blocks_order', JSON.stringify(blockIds));
    
    const blocks = document.querySelectorAll('.workspace-block');
    const texts = {};
    blocks.forEach(block => {
        const id = block.id;
        const textSpan = block.querySelector('.block-additional-text');
        if (textSpan && textSpan.textContent !== "No additional text") {
            texts[id] = textSpan.textContent;
        }
    });
    localStorage.setItem('dspy_block_texts', JSON.stringify(texts));
}

function loadTextsFromLocalStorage() {
    const savedTexts = localStorage.getItem('dspy_block_texts');
    if (savedTexts) {
        const texts = JSON.parse(savedTexts);
        const blocks = document.querySelectorAll('.workspace-block');
        blocks.forEach(block => {
            const id = block.id;
            if (texts[id]) {
                const textSpan = block.querySelector('.block-additional-text');
                if (textSpan) {
                    textSpan.textContent = texts[id];
                }
            }
        });
    }
}

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
    const validTypes = new Set([
        "bestofn", "chainofthought", "codeact", "predict",
        "programofthought", "react", "refine", "rlm", "multichaincomparison"
    ]);
    if (validTypes.has(type)) {
        isDropping = true;
        htmx.ajax('POST', `/add/${type}`, {
            target: '#ws',
            swap: 'outerHTML'
        }).then(() => { isDropping = false; })
          .catch(() => { isDropping = false; });
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
            saveBlocksToLocalStorage(order);
            htmx.ajax('POST', '/reorder', {
                target: '#ws',
                values: {order: JSON.stringify(order)},
                swap: 'outerHTML'
            });
        }
    });
}

document.body.addEventListener('htmx:afterSwap', (evt) => {
    if (evt.detail.target && evt.detail.target.id === 'ws') {
        setTimeout(() => {
            loadTextsFromLocalStorage();
            initSortable();
        }, 10);
    }
});

initSortable();

if (!window.initialLoadDone) {
    window.initialLoadDone = true;
    const savedOrder = localStorage.getItem('dspy_blocks_order');
    if (savedOrder) {
        const blockIds = JSON.parse(savedOrder);
        htmx.ajax('POST', '/reorder', {
            target: '#ws',
            values: {order: JSON.stringify(blockIds)},
            swap: 'outerHTML'
        });
    } else {
        loadTextsFromLocalStorage();
    }
}