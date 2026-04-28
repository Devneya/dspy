from fasthtml.common import *
from monsterui.all import *
import config


def render_tab_item(block):
    is_active = config.active_block_id == block.id
    active_cls = "border-primary" if is_active else "hover:bg-muted/50"
    return Div(
        DivLAligned(
            UkIcon(
                "grip-vertical",
                height=14,
                cls="cursor-grab text-muted-foreground flex-shrink-0",
            ),
            Span(block.label),
            Button(
                UkIcon("x", height=12),
                cls=(ButtonT.link, "text-destructive p-0.5 flex-shrink-0 shadow-none"),
                hx_post=f"/rm/{block.id}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                **{"onclick": "event.stopPropagation()"},
                title="Delete module",
            ),
            cls="gap-2",
        ),
        cls=f"px-4 py-2 cursor-pointer rounded-lg border-2 {active_cls} transition-colors",
        id=f"tab-{block.id}",
        **{
            "data-block-id": block.id,
            "hx_get": f"/select-tab/{block.id}",
            "hx_target": "#main-container",
            "hx_swap": "outerHTML",
        },
    )


def render_add_block_dropdown():
    return Div(
        Button(
            UkIcon("plus", height=16),
            cls=ButtonT.primary,
            **{"onclick": "toggleAddBlockMenu()"},
            title="Add new module",
        ),
        Div(
            *[
                Button(
                    config.MODULE_NAMES.get(block_type, block_type),
                    cls=(ButtonT.default, "w-full justify-start"),
                    hx_post=f"/add/{block_type}",
                    hx_target="#main-container",
                    hx_swap="outerHTML",
                    **{"onclick": "toggleAddBlockMenu()"},
                )
                for block_type in config.BLOCK_TYPES
            ],
            id="add-block-menu",
            cls="hidden absolute right-0 z-50 mt-1 w-56",
        ),
        cls="relative ml-2",
    )


def render_flow_connector():
    return Div(
        Div(cls="hidden sm:flex items-center px-1")(
            UkIcon("arrow-right", height=18, cls="text-muted-foreground/50"),
        ),
        Div(cls="sm:hidden flex justify-center py-1")(
            UkIcon("arrow-down", height=18, cls="text-muted-foreground/50"),
        ),
        cls="flex-shrink-0",
    )


def render_tabs():
    if not config.blocks:
        return render_empty_state()
    sorted_blocks = sorted(config.blocks, key=lambda x: x.position)
    return DivVStacked(
        DivFullySpaced(
            DivLAligned(
                DivLAligned(
                    *[
                        item
                        for i, block in enumerate(sorted_blocks)
                        for item in (
                            [render_tab_item(block)]
                            if i == len(sorted_blocks) - 1
                            else [render_tab_item(block), render_flow_connector()]
                        )
                    ],
                    id="tabs-container",
                    cls="gap-0.5 overflow-x-auto items-center flex-wrap",
                ),
                render_add_block_dropdown(),
                cls="gap-2",
            ),
        ),
    )


def render_empty_state():
    return DivCentered(
        Div(
            Button(
                DivLAligned(UkIcon("plus", height=16)),
                cls=ButtonT.primary,
                **{"onclick": "toggleAddBlockMenu()"},
            ),
            Div(
                *[
                    Button(
                        config.MODULE_NAMES.get(block_type, block_type),
                        cls=(ButtonT.default, "w-full justify-start"),
                        hx_post=f"/add/{block_type}",
                        hx_target="#main-container",
                        hx_swap="outerHTML",
                        **{"onclick": "toggleAddBlockMenu()"},
                    )
                    for block_type in config.BLOCK_TYPES
                ],
                id="add-block-menu",
                cls="hidden absolute left-0 z-50 mt-2 w-56",
            ),
            cls="relative",
        ),
        cls="py-8",
    )
