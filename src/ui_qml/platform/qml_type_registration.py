from __future__ import annotations

from PySide6.QtQml import qmlRegisterModule, qmlRegisterUncreatableType

from src.ui_qml.platform.access_workspace_state import PlatformAdminAccessWorkspaceController
from src.ui_qml.platform.admin_workspace_state import PlatformAdminWorkspaceController
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.workspace_state import (
    PlatformControlWorkspaceController,
    PlatformSettingsWorkspaceController,
    PlatformWorkspaceControllerBase,
)

_REGISTERED = False


def register_platform_qml_types() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    qmlRegisterModule("Platform.Controllers", 1, 0)
    qmlRegisterUncreatableType(
        PlatformWorkspaceControllerBase,
        "Platform.Controllers",
        1,
        0,
        "PlatformWorkspaceControllerBase",
        "Platform workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        PlatformAdminWorkspaceController,
        "Platform.Controllers",
        1,
        0,
        "PlatformAdminWorkspaceController",
        "Platform workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        PlatformAdminAccessWorkspaceController,
        "Platform.Controllers",
        1,
        0,
        "PlatformAdminAccessWorkspaceController",
        "Platform workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        PlatformControlWorkspaceController,
        "Platform.Controllers",
        1,
        0,
        "PlatformControlWorkspaceController",
        "Platform workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        PlatformSettingsWorkspaceController,
        "Platform.Controllers",
        1,
        0,
        "PlatformSettingsWorkspaceController",
        "Platform workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        PlatformWorkspaceCatalog,
        "Platform.Controllers",
        1,
        0,
        "PlatformWorkspaceCatalog",
        "Platform workspace catalogs are provided by the shell runtime.",
    )
    _REGISTERED = True


__all__ = ["register_platform_qml_types"]
