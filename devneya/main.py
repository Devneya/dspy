from fasthtml.common import *
from monsterui.all import *

app, rt = fast_app(
    live=False,
    hdrs=(
        Theme.blue.headers(),
        Meta(name="live-reload", content="disabled"),
        Link(rel="stylesheet", href="/static/styles.css"),
        Script(src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js", defer=True),
        Script(src="/static/scripts.js", defer=True),
    )
)

BLOCK_TYPES = {
    "bestofn": {"color": "bg-red-500", "label": "BestOfN"},
    "chainofthought": {"color": "bg-blue-500", "label": "ChainOfThought"},
    "codeact": {"color": "bg-green-500", "label": "CodeAct"},
    "predict": {"color": "bg-yellow-500", "label": "Predict"},
    "programofthought": {"color": "bg-purple-500", "label": "ProgramOfThought"},
    "react": {"color": "bg-pink-500", "label": "ReAct"},
    "refine": {"color": "bg-indigo-500", "label": "Refine"},
    "rlm": {"color": "bg-teal-500", "label": "RLM"},
    "multichaincomparison": {"color": "bg-orange-500", "label": "MultiChainComparison"}
}

blocks = []

class Block:
    def __init__(self, block_type, position, text=""):
        self.id = f"b{len(blocks)}-{block_type}"
        self.type = block_type
        self.position = position
        self.color = BLOCK_TYPES[block_type]["color"]
        self.label = BLOCK_TYPES[block_type]["label"]
        self.text = text

def render_palette():
    return Div(
        H3("DSPy Modules", cls="font-bold text-lg mb-4 text-center"),
        *[Div(
            Card(
                Span(info["label"], cls="font-medium"),
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
            DivCentered(
                P("Drop modules here", cls="text-gray-400 dark:text-gray-500 text-lg"),
            ),
            id="working-area", 
            cls="flex items-center justify-center  bg-gray-50 dark:bg-gray-900 rounded-xl border-3 border-dashed border-gray-300 dark:border-gray-700 p-6"
        )
    
    return Div(
        *[Div(
            Div(
                Div(
                    Span(b.label, cls="font-medium"),
                    Span(b.id, cls="block-id"),
                    cls="flex items-center flex-1"
                ),
                Button(
                    UkIcon("x", height=16), 
                    cls="text-white hover:text-gray-200",
                    hx_delete=f"/rm/{b.id}", 
                    hx_target="#ws", 
                    hx_swap="outerHTML"
                ),
                cls="flex items-center justify-between p-3 border-b border-white/20"
            ),
            Textarea(
                b.text,
                cls="w-full p-2 mt-2 bg-white/10 text-white rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-white/50",
                id=f"textarea-{b.id}",
                **{"data-block-id": b.id}
            ),
            id=b.id,
            draggable="false",
            cls=f"{b.color} text-white rounded-lg shadow-md mb-2 cursor-grab workspace-block p-3"
        ) for b in sorted(blocks, key=lambda x: x.position)],
        id="working-area",
        cls="p-2 bg-gray-50 dark:bg-gray-900 rounded-xl border-2 border-gray-200 dark:border-gray-700"
    )

def render_ws():
    return Div(
        Div(
            H3("Workspace", cls="font-bold text-xl"),
            cls="flex justify-between items-center mb-4"
        ),
        render_workspace(),
        Div(
            Button("Clear All", 
                   cls="bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 rounded-lg clear-btn",
                   hx_post="/clear", 
                   hx_target="#ws", 
                   hx_swap="outerHTML"),
            cls="mt-4"
        ),
        id="ws",
        cls="w-full h-full"
    )

@rt("/")
def get():
    return Container(
        Button(
            UkIcon("sun", cls="light-icon"),
            UkIcon("moon", cls="dark-icon"),
            cls="fixed top-5 right-5 z-1000 p-2 rounded-lg bg-gray-200 dark:bg-gray-700 theme-toggle-btn",
            onclick="document.documentElement.classList.toggle('dark')"
        ),
        H1("DSPy Module Arranger", cls="font-bold text-4xl text-center my-6"),
        Div(
            render_palette(), 
            Div(render_ws(), cls="flex-1 w-full"), 
            cls="flex items-stretch"
        ),
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