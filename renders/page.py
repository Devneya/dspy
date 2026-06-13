from fasthtml.common import *
from monsterui.all import *
from data.block_data import WrapperBlock
from renders.tabs import render_tabs
from renders.table import render_table_with_header
from renders.wrapper import render_wrapper_workspace
from renders.inference import render_inference_section
import config


def render_full_page():
    active_block = (
        next((b for b in config.blocks if b.id == config.active_block_id), None)
        if config.active_block_id
        else (config.blocks[0] if config.blocks else None)
    )
    return Container(
        render_mode_switch(),
        (
            render_tabs_view(active_block)
            if config.current_mode == "build"
            else render_use_view()
        ),
        id="main-container",
        cls=ContainerT.xl,
    )


def render_mode_switch():
    is_build = config.current_mode == "build"
    return DivCentered(
        DivLAligned(
            Button(
                "Build",
                cls=(ButtonT.primary if is_build else ButtonT.default) + " text-sm",
                hx_post="/switch-mode/build",
                hx_target="#main-container",
                hx_swap="outerHTML",
            ),
            Button(
                "Use",
                cls=(ButtonT.default if is_build else ButtonT.primary) + " text-sm",
                hx_post="/switch-mode/use",
                hx_target="#main-container",
                hx_swap="outerHTML",
            ),
            cls="gap-0",
        ),
        cls="mb-4",
    )


def render_tabs_view(active_block):
    tabs_row = Div(render_tabs(), cls="w-full")

    if not active_block:
        return DivVStacked(tabs_row)

    if isinstance(active_block, WrapperBlock):
        return DivVStacked(
            tabs_row,
            render_wrapper_workspace(active_block),
        )

    return DivVStacked(
        tabs_row,
        DivLAligned(
            render_table_with_header(active_block, "inputs"),
            render_table_with_header(active_block, "outputs"),
            cls="w-full mt-4",
        ),
    )


def render_use_view():
    if not config.is_optimized:
        return DivVStacked(
            Button(
                Span("Optimize", cls="ml-1"),
                cls=(ButtonT.primary, "text-sm"),
                id="optimize-all-btn",
                hx_post="/optimize",
                hx_target="#use-content",
                hx_swap="innerHTML",
            ),
            Div(id="use-content"),
        )

    return DivVStacked(
        render_inference_section(),
    )
