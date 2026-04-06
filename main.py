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


def parse_signature(signature_str):
    if not signature_str or "->" not in signature_str:
        return [], []

    inputs_part, outputs_part = map(str.strip, signature_str.split("->", 1))

    def parse_fields(fields_str):
        if not fields_str:
            return []
        fields = []
        for field in fields_str.split(","):
            field = field.strip()
            if not field:
                continue
            if ":" in field:
                name, type = field.split(":", 1)
                fields.append((name.strip(), type.strip()))
            else:
                fields.append((field, "str"))
        return fields

    return parse_fields(inputs_part), parse_fields(outputs_part)


class BlockData:
    def __init__(self, block_type, position):
        global block_id
        self.id = f"b{block_id}"
        self.type = block_type
        self.position = position
        self.label = MODULE_NAMES.get(block_type, block_type)
        self.signature = ""
        self.params = {}
        block_id += 1


class TableData:
    def __init__(self):
        self.columns = []
        self.rows = []
        self.next_id = 1

    def update_columns_from_blocks(self, blocks):
        new_columns = set()
        for block in blocks:
            if block.signature:
                inputs, outputs = parse_signature(block.signature)
                for name, type in inputs:
                    new_columns.add(f"{name}: {type}")
                for name, type in outputs:
                    new_columns.add(f"{name}: {type}")

        old_columns = self.columns
        self.columns = sorted(list(new_columns))

        if old_columns and self.rows:
            new_rows = []
            for row in self.rows:
                new_row = {"id": row["id"]}
                for col in self.columns:
                    new_row[col] = row.get(col, "")
                new_rows.append(new_row)
            self.rows = new_rows
        elif not self.columns:
            self.rows = []

        return self.columns

    def add_row(self):
        row = {"id": self.next_id}
        for col in self.columns:
            row[col] = ""
        self.rows.append(row)
        self.next_id += 1
        return self.rows

    def delete_row(self, row_id):
        self.rows = [r for r in self.rows if r["id"] != row_id]
        return self.rows

    def clear_rows(self):
        self.rows = []
        self.next_id = 1
        return self.rows

    def clear(self):
        self.columns = []
        self.rows = []
        self.next_id = 1
        return self.columns

    def restore(self, data):
        if "columns" in data:
            self.columns = data["columns"]
        if "rows" in data:
            self.rows = data["rows"]
        max_id = 0
        for row in self.rows:
            max_id = max(max_id, row.get("id", 0))
        self.next_id = max_id + 1 if max_id > 0 else 1
        return self.columns


blocks = []
block_id = 1
table = TableData()


# ==================== RENDER FUNCTIONS ====================


def render_palette():
    return Card(
        H3("DSPy Modules", cls="text-lg font-semibold mb-3"),
        Div(
            *[
                Div(
                    Button(
                        UkIcon("grip-vertical", height=14, cls="mr-2"),
                        MODULE_NAMES.get(block_type, block_type),
                        cls=ButtonT.default
                        + " w-full justify-start cursor-grab active:cursor-grabbing",
                        draggable="true",
                        **{"data-block-type": block_type},
                    ),
                    cls="cursor-grab active:cursor-grabbing",
                )
                for block_type in BLOCK_TYPES
            ],
            cls="space-y-2",
        ),
        cls="w-72",
    )


def render_workspace():
    workspace = (
        Div(
            *[render_block(b) for b in sorted(blocks, key=lambda x: x.position)],
            id="working-area",
            cls="space-y-2",
        )
        if blocks
        else Div(
            DivCentered(
                P("Drag and drop modules here", cls="text-muted-foreground text-lg"),
                cls="py-10",
            ),
            id="working-area",
            cls="border-2 border-dashed rounded-lg",
        )
    )

    return Div(
        H3("Pipeline", cls="text-lg font-semibold mb-4"),
        workspace,
        Div(
            Button(
                DivLAligned(UkIcon("trash-2", height=16), " Clear All"),
                hx_post="/clear",
                hx_target="#main-container",
                hx_swap="outerHTML",
                hx_confirm="Remove all blocks and clear all training data?",
                cls=ButtonT.destructive,
            ),
            cls="mt-4",
        ),
        cls="flex-1",
    )


def render_block(block):
    display_text = block.signature if block.signature else "Right click to configure"
    return Div(
        Div(
            Div(
                Span(block.label, cls="font-medium"),
                Span(block.id, cls="text-xs text-muted-foreground ml-2"),
                cls="flex items-center gap-2",
            ),
            Button(
                UkIcon("trash-2", height=14),
                hx_post=f"/rm/{block.id}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                cls=ButtonT.ghost + " p-1",
            ),
            cls="flex justify-between items-center",
        ),
        Div(
            Span(display_text, cls="text-muted-foreground"),
            cls="mt-2 pt-1",
        ),
        id=block.id,
        draggable="true",
        cls="workspace-block p-3 border rounded-lg bg-card cursor-move",
        data_type=block.type,
        data_signature=block.signature,
        data_params=json.dumps(block.params),
    )


def render_context_menu(block_id, block_type, current_signature, current_params):
    schema = DSPY_MODULE_SCHEMAS.get(block_type.lower(), {})
    parameters = schema.get("parameters", {})

    previous_signatures = []
    current_index = next((i for i, b in enumerate(blocks) if b.id == block_id), -1)
    if current_index > 0:
        for b in blocks[:current_index]:
            if b.signature:
                previous_signatures.append(b.signature)

    signature_suggestions = []
    for sig in previous_signatures:
        escaped_sig = sig.replace("'", "\\'")
        signature_suggestions.append(
            Button(
                sig,
                cls="w-full text-left px-3 py-2 text-sm hover:bg-muted rounded",
                onclick=f"document.getElementById('signature-input').value = '{escaped_sig}';",
            )
        )

    signature_tab = Div(
        Div(
            *signature_suggestions,
            cls=(
                "space-y-1 max-h-48 overflow-y-auto mb-3"
                if signature_suggestions
                else ""
            ),
        ),
        Input(
            id="signature-input",
            value=current_signature,
            placeholder="input: type -> output: type",
            cls="w-full px-3 py-2 border rounded-md text-sm",
        ),
        id="signature-tab",
    )

    param_fields = []
    for param_name, param_config in parameters.items():
        input_type = "number" if param_config.get("type") == "int" else "text"
        current_value = current_params.get(param_name, "")
        param_fields.append(
            LabelInput(
                param_name.title(),
                id=f"param-{param_name}",
                value=current_value,
                type=input_type,
            )
        )

    params_tab = Div(
        Div(*param_fields, cls="space-y-3"),
        id="params-tab",
        cls="hidden",
    )

    return Card(
        Div(
            Div(
                Button(
                    "Signature",
                    id="tab-signature-btn",
                    cls=ButtonT.primary + " text-sm px-4 py-2 rounded",
                ),
                Button(
                    "Parameters",
                    id="tab-params-btn",
                    cls=ButtonT.secondary + " text-sm px-4 py-2 rounded",
                ),
                cls="flex gap-2 border-b pb-2 mb-4",
            ),
            signature_tab,
            params_tab,
            Divider(cls="my-4"),
            Button(
                DivLAligned(UkIcon("save", height=16), " Save"),
                cls=ButtonT.primary + " w-full menu-save-btn",
            ),
            cls="p-4",
        ),
        id=f"menu-{block_id}",
        cls="fixed z-50 w-96 shadow-xl border rounded-lg bg-card",
    )


def render_table_section():
    if not table.columns:
        return Div(
            Div(
                H3("Examples", cls="table-main-title text-lg font-semibold"),
                cls="mb-4",
            ),
            Div(
                P(
                    "Configure block signatures to create columns",
                    cls="text-muted-foreground text-center py-10",
                ),
                cls="border-2 border-dashed rounded-lg",
            ),
            id="table-section",
            cls="w-full",
        )
    table_rows = []
    for row in table.rows:
        cells = [
            Td(
                Span(row["id"], cls="inline-block w-full text-center"),
                cls="px-3 py-2 font-mono text-sm w-16 text-center",
            ),
            *[
                Td(
                    Input(
                        type="text",
                        name=f"cell_{row['id']}_{col}",
                        value=row.get(col, ""),
                        cls="w-full px-2 py-1 border rounded text-sm",
                    ),
                    cls="px-2 py-1",
                )
                for col in table.columns
            ],
            Td(
                Button(
                    UkIcon("trash-2", height=14),
                    cls=ButtonT.ghost + " p-1 text-destructive",
                    hx_post=f"/table/delete-row/{row['id']}",
                    hx_target="#table-section",
                    hx_swap="outerHTML",
                ),
                cls="text-center px-2 py-1 w-16",
            ),
        ]
        table_rows.append(Tr(*cells))
    return Div(
        Div(
            Div(
                H3("Training Data", cls="table-main-title text-lg font-semibold"),
                cls="mb-4",
            ),
            Div(
                Table(
                    Thead(
                        Tr(
                            Th(
                                "#",
                                cls="px-3 py-2 text-left text-sm font-medium border-b w-16",
                            ),
                            *[
                                Th(
                                    col,
                                    cls="px-2 py-2 text-left text-sm font-medium border-b",
                                )
                                for col in table.columns
                            ],
                            Th(
                                "",
                                cls="px-2 py-2 text-center text-sm font-medium border-b w-16",
                            ),
                        ),
                        cls="bg-muted",
                    ),
                    Tbody(*table_rows),
                    cls="w-full border-collapse",
                ),
                cls="overflow-x-auto",
            ),
            Div(
                Button(
                    DivLAligned(UkIcon("plus", height=16), " Add Row"),
                    cls=ButtonT.primary,
                    hx_post="/table/add-row",
                    hx_target="#table-section",
                    hx_swap="outerHTML",
                ),
                Button(
                    DivLAligned(UkIcon("trash-2", height=16), " Clear All"),
                    cls=ButtonT.destructive,
                    hx_post="/table/clear",
                    hx_target="#table-section",
                    hx_swap="outerHTML",
                    hx_confirm="Clear all training data rows?",
                ),
                cls="flex justify-end gap-2 mt-4",
            ),
            cls="table-content",
        ),
        id="table-section",
        cls="w-full",
    )


def render_full_page():
    return Container(
        H1("DSPy Module Builder", cls="text-3xl font-bold text-center my-8"),
        Div(
            Div(
                render_palette(),
                render_workspace(),
                cls="flex gap-6",
            ),
            render_table_section(),
            cls="space-y-6",
        ),
        id="main-container",
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
            cls="theme-toggle-btn fixed top-4 right-4 z-50",
            id="theme-toggle",
        ),
        render_full_page(),
    )


@rt("/add/{btype}")
def add_block(btype: str):
    if btype not in BLOCK_TYPES:
        return render_full_page()
    blocks.append(BlockData(btype, len(blocks)))
    table.update_columns_from_blocks(blocks)
    return render_full_page()


@rt("/update-config/{bid}")
def update_config(bid: str, signature: str = "", placeholder_param: str = None):
    params = {}
    if placeholder_param is not None:
        params["placeholder_param"] = placeholder_param

    for block in blocks:
        if block.id == bid:
            block.signature = signature
            block.params = params
            break

    table.update_columns_from_blocks(blocks)
    return render_full_page()


@rt("/context-menu/{block_id}")
def get_context_menu(block_id: str):
    block = next((b for b in blocks if b.id == block_id), None)
    if not block:
        return ""
    return Html(
        render_context_menu(block_id, block.type, block.signature, block.params)
    )


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
    table.update_columns_from_blocks(blocks)
    return render_full_page()


@rt("/clear")
def clear():
    global blocks
    blocks.clear()
    table.update_columns_from_blocks(blocks)
    return render_full_page()


@rt("/rm/{bid}")
def delete_block(bid: str):
    global blocks
    blocks = [b for b in blocks if b.id != bid]
    for i, b in enumerate(blocks):
        b.position = i
    table.update_columns_from_blocks(blocks)
    return render_full_page()


@rt("/table/add-row")
def add_table_row():
    table.add_row()
    return render_table_section()


@rt("/table/delete-row/{row_id}")
def delete_table_row(row_id: int):
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
        if data:
            table.restore(data)
        return render_table_section()
    except Exception as e:
        print(f"Error restoring table: {e}")
        return "Error", 500


@rt("/table/clear", methods=["POST"])
def clear_table():
    table.clear_rows()
    return render_table_section()


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

if __name__ == "__main__":
    serve(host=HOST, port=PORT)
