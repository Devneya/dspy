from fasthtml.common import *
from monsterui.all import *
from data.block_data import WrapperBlock
from renders.tabs import render_tabs
from renders.table import render_table_with_header
from renders.wrapper import render_wrapper_workspace
import config


def render_full_page():
    active_block = (
        next((b for b in config.blocks if b.id == config.active_block_id), None)
        if config.active_block_id
        else (config.blocks[0] if config.blocks else None)
    )
    return Container(
        render_tabs_view(active_block),
        id="main-container",
        cls=ContainerT.xl,
    )


def render_tabs_view(active_block):
    tabs_row = Div(render_tabs(), cls="w-full")
    if not active_block:
        return DivVStacked(tabs_row)
    if isinstance(active_block, WrapperBlock):
        return DivVStacked(tabs_row, render_wrapper_workspace(active_block))
    return DivVStacked(
        tabs_row,
        DivLAligned(
            render_table_with_header(active_block, "inputs"),
            render_table_with_header(active_block, "outputs"),
            cls="w-full mt-4",
        ),
    )
