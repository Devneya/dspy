from fasthtml.common import *
from monsterui.all import *
from data.table_data import table
import config
import json


def render_column_header(block_id, table_type, column_index, value=""):
    block = next(b for b in config.blocks if b.id == block_id)
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
                cls="bg-muted",
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
                style="padding: 0; margin: 0; height: 41px;",
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
                    cls="w-full border-2 border-transparent outline-0 ring-0 bg-transparent px-3 py-2 m-0 rounded-none block h-full focus:border-primary focus:ring-1 focus:ring-primary",
                    style="box-shadow: none; -webkit-appearance: none; -moz-appearance: none; margin: 0;",
                ),
                cls="border border-border",
                style="padding: 0; margin: 0; height: 41px;",
            )
        )
    if table_type == "outputs":
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
    return Tr(*cells, cls="hover:bg-muted/50", style="padding: 0; margin: 0;")


def render_table_inner(block, table_type):
    columns = block.get_columns(table_type)
    body_content = [render_table_row(row, columns, table_type) for row in table.rows]
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
                    cls="border border-border",
                    style="padding: 0; margin: 0; height: 41px;",
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
        H5(title, cls="mb-3"),
        render_table_inner(block, table_type),
        cls="flex-1 self-start",
    )
