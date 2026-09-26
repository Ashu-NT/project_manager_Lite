"""Builds the shell's Global Navigation Tree ("where am I in TECHASH?") from
an already-accessibility-filtered list of `NavigationItemViewModel`s."""

from __future__ import annotations

from src.ui_qml.shell.context_navigation import (
    ContextNavigationGroupViewModel,
    ContextNavigationItemViewModel,
    ContextNavigationViewModel,
)
from src.ui_qml.shell.navigation import NavigationItemViewModel

_ROOT_GROUP = ""
_BUSINESS_GROUP = "business"
_ADMINISTRATION_GROUP = "administration"
_SUPPORT_GROUP = "support"

_GROUP_LABELS: dict[str, str] = {
    _ROOT_GROUP: "",
    _BUSINESS_GROUP: "Business",
    _ADMINISTRATION_GROUP: "Administration",
    _SUPPORT_GROUP: "Support",
}

_GROUP_ORDER: dict[str, int] = {
    _ROOT_GROUP: 0,
    _BUSINESS_GROUP: 10,
    _ADMINISTRATION_GROUP: 20,
    _SUPPORT_GROUP: 30,
}

_ICON_BY_MODULE_CODE: dict[str, str] = {
    "shell": "dashboard",
    "platform": "admin",
    "project_management": "project",
}

# Module code -> (global area group, display order within that group).
_GLOBAL_AREA_BY_MODULE_CODE: dict[str, tuple[str, int]] = {
    "shell": (_ROOT_GROUP, 0),
    "project_management": (_BUSINESS_GROUP, 0),
    "platform": (_ADMINISTRATION_GROUP, 0),
}


def build_global_navigation_tree(
    items: list[NavigationItemViewModel],
) -> ContextNavigationViewModel:
    groups: dict[str, list[ContextNavigationItemViewModel]] = {}
    for item in items:
        area = _GLOBAL_AREA_BY_MODULE_CODE.get(item.module_code)
        if area is None:
            continue
        group_id, order = area
        groups.setdefault(group_id, []).append(
            ContextNavigationItemViewModel(
                id=item.route_id,
                label=item.title,
                icon_key=_ICON_BY_MODULE_CODE.get(item.module_code, "module"),
                route_id=item.route_id,
                group_id=group_id,
                order=order,
            )
        )

    group_view_models = [
        ContextNavigationGroupViewModel(
            id=group_id,
            label=_GROUP_LABELS.get(group_id, group_id),
            order=_GROUP_ORDER.get(group_id, 999),
            items=tuple(sorted(group_items, key=lambda item: item.order)),
        )
        for group_id, group_items in groups.items()
    ]

    return ContextNavigationViewModel(
        workspace_id="global",
        title="TECHASH Enterprise",
        groups=tuple(group_view_models),
    )


__all__ = ["build_global_navigation_tree"]
