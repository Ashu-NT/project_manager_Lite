"""Phase 6F: shell header integration -- OrganizationSwitcher, notification
bell/drawer, fake-search removal, and real end-to-end shell wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, Qt, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.core.platform.api.desktop.events.notifications.models.notification import NotificationDto
from src.core.platform.api.desktop.master_data.org.models.organization import OrganizationDto
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.shell.controllers.notifications.notifications_controller import (
    NotificationsController,
)
from src.ui_qml.shell.controllers.organization.organization_switcher_controller import (
    OrganizationSwitcherController,
)
from src.ui_qml.shell.presenters.notifications.notifications_presenter import (
    NotificationsPresenter,
)
from src.ui_qml.shell.presenters.organization.organization_switcher_presenter import (
    OrganizationSwitcherPresenter,
)
from src.ui_qml.shell.qml_engine import create_qml_engine
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_registry import build_qml_route_registry
from src.ui_qml.shell.qml_engine import load_qml
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

ROOT = Path(__file__).resolve().parents[3]
SHELL_HEADER_SOURCE = (ROOT / "ui_qml/shell/qml/ShellHeader.qml").read_text(encoding="utf-8")


# -- fake search / dead affordance removal -----------------------------------------------


def test_shell_header_no_longer_contains_fake_global_search():
    assert "Global search" not in SHELL_HEADER_SOURCE


def test_shell_header_no_longer_contains_dead_approvals_notifications_icons():
    assert '"label": "Approvals"' not in SHELL_HEADER_SOURCE
    assert '"label": "Notifications"' not in SHELL_HEADER_SOURCE


def test_shell_header_uses_real_organization_switcher_and_notification_bell():
    assert "OrganizationSwitcher {" in SHELL_HEADER_SOURCE
    assert "NotificationBell {" in SHELL_HEADER_SOURCE


# -- fakes for organization/notification apis -----------------------------------------------


def _org(id_: str, name: str) -> OrganizationDto:
    return OrganizationDto(
        id=id_, organization_code=id_.upper(), display_name=name,
        timezone_name="UTC", base_currency="USD", is_enabled=True, version=1,
    )


class _FakeTenantApi:
    def __init__(self, organizations, active_id):
        self._organizations = organizations
        self._active_id = active_id

    def list_accessible_organizations(self):
        return DesktopApiResult(ok=True, data=tuple(self._organizations))

    def get_active_organization(self):
        active = next((o for o in self._organizations if o.id == self._active_id), None)
        return DesktopApiResult(ok=True, data=active)

    def switch_to_organization(self, organization_id):
        self._active_id = organization_id
        target = next(o for o in self._organizations if o.id == organization_id)
        return DesktopApiResult(ok=True, data=target)


class _FakeNotificationApi:
    def __init__(self, notifications, unread_count):
        self._notifications = list(notifications)
        self._unread_count = unread_count

    def count_my_unread(self):
        return DesktopApiResult(ok=True, data=self._unread_count)

    def list_my_notifications(self, *, unread_only=False, limit=50):
        return DesktopApiResult(ok=True, data=tuple(self._notifications))

    def mark_read(self, notification_id):
        for i, n in enumerate(self._notifications):
            if n.id == notification_id:
                updated = NotificationDto(
                    id=n.id, category=n.category, title=n.title, body=n.body,
                    created_at=n.created_at, read_at=datetime.now(timezone.utc),
                    is_read=True, metadata={},
                )
                self._notifications[i] = updated
                self._unread_count = max(0, self._unread_count - 1)
                return DesktopApiResult(ok=True, data=updated)
        return DesktopApiResult(ok=False, error=None)

    def mark_all_read(self):
        count = sum(1 for n in self._notifications if not n.is_read)
        self._notifications = [
            NotificationDto(
                id=n.id, category=n.category, title=n.title, body=n.body,
                created_at=n.created_at, read_at=datetime.now(timezone.utc),
                is_read=True, metadata={},
            )
            for n in self._notifications
        ]
        self._unread_count = 0
        return DesktopApiResult(ok=True, data=count)


def _notification(id_: str, *, title: str = "Hello", is_read: bool = False) -> NotificationDto:
    return NotificationDto(
        id=id_, category="test.event", title=title, body="Body",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        read_at=None, is_read=is_read, metadata={},
    )


def _relevant_warnings(messages: list[str]) -> list[str]:
    return [
        m for m in messages
        if "ReferenceError" in m or "TypeError" in m or "unknown icon name" in m
        or "is not defined" in m
    ]


def _load_full_shell(qapp, *, org_api=None, notification_api=None, theme_mode="light"):
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    if theme_mode == "dark":
        shell_context.setThemeMode("dark")

    org_controller = OrganizationSwitcherController(
        presenter=OrganizationSwitcherPresenter(tenant_api=org_api)
    )
    org_controller.refresh()
    notifications_controller = NotificationsController(
        presenter=NotificationsPresenter(api=notification_api), shell_context=shell_context
    )
    notifications_controller.refresh()

    engine = create_qml_engine()
    shell_route = registry.get("shell.app")
    load_qml(
        engine,
        shell_route.qml_path,
        initial_properties={
            "shellModel": shell_context,
            "platformCatalog": PlatformWorkspaceCatalog(),
            "pmCatalog": ProjectManagementWorkspaceCatalog(),
            "globalOverviewController": None,
            "organizationSwitcherController": org_controller,
            "notificationsController": notifications_controller,
        },
    )
    QTest.qWait(500)
    return previous_handler, messages, engine, shell_context, org_controller, notifications_controller


def _teardown(previous_handler, engine, qapp) -> None:
    for root_object in engine.rootObjects():
        root_object.deleteLater()
    qapp.processEvents()
    qInstallMessageHandler(previous_handler)


# -- warning-free full shell load -------------------------------------------------------------


@pytest.mark.parametrize("theme_mode", ["light", "dark"])
def test_full_shell_loads_without_warnings(qapp, theme_mode) -> None:
    org_api = _FakeTenantApi([_org("org-1", "Org One"), _org("org-2", "Org Two")], "org-1")
    notification_api = _FakeNotificationApi([_notification("n1")], 1)
    previous_handler, messages, engine, *_ = _load_full_shell(
        qapp, org_api=org_api, notification_api=notification_api, theme_mode=theme_mode
    )
    try:
        assert _relevant_warnings(messages) == []
    finally:
        _teardown(previous_handler, engine, qapp)


# -- badge visibility -------------------------------------------------------------------


def test_badge_hidden_when_unread_count_is_zero(qapp) -> None:
    notification_api = _FakeNotificationApi([], 0)
    previous_handler, messages, engine, _shell_context, _org_controller, notifications_controller = (
        _load_full_shell(qapp, notification_api=notification_api)
    )
    try:
        assert notifications_controller.unreadCount == 0
    finally:
        _teardown(previous_handler, engine, qapp)


def test_badge_shows_exact_nonzero_unread_count(qapp) -> None:
    notification_api = _FakeNotificationApi([_notification("n1"), _notification("n2")], 2)
    previous_handler, messages, engine, _shell_context, _org_controller, notifications_controller = (
        _load_full_shell(qapp, notification_api=notification_api)
    )
    try:
        assert notifications_controller.unreadCount == 2
    finally:
        _teardown(previous_handler, engine, qapp)


# -- drawer open/close -------------------------------------------------------------------


def test_notifications_drawer_opens_on_bell_activation(qapp) -> None:
    notification_api = _FakeNotificationApi([_notification("n1")], 1)
    previous_handler, messages, engine, *_ = _load_full_shell(qapp, notification_api=notification_api)
    try:
        root = engine.rootObjects()[0]
        header = _find_by_object_name(root, "shellHeader")
        assert header is not None
        header.notificationsRequested.emit()
        qapp.processEvents()
        main_window = _find_by_object_name(root, "mainWindow")
        assert main_window is not None
        assert main_window.property("_notificationsPanelOpen") is True
    finally:
        _teardown(previous_handler, engine, qapp)


def _find_by_object_name(obj, object_name: str):
    if obj.objectName() == object_name:
        return obj
    for child in obj.children():
        found = _find_by_object_name(child, object_name)
        if found is not None:
            return found
    return None
