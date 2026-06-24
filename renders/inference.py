from fasthtml.common import *
from monsterui.all import *
from data.table_data import inference_table
import config
from renders.table import (
    build_add_row_button,
    build_cell,
    build_delete_cell,
    build_header_cell,
    build_row_id_cell,
)


def get_top_level_inputs():
    all_inputs = set()
    all_outputs = set()

    for block in config.blocks:
        if hasattr(block, "input_columns"):
            all_inputs.update(block.input_columns)
        if hasattr(block, "output_columns"):
            all_outputs.update(block.output_columns)

    return all_inputs - all_outputs


def get_output_columns():
    all_outputs = set()
    for block in config.blocks:
        if hasattr(block, "output_columns"):
            all_outputs.update(block.output_columns)
    return all_outputs


def render_input_table():
    top_inputs = sorted(get_top_level_inputs())
    if not top_inputs:
        return Div(P("No inputs needed", cls="text-sm text-muted-foreground"))
    if not inference_table.rows:
        inference_table.add_row()
    header_cells = [
        Th(
            "",
            cls="w-12 text-center border border-border bg-muted",
            style="padding: 0; margin: 0;",
        )
    ]
    for col in top_inputs:
        header_cells.append(build_header_cell(col))
    body_rows = []
    for row in inference_table.rows:
        cells = [build_row_id_cell(row["id"])]
        for col in top_inputs:
            cells.append(
                build_cell(
                    value=row.get(col, ""),
                    col=col,
                    row_id=row["id"],
                    placeholder=f"Enter {col}",
                    cell_attrs=lambda r, c: {
                        "hx_post": "/save-inference-cell",
                        "hx_trigger": "change",
                        "hx_vals": f'{{"row_id": "{r}", "col_name": "{c}"}}',
                        "hx_include": "this",
                        "hx_swap": "none",
                    },
                    row_id_prefix="infer",
                )
            )
        cells.append(
            build_delete_cell("/inference/delete-row", row["id"], "#inference-section")
        )
        body_rows.append(
            Tr(*cells, cls="hover:bg-muted/50", style="padding: 0; margin: 0;")
        )
    body_rows.append(
        Tr(
            build_add_row_button("/inference/add-row", "#inference-section"),
            style="padding: 0; margin: 0;",
        )
    )
    return DivVStacked(
        H5("Inputs", cls="mb-3"),
        Table(
            Thead(Tr(*header_cells, style="padding: 0; margin: 0;")),
            Tbody(*body_rows),
            cls="w-full",
            style="border-collapse: collapse; border-spacing: 0;",
        ),
        cls="flex-1 self-start",
    )


def render_output_table():
    output_cols = sorted(get_output_columns())
    result_cols = [
        c
        for c in sorted(inference_table.columns - {"id"})
        if c not in get_top_level_inputs()
    ]
    all_outputs = output_cols + [c for c in result_cols if c not in output_cols]
    if not all_outputs:
        return DivVStacked(
            H5("Outputs", cls="mb-3"),
            P("Run inference to see results", cls="text-sm text-muted-foreground"),
            cls="flex-1 self-start",
        )

    header_cells = []
    for col in all_outputs:
        header_cells.append(build_header_cell(col))
    body_rows = []
    for row in inference_table.rows:
        cells = []
        for col in all_outputs:
            cells.append(
                build_cell(
                    value=row.get(col, "—"), col=col, row_id=row["id"], readonly=True
                )
            )
        body_rows.append(
            Tr(*cells, cls="hover:bg-muted/50", style="padding: 0; margin: 0;")
        )
    return DivVStacked(
        H5("Outputs", cls="mb-3"),
        Table(
            Thead(Tr(*header_cells, style="padding: 0; margin: 0;")),
            Tbody(*body_rows),
            cls="w-full",
            style="border-collapse: collapse; border-spacing: 0;",
        ),
        cls="flex-1 self-start",
    )


def render_inference_section():
    return DivVStacked(
        Div(
            Div(render_input_table(), style="flex: 1;"),
            Div(render_output_table(), style="flex: 1;"),
            style="display: flex; gap: 0; width: 100%; margin-top: 16px;",
        ),
        DivLAligned(
            Button(
                UkIcon("upload", height=14),
                Span("Load Inputs", cls="ml-1"),
                cls=(ButtonT.default, "text-sm mt-4 ml-2"),
                **{
                    "onclick": "document.getElementById('inference-file-input').click()"
                },
            ),
            Button(
                UkIcon("play", height=14),
                Span("Run", cls="ml-1"),
                cls=(ButtonT.primary, "text-sm mt-4"),
                hx_post="/infer",
                hx_target="#inference-section",
                hx_swap="outerHTML",
                hx_include="[id^='infer_']",
            ),
            Button(
                UkIcon("download", height=14),
                Span("Save Outputs", cls="ml-1"),
                cls=(ButtonT.default, "text-sm mt-4 ml-2"),
                **{"onclick": "window.location.href='/inference/download'"},
            ),
            Span(
                "", id="inference-status", cls="text-xs text-muted-foreground ml-3 mt-4"
            ),
            cls="items-center",
        ),
        Input(
            type="file",
            name="file",
            accept=".csv,.json,.yaml,.yml",
            cls="hidden",
            id="inference-file-input",
            hx_post="/inference/upload",
            hx_target="#inference-section",
            hx_swap="outerHTML",
            hx_encoding="multipart/form-data",
            hx_trigger="change",
        ),
        cls="w-full",
        id="inference-section",
    )
