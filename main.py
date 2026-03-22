from fasthtml.common import *
from monsterui.all import *
import json
import time
import os

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
table_entries = []
entry_id = 1

class Block:
    def __init__(self, block_type, position, text=""):
        global block_id
        self.id = f"b{block_id}"
        self.type = block_type
        self.position = position
        self.label = block_type
        self.additional_text = text
        block_id += 1

# ==================== RENDER FUNCTIONS ====================
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
            Span(block.additional_text if block.additional_text else "placeholder for dspy module signature input", 
                 cls="block-additional-text"),
            cls="block-text-display"
        ),
        id=block.id,
        draggable="false",
        cls=f"workspace-block block-{block.type}",
        **{"oncontextmenu": f"showContextMenu(event, '{block.id}'); return false;"}
    )

def render_table():
    if not table_entries:
        return Div(
            P("No entries. Add one below.", cls="empty-message"),
            cls="table-empty"
        )
    
    return Div(
        Table(
            Thead(
                Tr(
                    Th("Input", cls="table-header"),
                    Th("Output", cls="table-header"),
                    Th("", cls="table-header-actions")
                )
            ),
            Tbody(
                *[Tr(
                    Td(entry["key"], cls="table-cell"),
                    Td(entry["value"], cls="table-cell"),
                    Td(
                        Button(
                            UkIcon("trash-2", height=14),
                            cls="delete-entry-btn",
                            hx_post=f"/table/delete/{entry['id']}",
                            hx_target="#table-section",
                            hx_swap="outerHTML"
                        ),
                        cls="table-cell-actions"
                    )
                ) for entry in table_entries]
            ),
            cls="data-table"
        ),
        id="table-body"
    )

def render_table_section():
    return Div(
        Div(
            H3("Training Examples", cls="table-title"),
            Button(
                UkIcon("plus", height=16),
                " Add",
                cls="add-entry-btn",
                hx_get="/table/add-form",
                hx_target="#table-section",
                hx_swap="outerHTML"
            ),
            cls="table-header-row"
        ),
        render_table(),
        id="table-section"
    )

def render_add_form():
    return Div(
        Div(
            H3("Training Examples", cls="table-title"),
            cls="table-header-row"
        ),
        Div(
            Form(
                Div(
                    Input(type="text", name="key", placeholder="Input", required=True, cls="form-input"),
                    Input(type="text", name="value", placeholder="Output", required=True, cls="form-input"),
                    Button("Save", type="submit", cls="form-save-btn"),
                    Button("Cancel", cls="form-cancel-btn", 
                           hx_get="/table/cancel", 
                           hx_target="#table-section", 
                           hx_swap="outerHTML"),
                    cls="form-row"
                ),
                hx_post="/table/add",
                hx_target="#table-section",
                hx_swap="outerHTML",
                cls="add-form"
            ),
        ),
        id="table-section"
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

# ==================== ROUTES ====================
@rt("/")
def get():
    return Container(
        Meta(name="server-start", content=str(int(time.time()))),
        Button(
            UkIcon("sun", cls="light-icon"),
            UkIcon("moon", cls="dark-icon"),
            cls="theme-toggle-btn",
            id="theme-toggle",
        ),
        H1("DSPy Module Builder", cls="main-title"),
        Div(
            render_palette(),
            Div(render_ws(), cls="workspace-container"),
            Div(render_table_section(), cls="table-container"),
            cls="three-column-layout"
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

@rt("/table/add-form")
def get_add_form():
    return render_add_form()

@rt("/table/cancel")
def cancel_add():
    return render_table_section()

@rt("/table/add")
def add_table_entry(key: str, value: str):
    global entry_id, table_entries
    if key and value:
        table_entries.append({"id": entry_id, "key": key, "value": value})
        entry_id += 1
    return render_table_section()

@rt("/table/delete/{entry_id}")
def delete_table_entry(entry_id: int):
    global table_entries
    table_entries = [e for e in table_entries if e["id"] != entry_id]
    return render_table_section()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

if __name__ == "__main__":
    serve(host=HOST, port=PORT)