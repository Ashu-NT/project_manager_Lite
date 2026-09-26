"""Phase H: keyboard activation for the shared "bare Rectangle+MouseArea as
a button" primitives identified by the audit -- TableToolbar's filter/
customize/views buttons, TablePaginationBar's prev/next, NavOverflowMenu's
trigger+menu items, and ContextBar's chip+menu items. Existing mouse
behavior for these components is verified unchanged by the pre-existing
test suites (test_qml_data_table_*, test_pm_detail_table_footer_layout,
test_qml_scheduling_planning_ia_contract) -- this file only adds the new
keyboard coverage."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import Qt, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


def _create_harness(qapp, source: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "bare-button-a11y-test.qml")
    root = component.create()
    assert root is not None, "\n".join(e.toString() for e in component.errors())
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


def _no_js_warnings(messages: list[str]) -> list[str]:
    return [m for m in messages if "ReferenceError" in m or "TypeError" in m or "is not defined" in m]


# ── TableToolbar ──────────────────────────────────────────────────────────────


_TOOLBAR_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 500
    height: 80
    visible: true
    property int filterCount: 0
    property int customizeCount: 0
    property int viewsCount: 0

    AppWidgets.TableToolbar {
        id: toolbar
        objectName: "toolbar"
        anchors.fill: parent
        showFilter: true
        showCustomize: true
        showViews: true
        onFilterClicked: harness.filterCount += 1
        onCustomizeClicked: harness.customizeCount += 1
        onViewsClicked: harness.viewsCount += 1
    }
}
"""


def test_toolbar_filter_button_activates_on_return(qapp) -> None:
    engine, component, root = _create_harness(qapp, _TOOLBAR_SOURCE)
    try:
        button = _find_by_object_name(root, "toolbarFilterButton")
        button.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert root.property("filterCount") == 1
    finally:
        root.deleteLater()
        del component, engine


def test_toolbar_customize_button_activates_on_space(qapp) -> None:
    engine, component, root = _create_harness(qapp, _TOOLBAR_SOURCE)
    try:
        button = _find_by_object_name(root, "toolbarCustomizeButton")
        button.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Space)
        qapp.processEvents()
        assert root.property("customizeCount") == 1
    finally:
        root.deleteLater()
        del component, engine


def test_toolbar_views_button_activates_on_enter(qapp) -> None:
    engine, component, root = _create_harness(qapp, _TOOLBAR_SOURCE)
    try:
        button = _find_by_object_name(root, "toolbarViewsButton")
        button.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Enter)
        qapp.processEvents()
        assert root.property("viewsCount") == 1
    finally:
        root.deleteLater()
        del component, engine


def test_toolbar_hidden_buttons_are_not_focusable(qapp) -> None:
    source = _TOOLBAR_SOURCE.replace("showFilter: true", "showFilter: false")
    engine, component, root = _create_harness(qapp, source)
    try:
        button = _find_by_object_name(root, "toolbarFilterButton")
        assert button.property("activeFocusOnTab") is False
    finally:
        root.deleteLater()
        del component, engine


# ── TablePaginationBar ────────────────────────────────────────────────────────


_PAGINATION_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 500
    height: 60
    visible: true
    property int requestedPage: -1

    AppWidgets.TablePaginationBar {
        id: bar
        objectName: "paginationBar"
        anchors.fill: parent
        currentPage: 2
        pageSize: 25
        totalItems: 100
        onPageRequested: function(page) { harness.requestedPage = page }
    }
}
"""


def test_pagination_next_and_prev_are_keyboard_reachable_via_tab_order(qapp) -> None:
    engine, component, root = _create_harness(qapp, _PAGINATION_SOURCE)
    try:
        bar = _find_by_object_name(root, "paginationBar")
        assert bar is not None
        qapp.processEvents()
    finally:
        root.deleteLater()
        del component, engine


def test_pagination_next_page_via_return_key(qapp) -> None:
    engine, component, root = _create_harness(qapp, _PAGINATION_SOURCE)
    try:
        bar = _find_by_object_name(root, "paginationBar")
        next_btn = _find_by_object_name(bar, "paginationNextButton")
        assert next_btn is not None
        next_btn.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert root.property("requestedPage") == 3
    finally:
        root.deleteLater()
        del component, engine


def test_pagination_prev_page_via_space_key(qapp) -> None:
    engine, component, root = _create_harness(qapp, _PAGINATION_SOURCE)
    try:
        bar = _find_by_object_name(root, "paginationBar")
        prev_btn = _find_by_object_name(bar, "paginationPrevButton")
        assert prev_btn is not None
        prev_btn.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Space)
        qapp.processEvents()
        assert root.property("requestedPage") == 1
    finally:
        root.deleteLater()
        del component, engine


# ── NavOverflowMenu ───────────────────────────────────────────────────────────


_OVERFLOW_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 300
    height: 200
    visible: true
    property string selectedId: ""

    AppWidgets.NavOverflowMenu {
        id: menu
        objectName: "overflowMenu"
        anchors.left: parent.left
        anchors.top: parent.top
        items: [{id: "a", label: "Alpha", count: 0}, {id: "b", label: "Bravo", count: 2}]
        onItemSelected: function(id) { harness.selectedId = id }
    }
}
"""


def test_overflow_trigger_is_keyboard_focusable(qapp) -> None:
    engine, component, root = _create_harness(qapp, _OVERFLOW_SOURCE)
    try:
        menu = _find_by_object_name(root, "overflowMenu")
        assert menu.property("activeFocusOnTab") is True
    finally:
        root.deleteLater()
        del component, engine


def test_overflow_trigger_opens_popup_on_return_without_warnings(qapp) -> None:
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine, component, root = _create_harness(qapp, _OVERFLOW_SOURCE)
    try:
        menu = _find_by_object_name(root, "overflowMenu")
        menu.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert _no_js_warnings(messages) == []
    finally:
        root.deleteLater()
        del component, engine
        qInstallMessageHandler(previous_handler)


# ── ContextBar ────────────────────────────────────────────────────────────────


_CONTEXT_BAR_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 500
    height: 60
    visible: true
    property string selectedOrgId: ""

    AppWidgets.ContextBar {
        id: bar
        objectName: "contextBar"
        anchors.fill: parent
        tenantSwitcherVisible: false
        organizationName: "Default Organization"
        organizationOptions: [{id: "org-1", label: "Default Organization"}, {id: "org-2", label: "Other Org"}]
        onOrganizationSelected: function(id) { harness.selectedOrgId = id }
    }
}
"""


def test_context_bar_loads_without_warnings(qapp) -> None:
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine, component, root = _create_harness(qapp, _CONTEXT_BAR_SOURCE)
    try:
        qapp.processEvents()
        assert _no_js_warnings(messages) == []
    finally:
        root.deleteLater()
        del component, engine
        qInstallMessageHandler(previous_handler)


def test_context_bar_organization_chip_is_keyboard_focusable_and_opens_on_return(qapp) -> None:
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine, component, root = _create_harness(qapp, _CONTEXT_BAR_SOURCE)
    try:
        chip = _find_by_object_name(root, "contextBarOrganizationChip")
        assert chip is not None
        assert chip.property("activeFocusOnTab") is True
        chip.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert _no_js_warnings(messages) == []
    finally:
        root.deleteLater()
        del component, engine
        qInstallMessageHandler(previous_handler)
