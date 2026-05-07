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
    tabs_row = DivFullySpaced(
        render_tabs(),
        Button(
            Span("OPTIMIZE", cls="ml-1"),
            cls=(ButtonT.primary, "text-sm flex-shrink-0"),
            id="optimize-all-btn",
            hx_post="/optimize",
            hx_target="#optimize-status",
            hx_swap="innerHTML",
        ),
        cls="w-full items-center",
    )

    if not active_block:
        return DivVStacked(
            tabs_row,
            Div(id="optimize-status", cls="text-sm text-muted-foreground mt-1"),
        )

    if isinstance(active_block, WrapperBlock):
        return DivVStacked(
            tabs_row,
            Div(id="optimize-status", cls="text-sm text-muted-foreground mt-1"),
            render_wrapper_workspace(active_block),
        )

    return DivVStacked(
        tabs_row,
        Div(id="optimize-status", cls="text-sm text-muted-foreground mt-1"),
        DivLAligned(
            render_table_with_header(active_block, "inputs"),
            render_table_with_header(active_block, "outputs"),
            cls="w-full mt-4",
        ),
    )
