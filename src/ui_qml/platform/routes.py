from __future__ import annotations

from pathlib import Path

from src.ui_qml.shell.routes import QmlRoute


def platform_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_platform_routes() -> list[QmlRoute]:
    return [
        # R2: the single, unified, navigable Platform entry point (target
        # architecture -- collapses the 4 legacy top-level routes below into
        # one shell-navigation entry, per the approved design doc).
        QmlRoute(
            route_id="platform.workspace",
            module_code="platform",
            module_label="Platform",
            group_label="Platform",
            title="Platform",
            qml_path=platform_qml_path("workspace", "PlatformWorkspace.qml"),
            presenter_key=None,
        ),
        # The 4 routes below are kept registered, but NOT navigable
        # (appears_in_navigation=False), for two reasons only: (1)
        # AdminConsolePage.qml/ControlWorkspacePage.qml/SettingsWorkspacePage.qml
        # each call `platformCatalog.workspace("platform.<x>")` by this exact
        # hardcoded string today for their own header title/summary -- removing
        # these entries would silently blank that text; (2) the full
        # offscreen-QML-load regression test iterates every registered route,
        # so keeping them registered keeps that coverage. Nothing in the new
        # shell ever calls `selectRoute()` with these ids. They are removed
        # only when the pages that reference them stop doing so (tied to the
        # admin_console facade's own documented removal criteria).
        QmlRoute(
            route_id="platform.admin",
            module_code="platform",
            module_label="Platform",
            group_label="Administration",
            title="Admin Console",
            qml_path=platform_qml_path("admin_console", "AdminWorkspace.qml"),
            presenter_key="platform.admin",
            appears_in_navigation=False,
        ),
        QmlRoute(
            route_id="platform.control",
            module_code="platform",
            module_label="Platform",
            group_label="Control",
            title="Control Center",
            qml_path=platform_qml_path("control", "ControlWorkspace.qml"),
            presenter_key="platform.control",
            appears_in_navigation=False,
        ),
        QmlRoute(
            route_id="platform.settings",
            module_code="platform",
            module_label="Platform",
            group_label="Settings",
            title="Settings",
            qml_path=platform_qml_path("settings", "SettingsWorkspace.qml"),
            presenter_key="platform.settings",
            appears_in_navigation=False,
        ),
        QmlRoute(
            route_id="platform.tenants",
            module_code="platform",
            module_label="Platform",
            group_label="Tenants",
            title="Tenant Management",
            qml_path=platform_qml_path("tenants", "TenantManagementWorkspace.qml"),
            presenter_key=None,
            appears_in_navigation=False,
        ),
    ]


__all__ = ["build_platform_routes", "platform_qml_path"]
