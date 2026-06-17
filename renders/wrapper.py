from fasthtml.common import *
from monsterui.all import *
from data.table_data import table
from renders.table import render_table_inner
import json


def render_wrapper_workspace(block):
    wrapped = block.get_wrapped_block()
    rows_json = json.dumps(table.rows)
    wrapped_inputs_json = json.dumps(wrapped.input_columns)
    wrapped_outputs_json = json.dumps(wrapped.output_columns)

    return Div(
        DivVStacked(
            H4("Example Data", cls="mb-3 mt-6"),
        ),
        Div(
            Div(
                render_table_inner(wrapped, "inputs", readonly=True),
                style="flex: 1; border-right: 3px solid hsl(var(--muted-foreground));",
            ),
            Div(
                render_table_inner(
                    wrapped, "outputs", readonly=True, block_id_score=block.id
                ),
                style="flex: 1;",
            ),
            style="display: flex; gap: 0; width: 100%; margin-top: 16px;",
        ),
        DivVStacked(
            DivHStacked(
                DivVStacked(
                    H5("Threshold", cls="mb-3 mt-6"),
                    Input(
                        type="number",
                        value=str(block.threshold),
                        step="0.05",
                        min="0",
                        id=f"threshold-{block.id}",
                        name="threshold",
                        cls="w-32",
                        hx_post="/save-threshold",
                        hx_vals=f'{{"block_id": "{block.id}"}}',
                        hx_trigger="change",
                        **{
                            "onchange": f"window._wrapperData['{block.id}'].threshold = parseFloat(this.value);",
                            "data-block-id": block.id,
                        },
                    ),
                    cls="gap-0",
                ),
                DivVStacked(
                    H5("Repeat Count", cls="mb-3 mt-6"),
                    Input(
                        type="number",
                        value=str(block.N),
                        step="1",
                        min="1",
                        id=f"repeat-{block.id}",
                        name="repeat",
                        cls="w-32",
                        hx_post="/save-repeat",
                        hx_vals=f'{{"block_id": "{block.id}"}}',
                        hx_trigger="change",
                    ),
                    cls="gap-0",
                ),
            ),
            DivCentered(
                DivLAligned(
                    H5("Reward Function", cls="mb-0"),
                    Button(
                        UkIcon("save", height=14),
                        cls=(
                            ButtonT.link,
                            "text-sm ml-2 p-0 flex-shrink-0 shadow-none opacity-60 hover:opacity-100",
                        ),
                        **{
                            "onclick": f"window.DSPyRewardEditor.saveCode('{block.id}')"
                        },
                    ),
                    Button(
                        UkIcon("play", height=14),
                        cls=(
                            ButtonT.link,
                            "text-sm text-primary ml-2 p-0 flex-shrink-0 shadow-none opacity-60 hover:opacity-100",
                        ),
                        id=f"test-btn-{block.id}",
                        **{
                            "onclick": f"window.DSPyRewardEditor.testReward('{block.id}')"
                        },
                    ),
                    Span(
                        "",
                        id=f"test-status-{block.id}",
                        cls="text-xs text-muted-foreground ml-2 p-0",
                    ),
                    cls="items-center gap-0",
                ),
                cls="mb-3",
            ),
            P(
                Code("reward_fn(inputs, prediction)"),
                Span(" → scalar (float, int, bool)", cls="text-muted-foreground"),
                cls="text-sm mb-3 m-0",
            ),
            Div(
                id=f"monaco-editor-{block.id}",
                cls="monaco-container border rounded-lg overflow-hidden",
                style="min-height: 200px;",
                **{
                    "data-code": block.reward_code,
                    "data-block-id": block.id,
                },
            ),
            Textarea(
                block.reward_code,
                id=f"code-editor-{block.id}",
                name="reward_code",
                style="display:none;",
            ),
        ),
        Script(f"""
            window._wrapperData = window._wrapperData || {{}};
            window._wrapperData['{block.id}'] = {{
                rows: {rows_json},
                inputCols: {wrapped_inputs_json},
                outputCols: {wrapped_outputs_json},
                threshold: {block.threshold},
            }};
            setTimeout(function() {{
                if (window.DSPyRewardEditor) {{
                    window.DSPyRewardEditor.createEditor('{block.id}');
                }}
            }}, 100);
        """),
        cls="mt-6 w-full",
    )
