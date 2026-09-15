from __future__ import annotations

from src.ui_qml.shell.context import ShellContext
from src.ui_qml.shell.navigation import NavigationItemViewModel, filter_navigation_items
from src.ui_qml.shell.presenters.navigation.navigation_accessibility_presenter import (
    NavigationAccessibilityPresenter,
)


class NavigationAccessibilityCoordinator:
    """Keeps ShellContext.navigationItems filtered to the current user's
    accessible EnterpriseModules, re-resolving on shell_context.scopeChanged
    (tenant/organization switch). This is the one place the shell decides
    which top-level routes are visible -- ShellDrawer.qml renders whatever
    it is given and makes no accessibility decisions of its own; the current
    route, if it becomes inaccessible, is handled by ShellContext itself
    (setNavigationItems redirects to the home route).
    """

    def __init__(
        self,
        *,
        shell_context: ShellContext,
        presenter: NavigationAccessibilityPresenter,
        all_navigation_items: list[NavigationItemViewModel],
    ) -> None:
        self._shell_context = shell_context
        self._presenter = presenter
        self._all_navigation_items = all_navigation_items
        shell_context.scopeChanged.connect(self.refresh)

    def refresh(self) -> None:
        accessible_module_codes = self._presenter.load_accessible_module_codes()
        filtered = filter_navigation_items(
            self._all_navigation_items, accessible_module_codes=accessible_module_codes
        )
        self._shell_context.setNavigationItems(filtered)


__all__ = ["NavigationAccessibilityCoordinator"]
