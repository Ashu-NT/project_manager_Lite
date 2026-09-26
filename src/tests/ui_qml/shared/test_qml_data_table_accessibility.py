from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine

ROWS_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 640
    height: 300
    visible: true
    property string selectedRowId: ""
    property string activatedRowId: ""
    property int selectedCount: 0
    property int activatedCount: 0
    readonly property bool tableActiveFocusOnTab: table._mainViewRef.activeFocusOnTab
    readonly property int tableAccessibleRole: table._mainViewRef.Accessible.role
    readonly property string tableAccessibleName: table._mainViewRef.Accessible.name

    AppWidgets.DataTable {
        id: table
        objectName: "dataTable"
        anchors.fill: parent
        columns: [{key: "name", label: "Name", sortable: true}]
        rows: [
            {id: "1", name: "Alpha"},
            {id: "2", name: "Bravo"},
            {id: "3", name: "Charlie"}
        ]
        accessibleName: "Test Records"
        onRowSelected: function(rowId) {
            harness.selectedRowId = rowId
            harness.selectedCount += 1
        }
        onRowActivated: function(rowId) {
            harness.activatedRowId = rowId
            harness.activatedCount += 1
        }
    }
}
"""


def _create_harness(qapp, source: str = ROWS_SOURCE):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "data-table-a11y-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _find_by_object_name(obj, name):
    if obj.objectName() == name:
        return obj
    for child in obj.children():
        found = _find_by_object_name(child, name)
        if found is not None:
            return found
    return None


def _main_view(table_item):
    return table_item.property("_mainViewRef")


def test_table_is_keyboard_focusable(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        assert root.property("tableActiveFocusOnTab") is True
    finally:
        root.deleteLater()
        del component, engine


def test_table_has_table_role_and_caller_supplied_name(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        assert root.property("tableAccessibleRole") == QAccessible.Role.Table.value
        assert root.property("tableAccessibleName") == "Test Records"
    finally:
        root.deleteLater()
        del component, engine


def test_down_arrow_moves_focus_and_selects_first_row(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_Down)
        qapp.processEvents()

        assert root.property("selectedRowId") == "1"
        assert root.property("selectedCount") == 1
    finally:
        root.deleteLater()
        del component, engine


def test_down_arrow_twice_selects_second_row(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_Down)
        QTest.keyClick(root, Qt.Key.Key_Down)
        qapp.processEvents()

        assert root.property("selectedRowId") == "2"
        assert root.property("selectedCount") == 2
    finally:
        root.deleteLater()
        del component, engine


def test_up_arrow_moves_back_up(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_Down)
        QTest.keyClick(root, Qt.Key.Key_Down)
        QTest.keyClick(root, Qt.Key.Key_Up)
        qapp.processEvents()

        assert root.property("selectedRowId") == "1"
        assert root.property("selectedCount") == 3
    finally:
        root.deleteLater()
        del component, engine


def test_end_key_jumps_to_last_row(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_End)
        qapp.processEvents()

        assert root.property("selectedRowId") == "3"
    finally:
        root.deleteLater()
        del component, engine


def test_home_key_jumps_to_first_row_after_end(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_End)
        QTest.keyClick(root, Qt.Key.Key_Home)
        qapp.processEvents()

        assert root.property("selectedRowId") == "1"
    finally:
        root.deleteLater()
        del component, engine


def test_return_activates_current_row(qapp) -> None:
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_Down)
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()

        assert root.property("activatedRowId") == "1"
        assert root.property("activatedCount") == 1
    finally:
        root.deleteLater()
        del component, engine


def test_return_without_prior_navigation_does_not_activate(qapp) -> None:
    """No row is "current" until the user has actually navigated -- Enter
    must not silently activate an arbitrary row."""
    engine, component, root = _create_harness(qapp)
    try:
        table = _find_by_object_name(root, "dataTable")
        main_view = _main_view(table)
        main_view.forceActiveFocus()
        qapp.processEvents()

        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()

        assert root.property("activatedCount") == 0
    finally:
        root.deleteLater()
        del component, engine


def test_mouse_click_still_selects_row(qapp) -> None:
    """Regression: existing mouse interaction is unchanged by the keyboard
    hardening."""
    engine, component, root = _create_harness(qapp)
    try:
        QTest.mouseClick(
            root,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(80, 20 + 32),  # header height + first row
        )
        qapp.processEvents()

        assert root.property("selectedRowId") == "1"
        assert root.property("selectedCount") == 1
    finally:
        root.deleteLater()
        del component, engine


def _set_theme(engine, mode: str) -> None:
    component = QQmlComponent(engine)
    component.setData(
        (
            'import QtQuick\nimport App.Theme 1.0 as Theme\n'
            'QtObject { Component.onCompleted: Theme.AppTheme.themeMode = "%s" }' % mode
        ).encode("utf-8"),
        "set-theme.qml",
    )
    obj = component.create()
    assert obj is not None, "\n".join(e.toString() for e in component.errors())


def test_data_table_loads_without_warnings_light_and_dark(qapp) -> None:

    from PySide6.QtCore import qInstallMessageHandler

    for mode in ("light", "dark"):
        messages: list[str] = []
        previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
        engine = create_qml_engine()
        _set_theme(engine, mode)
        component = QQmlComponent(engine)
        component.setData(dedent(ROWS_SOURCE).encode("utf-8"), "data-table-theme-test.qml")
        root = component.create()
        try:
            assert root is not None, "\n".join(e.toString() for e in component.errors())
            qapp.processEvents()
            relevant = [
                m for m in messages
                if "ReferenceError" in m or "TypeError" in m or "is not defined" in m
            ]
            assert relevant == [], f"mode={mode} warnings={relevant}"
        finally:
            if root is not None:
                root.deleteLater()
            qapp.processEvents()
            qInstallMessageHandler(previous_handler)


def _set_density(engine, mode: str) -> None:
    component = QQmlComponent(engine)
    component.setData(
        (
            'import QtQuick\nimport App.Theme 1.0 as Theme\n'
            'QtObject { Component.onCompleted: Theme.AppTheme.densityMode = "%s" }' % mode
        ).encode("utf-8"),
        "set-density.qml",
    )
    obj = component.create()
    assert obj is not None, "\n".join(e.toString() for e in component.errors())


def test_data_table_instantiates_in_every_density_mode(qapp) -> None:
    for mode in ("compact", "comfortable", "spacious"):
        engine = create_qml_engine()
        _set_density(engine, mode)
        component = QQmlComponent(engine)
        component.setData(dedent(ROWS_SOURCE).encode("utf-8"), "data-table-density-test.qml")
        root = component.create()
        try:
            assert root is not None, "\n".join(e.toString() for e in component.errors())
            qapp.processEvents()
        finally:
            if root is not None:
                root.deleteLater()
            qapp.processEvents()


def test_filter_button_is_keyboard_activatable(qapp) -> None:
    source = ROWS_SOURCE.replace(
        'accessibleName: "Test Records"',
        'accessibleName: "Test Records"\n        showFilter: true\n        property int filterClickCount: 0\n        onFilterClicked: filterClickCount += 1',
    )
    engine, component, root = _create_harness(qapp, source)
    try:
        table = _find_by_object_name(root, "dataTable")
        filter_button = _find_by_object_name(root, "dataTableFilterButton")
        assert filter_button is not None
        filter_button.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert table.property("filterClickCount") == 1
    finally:
        root.deleteLater()
        del component, engine
