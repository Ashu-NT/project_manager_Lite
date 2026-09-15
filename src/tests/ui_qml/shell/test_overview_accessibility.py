"""Phase 6E closeout: module icon mapping + keyboard/focus accessibility for
ModuleCard.qml and ActionCenterRow.qml."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from PySide6.QtCore import QUrl, Qt, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


def _create_harness(qapp, source: str):
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "overview-accessibility-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return previous_handler, messages, engine, component, root


def _teardown(previous_handler, root, qapp) -> None:
    root.deleteLater()
    qapp.processEvents()
    qInstallMessageHandler(previous_handler)


# -- Module icon mapping -------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_code,expected_icon",
    [
        ("platform", "admin"),
        ("project_management", "project"),
        ("some_future_module", "module"),
        ("", "module"),
    ],
)
def test_module_icon_map_resolves_to_a_registered_icon(qapp, module_code, expected_icon) -> None:
    widgets_dir = Path(__file__).resolve().parents[3] / "ui_qml/shared/qml/App/Widgets"
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    source = (
        'import QtQuick\n'
        'import "ModuleIconMap.js" as ModuleIconMap\n'
        'QtObject { property string resolved: ModuleIconMap.iconNameFor("%s") }' % module_code
    )
    component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(widgets_dir / "dummy.qml")))
    obj = component.create()
    assert obj is not None, "\n".join(error.toString() for error in component.errors())
    assert obj.property("resolved") == expected_icon


@pytest.mark.parametrize(
    "module_code,expected_icon",
    [
        ("platform", "admin"),
        ("project_management", "project"),
        ("some_future_module", "module"),
    ],
)
def test_module_card_resolves_known_and_unknown_icon_keys_without_warnings(
    qapp, module_code, expected_icon
) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp,
        f"""
        import QtQuick
        import App.Widgets 1.0 as AppWidgets
        Window {{
            width: 400
            height: 200
            visible: true
            AppWidgets.ModuleCard {{
                id: card
                width: 360
                moduleCode: "{module_code}"
                title: "Some Module"
                description: "desc"
                iconKey: "{module_code}"
                summaryText: "1 thing"
                routeId: "some.route"
            }}
        }}
        """,
    )
    try:
        qapp.processEvents()
        unknown_icon_warnings = [m for m in messages if "unknown icon name" in m]
        assert unknown_icon_warnings == [], unknown_icon_warnings
    finally:
        _teardown(previous_handler, root, qapp)


# -- ModuleCard keyboard / focus -------------------------------------------------------------


def _module_card_harness_source(*, navigable: bool) -> str:
    route = "project_management.projects" if navigable else ""
    return f"""
    import QtQuick
    import App.Widgets 1.0 as AppWidgets
    Window {{
        id: harness
        width: 400
        height: 200
        visible: true
        property int activatedCount: 0
        property int cardAccessibleRole: card.Accessible.role
        property int buttonRoleValue: Accessible.Button
        property var cardRef: card
        AppWidgets.ModuleCard {{
            id: card
            width: 360
            moduleCode: "project_management"
            title: "Project Management"
            description: "desc"
            iconKey: "project_management"
            summaryText: "1 thing"
            routeId: "{route}"
            onActivated: harness.activatedCount += 1
        }}
    }}
    """


def test_module_card_activates_on_keyboard_return(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp, _module_card_harness_source(navigable=True)
    )
    try:
        card = root.property("cardRef")
        card.forceActiveFocus()
        qapp.processEvents()
        assert card.property("activeFocus") is True

        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert root.property("activatedCount") == 1

        QTest.keyClick(root, Qt.Key.Key_Space)
        qapp.processEvents()
        assert root.property("activatedCount") == 2
    finally:
        _teardown(previous_handler, root, qapp)


def test_module_card_is_keyboard_reachable_when_navigable(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp, _module_card_harness_source(navigable=True)
    )
    try:
        card = root.property("cardRef")
        assert card.property("activeFocusOnTab") is True
        assert root.property("cardAccessibleRole") == root.property("buttonRoleValue")
    finally:
        _teardown(previous_handler, root, qapp)


def test_informational_module_card_is_not_keyboard_reachable(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp, _module_card_harness_source(navigable=False)
    )
    try:
        card = root.property("cardRef")
        assert card.property("activeFocusOnTab") is False

        card.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()

        assert root.property("activatedCount") == 0
    finally:
        _teardown(previous_handler, root, qapp)


# -- ActionCenterRow keyboard / focus ---------------------------------------------------------


def _action_center_row_harness_source(*, navigable: bool) -> str:
    route = "project_management.tasks" if navigable else ""
    return f"""
    import QtQuick
    import App.Widgets 1.0 as AppWidgets
    Window {{
        id: harness
        width: 400
        height: 120
        visible: true
        property int activatedCount: 0
        property var rowRef: row
        AppWidgets.ActionCenterRow {{
            id: row
            width: 360
            title: "Review project estimates"
            moduleLabel: "Project Management"
            subjectDisplay: "Facility Upgrade"
            actionState: "todo"
            statusLabel: "To do"
            dueLabel: "Due 12 Sep"
            routeId: "{route}"
            onActivated: harness.activatedCount += 1
        }}
    }}
    """


def test_action_center_row_activates_on_keyboard_enter_and_space(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp, _action_center_row_harness_source(navigable=True)
    )
    try:
        row = root.property("rowRef")
        row.forceActiveFocus()
        qapp.processEvents()
        assert row.property("activeFocus") is True

        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert root.property("activatedCount") == 1

        QTest.keyClick(root, Qt.Key.Key_Space)
        qapp.processEvents()
        assert root.property("activatedCount") == 2
    finally:
        _teardown(previous_handler, root, qapp)


def test_action_center_row_without_route_is_not_keyboard_reachable(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp, _action_center_row_harness_source(navigable=False)
    )
    try:
        row = root.property("rowRef")
        assert row.property("activeFocusOnTab") is False

        row.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()

        assert root.property("activatedCount") == 0
    finally:
        _teardown(previous_handler, root, qapp)


def test_action_center_row_has_no_qml_warnings_on_activation(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(
        qapp, _action_center_row_harness_source(navigable=True)
    )
    try:
        row = root.property("rowRef")
        row.forceActiveFocus()
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()

        relevant = [m for m in messages if "ReferenceError" in m or "TypeError" in m]
        assert relevant == []
    finally:
        _teardown(previous_handler, root, qapp)
