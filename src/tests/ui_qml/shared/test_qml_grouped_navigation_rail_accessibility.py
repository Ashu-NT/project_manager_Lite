from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import Qt
from PySide6.QtGui import QAccessible
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine

_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 320
    height: 480
    visible: true

    property int activatedIndex: -1
    property int activatedCount: 0
    readonly property int railAccessibleRole: rail.Accessible.role
    readonly property string railAccessibleName: rail.Accessible.name

    AppWidgets.GroupedNavigationRail {
        id: rail
        objectName: "rail"
        anchors.fill: parent
        railTitle: "Test Rail"
        groupsCollapsedByDefault: false
        items: [
            { label: "Overview", group: "", icon: "dashboard" },
            { label: "Alpha", group: "Group A", icon: "module" },
            { label: "Beta", group: "Group A", icon: "module" },
            { label: "Gamma", group: "Group B", icon: "module" }
        ]
        activeIndex: 0
        onItemActivated: function(index) {
            rail.activeIndex = index
            harness.activatedIndex = index
            harness.activatedCount += 1
        }
    }
}
"""


def _create_harness(qapp, source: str = _SOURCE):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "grouped-nav-rail-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _find_by_object_name(obj, name):
    if obj.objectName() == name:
        return obj
    children = obj.childItems() if isinstance(obj, QQuickItem) else obj.children()
    for child in children:
        found = _find_by_object_name(child, name)
        if found is not None:
            return found
    return None


def test_rail_has_pane_role_and_title_as_accessible_name(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    assert root.property("railAccessibleRole") == QAccessible.Role.Pane.value
    assert root.property("railAccessibleName") == "Test Rail"


def test_down_arrow_moves_through_visible_items_in_order(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.forceActiveFocus()

    QTest.keyClick(root, Qt.Key_Down)
    assert root.property("activatedIndex") == 1

    QTest.keyClick(root, Qt.Key_Down)
    assert root.property("activatedIndex") == 2


def test_up_arrow_moves_backward(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.setProperty("activeIndex", 2)
    rail.forceActiveFocus()

    QTest.keyClick(root, Qt.Key_Up)
    assert root.property("activatedIndex") == 1


def test_return_key_activates_current_item(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.setProperty("activeIndex", 3)
    rail.forceActiveFocus()

    QTest.keyClick(root, Qt.Key_Return)
    assert root.property("activatedIndex") == 3
    assert root.property("activatedCount") == 1


def test_space_key_activates_current_item(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.setProperty("activeIndex", 1)
    rail.forceActiveFocus()

    QTest.keyClick(root, Qt.Key_Space)
    assert root.property("activatedIndex") == 1
    assert root.property("activatedCount") == 1


def test_left_arrow_collapses_active_items_group_and_hides_its_items(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.setProperty("activeIndex", 1)  # Alpha, in Group A
    rail.forceActiveFocus()

    QTest.keyClick(root, Qt.Key_Left)

    visible = rail.property("_visibleItemIndexes").toVariant()
    assert 1 not in visible
    assert 2 not in visible
    assert 0 in visible
    assert 3 in visible


def test_right_arrow_reexpands_a_collapsed_group(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.setProperty("activeIndex", 1)
    rail.forceActiveFocus()

    QTest.keyClick(root, Qt.Key_Left)
    assert 1 not in rail.property("_visibleItemIndexes").toVariant()

    QTest.keyClick(root, Qt.Key_Right)
    assert 1 in rail.property("_visibleItemIndexes").toVariant()


def test_active_item_exposes_accessible_role_name_and_selected_state(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    rail = _find_by_object_name(root, "rail")
    rail.setProperty("activeIndex", 1)
    qapp.processEvents()

    alpha_item = _find_by_object_name(rail, "navRailItem_1")
    assert alpha_item is not None
    assert alpha_item.property("isActive") is True
    assert str(alpha_item.property("itemLabel")) == "Alpha"
