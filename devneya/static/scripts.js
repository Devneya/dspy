function saveBlocksToLocalStorage(blockIds) {
    localStorage.setItem('dspy_blocks_order', JSON.stringify(blockIds));
}

function loadBlocksFromLocalStorage() {
    const savedOrder = localStorage.getItem('dspy_blocks_order');
    if (savedOrder) {
        const blockIds = JSON.parse(savedOrder);
        htmx.ajax('POST', '/reorder', {
            target: '#ws',
            values: {order: JSON.stringify(blockIds)},
            swap: 'outerHTML'
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
            const area = document.getElementById('working-area');
            if (area) {
                const order = Array.from(area.children).map(c => c.id);
                saveBlocksToLocalStorage(order);
            }
            initSortable();
        }, 10);
    }
});

initSortable();
loadBlocksFromLocalStorage();