from __future__ import annotations

from pathlib import Path

from src.ui_qml.shell.routes import QmlRoute


def platform_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_platform_routes() -> list[QmlRoute]:
    return [
        # The single, unified, navigable Platform entry point. The 4 legacy
        # per-surface routes (platform.admin/control/settings/tenants) that
        # used to sit alongside this one were retired in R5.9, once every
        # capability they hosted (or, for admin/control/settings, could be
        # reached from) had its own standalone extraction and no longer
        # depended on `platformCatalog.workspace("platform.<x>")` for header
        # text. ControlWorkspacePage.qml/SettingsWorkspacePage.qml/
        # TenantManagementWorkspacePage.qml themselves were NOT deleted --
        # they're real, current content hosted directly by
        # PlatformWorkspacePage.qml, reached without going through the route
        # system at all.
        QmlRoute(
            route_id="platform.workspace",
            module_code="platform",
            module_label="Platform",
            group_label="Platform",
            title="Platform",
            qml_path=platform_qml_path("workspace", "PlatformWorkspace.qml"),
            presenter_key=None,
        ),
    ]


__all__ = ["build_platform_routes", "platform_qml_path"]
