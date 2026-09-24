"""A workspace list page's own QML source statically binds properties into
a nested detail page inside a lazy Loader (e.g.
`AdminSiteDetailPage { departmentColumns: root._departmentColumns ... }`
inside SitesWorkspacePage.qml). QML validates those bindings against the
target component's ACTUAL declared properties only once the Loader
actually activates -- loading the outer page alone (as
test_qml_status_chip_consumers_load.py and other tests already do for the
detail pages themselves, in isolation) never exercises this, so a property
silently dropped from the detail page's own declaration (as happened to
Site Detail's `departmentColumns` during a refactor) went undetected until
it broke the live app with "Cannot assign to non-existent property".

This activates each such Loader for real and asserts no
qWarning/qCritical fires -- the same category of error QML raises for a
static "Cannot assign to non-existent property" binding failure.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

UI_QML_ROOT = REPO_ROOT / "src" / "ui_qml"

# (workspace page, property that toggles its nested-detail Loader active)
_WORKSPACE_PAGES_WITH_LAZY_DETAIL_LOADER = [
    "platform/qml/workspaces/sites/SitesWorkspacePage.qml",
    "platform/qml/workspaces/organizations/OrganizationsWorkspacePage.qml",
    "platform/qml/workspaces/departments/DepartmentsWorkspacePage.qml",
]


def _ensure_qgui_application() -> QGuiApplication:
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["workspace-detail-loader-bindings-test"])


def _pump(n: int = 20) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


@pytest.mark.parametrize("relative_path", _WORKSPACE_PAGES_WITH_LAZY_DETAIL_LOADER)
def test_activating_the_nested_detail_loader_raises_no_qml_warnings(relative_path: str) -> None:
    _ensure_qgui_application()
    messages: list[str] = []

    def _handler(msg_type, context, message):
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            messages.append(message)

    previous_handler = qInstallMessageHandler(_handler)
    try:
        engine = create_qml_engine()
        qml_path = UI_QML_ROOT / relative_path
        assert qml_path.exists(), qml_path
        load_qml(engine, qml_path)
        assert len(engine.rootObjects()) == 1
        root = engine.rootObjects()[0]

        root.setProperty("detailOpen", True)
        _pump()
    finally:
        qInstallMessageHandler(previous_handler)

    offending = [m for m in messages if "Cannot assign to non-existent property" in m or "unavailable" in m]
    assert offending == [], f"{relative_path}: {offending}"
