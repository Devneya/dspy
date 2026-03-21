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
    "bestofn",
    "chainofthought",
    "codeact",
    "predict",
    "programofthought",
    "react",
    "refine",
    "rlm",
    "multichaincomparison"
}

blocks = []

class Block:
    def __init__(self, block_type, position, text=""):
        self.id = f"b{len(blocks)}-{block_type}"
        self.type = block_type
        self.position = position
        self.label = block_type
        self.text = text

def render_palette():
    return Div(
        H3("DSPy Modules", cls="palette-title"),
        *[Div(
            Card(
                Span(block_type, cls="block-label"),
                cls=f"block-card bg-primary text-white",
            ),
            draggable="true",
            **{"data-block-type": block_type},
            cls="draggable-item"
        ) for block_type in BLOCK_TYPES],
        cls="palette-scroll",
        id="palette"
    )

def render_workspace():
    if not blocks:
        return Div(
            DivCentered(
                P("Drop modules here", cls="empty-message"),
            ),
            id="working-area", 
            cls="empty-workspace"
        )
    
    return Div(
        *[Div(
            Div(
                Div(
                    Span(b.label, cls="block-label"),
                    Span(b.id, cls="block-id"),
                ),
                Button(
                    UkIcon("x", height=16),
                    hx_delete=f"/rm/{b.id}",
                    hx_target="#ws",
                    hx_swap="outerHTML"
                ),
                cls="block-header"
            ),
            Textarea(
                b.text,
                id=f"textarea-{b.id}",
                **{"data-block-id": b.id},
                cls="block-textarea"
            ),
            id=b.id,
            draggable="false",
            cls=f"workspace-block block-{b.type}"
        ) for b in sorted(blocks, key=lambda x: x.position)],
        id="working-area",
        cls="workspace"
    )

def render_ws():
    return Div(
        Div(H3("Workspace", cls="workspace-title")),
        render_workspace(),
        Div(
            Button("Clear All",
                   hx_post="/clear",
                   hx_target="#ws",
                   hx_swap="outerHTML",
                   cls="clear-btn"),
        ),
        id="ws"
    )

@rt("/")
def get():
    return Container(
        Button(
            UkIcon("sun", cls="light-icon"),
            UkIcon("moon", cls="dark-icon"),
            cls="theme-toggle-btn",
            onclick="document.documentElement.classList.toggle('dark')"
        ),
        H1("DSPy Module Arranger", cls="main-title"),
        Div(
            render_palette(),
            Div(render_ws(), cls="workspace-container"),
            cls="main-container"
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