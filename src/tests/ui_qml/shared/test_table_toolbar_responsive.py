"""TableToolbar is the single shared owner of every embedded/detail-page
table workspace's toolbar row (AdminEntityWorkspace and ~30 direct
consumers across Platform and Project Management). At a constrained width
its old single flat RowLayout let the right-side action buttons (Refresh,
the primary create/add action) overflow past the toolbar's own bounds and
get clipped by an ancestor's `clip: true` -- reproduced here directly
against the shared component, not against any one consumer page.

The fix groups controls into query (search/filters), table (Columns/Views)
and command (Refresh/Import/Export/primary action) clusters and reflows
them from one row to two, and -- only if even the second row can't fit --
folds Refresh/Columns/Views into a shared overflow menu while keeping the
primary action and search/filters always reachable. The breakpoints are
computed from each control's own implicitWidth so this holds for any
combination of filters/actions a caller wires up (Site Employees has two
filters, Organization Employees has one, Activity toolbars have zero
customize/create controls, etc.)."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Button/label implicitWidth (and therefore the breakpoint thresholds under
# test) depends on real glyph metrics -- without a font directory, offscreen
# Text elements measure as blank and every width collapses to icon-only.
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

from PySide6.QtCore import QCoreApplication, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

# A Window-wrapped probe is required for Layout geometry (implicitHeight/
# Layout.fillWidth resolution) to settle in an offscreen QQmlApplicationEngine
# -- a bare non-Window root does not reliably get a render/polish pass.
_PROBE_QML = """
import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

Window {
    id: win
    objectName: "probeWindow"
    width: 1600
    height: 200
    visible: true

    property alias toolbarWidth: toolbar.width
    property alias showFilter: toolbar.showFilter
    property alias showCustomize: toolbar.showCustomize
    property alias showViews: toolbar.showViews
    property alias showRefresh: toolbar.showRefresh
    property alias showImport: toolbar.showImport
    property alias showExport: toolbar.showExport
    property alias showCreate: toolbar.showCreate
    property alias createLabel: toolbar.createLabel
    property alias filterCount: filterRepeater.model

    AppWidgets.TableToolbar {
        id: toolbar
        objectName: "probeToolbar"
        x: 0
        y: 0
        width: 1600
        showSearch: true

        Repeater {
            id: filterRepeater
            model: 0
            delegate: AppControls.ComboBox {
                Layout.preferredWidth: 150
                model: ["All", "A", "B"]
            }
        }
    }
}
"""


def _settle(app, seconds: float = 0.6) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


def _load(engine):
    """Returns (root, qml_path) -- the caller unlinks qml_path in its
    finally block once the engine's root objects are torn down."""
    qml_path = Path(tempfile.mktemp(suffix=".qml"))
    qml_path.write_text(_PROBE_QML, encoding="utf-8")
    load_qml(engine, qml_path)
    return engine.rootObjects()[0], qml_path


def _visible_action_items(toolbar):
    names = [
        "toolbarSearchField",
        "toolbarFilterButton",
        "toolbarCustomizeButton",
        "toolbarViewsButton",
        "toolbarRefreshButton",
        "toolbarImportButton",
        "toolbarExportButton",
        "toolbarOverflowButton",
        "toolbarCreateButton",
    ]
    found = {}
    for name in names:
        item = toolbar.findChild(QQuickItem, name)
        if item is not None and item.property("visible"):
            found[name] = item
    return found


def _assert_no_clipping(toolbar, root, label):
    toolbar_width = toolbar.width()
    for name, item in _visible_action_items(toolbar).items():
        top_left = item.mapToItem(toolbar, 0, 0)
        bottom_right = item.mapToItem(toolbar, item.width(), item.height())
        assert top_left.x() >= -0.5, f"{label}: {name} starts left of toolbar (x={top_left.x()})"
        assert bottom_right.x() <= toolbar_width + 0.5, (
            f"{label}: {name} right edge ({bottom_right.x()}) exceeds toolbar width ({toolbar_width})"
        )
        assert item.width() > 0 and item.height() > 0, f"{label}: {name} has zero size"


def _set_filter_count(root, qapp, count: int) -> None:
    root.setProperty("filterCount", count)
    _settle(qapp)


def test_case_a_search_status_columns_refresh_create(qapp) -> None:
    messages: list[str] = []
    qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    root, qml_path = _load(engine)
    try:
        _settle(qapp)
        root.setProperty("showCustomize", True)
        root.setProperty("showRefresh", True)
        root.setProperty("showCreate", True)
        root.setProperty("createLabel", "New Employee")
        _set_filter_count(root, qapp, 1)

        toolbar = root.findChild(QQuickItem, "probeToolbar")

        for width, label in ((1600, "wide"), (760, "medium"), (360, "narrow")):
            root.setProperty("toolbarWidth", width)
            _settle(qapp)
            _assert_no_clipping(toolbar, root, f"case A {label} ({width}px)")

        relevant = [m for m in messages if "TypeError" in m or "ReferenceError" in m or "Binding loop" in m]
        assert not relevant, "\n".join(relevant)
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)


def test_case_b_search_department_status_columns_refresh_create(qapp) -> None:
    messages: list[str] = []
    qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    root, qml_path = _load(engine)
    try:
        _settle(qapp)
        root.setProperty("showCustomize", True)
        root.setProperty("showRefresh", True)
        root.setProperty("showCreate", True)
        root.setProperty("createLabel", "New Employee")
        _set_filter_count(root, qapp, 2)

        toolbar = root.findChild(QQuickItem, "probeToolbar")

        for width, label in ((1600, "wide"), (760, "medium"), (360, "narrow")):
            root.setProperty("toolbarWidth", width)
            _settle(qapp)
            _assert_no_clipping(toolbar, root, f"case B {label} ({width}px)")

        relevant = [m for m in messages if "TypeError" in m or "ReferenceError" in m or "Binding loop" in m]
        assert not relevant, "\n".join(relevant)
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)


def test_wide_layout_is_single_row(qapp) -> None:
    engine = create_qml_engine()
    root, qml_path = _load(engine)
    try:
        _settle(qapp)
        root.setProperty("showCustomize", True)
        root.setProperty("showRefresh", True)
        root.setProperty("showCreate", True)
        root.setProperty("createLabel", "New Employee")
        _set_filter_count(root, qapp, 1)
        root.setProperty("toolbarWidth", 1600)
        _settle(qapp)

        toolbar = root.findChild(QQuickItem, "probeToolbar")
        bottom_row = toolbar.findChild(QQuickItem, "toolbarBottomRow")
        assert bottom_row.property("visible") is False
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)


def test_narrow_layout_folds_secondary_actions_into_overflow_and_keeps_primary(qapp) -> None:
    engine = create_qml_engine()
    root, qml_path = _load(engine)
    try:
        _settle(qapp)
        root.setProperty("showCustomize", True)
        root.setProperty("showRefresh", True)
        root.setProperty("showCreate", True)
        root.setProperty("createLabel", "New Employee")
        _set_filter_count(root, qapp, 2)
        root.setProperty("toolbarWidth", 320)
        _settle(qapp)

        toolbar = root.findChild(QQuickItem, "probeToolbar")
        overflow = toolbar.findChild(QQuickItem, "toolbarOverflowButton")
        create = toolbar.findChild(QQuickItem, "toolbarCreateButton")
        refresh = toolbar.findChild(QQuickItem, "toolbarRefreshButton")
        customize = toolbar.findChild(QQuickItem, "toolbarCustomizeButton")

        assert overflow.property("visible") is True
        assert create.property("visible") is True
        assert refresh.property("visible") is False
        assert customize.property("visible") is False

        overflow_items = overflow.property("items")
        overflow_items = overflow_items.toVariant() if hasattr(overflow_items, "toVariant") else overflow_items
        ids = {entry["id"] for entry in overflow_items}
        assert "refresh" in ids
        assert "customize" in ids
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)


def test_zero_filters_and_no_primary_action_does_not_crash(qapp) -> None:
    """Generalization guard: Activity-style toolbars with no create action
    and no Columns/Views must still reflow cleanly (no crash, no clipping,
    no pointless empty second row)."""
    engine = create_qml_engine()
    root, qml_path = _load(engine)
    try:
        _settle(qapp)
        root.setProperty("showCustomize", False)
        root.setProperty("showViews", False)
        root.setProperty("showRefresh", True)
        root.setProperty("showCreate", False)
        _set_filter_count(root, qapp, 0)

        toolbar = root.findChild(QQuickItem, "probeToolbar")
        for width in (1600, 500, 250):
            root.setProperty("toolbarWidth", width)
            _settle(qapp)
            _assert_no_clipping(toolbar, root, f"zero-filter/no-primary ({width}px)")
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)
