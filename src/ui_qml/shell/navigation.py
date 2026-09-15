from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.shell.routes import QmlRoute


@dataclass(frozen=True)
class NavigationItemViewModel:
    route_id: str
    module_code: str
    module_label: str
    group_label: str
    title: str
    qml_source: str


def build_navigation_items(routes: list[QmlRoute]) -> list[NavigationItemViewModel]:
    return [
        NavigationItemViewModel(
            route_id=route.route_id,
            module_code=route.module_code,
            module_label=route.module_label,
            group_label=route.group_label,
            title=route.title,
            qml_source=route.qml_path.as_uri(),
        )
        for route in routes
    ]


_ALWAYS_AVAILABLE_MODULE_CODES = frozenset({"shell", "platform"})


def is_navigation_item_accessible(
    module_code: str, *, accessible_module_codes: frozenset[str]
) -> bool:
    normalized = str(module_code or "").strip().lower()
    if normalized in _ALWAYS_AVAILABLE_MODULE_CODES:
        return True
    return normalized in accessible_module_codes


def filter_navigation_items(
    items: list[NavigationItemViewModel], *, accessible_module_codes: frozenset[str]
) -> list[NavigationItemViewModel]:
    """Presentation-safe navigation accessibility projection: consumes an
    already-resolved accessible-module set (see PlatformRuntimeApplicationService
    .list_accessible_modules(), the same authoritative source Global Overview's
    module cards and Quick Actions already use) and returns only the items the
    current user may see. No permission/role logic lives here or in QML --
    this is a pure filter over already-decided accessibility."""
    return [
        item
        for item in items
        if is_navigation_item_accessible(
            item.module_code, accessible_module_codes=accessible_module_codes
        )
    ]


__all__ = [
    "NavigationItemViewModel",
    "build_navigation_items",
    "filter_navigation_items",
    "is_navigation_item_accessible",
]
