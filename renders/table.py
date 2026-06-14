from fasthtml.common import *
from monsterui.all import *
from data.table_data import table
import config
import json


def render_column_header(block_id, table_type, column_index, value="", readonly=False):
    block = next(b for b in config.blocks if b.id == block_id)
    if readonly:
        return Div(
            DivLAligned(
                Input(
                    type="text",
                    value=value,
                    readonly=True,
                    cls="border-0 outline-0 ring-0 bg-transparent font-medium text-sm px-3 py-2 m-0 rounded-none block flex-1 cursor-default",
                    style="box-shadow: none;",
                ),
                cls="gap-1 items-center border border-border",
            ),
            cls="relative w-full",
        )
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
                        "window.showColumnSuggestions(this); this.parentElement.classList.add('border-primary', 'ring-1', 'ring-primary')"
                        if table_type == "inputs"
                        else "this.parentElement.classList.add('border-primary', 'ring-1', 'ring-primary')"
                    ),
                    "onblur": "window.validateAndSaveColumn(this); this.parentElement.classList.remove('border-primary', 'ring-1', 'ring-primary')",
                    "oninput": (
                        "window.filterColumnSuggestions(this)"
                        if table_type == "inputs"
                        else "window.checkColumnName(this)"
                    ),
                },
            ),
            Button(
                UkIcon("x", height=14),
                cls=(ButtonT.link, "text-destructive p-0.5 shadow-none"),
                hx_delete=f"/block/{block_id}/delete-column/{table_type}/{column_index}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                title="Delete column",
            ),
            cls="gap-1 items-center border border-border",
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


def render_table_header(block, table_type, readonly=False):
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
                render_column_header(block.id, table_type, i, col, readonly),
                cls="bg-muted",
                style="padding: 0; margin: 0;",
            )
        )
    if not readonly:
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
    if readonly and table_type == "outputs":
        header_cells.append(
            Th(
                Div(
                    DivLAligned(
                        Input(
                            type="text",
                            value="score",
                            readonly=True,
                            cls="border-0 outline-0 ring-0 bg-transparent font-medium text-sm px-3 py-2 m-0 rounded-none block flex-1 cursor-default text-center",
                            style="box-shadow: none;",
                        ),
                        cls="gap-1 items-center border border-border",
                    ),
                    cls="relative w-full",
                ),
                cls="bg-muted",
                style="padding: 0; margin: 0;",
            )
        )
    return Tr(*header_cells, style="padding: 0; margin: 0;")


def render_table_row(row, columns, table_type, readonly=False, block_id_score=None):
    cells = []
    if table_type == "inputs":
        cells.append(
            Td(
                str(row["id"]),
                cls="border border-border text-center text-muted-foreground text-sm w-12",
                style="padding: 0; margin: 0; height: 41px; line-height: 41px;",
            )
        )
    for col in columns:
        cells.append(
            Td(
                Input(
                    type="text",
                    value=row.get(col, ""),
                    placeholder=f"Enter {col}" if not readonly else "",
                    id=f"cell_{row['id']}_{col}",
                    name=f"cell_{row['id']}_{col}",
                    readonly=readonly,
                    hx_post="/save-cell" if not readonly else None,
                    hx_trigger="change delay:300ms" if not readonly else None,
                    hx_vals=f'{{"row_id": "{row["id"]}", "col_name": "{col}"}}' if not readonly else None,
                    hx_include="this",
                    cls=(
                        "w-full border-2 border-transparent outline-0 ring-0 bg-transparent px-3 py-2 m-0 rounded-none block h-full focus:border-primary focus:ring-1 focus:ring-primary"
                        if not readonly
                        else "w-full border-0 outline-0 ring-0 bg-transparent px-3 py-2 m-0 rounded-none block h-full cursor-default"
                    ),
                    style="box-shadow: none; -webkit-appearance: none; -moz-appearance: none; margin: 0;",
                ),
                cls="border border-border",
                style="padding: 0; margin: 0; height: 41px;",
            )
        )
    if table_type == "outputs" and not readonly:
        cells.append(
            Td(
                Button(
                    UkIcon("x"),
                    cls=(ButtonT.link, "text-destructive p-0 shadow-none"),
                    hx_delete=f"/table/delete-row/{row['id']}",
                    hx_target="#main-container",
                    hx_swap="outerHTML",
                    title="Delete row",
                ),
                cls="border border-border text-center w-10",
                style="padding: 0; margin: 0; height: 41px;",
            )
        )
    if readonly and block_id_score and table_type == "outputs":
        cells.append(
            Td(
                Span(
                    "—",
                    id=f"score-{block_id_score}-{row['id']}",
                    cls="reward-score text-sm",
                    style="display: block; line-height: 41px;",
                ),
                cls="border border-border text-center w-16",
                style="padding:0;margin:0;height:41px;",
            )
        )
    return Tr(*cells, cls="hover:bg-muted/50", style="padding: 0; margin: 0;")


def render_table_inner(block, table_type, readonly=False, block_id_score=None):
    columns = block.get_columns(table_type)
    body_content = [
        render_table_row(row, columns, table_type, readonly, block_id_score)
        for row in table.rows
    ]
    if table_type == "inputs" and not readonly:
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
                    cls="border border-border",
                    style="padding: 0; margin: 0; height: 41px;",
                ),
                style="padding: 0; margin: 0;",
            )
        )
    return Table(
        Thead(render_table_header(block, table_type, readonly)),
        Tbody(*body_content if isinstance(body_content, list) else [body_content]),
        cls="w-full {carry_cls}",
        style="border-collapse: collapse; border-spacing: 0; {carry_style}",
    )


def render_table_with_header(block, table_type, readonly=False, block_id_score=None):
    title = "Input Examples" if table_type == "inputs" else "Output Examples"
    return DivVStacked(
        H5(title, cls="mb-3"),
        render_table_inner(block, table_type, readonly, block_id_score),
        cls="flex-1 self-start",
    )
