from fasthtml.common import *
from monsterui.all import *
from renders.tabs import render_tabs
from renders.table import render_table_with_header
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
    return DivVStacked(
        Div(render_tabs(), cls="w-full"),
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
    )
