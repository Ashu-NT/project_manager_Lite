from __future__ import annotations

from src.core.platform.api.desktop.platform_runtime.runtime import (
    PlatformRuntimeDesktopApi,
)


class NavigationAccessibilityPresenter:
    """Resolves the current user's accessible EnterpriseModule codes for shell
    navigation filtering -- a thin read over PlatformRuntimeDesktopApi
    .list_accessible_modules(), the same authoritative source Global
    Overview's module cards and Quick Actions already use. Fails closed: an
    unavailable/errored API result resolves to an empty accessible set (only
    the always-available "shell"/"platform" routes remain visible) rather
    than risk showing a module the user cannot actually use.
    """

    def __init__(self, *, platform_runtime_api: PlatformRuntimeDesktopApi | None = None) -> None:
        self._platform_runtime_api = platform_runtime_api

    def load_accessible_module_codes(self) -> frozenset[str]:
        if self._platform_runtime_api is None:
            return frozenset()
        result = self._platform_runtime_api.list_accessible_modules()
        if not result.ok or result.data is None:
            return frozenset()
        return frozenset(module.code for module in result.data)


__all__ = ["NavigationAccessibilityPresenter"]
