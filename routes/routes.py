from fasthtml.common import *
from monsterui.all import *
from data.block_data import create_block, RegularBlock, WrapperBlock
from data.table_data import table, inference_table
from renders.inference import get_top_level_inputs, render_inference_section
from renders.page import render_full_page
import config
import json
import time

app, rt = fast_app(
    live=False,
    hdrs=Theme.blue.headers(daisy=True, icons=True)
    + [
        Meta(name="live-reload", content="disabled"),
        Script(
            src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js",
            defer=True,
        ),
        Script(
            src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js",
            defer=True,
        ),
        Script(src="/static/scripts.js", defer=True),
        Script(src="/static/editor.js", defer=True),
    ],
)


@rt("/")
def get():
    if not config.blocks and not config.init_predict:
        config.init_predict = True
        config.blocks.append(create_block("predict", 0))
        config.active_block_id = config.blocks[0].id
        config.blocks[0].input_columns = ["mood", "question"]
        config.blocks[0].output_columns = ["answer"]
        table.sync_columns_from_blocks(config.blocks)
        table.add_row()
        table.rows[0]["mood"] = "good"
        table.rows[0]["question"] = "How are you doing?"
        table.rows[0]["answer"] = "Great, thanks! And you?"
        table.add_row()
        table.rows[1]["mood"] = "neutral"
        table.rows[1]["question"] = "What's up?"
        table.rows[1]["answer"] = "Not much, what about you?"
        table.add_row()
        table.rows[2]["mood"] = "bad"
        table.rows[2]["question"] = "How's it going?"
        table.rows[2]["answer"] = "Horrible, that's how. You?"

    return Container(
        Meta(name="server-start", content=str(int(time.time()))),
        Script(
            f"window.DSPY_MODULE_SCHEMAS = {json.dumps(config.DSPY_MODULE_SCHEMAS)};"
        ),
        ToggleBtn(
            UkIcon("sun", cls="light-icon"),
            UkIcon("moon", cls="dark-icon"),
            cls="fixed bottom-4 right-4 z-50 shadow-none",
            id="theme-toggle",
        ),
        render_full_page(),
    )


@rt("/optimize", methods=["POST"])
async def optimize_all():
    config.is_optimized = True
    return (render_inference_section(),)


@rt("/select-tab/{block_id}")
def select_tab(block_id: str):
    config.active_block_id = block_id
    return render_full_page()


@rt("/add/{btype}")
def add_block(btype: str):
    if btype not in config.BLOCK_TYPES:
        return render_full_page()
    if btype in config.WRAPPER_TYPES and (
        len(config.blocks) == 0 or isinstance(config.blocks[-1], WrapperBlock)
    ):
        return render_full_page()
    new_block = create_block(btype, len(config.blocks))
    config.blocks.append(new_block)
    config.active_block_id = new_block.id
    table.sync_columns_from_blocks(config.blocks)
    config.mark_unoptimized()
    return render_full_page()


@rt("/reorder-tabs")
def reorder_tabs(order: str):
    try:
        new_order = json.loads(order)
        block_map = {b.id: b for b in config.blocks}
        reordered = [block_map[bid] for bid in new_order if bid in block_map]
        if len(reordered) != len(config.blocks):
            return render_full_page()
        if isinstance(reordered[0], WrapperBlock):
            return render_full_page()
        for i, b in enumerate(reordered):
            if isinstance(b, WrapperBlock):
                if i > 0 and not isinstance(reordered[i - 1], WrapperBlock):
                    b.wrapped_block_id = reordered[i - 1].id
        for i, b in enumerate(reordered):
            if isinstance(b, WrapperBlock) and isinstance(
                reordered[i - 1], WrapperBlock
            ):
                return render_full_page()
        config.blocks[:] = reordered
        for i, b in enumerate(config.blocks):
            b.position = i
    except Exception:
        pass
    config.mark_unoptimized()
    return render_full_page()


@rt("/rm/{bid}")
def delete_block(bid: str):
    remaining = [b for b in config.blocks if b.id != bid]
    if remaining and isinstance(remaining[0], WrapperBlock):
        return render_full_page()
    for i in range(len(remaining) - 1):
        if isinstance(remaining[i], WrapperBlock) and isinstance(
            remaining[i + 1], WrapperBlock
        ):
            return render_full_page()
    config.blocks[:] = remaining
    for i, b in enumerate(config.blocks):
        b.position = i
        if isinstance(b, WrapperBlock):
            b.wrapped_block_id = config.blocks[i - 1].id if i > 0 else None
    if config.active_block_id == bid:
        config.active_block_id = config.blocks[0].id if config.blocks else None
    table.sync_columns_from_blocks(config.blocks)
    config.mark_unoptimized()
    return render_full_page()


@rt("/block/{block_id}/add-column/{table_type}")
def add_column(block_id: str, table_type: str):
    block = next((b for b in config.blocks if b.id == block_id), None)
    if block is not None and isinstance(block, RegularBlock):
        if table_type == "inputs":
            block.input_columns.append("")
        else:
            block.output_columns.append("")
        table.sync_columns_from_blocks(config.blocks)
    config.mark_unoptimized()
    return render_full_page()


@rt("/block/{block_id}/delete-column/{table_type}/{col_index}", methods=["DELETE"])
def delete_column(block_id: str, table_type: str, col_index: int):
    block = next((b for b in config.blocks if b.id == block_id), None)
    if block is not None and isinstance(block, RegularBlock):
        columns = (
            block.input_columns if table_type == "inputs" else block.output_columns
        )
        if len(columns) > 1:
            block.delete_column(table_type, col_index)
            table.sync_columns_from_blocks(config.blocks)
    config.mark_unoptimized()
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

    block = next((b for b in config.blocks if b.id == block_id), None)
    if not block:
        return ""
    columns = block.input_columns if table_type == "inputs" else block.output_columns
    if col_index >= len(columns):
        return ""
    if not value:
        if is_new and len(columns) > 1:
            del columns[col_index]
            table.sync_columns_from_blocks(config.blocks)
            return render_full_page()
        columns[col_index] = original_value
        return ""
    if table_type == "outputs":
        used_columns = block.get_used_column_names("outputs") - {original_value}
        if value in used_columns:
            columns[col_index] = original_value
            return ""
    columns[col_index] = value
    table.sync_columns_from_blocks(config.blocks)
    config.mark_unoptimized()
    # fix later
    return Response(
        status_code=200,
        headers={"HX-Refresh": "true"}
    )


@rt("/table/add-row")
def add_table_row():
    table.add_row()
    config.mark_unoptimized()
    return render_full_page()


@rt("/table/delete-row/{row_id}", methods=["DELETE"])
def delete_table_row(row_id: int):
    table.delete_row(row_id)
    config.mark_unoptimized()
    return render_full_page()


@rt("/save-cell", methods=["POST"])
async def save_cell(request):
    form = await request.form()
    row_id = int(form.get("row_id", 0))
    col_name = form.get("col_name", "")
    for key, value in form.items():
        if key not in ("row_id", "col_name"):
            table.update_cell(row_id, col_name, value)
            break
    return ""


@rt("/save-reward-code", methods=["POST"])
async def save_reward_code(request):
    form = await request.form()
    block_id = form.get("block_id", "")
    code = form.get("code", "")
    block = next((b for b in config.blocks if b.id == block_id), None)
    if block and isinstance(block, WrapperBlock):
        block.reward_code = code
    config.mark_unoptimized()
    return ""


@rt("/save-threshold", methods=["POST"])
async def save_threshold(request):
    form = await request.form()
    block_id = form.get("block_id", "")
    threshold = form.get("threshold", "0.5")
    block = next((b for b in config.blocks if b.id == block_id), None)
    if block and isinstance(block, WrapperBlock):
        try:
            block.threshold = float(threshold)
        except ValueError:
            pass
    config.mark_unoptimized()
    return ""


@rt("/switch-mode/{mode}")
def switch_mode(mode: str):
    if mode in ("build", "use"):
        config.current_mode = mode
    return render_full_page()


@rt("/inference/add-row")
def add_inference_row():
    inference_table.add_row()
    return render_inference_section()


@rt("/inference/delete-row/{row_id}", methods=["DELETE"])
def delete_inference_row(row_id: int):
    inference_table.delete_row(row_id)
    return render_inference_section()


@rt("/save-inference-cell", methods=["POST"])
async def save_inference_cell(request):
    form = await request.form()
    row_id = int(form.get("row_id", 0))
    col_name = form.get("col_name", "")
    for key, value in form.items():
        if key not in ("row_id", "col_name"):
            inference_table.update_cell(row_id, col_name, value)
            break
    return ""


@rt("/inference/upload", methods=["POST"])
async def upload_inference_file(request):
    import csv
    import io
    import json as json_module

    form = await request.form()
    file = form.get("file")

    if not file:
        return render_inference_section()

    content = await file.read()
    filename = file.filename.lower()
    top_inputs = sorted(get_top_level_inputs())

    if filename.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(content.decode()))
        for row in reader:
            inference_table.add_row()
            for col in top_inputs:
                if col in row:
                    inference_table.rows[-1][col] = row[col]

    elif filename.endswith(".json"):
        data = json_module.loads(content)
        rows = data if isinstance(data, list) else [data]
        for item in rows:
            inference_table.add_row()
            for col in top_inputs:
                if col in item:
                    inference_table.rows[-1][col] = str(item[col])

    return render_inference_section()


@rt("/infer", methods=["POST"])
async def run_inference(request):
    return Div(P("placeholder"))
