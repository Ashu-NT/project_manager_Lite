from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.shell.navigation import NavigationItemViewModel


class ShellContext(QObject):
    appTitleChanged = Signal()
    currentRouteIdChanged = Signal()
    currentRouteSourceChanged = Signal()
    navigationItemsChanged = Signal()
    themeModeChanged = Signal()
    userDisplayNameChanged = Signal()

    def __init__(
        self,
        *,
        app_title: str,
        navigation_items: list[NavigationItemViewModel],
        current_route_id: str = "",
        theme_mode: str = "light",
        user_display_name: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_title = app_title
        self._navigation_items = navigation_items
        self._current_route_id = current_route_id
        self._theme_mode = theme_mode
        self._user_display_name = user_display_name
        self._navigation_item_by_route_id = {
            item.route_id: item
            for item in navigation_items
        }

    @Property(str, notify=appTitleChanged)
    def appTitle(self) -> str:
        return self._app_title

    @Property(str, notify=currentRouteIdChanged)
    def currentRouteId(self) -> str:
        return self._current_route_id

    @Property(str, notify=currentRouteSourceChanged)
    def currentRouteSource(self) -> str:
        item = self._navigation_item_by_route_id.get(self._current_route_id)
        if item is None:
            return ""
        return item.qml_source

    @Property("QVariantList", notify=navigationItemsChanged)
    def navigationItems(self) -> list[dict[str, str]]:
        return [
            {
                "routeId": item.route_id,
                "moduleLabel": item.module_label,
                "groupLabel": item.group_label,
                "title": item.title,
                "qmlSource": item.qml_source,
            }
            for item in self._navigation_items
        ]

    @Property(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @Property(str, notify=userDisplayNameChanged)
    def userDisplayName(self) -> str:
        return self._user_display_name

    @Slot(str)
    def selectRoute(self, route_id: str) -> None:
        route_id = route_id.strip()
        if route_id == self._current_route_id:
            return
        known_route_ids = {item.route_id for item in self._navigation_items}
        if route_id not in known_route_ids:
            return
        self._current_route_id = route_id
        self.currentRouteIdChanged.emit()
        self.currentRouteSourceChanged.emit()


def build_shell_context(navigation_items: list[NavigationItemViewModel]) -> ShellContext:
    current_route_id = navigation_items[0].route_id if navigation_items else ""
    return ShellContext(
        app_title="TECHASH Enterprise",
        navigation_items=navigation_items,
        current_route_id=current_route_id,
    )


__all__ = ["ShellContext", "build_shell_context"]
