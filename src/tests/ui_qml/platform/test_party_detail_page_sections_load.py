"""AdminPartyDetailPage.qml's final section set is exactly Overview /
Activity (no Contacts/Customer-Client-Profile/Linked-Projects/Documents/
Audit tabs, and no hidden/dead placeholder tabs "for later"). Activates
every one of the two sections' lazy Loaders for real and asserts no
qWarning/qCritical fires -- the same category of error QML raises for a
static "Cannot assign to non-existent property" binding failure. Mirrors
test_department_detail_page_sections_load.py's approach."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication

from src.tests.path_rewrites import REPO_ROOT
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

UI_QML_ROOT = REPO_ROOT / "src" / "ui_qml"
_DETAIL_PAGE_PATH = UI_QML_ROOT / "platform" / "qml" / "workspaces" / "parties" / "AdminPartyDetailPage.qml"


def _ensure_qgui_application() -> QGuiApplication:
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["party-detail-page-sections-test"])


def _pump(n: int = 20) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def test_final_section_set_is_exactly_overview_activity() -> None:
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(engine, _DETAIL_PAGE_PATH)
    assert len(engine.rootObjects()) == 1
    root = engine.rootObjects()[0]

    sections = root.property("_sections").toVariant()
    labels = [str(section["label"]) for section in sections]
    assert labels == ["Overview", "Activity"]


def test_activating_every_section_loader_raises_no_qml_warnings() -> None:
    _ensure_qgui_application()
    messages: list[str] = []

    def _handler(msg_type, context, message):
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            messages.append(message)

    previous_handler = qInstallMessageHandler(_handler)
    try:
        engine = create_qml_engine()
        load_qml(engine, _DETAIL_PAGE_PATH)
        assert len(engine.rootObjects()) == 1
        root = engine.rootObjects()[0]

        for index in range(2):
            root.setProperty("activeSectionIndex", index)
            _pump()
    finally:
        qInstallMessageHandler(previous_handler)

    offending = [m for m in messages if "Cannot assign to non-existent property" in m or "unavailable" in m]
    assert offending == [], offending
