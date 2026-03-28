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

table_entries = {
    "inputs": {
        "columns": ["default"],
        "rows": []
    },
    "outputs": {
        "columns": ["default"],
        "rows": []
    }
}
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
                cls="block-card"
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
        cls="workspace-block",
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
        id="ws",
        cls="workspace-container"
    )

# ==================== TABLE RENDERING ====================

def render_table_section():
    return Div(
        Div(
            H3("Training Data", cls="table-main-title"),
            cls="table-header-row"
        ),
        Div(
            Div(
                Div(
                    Div(
                        H4("Inputs", cls="subtable-title"),
                        render_input_columns_section(),
                        cls="subtable-header"
                    ),
                    render_input_table(),
                    cls="subtable"
                ),
                Div(
                    Div(
                        H4("Outputs", cls="subtable-title"),
                        render_output_columns_section(),
                        cls="subtable-header"
                    ),
                    render_output_table(),
                    cls="subtable"
                ),
                cls="subtables-side-by-side"
            ),
            Div(
                Button(
                    UkIcon("plus", height=18),
                    cls="add-row-btn",
                    hx_post="/table/add-row",
                    hx_target="#table-section",
                    hx_swap="outerHTML"
                ),
                cls="add-row-button-container"
            ),
            cls="table-content"
        ),
        id="table-section",
        cls="table-container"
    )

def render_input_columns_section():
    columns = table_entries["inputs"]["columns"]
    return Div(
        Div(
            *[render_column_tag("inputs", col) for col in columns],
            Button(
                UkIcon("plus", height=12),
                cls="add-column-btn",
                hx_post=f"/table/add-column/inputs",
                hx_target="#table-section",
                hx_swap="outerHTML"
            ),
            cls="columns-list"
        ),
        cls="columns-manager"
    )

def render_output_columns_section():
    columns = table_entries["outputs"]["columns"]
    return Div(
        Div(
            *[render_column_tag("outputs", col) for col in columns],
            Button(
                UkIcon("plus", height=12),
                cls="add-column-btn",
                hx_post=f"/table/add-column/outputs",
                hx_target="#table-section",
                hx_swap="outerHTML"
            ),
            cls="columns-list"
        ),
        cls="columns-manager"
    )

def render_column_tag(subtable, col_name):
    return Span(
        Span(col_name, cls="column-name-text"),
        Button(
            UkIcon("edit-2", height=10),
            cls="rename-column-btn",
            title="Rename",
            hx_get=f"/table/rename-column-form/{subtable}/{col_name}",
            hx_target=f"#column-{subtable}-{col_name.replace(' ', '-')}",
            hx_swap="outerHTML"
        ),
        Button(
            UkIcon("x", height=10),
            cls="delete-column-btn",
            title="Delete",
            hx_post=f"/table/delete-column/{subtable}/{col_name}",
            hx_target="#table-section",
            hx_swap="outerHTML",
            hx_confirm="Delete this column?"
        ),
        id=f"column-{subtable}-{col_name.replace(' ', '-')}",
        cls="column-tag"
    )

def render_input_table():
    if not table_entries["inputs"]["rows"]:
        return Div(cls="table-empty")
    
    columns = table_entries["inputs"]["columns"]
    rows = table_entries["inputs"]["rows"]
    
    return Div(
        Table(
            Thead(
                Tr(
                    Th("#", cls="table-header"),
                    *[Th(col, cls="table-header") for col in columns],
                    Th("", cls="table-header-actions")
                )
            ),
            Tbody(
                *[Tr(
                    Td(row['id'], cls="table-cell-id"),
                    *[Td(
                        Input(
                            type="text",
                            name=f"input_{row['id']}_{col}",
                            value=row.get(col, ""),
                            cls="inline-input"
                        ),
                        cls="table-cell"
                    ) for col in columns],
                    Td(
                        Button(
                            UkIcon("trash-2", height=14),
                            cls="delete-entry-btn",
                            hx_post=f"/table/delete-row/{row['id']}",
                            hx_target="#table-section",
                            hx_swap="outerHTML",
                            hx_confirm="Delete this row?"
                        ),
                        cls="table-cell-actions"
                    )
                ) for row in rows]
            ),
            cls="data-table"
        ),
        id="input-table-body"
    )

def render_output_table():
    if not table_entries["outputs"]["rows"]:
        return Div(cls="table-empty")
    
    columns = table_entries["outputs"]["columns"]
    rows = table_entries["outputs"]["rows"]
    
    return Div(
        Table(
            Thead(
                Tr(
                    Th("#", cls="table-header"),
                    *[Th(col, cls="table-header") for col in columns],
                    Th("", cls="table-header-actions")
                )
            ),
            Tbody(
                *[Tr(
                    Td(row['id'], cls="table-cell-id"),
                    *[Td(
                        Input(
                            type="text",
                            name=f"output_{row['id']}_{col}",
                            value=row.get(col, ""),
                            cls="inline-input"
                        ),
                        cls="table-cell"
                    ) for col in columns],
                    Td(
                        Button(
                            UkIcon("trash-2", height=14),
                            cls="delete-entry-btn",
                            hx_post=f"/table/delete-row/{row['id']}",
                            hx_target="#table-section",
                            hx_swap="outerHTML",
                            hx_confirm="Delete this row?"
                        ),
                        cls="table-cell-actions"
                    )
                ) for row in rows]
            ),
            cls="data-table"
        ),
        id="output-table-body"
    )

def render_rename_column_form(subtable, col_name):
    return Span(
        Form(
            Input(type="text", name="new_name", value=col_name, required=True, 
                  cls="rename-input", autofocus=True),
            Button(UkIcon("check", height=10), type="submit", cls="rename-save-btn"),
            Button(UkIcon("x", height=10), type="button", cls="rename-cancel-btn",
                   hx_get=f"/table/cancel-rename/{subtable}/{col_name}",
                   hx_target=f"#column-{subtable}-{col_name.replace(' ', '-')}",
                   hx_swap="outerHTML"),
            hx_post=f"/table/rename-column/{subtable}/{col_name}",
            hx_target="#table-section",
            hx_swap="outerHTML",
            cls="rename-form"
        ),
        cls="column-tag editing"
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
            Div(
                render_palette(),
                render_ws(),
                cls="palette-workspace-row"
            ),
            render_table_section(),
            cls="main-vertical-layout"
        ),
        cls="container"
    )

# ==================== BLOCK ROUTES ====================

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

# ==================== TABLE ROUTES ====================

@rt("/table-section")
def get_table_section():
    return render_table_section()

@rt("/table/restore", methods=["POST"])
async def restore_table_data(request):
    global table_entries, entry_id
    try:
        data = await request.json()
        
        # If data is empty, don't restore (keep current state)
        if not data or (not data.get("inputs") and not data.get("outputs")):
            return "OK"
        
        if "inputs" in data:
            if "columns" in data["inputs"] and data["inputs"]["columns"]:
                table_entries["inputs"]["columns"] = data["inputs"]["columns"]
            if "rows" in data["inputs"]:
                table_entries["inputs"]["rows"] = data["inputs"]["rows"]
        
        if "outputs" in data:
            if "columns" in data["outputs"] and data["outputs"]["columns"]:
                table_entries["outputs"]["columns"] = data["outputs"]["columns"]
            if "rows" in data["outputs"]:
                table_entries["outputs"]["rows"] = data["outputs"]["rows"]
        
        # Update entry_id
        max_id = 0
        for row in table_entries["inputs"]["rows"]:
            if row.get("id", 0) > max_id:
                max_id = row["id"]
        for row in table_entries["outputs"]["rows"]:
            if row.get("id", 0) > max_id:
                max_id = row["id"]
        entry_id = max_id + 1 if max_id > 0 else 1
        
        return "OK"
    except Exception as e:
        print(f"Error restoring table: {e}")
        return "Error", 500

@rt("/table/add-column/{subtable}")
def add_column(subtable: str):
    global table_entries
    columns = table_entries[subtable]["columns"]
    new_col_num = len([c for c in columns if c.startswith("col_")]) + 1
    new_col_name = f"col_{new_col_num}"
    
    table_entries[subtable]["columns"].append(new_col_name)
    for row in table_entries[subtable]["rows"]:
        row[new_col_name] = ""
    
    return render_table_section()

@rt("/table/delete-column/{subtable}/{col_name}")
def delete_column(subtable: str, col_name: str):
    global table_entries
    if col_name in table_entries[subtable]["columns"]:
        if len(table_entries[subtable]["columns"]) == 1:
            return render_table_section()
        
        table_entries[subtable]["columns"].remove(col_name)
        for row in table_entries[subtable]["rows"]:
            if col_name in row:
                del row[col_name]
    
    return render_table_section()

@rt("/table/rename-column-form/{subtable}/{col_name}")
def rename_column_form(subtable: str, col_name: str):
    return render_rename_column_form(subtable, col_name)

@rt("/table/cancel-rename/{subtable}/{col_name}")
def cancel_rename(subtable: str, col_name: str):
    return render_column_tag(subtable, col_name)

@rt("/table/rename-column/{subtable}/{col_name}")
def rename_column(subtable: str, col_name: str, new_name: str):
    global table_entries
    if new_name and new_name not in table_entries[subtable]["columns"]:
        idx = table_entries[subtable]["columns"].index(col_name)
        table_entries[subtable]["columns"][idx] = new_name
        
        for row in table_entries[subtable]["rows"]:
            if col_name in row:
                row[new_name] = row.pop(col_name)
    
    return render_table_section()

@rt("/table/add-row")
def add_table_row():
    global entry_id, table_entries
    
    input_row = {"id": entry_id}
    for col in table_entries["inputs"]["columns"]:
        input_row[col] = ""
    
    output_row = {"id": entry_id}
    for col in table_entries["outputs"]["columns"]:
        output_row[col] = ""
    
    table_entries["inputs"]["rows"].append(input_row)
    table_entries["outputs"]["rows"].append(output_row)
    
    entry_id += 1
    return render_table_section()

@rt("/table/delete-row/{row_id}")
def delete_table_row(row_id: int):
    global table_entries
    table_entries["inputs"]["rows"] = [r for r in table_entries["inputs"]["rows"] if r["id"] != row_id]
    table_entries["outputs"]["rows"] = [r for r in table_entries["outputs"]["rows"] if r["id"] != row_id]
    return render_table_section()

@rt("/table/restore", methods=["POST"])
async def restore_table_data(request):
    global table_entries, entry_id
    try:
        data = await request.json()
        
        if "inputs" in data:
            table_entries["inputs"]["columns"] = data["inputs"].get("columns", ["default"])
            table_entries["inputs"]["rows"] = data["inputs"].get("rows", [])
        
        if "outputs" in data:
            table_entries["outputs"]["columns"] = data["outputs"].get("columns", ["default"])
            table_entries["outputs"]["rows"] = data["outputs"].get("rows", [])
        
        # Update entry_id
        max_id = 0
        for row in table_entries["inputs"]["rows"]:
            if row.get("id", 0) > max_id:
                max_id = row["id"]
        for row in table_entries["outputs"]["rows"]:
            if row.get("id", 0) > max_id:
                max_id = row["id"]
        entry_id = max_id + 1 if max_id > 0 else 1
        
    except Exception as e:
        print(f"Error restoring table: {e}")
    
    return "OK"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

if __name__ == "__main__":
    serve(host=HOST, port=PORT)