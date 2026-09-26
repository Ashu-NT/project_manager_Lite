from __future__ import annotations

from textwrap import dedent

from PySide6.QtQml import QQmlComponent

from src.ui_qml.shell.qml_engine import create_qml_engine

_SOURCE = """
import QtQuick
import App.Widgets 1.0 as AppWidgets

Window {
    id: harness
    width: 300
    height: 400
    visible: true

    property string activatedId: ""
    property string activatedRouteId: ""

    AppWidgets.NavigationTree {
        id: tree
        objectName: "tree"
        anchors.fill: parent
        railTitle: "Test"
        groups: [
            {
                "id": "", "label": "", "order": 0, "expandedByDefault": true,
                "items": [
                    { "id": "overview", "label": "Overview", "iconKey": "dashboard", "routeId": "shell.home", "groupId": "", "order": 0 }
                ]
            },
            {
                "id": "business", "label": "Business", "order": 10, "expandedByDefault": true,
                "items": [
                    { "id": "project_management.workspace", "label": "Project Management", "iconKey": "project", "routeId": "project_management.workspace", "groupId": "business", "order": 0 }
                ]
            },
            {
                "id": "administration", "label": "Administration", "order": 20, "expandedByDefault": true,
                "items": [
                    { "id": "platform.workspace", "label": "Platform", "iconKey": "platform", "routeId": "platform.workspace", "groupId": "administration", "order": 0 }
                ]
            }
        ]
        activeId: "platform.workspace"
        onItemActivated: function(id, routeId) {
            harness.activatedId = id
            harness.activatedRouteId = routeId
        }
    }
}
"""


def _create_harness(qapp):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(_SOURCE).encode("utf-8"), "navigation-tree-test.qml")
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


def test_groups_flatten_in_order_with_group_labels(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    tree = _find_by_object_name(root, "tree")
    flat = tree.property("_flatItems").toVariant()

    assert [item["id"] for item in flat] == [
        "overview",
        "project_management.workspace",
        "platform.workspace",
    ]
    assert flat[0]["group"] == ""
    assert flat[1]["group"] == "Business"
    assert flat[2]["group"] == "Administration"


def test_active_id_resolves_to_correct_flat_index(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    tree = _find_by_object_name(root, "tree")
    assert tree.property("_activeIndex") == 2


def test_item_activated_emits_id_and_route_id(qapp) -> None:
    _engine, _component, root = _create_harness(qapp)
    tree = _find_by_object_name(root, "tree")
    tree.itemActivated.emit("project_management.workspace", "project_management.workspace")
    assert root.property("activatedId") == "project_management.workspace"
    assert root.property("activatedRouteId") == "project_management.workspace"
