"""Regression coverage for a reported InlineMessage leakage bug: every
Platform admin dialog (Organization/Site/Department/Employee/User/Party/
Document/Calendar editors) saves through the one shared
`AdminDialogHost.qml::_handleResult()`. On failure it correctly copies the
backend message into the dialog's own local errorMessage (so the modal
shows it) -- but it also left that same text sitting in the workspace
controller's shared errorMessage, the exact property the list/detail
InlineMessage behind the dialog reads. That let a dialog-only validation/
backend failure leak onto the page behind the modal, and linger there
(reappearing later) since nothing ever cleared it. `_handleResult()` now
calls `workspaceController.clearMessages()` on failure."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, Q_ARG, QMetaObject, qInstallMessageHandler

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

DIALOG_HOST = Path("src/ui_qml/platform/qml/Platform/Dialogs/AdminDialogHost.qml")


def _pump(n: int = 10) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def test_dialog_host_clears_shared_controller_message_on_failure(services, qapp) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        load_qml(
            engine,
            DIALOG_HOST.resolve(),
            initial_properties={"workspaceController": admin, "platformCatalog": catalog},
        )
        root = engine.rootObjects()[0]
        _pump()

        # A stale message already sitting on the shared controller -- as if
        # a prior list/detail action had left one there.
        admin._set_error_message("Stale prior error")
        admin._set_feedback_message("Stale prior success")

        ok = QMetaObject.invokeMethod(
            root,
            "_handleResult",
            Q_ARG("QVariant", {}),
            Q_ARG("QVariant", {"ok": False, "message": "Organization code already exists."}),
        )
        assert ok
        _pump()

        assert admin.errorMessage == "", (
            "a dialog's own failure must not linger on the shared workspace "
            "controller message once the dialog has shown it locally"
        )
        assert admin.feedbackMessage == ""

        relevant = [
            m for m in messages
            if "TypeError" in m or "ReferenceError" in m or "is not defined" in m
            or "unknown icon name" in m or "Cannot read propert" in m
        ]
        assert relevant == [], relevant
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qInstallMessageHandler(previous_handler)


def test_dialog_host_success_path_still_surfaces_feedback_on_the_page(services, qapp) -> None:
    """The failure-path clear must not regress the (correct, intended)
    success path: a Create dialog's confirmation should still reach the
    list-scoped InlineMessage once the dialog closes."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    engine = create_qml_engine()
    try:
        load_qml(
            engine,
            DIALOG_HOST.resolve(),
            initial_properties={"workspaceController": admin, "platformCatalog": catalog},
        )
        root = engine.rootObjects()[0]
        _pump()

        admin._set_feedback_message("Organization created.")

        ok = QMetaObject.invokeMethod(
            root,
            "_handleResult",
            Q_ARG("QVariant", {"close": True}),
            Q_ARG("QVariant", {"ok": True, "message": "Organization created."}),
        )
        assert ok
        _pump()

        assert admin.feedbackMessage == "Organization created.", (
            "a successful dialog action's confirmation must still reach the "
            "workspace page once the dialog closes"
        )
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
