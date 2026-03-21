from fasthtml.common import *
from monsterui.all import *
import json

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

BLOCK_TYPES = ["bestofn", 
               "chainofthought", 
               "codeact", 
               "predict", 
               "programofthought", 
               "react", 
               "refine", 
               "rlm", 
               "multichaincomparison"]

blocks = []
block_id = 1

class Block:
    def __init__(self, block_type, position, text=""):
        global block_id
        self.id = f"b{block_id}"
        self.type = block_type
        self.position = position
        self.label = block_type
        self.additional_text = text
        block_id += 1

def render_palette():
    return Div(
        H3("DSPy Modules", cls="palette-title"),
        *[Div(
            Card(
                Span(block_type, cls="block-label"),
                cls="block-card",
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
                    hx_post=f"/rm/{b.id}",
                    hx_target="#ws",
                    hx_swap="outerHTML"
                ),
                cls="block-header"
            ),
            Div(
                Span(b.additional_text if b.additional_text else "No additional text", 
                     cls="block-additional-text"),
                cls="block-text-display"
            ),
            id=b.id,
            draggable="false",
            cls=f"workspace-block block-{b.type}",
            **{"oncontextmenu": f"showContextMenu(event, '{b.id}'); return false;"}
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
def add_block(btype: str):
    if btype not in BLOCK_TYPES:
        return render_ws()
    blocks.append(Block(btype, len(blocks)))
    return render_ws()

@rt("/update-text/{bid}")
def update_text(bid: str, text: str):
    global blocks
    for block in blocks:
        if block.id == bid:
            block.additional_text = text
            break
    return render_ws()

@rt("/reorder")
def reorder(order: str):
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
def clear():
    global blocks
    blocks.clear()
    return render_ws()

@rt("/rm/{bid}")
def delete_block(bid: str):
    global blocks
    blocks = [b for b in blocks if b.id != bid]
    for i, b in enumerate(blocks):
        b.position = i
    return render_ws()

if __name__ == "__main__":
    serve(host="127.0.0.1", port=5001)