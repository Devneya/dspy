from fasthtml.common import *
from monsterui.all import *
import json
import time
import os

SCHEMA_PATH = os.path.join("static", "dspy_schemas.json")
with open(SCHEMA_PATH, "r") as f:
    DSPY_MODULE_SCHEMAS = json.load(f)

BLOCK_TYPES = list(DSPY_MODULE_SCHEMAS.keys())

MODULE_NAMES = {
    block_type: schema["name"] for block_type, schema in DSPY_MODULE_SCHEMAS.items()
}

app, rt = fast_app(
    live=False,
    hdrs=Theme.blue.headers(daisy=True, icons=True)
    + [
        Meta(name="live-reload", content="disabled"),
        Script(
            src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js",
            defer=True,
        ),
        Script(src="/static/scripts.js", defer=True),
    ],
)


class BlockData:
    def __init__(self, block_type, position):
        global block_id
        self.id = f"b{block_id}"
        self.type = block_type
        self.position = position
        self.label = MODULE_NAMES.get(block_type, block_type)
        self.config = {}
        block_id += 1


class TableData:
    def __init__(self):
        self.entries = {
            "inputs": {"columns": ["default"], "rows": []},
            "outputs": {"columns": ["default"], "rows": []},
        }
        self.next_id = 1

    def add_row(self):
        row = {"id": self.next_id}
        for col in self.entries["inputs"]["columns"]:
            row[col] = ""
        self.entries["inputs"]["rows"].append(row)

        row = {"id": self.next_id}
        for col in self.entries["outputs"]["columns"]:
            row[col] = ""
        self.entries["outputs"]["rows"].append(row)

        self.next_id += 1
        return self.entries

    def delete_row(self, row_id):
        self.entries["inputs"]["rows"] = [
            r for r in self.entries["inputs"]["rows"] if r["id"] != row_id
        ]
        self.entries["outputs"]["rows"] = [
            r for r in self.entries["outputs"]["rows"] if r["id"] != row_id
        ]
        return self.entries

    def add_column(self, subtable):
        columns = self.entries[subtable]["columns"]
        new_col_num = len([c for c in columns if c.startswith("col_")]) + 1
        new_col_name = f"col_{new_col_num}"
        self.entries[subtable]["columns"].append(new_col_name)
        for row in self.entries[subtable]["rows"]:
            row[new_col_name] = ""
        return self.entries

    def delete_column(self, subtable, col_name):
        if col_name in self.entries[subtable]["columns"]:
            if len(self.entries[subtable]["columns"]) > 1:
                self.entries[subtable]["columns"].remove(col_name)
                for row in self.entries[subtable]["rows"]:
                    if col_name in row:
                        del row[col_name]
        return self.entries

    def rename_column(self, subtable, old_name, new_name):
        if new_name and new_name not in self.entries[subtable]["columns"]:
            idx = self.entries[subtable]["columns"].index(old_name)
            self.entries[subtable]["columns"][idx] = new_name
            for row in self.entries[subtable]["rows"]:
                if old_name in row:
                    row[new_name] = row.pop(old_name)
        return self.entries

    def clear(self):
        self.entries = {
            "inputs": {"columns": ["default"], "rows": []},
            "outputs": {"columns": ["default"], "rows": []},
        }
        self.next_id = 1
        return self.entries

    def restore(self, data):
        if "inputs" in data:
            if "columns" in data["inputs"] and data["inputs"]["columns"]:
                self.entries["inputs"]["columns"] = data["inputs"]["columns"]
            if "rows" in data["inputs"]:
                self.entries["inputs"]["rows"] = data["inputs"]["rows"]

        if "outputs" in data:
            if "columns" in data["outputs"] and data["outputs"]["columns"]:
                self.entries["outputs"]["columns"] = data["outputs"]["columns"]
            if "rows" in data["outputs"]:
                self.entries["outputs"]["rows"] = data["outputs"]["rows"]

        max_id = 0
        for row in self.entries["inputs"]["rows"]:
            max_id = max(max_id, row.get("id", 0))
        for row in self.entries["outputs"]["rows"]:
            max_id = max(max_id, row.get("id", 0))
        self.next_id = max_id + 1 if max_id > 0 else 1
        return self.entries


blocks = []
block_id = 1
table = TableData()

# ==================== RENDER FUNCTIONS ====================


def render_palette():
    return Card(
        H3("DSPy Modules", cls="palette-title"),
        Div(
            *[
                Div(
                    Card(
                        Span(
                            MODULE_NAMES.get(block_type, block_type), cls="block-label"
                        ),
                        cls=CardT.hover,
                    ),
                    draggable="true",
                    **{"data-block-type": block_type},
                    cls="draggable-item cursor-grab",
                )
                for block_type in BLOCK_TYPES
            ],
            cls="palette-scroll space-y-2",
        ),
        id="palette",
        cls="w-72",
    )


def render_workspace():
    if not blocks:
        return Div(
            DivCentered(
                P("Drop modules here", cls="text-muted-foreground text-lg"), cls="py-20"
            ),
            id="working-area",
            cls="border-2 border-dashed min-h-[200px]",
        )

    return Div(
        *[render_block(b) for b in sorted(blocks, key=lambda x: x.position)],
        id="working-area",
        cls="min-h-[200px]",
    )


def render_ws():
    return Div(
        Div(H3("Workspace", cls="workspace-title text-xl font-semibold")),
        render_workspace(),
        Div(
            Button(
                "Clear All",
                hx_post="/clear",
                hx_target="#ws",
                hx_swap="outerHTML",
                cls=ButtonT.destructive,
            ),
            cls="mt-4",
        ),
        id="ws",
        cls="flex-1",
    )


def render_block(block):
    signature = block.config.get("signature", "") if block.config else ""
    display_text = signature if signature else "Click to configure"
    return Div(
        Div(
            Div(
                Span(block.label, cls="font-medium"),
                Span(block.id, cls="text-xs text-muted-foreground ml-2"),
                cls="flex items-center gap-2",
            ),
            Button(
                UkIcon("x", height=14),
                hx_post=f"/rm/{block.id}",
                hx_target="#ws",
                hx_swap="outerHTML",
                cls=ButtonT.ghost + " p-0.5",
            ),
            cls="flex justify-between items-center",
        ),
        Div(
            Span(display_text, cls="font-mono text-xs text-muted-foreground"),
            cls="mt-1 pt-1",
        ),
        id=block.id,
        draggable="true",
        cls="workspace-block p-2 border rounded mb-1 bg-card cursor-move",
        data_type=block.type,
        data_config=json.dumps(block.config),
    )


def render_context_menu(block_id, block_type, current_config):
    schema = DSPY_MODULE_SCHEMAS.get(block_type.lower(), {})
    parameters = schema.get("parameters", {})

    form_fields = []
    for param_name, param_config in parameters.items():
        if param_name == "signature":
            form_fields.append(
                Div(
                    LabelInput(
                        param_name.title(),
                        id=param_name,
                        value=current_config.get(param_name, ""),
                        placeholder="question -> answer",
                        cls="w-full",
                    ),
                    cls="mb-3",
                )
            )
        else:
            input_type = "number" if param_config.get("type") == "int" else "text"
            form_fields.append(
                Div(
                    LabelInput(
                        param_name.title(),
                        id=param_name,
                        value=current_config.get(param_name, ""),
                        type=input_type,
                        cls="w-full",
                    ),
                    cls="mb-3",
                )
            )

    return Card(
        Div(
            Div(
                H4(f"Configure {block_type}", cls="text-lg font-semibold"),
                Button(UkIcon("x"), cls=ButtonT.ghost + " p-1 menu-close-btn"),
                cls="flex justify-between items-center mb-4",
            ),
            Divider(cls="my-2"),
            Div(*form_fields, cls="my-3"),
            Divider(cls="my-2"),
            Div(
                Button(
                    UkIcon("save", height=16),
                    cls=ButtonT.primary + " menu-save-btn flex items-center gap-2",
                ),
                cls="flex justify-end mt-4",
            ),
            cls="p-4",
        ),
        id=f"menu-{block_id}",
        cls="fixed z-50 w-96 shadow-xl border rounded-lg bg-card",
    )


def render_table_section():
    return Card(
        Div(
            H3("Training Data", cls="table-main-title text-lg font-semibold"),
            cls="table-header-row mb-4",
        ),
        Div(
            Div(
                Div(
                    Div(
                        H4("Inputs", cls="subtable-title text-md font-medium"),
                        render_columns_section("inputs"),
                        cls="subtable-header mb-4",
                    ),
                    render_data_table("inputs"),
                    cls="subtable p-4 border rounded",
                ),
                Div(
                    Div(
                        H4("Outputs", cls="subtable-title text-md font-medium"),
                        render_columns_section("outputs"),
                        cls="subtable-header mb-4",
                    ),
                    render_data_table("outputs"),
                    cls="subtable p-4 border rounded",
                ),
                cls="subtables-side-by-side grid grid-cols-2 gap-6",
            ),
            Div(
                Button(
                    UkIcon("plus", height=18),
                    cls=ButtonT.primary + " rounded-full w-10 h-10 p-0",
                    hx_post="/table/add-row",
                    hx_target="#table-section",
                    hx_swap="outerHTML",
                ),
                cls="add-row-button-container flex justify-center mt-4",
            ),
            cls="table-content",
        ),
        id="table-section",
        cls="w-full",
    )


def render_columns_section(subtable):
    columns = table.entries[subtable]["columns"]
    return Div(
        Div(
            *[render_column_tag(subtable, col) for col in columns],
            Button(
                UkIcon("plus", height=12),
                cls=ButtonT.secondary + " text-xs px-2 py-1",
                hx_post=f"/table/add-column/{subtable}",
                hx_target="#table-section",
                hx_swap="outerHTML",
            ),
            cls="columns-list flex flex-wrap gap-2 items-center",
        ),
        cls="columns-manager",
    )


def render_column_tag(subtable, col_name):
    return Span(
        Span(col_name, cls="column-name-text mr-1"),
        Button(
            UkIcon("edit-2", height=10),
            cls=ButtonT.ghost + " p-1",
            title="Rename",
            hx_get=f"/table/rename-column-form/{subtable}/{col_name}",
            hx_target=f"#column-{subtable}-{col_name.replace(' ', '-')}",
            hx_swap="outerHTML",
        ),
        Button(
            UkIcon("x", height=10),
            cls=ButtonT.ghost + " p-1 text-destructive",
            title="Delete",
            hx_post=f"/table/delete-column/{subtable}/{col_name}",
            hx_target="#table-section",
            hx_swap="outerHTML",
            hx_confirm="Delete this column?",
        ),
        id=f"column-{subtable}-{col_name.replace(' ', '-')}",
        cls="column-tag inline-flex items-center gap-1 px-2 py-1 border rounded text-xs",
    )


def render_data_table(subtable):
    if not table.entries[subtable]["rows"]:
        return Div(cls="table-empty text-center py-10 text-muted-foreground")

    columns = table.entries[subtable]["columns"]
    rows = table.entries[subtable]["rows"]
    headers = ["#"] + columns + [""]

    table_rows = []
    for row in rows:
        cells = [
            Td(row["id"], cls="table-cell-id px-2 py-1"),
            *[
                Td(
                    Input(
                        type="text",
                        name=f"{subtable}_{row['id']}_{col}",
                        value=row.get(col, ""),
                        cls="inline-input w-full px-2 py-1 border rounded",
                    ),
                    cls="table-cell",
                )
                for col in columns
            ],
            Td(
                Button(
                    UkIcon("trash-2", height=14),
                    cls=ButtonT.ghost + " p-1 text-destructive",
                    hx_post=f"/table/delete-row/{row['id']}",
                    hx_target="#table-section",
                    hx_swap="outerHTML",
                    hx_confirm="Delete this row?",
                ),
                cls="table-cell-actions text-center",
            ),
        ]
        table_rows.append(Tr(*cells))

    return Div(
        Table(
            Thead(
                Tr(*[Th(header, cls="px-2 py-1 text-left") for header in headers]),
                cls="bg-muted",
            ),
            Tbody(*table_rows),
            cls="data-table w-full border-collapse",
        ),
        id=f"{subtable}-table-body",
    )


def render_rename_column_form(subtable, col_name):
    return Span(
        Form(
            Input(
                type="text",
                name="new_name",
                value=col_name,
                required=True,
                cls="rename-input px-2 py-1 text-xs border rounded",
                autofocus=True,
            ),
            Button(
                UkIcon("check", height=10),
                type="submit",
                cls=ButtonT.primary + " p-1",
            ),
            Button(
                UkIcon("x", height=10),
                type="button",
                cls=ButtonT.ghost + " p-1",
                hx_get=f"/table/cancel-rename/{subtable}/{col_name}",
                hx_target=f"#column-{subtable}-{col_name.replace(' ', '-')}",
                hx_swap="outerHTML",
            ),
            hx_post=f"/table/rename-column/{subtable}/{col_name}",
            hx_target="#table-section",
            hx_swap="outerHTML",
            cls="rename-form inline-flex gap-1 items-center",
        ),
        cls="column-tag editing inline-flex items-center gap-1",
    )


# ==================== ROUTES ====================


@rt("/")
def get():
    return Container(
        Meta(name="server-start", content=str(int(time.time()))),
        Script(f"window.DSPY_MODULE_SCHEMAS = {json.dumps(DSPY_MODULE_SCHEMAS)};"),
        ToggleBtn(
            UkIcon("sun", cls="light-icon"),
            UkIcon("moon", cls="dark-icon"),
            cls="theme-toggle-btn fixed top-5 right-5 z-50",
            id="theme-toggle",
        ),
        H1("DSPy Module Builder", cls="main-title text-4xl text-center my-6"),
        Div(
            Div(render_palette(), render_ws(), cls="palette-workspace-row flex gap-6"),
            render_table_section(),
            cls="main-vertical-layout flex flex-col gap-5",
        ),
        cls="container max-w-7xl mx-auto px-4",
    )


# ==================== BLOCK ROUTES ====================


@rt("/add/{btype}")
def add_block(btype: str):
    if btype not in BLOCK_TYPES:
        return render_ws()
    blocks.append(BlockData(btype, len(blocks)))
    return render_ws()


@rt("/update-config/{bid}")
def update_config(bid: str, config: str):
    try:
        config_dict = json.loads(config)
        for block in blocks:
            if block.id == bid:
                block.config = config_dict
                break
    except Exception as e:
        print(f"Error updating config: {e}")
    return render_ws()


@rt("/context-menu/{block_id}")
def get_context_menu(block_id: str):
    block = next((b for b in blocks if b.id == block_id), None)
    if not block:
        return ""

    block_type = block.type
    current_config = block.config or {}
    block_name = MODULE_NAMES.get(block_type, block_type)
    menu = render_context_menu(block_id, block_name, current_config)

    return Html(menu)


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


@rt("/table/add-column/{subtable}")
def add_column(subtable: str):
    global table
    table.add_column(subtable)
    return render_table_section()


@rt("/table/delete-column/{subtable}/{col_name}")
def delete_column(subtable: str, col_name: str):
    global table
    table.delete_column(subtable, col_name)
    return render_table_section()


@rt("/table/rename-column-form/{subtable}/{col_name}")
def rename_column_form(subtable: str, col_name: str):
    return render_rename_column_form(subtable, col_name)


@rt("/table/cancel-rename/{subtable}/{col_name}")
def cancel_rename(subtable: str, col_name: str):
    return render_column_tag(subtable, col_name)


@rt("/table/rename-column/{subtable}/{col_name}")
def rename_column(subtable: str, col_name: str, new_name: str):
    global table
    table.rename_column(subtable, col_name, new_name)
    return render_table_section()


@rt("/table/add-row")
def add_table_row():
    global table
    table.add_row()
    return render_table_section()


@rt("/table/delete-row/{row_id}")
def delete_table_row(row_id: int):
    global table
    table.delete_row(row_id)
    return render_table_section()


@rt("/table/restore", methods=["POST"])
async def restore_table_data(request):
    global table
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            form = await request.form()
            data_str = form.get("data")
            data = json.loads(data_str) if data_str else None
        if data and (data.get("inputs") or data.get("outputs")):
            table.restore(data)
        return render_table_section()
    except Exception as e:
        print(f"Error restoring table: {e}")
        return "Error", 500


@rt("/table/clear", methods=["POST"])
def clear_table():
    global table
    table.clear()
    return render_table_section()


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

if __name__ == "__main__":
    serve(host=HOST, port=PORT)
