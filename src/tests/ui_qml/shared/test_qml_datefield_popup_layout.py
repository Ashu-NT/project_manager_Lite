"""DateField's date popup used to pack Month/Day/Year into a single
3-column GridLayout with Layout.minimumWidth: 0 on the month combo --
in a narrow dialog (e.g. a date field inside a compact-width Project Edit
dialog), the popup itself got clamped narrow too, and the month combo
(needing room for "September"/"November") clipped its text down to
nothing. Redesigned: Month is a full-width row on its own; Day/Year form
a two-column row below, since both are short fixed-width values. This
verifies the new layout renders with real, non-clipped widths at a
realistically narrow boundary."""

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
    return QGuiApplication(["pm-datefield-popup-layout-test"])


_HARNESS_QML = """
import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls

ApplicationWindow {
    id: win
    visible: true
    width: 380
    height: 400

    property var fieldRef: field

    Item {
        id: narrowBoundary
        width: 260
        height: 40

        AppControls.DateField {
            id: field
            anchors.fill: parent
            text: "2026-03-15"
            popupBoundaryItem: narrowBoundary
        }
    }

    Component.onCompleted: field.datePopup.open()
}
"""


def test_date_popup_month_row_and_day_year_row_do_not_clip(tmp_path) -> None:
    _ensure_qgui_application()
    path = tmp_path / "datefield_harness.qml"
    path.write_text(_HARNESS_QML, encoding="utf-8")

    engine = create_qml_engine()
    engine.load(str(path))
    assert len(engine.rootObjects()) == 1
    window = engine.rootObjects()[0]

    for _ in range(20):
        QCoreApplication.processEvents()

    field = window.property("fieldRef")
    assert field is not None

    month_combo = field.property("monthCombo")
    day_combo = field.property("dayCombo")
    year_combo = field.property("yearCombo")
    assert month_combo is not None
    assert day_combo is not None
    assert year_combo is not None

    # The month combo now has the popup's full content width available
    # (no longer squeezed to a third of it), so it must render
    # comfortably wide enough to show a full month name, not clipped.
    assert month_combo.property("width") >= 150
    # Day/Year each need genuine room -- their Layout.minimumWidth floors
    # (64 / 84) must actually be respected, not squashed to near-zero.
    assert day_combo.property("width") >= 64
    assert year_combo.property("width") >= 84
