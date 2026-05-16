from __future__ import annotations

from PySide6.QtQml import qmlRegisterModule, qmlRegisterUncreatableType

from src.ui_qml.shell.context import ShellContext
from src.ui_qml.shell.login import ShellLoginController

_REGISTERED = False


def register_shell_qml_types() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    qmlRegisterModule("Shell.Context", 1, 0)
    qmlRegisterModule("Shell.Controllers", 1, 0)
    qmlRegisterUncreatableType(
        ShellContext,
        "Shell.Context",
        1,
        0,
        "ShellContext",
        "Shell runtime context is provided by the application shell.",
    )
    qmlRegisterUncreatableType(
        ShellLoginController,
        "Shell.Controllers",
        1,
        0,
        "ShellLoginController",
        "Shell login controllers are provided by the application shell.",
    )
    _REGISTERED = True


__all__ = ["register_shell_qml_types"]
