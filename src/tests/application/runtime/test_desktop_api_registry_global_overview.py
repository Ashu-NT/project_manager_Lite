from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.application.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.platform.api.desktop.events.notifications.notification import (
    PlatformNotificationDesktopApi,
)


def test_registry_exposes_global_overview_and_platform_notification_apis(services):
    registry = build_desktop_api_registry(services)

    assert isinstance(registry.global_overview, GlobalOverviewDesktopApi)
    assert isinstance(registry.platform_notification, PlatformNotificationDesktopApi)


def test_registry_global_overview_api_is_end_to_end_usable(services):
    registry = build_desktop_api_registry(services)

    context_result = registry.global_overview.get_context()

    assert context_result.ok is True
    assert context_result.data is not None
