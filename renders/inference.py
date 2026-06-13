from fasthtml.common import *
from monsterui.all import *
from data.table_data import inference_table
import config


def get_top_level_inputs():
    all_inputs = set()
    all_outputs = set()

    for block in config.blocks:
        if hasattr(block, "input_columns"):
            all_inputs.update(block.input_columns)
        if hasattr(block, "output_columns"):
            all_outputs.update(block.output_columns)

    return all_inputs - all_outputs


def render_inference_section():
    top_inputs = sorted(get_top_level_inputs())

    if top_inputs:
        inference_table.columns = set(top_inputs)
        for row in inference_table.rows:
            for col in top_inputs:
                if col not in row:
                    row[col] = ""

    if not inference_table.rows:
        inference_table.add_row()

    if not top_inputs:
        return DivVStacked(
            P("No inputs needed", cls="text-sm text-muted-foreground"),
            DivLAligned(
                Button(
                    UkIcon("play", height=14),
                    Span("Run", cls="ml-1"),
                    cls=(ButtonT.primary, "text-sm"),
                    id="run-inference-btn",
                    hx_post="/infer",
                    hx_target="#inference-results",
                    hx_swap="innerHTML",
                ),
                Button(
                    UkIcon("upload", height=14),
                    Span("Load file", cls="ml-1"),
                    cls=(ButtonT.default, "text-sm ml-2"),
                    **{"onclick": """
                        var input = document.getElementById('inference-file-input');
                        input.onchange = function() { this.closest('form').requestSubmit(); };
                        input.click();
                    """},
                ),
                Span(
                    "", id="inference-status", cls="text-xs text-muted-foreground ml-3"
                ),
                cls="items-center mt-4",
            ),
            Form(
                Input(
                    type="file",
                    name="file",
                    accept=".csv,.json",
                    cls="hidden",
                    id="inference-file-input",
                ),
                hx_post="/inference/upload",
                hx_target="#inference-section",
                hx_swap="outerHTML",
                hx_encoding="multipart/form-data",
                style="display:none;",
            ),
            Div(id="inference-results", cls="mt-4"),
            cls="w-full",
            id="inference-section",
        )

    header_cells = [
        Th(
            "",
            cls="w-12 text-center border border-border bg-muted",
            style="padding: 0; margin: 0;",
        ),
    ]
    for col in top_inputs:
        header_cells.append(
            Th(
                Div(
                    DivLAligned(
                        Input(
                            type="text",
                            value=col,
                            readonly=True,
                            cls="border-0 outline-0 ring-0 bg-transparent font-medium text-sm px-3 py-2 m-0 rounded-none block flex-1 cursor-default",
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

    body_rows = []
    for row in inference_table.rows:
        cells = [
            Td(
                str(row["id"]),
                cls="border border-border text-center text-muted-foreground text-sm w-12",
                style="padding: 0; margin: 0; height: 41px; line-height: 41px;",
            )
        ]
        for col in top_inputs:
            cells.append(
                Td(
                    Input(
                        type="text",
                        value=row.get(col, ""),
                        placeholder=f"Enter {col}",
                        id=f"infer_{row['id']}_{col}",
                        name=f"infer_{row['id']}_{col}",
                        hx_post="/save-inference-cell",
                        hx_trigger="change",
                        hx_vals=f'{{"row_id": "{row["id"]}", "col_name": "{col}"}}',
                        hx_include="this",
                        cls="w-full border-2 border-transparent outline-0 ring-0 bg-transparent px-3 py-2 m-0 rounded-none block h-full focus:border-primary focus:ring-1 focus:ring-primary",
                        style="box-shadow: none; -webkit-appearance: none; -moz-appearance: none; margin: 0;",
                    ),
                    cls="border border-border",
                    style="padding: 0; margin: 0; height: 41px;",
                )
            )
        cells.append(
            Td(
                Button(
                    UkIcon("x"),
                    cls=(ButtonT.link, "text-destructive p-0 shadow-none"),
                    hx_delete=f"/inference/delete-row/{row['id']}",
                    hx_target="#inference-section",
                    hx_swap="outerHTML",
                    title="Delete row",
                ),
                cls="border border-border text-center w-10",
                style="padding: 0; margin: 0; height: 41px;",
            )
        )
        body_rows.append(
            Tr(*cells, cls="hover:bg-muted/50", style="padding: 0; margin: 0;")
        )

    body_rows.append(
        Tr(
            Td(
                Button(
                    UkIcon("plus", height=16),
                    cls=ButtonT.primary,
                    hx_post="/inference/add-row",
                    hx_target="#inference-section",
                    hx_swap="outerHTML",
                    title="Add new row",
                ),
                cls="border border-border",
                style="padding: 0; margin: 0; height: 41px;",
            ),
            style="padding: 0; margin: 0;",
        )
    )

    return DivVStacked(
        Table(
            Thead(Tr(*header_cells, style="padding: 0; margin: 0;")),
            Tbody(*body_rows),
            cls="w-full",
            style="border-collapse: collapse; border-spacing: 0;",
        ),
        DivLAligned(
            Button(
                UkIcon("play", height=14),
                Span("Run", cls="ml-1"),
                cls=(ButtonT.primary, "text-sm mt-4"),
                id="run-inference-btn",
                hx_post="/infer",
                hx_target="#inference-results",
                hx_swap="innerHTML",
            ),
            Button(
                UkIcon("upload", height=14),
                Span("Load file", cls="ml-1"),
                cls=(ButtonT.default, "text-sm mt-4 ml-2"),
                **{"onclick": """
                    var input = document.getElementById('inference-file-input');
                    input.onchange = function() { this.closest('form').requestSubmit(); };
                    input.click();
                """},
            ),
            Span(
                "", id="inference-status", cls="text-xs text-muted-foreground ml-3 mt-4"
            ),
            cls="items-center",
        ),
        Form(
            Input(
                type="file",
                name="file",
                accept=".csv,.json",
                cls="hidden",
                id="inference-file-input",
            ),
            hx_post="/inference/upload",
            hx_target="#inference-section",
            hx_swap="outerHTML",
            hx_encoding="multipart/form-data",
            style="display:none;",
        ),
        Div(id="inference-results", cls="mt-4"),
        cls="w-full",
        id="inference-section",
    )
