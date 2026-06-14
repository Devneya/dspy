from fasthtml.common import *
from monsterui.all import *
from data.block_data import WrapperBlock
import config


def get_pair_info(block):
    if isinstance(block, WrapperBlock):
        return (None, block.get_wrapped_block())

    idx = next((i for i, b in enumerate(config.blocks) if b.id == block.id), -1)
    if 0 <= idx < len(config.blocks) - 1:
        next_block = config.blocks[idx + 1]
        if (
            isinstance(next_block, WrapperBlock)
            and next_block.wrapped_block_id == block.id
        ):
            return (next_block, None)

    return (None, None)


def render_tab_item(block, show_grip=False):
    is_active = config.active_block_id == block.id
    wrapped_by, wraps = get_pair_info(block)

    is_in_pair = wrapped_by is not None or wraps is not None

    pair_active = (
        is_active
        or (wrapped_by and wrapped_by.id == config.active_block_id)
        or (wraps and wraps.id == config.active_block_id)
    )

    if is_in_pair:
        if pair_active:
            bg_cls = "" if is_active else "bg-primary/15"
            border_cls = "border-primary" if is_active else "border-primary/50"
        else:
            bg_cls = "bg-muted/30"
            border_cls = "border-muted-foreground/20"

        if wrapped_by is not None:
            rounded_cls = "rounded-l-lg"
            border_cls += " border-r-0"
        else:
            rounded_cls = "rounded-r-lg"
            border_cls += " border-l-0"
    else:
        bg_cls = ""
        border_cls = (
            "border-primary" if is_active else "border-border hover:bg-muted/50"
        )
        rounded_cls = "rounded-lg"

    show_grip_icon = not is_in_pair or show_grip

    return Div(
        DivLAligned(
            (
                UkIcon(
                    "grip-vertical",
                    height=14,
                    cls="cursor-grab text-muted-foreground flex-shrink-0",
                )
                if show_grip_icon
                else ""
            ),
            Span(block.label, cls=f"text-sm".strip()),
            Button(
                UkIcon("x", height=12, cls="text-destructive"),
                cls="p-0.5 flex-shrink-0 shadow-none opacity-60 hover:opacity-100",
                hx_post=f"/rm/{block.id}",
                hx_target="#main-container",
                hx_swap="outerHTML",
                **{"onclick": "event.stopPropagation()"},
                title="Delete module",
            ),
            cls="gap-1.5",
        ),
        cls=f"px-3 py-2 cursor-pointer border-2 {border_cls} {bg_cls} {rounded_cls} transition-colors",
        id=f"tab-{block.id}",
        **{
            "data-block-id": block.id,
            "hx_get": f"/select-tab/{block.id}",
            "hx_target": "#main-container",
            "hx_swap": "outerHTML",
        },
    )


def render_add_block_dropdown():
    can_add_wrapper = len(config.blocks) > 0 and not isinstance(
        config.blocks[-1], WrapperBlock
    )

    available_types = [
        block_type
        for block_type in config.BLOCK_TYPES
        if block_type not in config.WRAPPER_TYPES or can_add_wrapper
    ]

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
                    title=config.DSPY_MODULE_SCHEMAS.get(block_type, {}).get("description", ""),
                    **{"onclick": "toggleAddBlockMenu()"},
                )
                for block_type in available_types
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
    tab_items = []
    i = 0

    while i < len(sorted_blocks):
        block = sorted_blocks[i]

        if i < len(sorted_blocks) - 1:
            next_block = sorted_blocks[i + 1]
            if (
                isinstance(next_block, WrapperBlock)
                and next_block.wrapped_block_id == block.id
            ):
                if i > 0:
                    tab_items.append(render_flow_connector())
                tab_items.append(render_tab_item(block, show_grip=True))
                tab_items.append(render_tab_item(next_block, show_grip=True))
                i += 2
                continue

        if i > 0:
            tab_items.append(render_flow_connector())
        tab_items.append(render_tab_item(block))
        i += 1

    return DivVStacked(
        DivFullySpaced(
            DivLAligned(
                DivLAligned(
                    *tab_items,
                    id="tabs-container",
                    cls="gap-0 overflow-x-auto items-center flex-wrap",
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
                UkIcon("plus", height=16),
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
                        title=config.DSPY_MODULE_SCHEMAS.get(block_type, {}).get("description", ""),
                        **{"onclick": "toggleAddBlockMenu()"},
                    )
                    for block_type in config.BLOCK_TYPES if block_type not in config.WRAPPER_TYPES
                ],
                id="add-block-menu",
                cls="hidden absolute left-0 z-50 mt-2 w-56",
            ),
            cls="relative",
        ),
        cls="py-8",
    )
