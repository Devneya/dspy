from fasthtml.common import *
from monsterui.all import *
import json
import os

def is_running_in_docker():
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_ENV') == 'true'

if is_running_in_docker():
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5001"))
else:
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5001"))

BLOCK_TYPES = ["bestofn", "chainofthought", "codeact", "predict", 
               "programofthought", "react", "refine", "rlm", "multichaincomparison"]

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
            DivCentered(P("Drop modules here", cls="empty-message")),
            id="working-area", 
            cls="empty-workspace"
        )
    
    return Div(
        *[render_block(b) for b in sorted(blocks, key=lambda x: x.position)],
        id="working-area",
        cls="workspace"
    )

def render_block(block):
    return Div(
        Div(
            Div(
                Span(block.label, cls="block-label"),
                Span(block.id, cls="block-id"),
            ),
            Button(
                UkIcon("x", height=16),
                hx_post=f"/rm/{block.id}",
                hx_target="#ws",
                hx_swap="outerHTML"
            ),
            cls="block-header"
        ),
        Div(
            Span(block.additional_text if block.additional_text else "Space for dspy module settings", 
                 cls="block-additional-text"),
            cls="block-text-display"
        ),
        id=block.id,
        draggable="false",
        cls=f"workspace-block block-{block.type}",
        **{"oncontextmenu": f"showContextMenu(event, '{block.id}'); return false;"}
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
        H1("DSPy Module Builder", cls="main-title"),
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
        new_order = json.loads(order)
        block_map = {b.id: b for b in blocks}
        reordered = [block_map[bid] for bid in new_order if bid in block_map]
        if len(reordered) == len(blocks):
            blocks = reordered
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
    serve(host=HOST, port=PORT)