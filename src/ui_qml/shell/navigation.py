from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.shell.routes import QmlRoute


@dataclass(frozen=True)
class NavigationItemViewModel:
    route_id: str
    module_label: str
    group_label: str
    title: str


def build_navigation_items(routes: list[QmlRoute]) -> list[NavigationItemViewModel]:
    return [
        NavigationItemViewModel(
            route_id=route.route_id,
            module_label=route.module_label,
            group_label=route.group_label,
            title=route.title,
        )
        for route in routes
    ]


__all__ = ["NavigationItemViewModel", "build_navigation_items"]
