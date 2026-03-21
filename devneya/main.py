from fasthtml.common import *
from monsterui.all import *

app, rt = fast_app(
    live=False,
    hdrs=(
        Theme.blue.headers(),
        Meta(name="live-reload", content="disabled"),
        Style("""
            * {
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
                -webkit-touch-callout: none;
            }
            input, textarea, [contenteditable="true"] {
                -webkit-user-select: text;
                -moz-user-select: text;
                -ms-user-select: text;
                user-select: text;
            }

            .palette-scroll {
                max-height: calc(100vh - 180px);
                overflow-y: auto;
                position: sticky;
                top: 20px;
                width: 280px;
            }

            .palette-scroll::-webkit-scrollbar {
                width: 6px;
            }
            .palette-scroll::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            .palette-scroll::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 10px;
            }
            .palette-scroll::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
            
            .block-card, .block-item, .workspace-block, .draggable-item > div, 
            button, .uk-button, .clear-btn, .theme-toggle-btn {
                border-radius: 12px !important;
            }
            
            .draggable-item .card, .draggable-item div[class*="bg-"] {
                border-radius: 12px !important;
            }
            
            .theme-toggle-btn {
                border-radius: 12px !important;
                padding: 8px 12px !important;
            }
        """)
    )
)

BLOCK_TYPES = {
    "bestofn": {
        "color": "bg-red-500",
        "label": "BestOfN",
    },
    "chainofthought": {
        "color": "bg-blue-500",
        "label": "ChainOfThought",
    },
    "codeact": {
        "color": "bg-green-500",
        "label": "CodeAct",
    },
    "predict": {
        "color": "bg-yellow-500",
        "label": "Predict",
    },
    "programofthought": {
        "color": "bg-purple-500",
        "label": "ProgramOfThought",
    },
    "react": {
        "color": "bg-pink-500",
        "label": "ReAct",
    },
    "refine": {
        "color": "bg-indigo-500",
        "label": "Refine",
    },
    "rlm": {
        "color": "bg-teal-500",
        "label": "RLM",
    },
    "multichaincomparison": {
        "color": "bg-orange-500",
        "label": "MultiChainComparison",
    }
}

blocks = []

class Block:
    def __init__(self, block_type, position):
        self.id = f"b{len(blocks)}-{block_type}"
        self.type = block_type
        self.position = position
        self.color = BLOCK_TYPES[block_type]["color"]
        self.label = BLOCK_TYPES[block_type]["label"]

def render_palette():
    return Div(
        H3("DSPy Modules", cls="text-lg mb-4 text-center"),
        *[Div(
            Card(
                Span(info["label"], cls="font-medium block-card"),
                cls=f"{info['color']} text-white",
            ),
            draggable="true",
            **{"data-block-type": block_type},
            cls="draggable-item mb-3 p-2 rounded-lg cursor-grab"
        ) for block_type, info in BLOCK_TYPES.items()],
        cls="bg-gray-100 dark:bg-gray-800 p-4 rounded-xl border-2 border-gray-200 dark:border-gray-700 mr-6 palette-scroll",
        id="palette"
    )

def render_workspace():
    if not blocks:
        return Div(
            P("Drop modules here", cls="text-gray-400 dark:text-gray-500 text-lg"), 
            id="working-area", 
            cls="flex items-center justify-center min-h-[400px] bg-gray-50 dark:bg-gray-900 rounded-xl border-3 border-dashed border-gray-300 dark:border-gray-700 p-6"
        )
    
    return Div(
        *[Div(
            Div(
                Span(b.label, cls="flex-1 font-medium block-item"),
                Button(UkIcon("x", height=16), 
                       cls="text-white hover:text-gray-200",
                       hx_delete=f"/rm/{b.id}", 
                       hx_target="#ws", 
                       hx_swap="outerHTML"),
                cls="flex items-center justify-between p-3"
            ),
            id=b.id,
            draggable="false",
            cls=f"{b.color} text-white rounded-lg shadow-md mb-2 cursor-grab workspace-block"
        ) for b in sorted(blocks, key=lambda x: x.position)],
        id="working-area",
        cls="p-2 min-h-[400px] bg-gray-50 dark:bg-gray-900 rounded-xl border-2 border-gray-200 dark:border-gray-700"
    )

def render_ws():
    return Div(
        H3("Workspace", cls="text-xl font-bold mb-4"),
        Button("Clear All", 
               cls=ButtonT.destructive + " mb-4 clear-btn",
               hx_post="/clear", 
               hx_target="#ws", 
               hx_swap="outerHTML"),
        render_workspace(), 
        id="ws"
    )

@rt("/")
def get():
    return Container(
        Button(
            UkIcon("sun"),
            cls="fixed top-5 right-5 z-1000 p-2 rounded-lg bg-gray-200 dark:bg-gray-700 theme-toggle-btn",
            onclick="document.documentElement.classList.toggle('dark')"
        ),
        H1("DSPy Module Arranger", cls="text-3xl font-bold text-center my-6"),
        Div(
            render_palette(), 
            Div(render_ws(), cls="flex-1"), 
            cls="flex"
        ),
        Script(src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"),
        Script("""
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
                // Accept only the nine module keys
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
                        htmx.ajax('POST', '/reorder', {
                            target: '#ws',
                            values: {order: JSON.stringify(order)},
                            swap: 'outerHTML'
                        });
                    }
                });
            }
            
            initSortable();
            
            document.body.addEventListener('htmx:afterSwap', (evt) => {
                if (evt.detail.target && evt.detail.target.id === 'ws') {
                    setTimeout(initSortable, 10);
                }
            });
        """)
    )

@rt("/add/{btype}")
def post(btype: str):
    if btype not in BLOCK_TYPES:
        return render_ws()
    blocks.append(Block(btype, len(blocks)))
    return render_ws()

@rt("/reorder")
def post(order: str):
    import json
    global blocks
    try:
        o = json.loads(order)
        block_map = {b.id: b for b in blocks}
        new_blocks = [block_map[bid] for bid in o if bid in block_map]
        if len(new_blocks) == len(blocks):
            blocks = new_blocks
            for i, b in enumerate(blocks):
                b.position = i
    except Exception:
        pass
    return render_ws()

@rt("/clear")
def post():
    global blocks
    blocks.clear()
    return render_ws()

@rt("/rm/{bid}")
def delete(bid: str):
    global blocks
    blocks = [b for b in blocks if b.id != bid]
    for i, b in enumerate(blocks):
        b.position = i
    return render_ws()

if __name__ == "__main__":
    serve(host="127.0.0.1", port=5001)