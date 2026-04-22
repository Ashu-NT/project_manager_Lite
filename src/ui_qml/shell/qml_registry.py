from __future__ import annotations

from collections.abc import Iterable

from src.ui_qml.shell.routes import QmlRoute, build_shell_routes


class QmlRouteRegistry:
    def __init__(self, routes: Iterable[QmlRoute] | None = None) -> None:
        self._routes: dict[str, QmlRoute] = {}
        for route in routes or []:
            self.register(route)

    def register(self, route: QmlRoute) -> None:
        if route.route_id in self._routes:
            raise ValueError(f"QML route already registered: {route.route_id}")
        self._routes[route.route_id] = route

    def get(self, route_id: str) -> QmlRoute:
        try:
            return self._routes[route_id]
        except KeyError as exc:
            raise KeyError(f"Unknown QML route: {route_id}") from exc

    def list_routes(self) -> list[QmlRoute]:
        return list(self._routes.values())


def build_qml_route_registry() -> QmlRouteRegistry:
    return QmlRouteRegistry(build_shell_routes())


__all__ = ["QmlRouteRegistry", "build_qml_route_registry"]
