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
        self.input_columns = self.get_default_input_columns(position)
        self.output_columns = self.get_default_output_columns(position)
        self.params = {}
        block_id += 1

    def get_default_input_columns(self, position):
        if position == 0:
            return ["Question"]
        prev_block = blocks[position - 1] if position > 0 else None
        if prev_block and prev_block.output_columns:
            return [prev_block.output_columns[0]]
        return ["Input"]

    def get_default_output_columns(self, position):
        return ["Answer"] if position == 0 else [f"Output_{position+1}"]

    def get_columns(self, table_type):
        return self.input_columns if table_type == "inputs" else self.output_columns

    def get_used_column_names(self, table_type=None):
        used = set()
        for b in blocks:
            if b.position < self.position:
                used.update([c for c in b.input_columns if c and c.strip()])
                used.update([c for c in b.output_columns if c and c.strip()])
        if table_type == "outputs":
            used.update([c for c in self.input_columns if c and c.strip()])
            used.update([c for c in self.output_columns if c and c.strip()])
        return used

    def delete_column(self, table_type, col_index):
        columns = self.input_columns if table_type == "inputs" else self.output_columns
        if col_index < len(columns):
            return columns.pop(col_index)
        return None


class TableData:
    def __init__(self):
        self.columns = {"Input", "Output"}
        self.rows = []
        self.next_id = 1

    def sync_columns_from_blocks(self, blocks):
        new_cols = {
            c
            for b in blocks
            for c in (*b.input_columns, *b.output_columns)
            if c and c.strip()
        } or {"Input", "Output"}

        if self.columns != new_cols:
            for row in self.rows:
                for col in new_cols - set(row.keys()):
                    row[col] = ""
                for col in set(row.keys()) - new_cols - {"id"}:
                    del row[col]
            self.columns = new_cols

        return list(self.columns)

    def add_row(self):
        row = {"id": self.next_id}
        for col in self.columns:
            row[col] = ""
        self.rows.append(row)
        self.next_id += 1
        return self.rows

    def delete_row(self, row_id):
        self.rows = [r for r in self.rows if r["id"] != row_id]
        for i, row in enumerate(self.rows, 1):
            row["id"] = i
        self.next_id = len(self.rows) + 1
        return self.rows

    def clear_rows(self):
        self.rows = []
        self.next_id = 1
        return self.rows

    def update_cell(self, row_id, col_name, value):
        for row in self.rows:
            if row["id"] == row_id:
                row[col_name] = value
                return True
        return False


init_predict = False
blocks = []
block_id = 1
active_block_id = None
table = TableData()


# ==================== RENDER FUNCTIONS ====================


def render_tab_item(block):
    is_active = active_block_id == block.id
    active_cls = "border-primary text-primary" if is_active else "border-transparent"
    return DivLAligned(
        UkIcon("grip-vertical", height=14, cls="cursor-grab text-muted-foreground"),
        Span(block.label),
        Button(
            UkIcon("x", height=12),
            cls=(ButtonT.ghost, "text-destructive p-0.5"),
            hx_post=f"/rm/{block.id}",
            hx_target="#main-container",
            hx_swap="outerHTML",
            **{"onclick": "event.stopPropagation()"},
            title="Delete module",
        ),
        cls=f"px-4 py-2 cursor-pointer border-b-2 {active_cls} gap-2",
        id=f"tab-{block.id}",
        **{
            "data-block-id": block.id,
            "hx_get": f"/select-tab/{block.id}",
            "hx_target": "#main-container",
            "hx_swap": "outerHTML",
        },
    )


def render_add_block_dropdown():
    return Div(
        Button(
            UkIcon("plus", height=16),
            cls=ButtonT.primary,
            **{"onclick": "toggleAddBlockMenu()"},
            title="Add new module",
        ),
        Div(
            *[
                Button(
                    MODULE_NAMES.get(block_type, block_type),
                    cls=(ButtonT.default, "w-full justify-start"),
                    hx_post=f"/add/{block_type}",
                    hx_target="#main-container",
                    hx_swap="outerHTML",
                    **{"onclick": "toggleAddBlockMenu()"},
                )
                for block_type in BLOCK_TYPES
            ],
            id="add-block-menu",
            cls="hidden absolute right-0 z-50 mt-1 w-56",
        ),
        cls="relative ml-2",
    )


def render_tabs():
    if not blocks:
        return render_empty_state()

    return DivVStacked(
        DivFullySpaced(
            DivLAligned(
                DivLAligned(
                    *[
                        render_tab_item(block)
                        for block in sorted(blocks, key=lambda x: x.position)
                    ],
                    id="tabs-container",
                    cls="gap-0.5 overflow-x-auto",
                ),
                render_add_block_dropdown(),
                cls="gap-2",
            ),
            Div(),
        ),
        DividerSplit(cls="my-2"),
        cls="mb-6",
    )


def render_column_header(block_id, table_type, column_index, value=""):
    block = next(b for b in blocks if b.id == block_id)
    used_columns = block.get_used_column_names(table_type)
    available_columns = (
        sorted(list(block.get_used_column_names())) if table_type == "inputs" else []
    )
    is_new = not value
    return Div(
        DivLAligned(
            Input(
                type="text",
                value=value,
                placeholder="Column name",
                name=f"col_{table_type}_{column_index}",
                autofocus=is_new,
                cls="border-0 outline-0 ring-0 bg-transparent font-medium text-sm px-3 py-2 m-0 rounded-none block flex-1",
                style="box-shadow: none;",
                **{
                    "data-block-id": block_id,
                    "data-table-type": table_type,
                    "data-column-index": column_index,
                    "data-original-value": value,
                    "data-is-new": str(is_new).lower(),
                    "data-available-columns": json.dumps(available_columns),
                    "data-used-columns": json.dumps(list(used_columns)),
                    "onfocus": (
                        "window.showColumnSuggestions(this)"
                        if table_type == "inputs"
                        else ""
                    ),
                    "onblur": "window.validateAndSaveColumn(this)",
                    "oninput": (
                        "window.filterColumnSuggestions(this)"
                        if table_type == "inputs"
                        else "window.checkColumnName(this)"
                    ),
                },
            ),
            Button(
                UkIcon("x", height=14),
                cls=(ButtonT.ghost, "text-destructive p-0.5"),
                hx_delete=f"/block/{block_id}/delete-column/{table_type}/{column_index}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                title="Delete column",
            ),
            cls="gap-1 items-center border border-border focus-within:border-primary focus-within:ring-1 focus-within:ring-primary",
        ),
        (
            Div(
                cls="column-suggestions hidden absolute z-50 mt-1 w-full bg-card border rounded shadow-lg max-h-48 overflow-y-auto overflow-x-auto"
            )
            if table_type == "inputs"
            else ""
        ),
        Div(cls="column-error hidden text-xs text-destructive mt-1"),
        cls="relative w-full",
    )


def render_table_header(block, table_type):
    columns = block.get_columns(table_type)
    header_cells = []
    if table_type == "inputs":
        header_cells.append(
            Th(
                "",
                cls="w-12 text-center border border-border bg-muted",
                style="padding: 0; margin: 0;",
            )
        )
    for i, col in enumerate(columns):
        header_cells.append(
            Th(
                render_column_header(block.id, table_type, i, col),
                cls="border border-border bg-muted",
                style="padding: 0; margin: 0;",
            )
        )
    header_cells.append(
        Th(
            Button(
                UkIcon("plus", height=14),
                cls=ButtonT.primary,
                hx_post=f"/block/{block.id}/add-column/{table_type}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                title="Add new column",
            ),
            cls="w-10 border border-border bg-muted",
            style="padding: 0; margin: 0;",
        )
    )
    return Tr(*header_cells, style="padding: 0; margin: 0;")


def render_table_row(row, columns, table_type):
    cells = []

    if table_type == "inputs":
        cells.append(
            Td(
                str(row["id"]),
                cls="border border-border text-center text-muted-foreground text-sm w-12",
                style="padding: 0; margin: 0;",
            )
        )

    for col in columns:
        cells.append(
            Td(
                Input(
                    type="text",
                    value=row.get(col, ""),
                    placeholder="Enter value",
                    id=f"cell_{row['id']}_{col}",
                    name=f"cell_{row['id']}_{col}",
                    **{
                        "data-row-id": row["id"],
                        "data-col": col,
                        "onchange": f"saveCell(this, {row['id']}, '{col}')",
                    },
                    cls="w-full border border-border outline-0 ring-0 bg-transparent px-3 py-2 m-0 focus:border-primary focus:ring-1 focus:ring-primary rounded-none block",
                    style="box-shadow: none; -webkit-appearance: none; -moz-appearance: none; margin: 0;",
                ),
                style="padding: 0; margin: 0;",
            )
        )

    if table_type == "outputs":
        cells.append(
            Td(
                Button(
                    UkIcon("x"),
                    cls=(ButtonT.ghost, "text-destructive p-0"),
                    hx_delete=f"/table/delete-row/{row['id']}",
                    hx_target="#main-container",
                    hx_swap="outerHTML",
                    style="padding: 0; margin: 0;",
                    title="Delete row",
                ),
                cls="border border-border text-center w-10",
                style="padding: 0; margin: 0;",
            )
        )
    return Tr(*cells, cls="hover:bg-muted/50", style="padding: 0; margin: 0;")


def render_table_inner(block, table_type):
    columns = block.get_columns(table_type)
    if not table.rows:
        body_content = Tr(
            Td(
                "Click '+' to add data",
                colspan=len(columns) + (2 if table_type == "inputs" else 1),
                cls=(TextT.center, TextPresets.muted_sm, "py-8 border border-border"),
            )
        )
    else:
        body_content = [
            render_table_row(row, columns, table_type) for row in table.rows
        ]
        if table_type == "inputs":
            body_content.append(
                Tr(
                    Td(
                        Button(
                            UkIcon("plus", height=16),
                            cls=ButtonT.primary,
                            hx_post="/table/add-row",
                            hx_target="#main-container",
                            hx_swap="outerHTML",
                            title="Add new row",
                        ),
                        style="padding: 0; margin: 0;",
                    ),
                    style="padding: 0; margin: 0;",
                )
            )
    return Table(
        Thead(render_table_header(block, table_type)),
        Tbody(*body_content if isinstance(body_content, list) else [body_content]),
        cls="w-full",
        style="border-collapse: collapse; border-spacing: 0;",
    )


def render_table_with_header(block, table_type):
    title = "Input Examples" if table_type == "inputs" else "Output Examples"
    return DivVStacked(
        DivFullySpaced(
            H5(title, cls="mb-0"),
            Button(
                UkIcon("rotate-ccw", height=14),
                cls=ButtonT.ghost,
                hx_post=f"/block/{block.id}/reset-columns/{table_type}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                hx_confirm=f"Reset {title.lower()}?",
                title=f"Reset {title.lower()}",
            ),
            cls="mb-0",
        ),
        render_table_inner(block, table_type),
        cls="flex-1 self-start",
    )


def render_empty_state():
    return DivCentered(
        Button(
            DivLAligned(UkIcon("plus", height=16), "Add your first module"),
            cls=ButtonT.primary,
            **{"onclick": "toggleAddBlockMenu()"},
        ),
        Div(
            *[
                Button(
                    MODULE_NAMES.get(block_type, block_type),
                    cls=(ButtonT.default, "w-full justify-start"),
                    hx_post=f"/add/{block_type}",
                    hx_target="#main-container",
                    hx_swap="outerHTML",
                    **{"onclick": "toggleAddBlockMenu()"},
                )
                for block_type in BLOCK_TYPES
            ],
            id="add-block-menu",
            cls="hidden absolute z-50 mt-1 w-56",
        ),
        cls="py-8",
    )


def render_full_page():
    active_block = (
        next((b for b in blocks if b.id == active_block_id), None)
        if active_block_id
        else (blocks[0] if blocks else None)
    )
    return Container(
        render_tabs_view(active_block),
        id="main-container",
        cls=ContainerT.xl,
    )


def render_tabs_view(active_block):
    return DivVStacked(
        Div(render_tabs(), cls="w-full"),
        (
            (
                DivLAligned(
                    (
                        render_table_with_header(active_block, "inputs")
                        if active_block
                        else ""
                    ),
                    (
                        render_table_with_header(active_block, "outputs")
                        if active_block
                        else ""
                    ),
                    cls="w-full",
                )
                if active_block
                else ""
            ),
        ),
    )


# ==================== ROUTES ====================


@rt("/")
def get():
    global blocks, init_predict, active_block_id
    if not blocks and not init_predict:
        init_predict = True
        blocks.append(BlockData("predict", 0))
        active_block_id = blocks[0].id
        for _ in range(5):
            table.add_row()
        table.rows[0]["Question"] = "What is the capital of Great Britain?"
        table.rows[0]["Answer"] = "London is the capital of Great Britain."

    return Container(
        Meta(name="server-start", content=str(int(time.time()))),
        Script(f"window.DSPY_MODULE_SCHEMAS = {json.dumps(DSPY_MODULE_SCHEMAS)};"),
        ToggleBtn(
            UkIcon("sun", cls="light-icon"),
            UkIcon("moon", cls="dark-icon"),
            cls="fixed bottom-4 right-4 z-50",
            id="theme-toggle",
        ),
        render_full_page(),
    )


@rt("/select-tab/{block_id}")
def select_tab(block_id: str):
    global active_block_id
    active_block_id = block_id
    return render_full_page()


@rt("/add/{btype}")
def add_block(btype: str):
    global active_block_id
    if btype not in BLOCK_TYPES:
        return render_full_page()

    new_block = BlockData(btype, len(blocks))
    blocks.append(new_block)
    active_block_id = new_block.id
    table.sync_columns_from_blocks(blocks)
    return render_full_page()


@rt("/reorder-tabs")
def reorder_tabs(order: str):
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
    return render_full_page()


@rt("/rm/{bid}")
def delete_block(bid: str):
    global blocks, active_block_id
    blocks = [b for b in blocks if b.id != bid]
    for i, b in enumerate(blocks):
        b.position = i

    if active_block_id == bid:
        active_block_id = blocks[0].id if blocks else None

    table.sync_columns_from_blocks(blocks)
    return render_full_page()


@rt("/block/{block_id}/add-column/{table_type}")
def add_column(block_id: str, table_type: str):
    block = next((b for b in blocks if b.id == block_id), None)
    if block is not None:
        if table_type == "inputs":
            block.input_columns.append("")
        else:
            block.output_columns.append("")
        table.sync_columns_from_blocks(blocks)
    return render_full_page()


@rt("/block/{block_id}/delete-column/{table_type}/{col_index}", methods=["DELETE"])
def delete_column(block_id: str, table_type: str, col_index: int):
    block = next((b for b in blocks if b.id == block_id), None)
    if block is not None:
        columns = (
            block.input_columns if table_type == "inputs" else block.output_columns
        )
        if len(columns) > 1:
            block.delete_column(table_type, col_index)
            table.sync_columns_from_blocks(blocks)
    return render_full_page()


@rt("/block/{block_id}/reset-columns/{table_type}")
def reset_columns(block_id: str, table_type: str):
    block = next((b for b in blocks if b.id == block_id), None)
    if block is not None:
        if table_type == "inputs":
            block.input_columns = block.get_default_input_columns(block.position)
        else:
            block.output_columns = block.get_default_output_columns(block.position)
        table.sync_columns_from_blocks(blocks)
    return render_full_page()


@rt("/save-column", methods=["POST"])
async def save_column(request):
    form = await request.form()
    block_id = form.get("block_id", "")
    table_type = form.get("table_type", "")
    col_index = int(form.get("col_index", 0))
    value = form.get("value", "").strip()
    original_value = form.get("original_value", "")
    is_new = form.get("is_new", "false").lower() == "true"

    block = next((b for b in blocks if b.id == block_id), None)
    if not block:
        return ""

    columns = block.input_columns if table_type == "inputs" else block.output_columns
    if col_index >= len(columns):
        return ""

    if not value:
        if is_new and len(columns) > 1:
            del columns[col_index]
            table.sync_columns_from_blocks(blocks)
            return render_full_page()
        columns[col_index] = original_value
        return ""

    if table_type == "outputs":
        used_columns = block.get_used_column_names("outputs") - {original_value}
        if value in used_columns:
            columns[col_index] = original_value
            return ""

    columns[col_index] = value
    table.sync_columns_from_blocks(blocks)
    return ""


@rt("/table/add-row")
def add_table_row():
    table.add_row()
    return render_full_page()


@rt("/table/delete-row/{row_id}", methods=["DELETE"])
def delete_table_row(row_id: int):
    table.delete_row(row_id)
    return render_full_page()


@rt("/save-cell", methods=["POST"])
async def save_cell(request):
    form = await request.form()
    row_id = int(form.get("row_id", 0))
    col_name = form.get("col_name", "")
    value = form.get("value", "")

    table.update_cell(row_id, col_name, value)
    return ""


@rt("/save-param", methods=["POST"])
async def save_param(request):
    form = await request.form()
    block_id = form.get("block_id", "")
    param_name = form.get("param_name", "")
    value = form.get("value", "")

    block = next((b for b in blocks if b.id == block_id), None)
    if block:
        block.params[param_name] = value

    return ""


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

if __name__ == "__main__":
    serve(host=HOST, port=PORT)
