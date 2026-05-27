from __future__ import annotations

from src.ui_qml.shell.navigation import NavigationItemViewModel, build_navigation_items
from src.ui_qml.shell.qml_registry import QmlRouteRegistry


def build_main_window_navigation(registry: QmlRouteRegistry) -> list[NavigationItemViewModel]:
    return build_navigation_items(registry.list_navigation_routes())


__all__ = ["build_main_window_navigation"]
