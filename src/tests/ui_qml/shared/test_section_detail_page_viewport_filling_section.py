"""A section that sizes itself to `detailPage.contentViewportHeight` (the
pattern Departments/Employees/Calendar/Activity all use so their own inner
Flickable can own scrolling) must make the outer `contentFlickable`
non-scrollable -- otherwise the whole section (its own fixed toolbar/footer
included) drags as one block instead of only its inner content scrolling."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtQuick import QQuickItem

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

_PROBE_QML = """
import QtQuick
import QtQuick.Window
import App.Widgets 1.0 as AppWidgets

Window {
    id: win
    width: 900
    height: 600
    visible: true

    AppWidgets.SectionDetailPage {
        id: page
        objectName: "probePage"
        anchors.fill: parent
        open: true
        title: "Probe"
        sections: [{"label": "Overview"}, {"label": "Filling"}]

        Rectangle {
            objectName: "fillingSection"
            width: parent ? parent.width : page.width
            height: page.activeSectionIndex === 1 ? Math.max(420, page.contentViewportHeight) : 0
            visible: height > 0
            color: "green"
        }
    }
}
"""


def _settle(app, *, seconds: float = 1.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def test_viewport_filling_section_makes_outer_flickable_non_scrollable(qapp) -> None:
    qml_path = Path(tempfile.mktemp(suffix=".qml"))
    qml_path.write_text(_PROBE_QML, encoding="utf-8")

    engine = create_qml_engine()
    try:
        load_qml(engine, qml_path)
        root = engine.rootObjects()[0]
        _settle(qapp)

        page = root.findChild(QQuickItem, "probePage")
        page.setProperty("activeSectionIndex", 1)
        _settle(qapp)

        flickable = root.findChild(QQuickItem, "sectionDetailContentFlickable")
        assert flickable is not None
        assert flickable.property("contentHeight") == flickable.height(), (
            "outer contentFlickable is scrollable even though the active "
            "section exactly fills the viewport"
        )
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)
