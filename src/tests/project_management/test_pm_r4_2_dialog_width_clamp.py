"""R4.2 follow-up: EntityDialog/CenteredDialog-based dialogs (Project Edit
among them) set a fixed literal `width` per-instance (e.g. "width: 560"),
which used to render past the edge of a narrower window -- section 11
rule 5 requires a dialog to clamp to available width, never exceed it.
CenteredDialog now corrects its own width after the fact once it's shown,
the same technique already proven for AnchoredPopup. This is a real,
windowed QML test (not offscreen-grab) since the earlier KpiStrip
incident showed offscreen rendering doesn't reliably stand in for real
window geometry."""

from __future__ import annotations

import os

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-r4-2-dialog-width-clamp-test"])


_HARNESS_QML = """
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ApplicationWindow {
    id: win
    visible: true
    width: 700
    height: 500

    property var dlgRef: dlg

    AppWidgets.EntityDialog {
        id: dlg
        title: "Edit Project"
        width: 900

        Item { Layout.preferredHeight: 10 }
    }

    Component.onCompleted: dlg.open()
}
"""


def test_entity_dialog_width_clamps_to_available_window_width(tmp_path) -> None:
    _ensure_qgui_application()
    path = tmp_path / "harness.qml"
    path.write_text(_HARNESS_QML, encoding="utf-8")

    engine = create_qml_engine()
    engine.load(str(path))
    assert len(engine.rootObjects()) == 1
    window = engine.rootObjects()[0]

    for _ in range(20):
        QCoreApplication.processEvents()

    dialog = window.property("dlgRef")
    assert dialog is not None
    # The dialog asked for width 900 but the window is only 700 wide --
    # it must be pulled back to fit (with side margins), never left at
    # its oversized literal value.
    assert dialog.property("width") < 900
    assert dialog.property("width") <= window.property("width")


def test_entity_dialog_does_not_clamp_when_it_already_fits(tmp_path) -> None:
    _ensure_qgui_application()
    harness = _HARNESS_QML.replace("width: 900", "width: 400").replace(
        "width: 700", "width: 900"
    )
    path = tmp_path / "harness_fits.qml"
    path.write_text(harness, encoding="utf-8")

    engine = create_qml_engine()
    engine.load(str(path))
    assert len(engine.rootObjects()) == 1
    window = engine.rootObjects()[0]

    for _ in range(20):
        QCoreApplication.processEvents()

    dialog = window.property("dlgRef")
    assert dialog is not None
    # Plenty of room (900px window, 400px dialog) -- must NOT be altered.
    assert dialog.property("width") == 400
