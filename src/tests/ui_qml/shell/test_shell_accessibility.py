"""Phase 6F: keyboard/focus accessibility for the new shell-header
interactive elements (NotificationBell, OrganizationSwitcher)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from PySide6.QtCore import QUrl, Qt, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine

# NotificationBell.qml/OrganizationSwitcher.qml are plain directory-local QML
# files (same resolution convention as TenantSwitcher.qml), not module-
# registered -- the harness component needs a base URL inside shell/qml/ so
# bare references to them resolve, exactly like ShellHeader.qml's own.
_SHELL_QML_DIR = Path(__file__).resolve().parents[3] / "ui_qml/shell/qml"


def _create_harness(qapp, source: str):
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        dedent(source).encode("utf-8"),
        QUrl.fromLocalFile(str(_SHELL_QML_DIR / "shell-accessibility-test.qml")),
    )
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return previous_handler, messages, engine, component, root


def _teardown(previous_handler, root, qapp) -> None:
    root.deleteLater()
    qapp.processEvents()
    qInstallMessageHandler(previous_handler)


# -- NotificationBell -------------------------------------------------------------------


def _bell_harness_source() -> str:
    return """
    import QtQuick
    Window {
        id: harness
        width: 200
        height: 100
        visible: true
        property int activatedCount: 0
        property var bellRef: bell
        NotificationBell {
            id: bell
            controller: null
            onActivated: harness.activatedCount += 1
        }
    }
    """


def test_bell_is_keyboard_reachable(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(qapp, _bell_harness_source())
    try:
        bell = root.property("bellRef")
        assert bell.property("activeFocusOnTab") is True
    finally:
        _teardown(previous_handler, root, qapp)


def test_bell_activates_on_keyboard_return_and_space(qapp) -> None:
    previous_handler, messages, engine, component, root = _create_harness(qapp, _bell_harness_source())
    try:
        bell = root.property("bellRef")
        bell.forceActiveFocus()
        qapp.processEvents()
        assert bell.property("activeFocus") is True

        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()
        assert root.property("activatedCount") == 1

        QTest.keyClick(root, Qt.Key.Key_Space)
        qapp.processEvents()
        assert root.property("activatedCount") == 2
    finally:
        _teardown(previous_handler, root, qapp)


# -- OrganizationSwitcher -------------------------------------------------------------------


def _org_switcher_harness_source(*, organizations: str, active_id: str) -> str:
    return f"""
    import QtQuick
    Window {{
        id: harness
        width: 300
        height: 100
        visible: true
        property var switcherRef: switcher
        QtObject {{
            id: fakeController
            property var organizations: {organizations}
            property string activeOrganizationId: "{active_id}"
            property bool isMultiOrganization: organizations.length > 1
            function switchToOrganization(id) {{ fakeController.activeOrganizationId = id }}
        }}
        OrganizationSwitcher {{
            id: switcher
            controller: fakeController
        }}
    }}
    """


def test_single_organization_switcher_is_not_keyboard_reachable(qapp) -> None:
    source = _org_switcher_harness_source(
        organizations='[{"id": "org-1", "displayName": "Only Org", "organizationCode": "ORG1", "status": "active"}]',
        active_id="org-1",
    )
    previous_handler, messages, engine, component, root = _create_harness(qapp, source)
    try:
        switcher = root.property("switcherRef")
        assert switcher.property("activeFocusOnTab") is False
    finally:
        _teardown(previous_handler, root, qapp)


def test_multi_organization_switcher_is_keyboard_reachable(qapp) -> None:
    source = _org_switcher_harness_source(
        organizations=(
            '[{"id": "org-1", "displayName": "Org One", "organizationCode": "ORG1", "status": "active"},'
            '{"id": "org-2", "displayName": "Org Two", "organizationCode": "ORG2", "status": "active"}]'
        ),
        active_id="org-1",
    )
    previous_handler, messages, engine, component, root = _create_harness(qapp, source)
    try:
        switcher = root.property("switcherRef")
        assert switcher.property("activeFocusOnTab") is True
    finally:
        _teardown(previous_handler, root, qapp)


def test_multi_organization_switcher_opens_menu_on_keyboard_return(qapp) -> None:
    source = _org_switcher_harness_source(
        organizations=(
            '[{"id": "org-1", "displayName": "Org One", "organizationCode": "ORG1", "status": "active"},'
            '{"id": "org-2", "displayName": "Org Two", "organizationCode": "ORG2", "status": "active"}]'
        ),
        active_id="org-1",
    )
    previous_handler, messages, engine, component, root = _create_harness(qapp, source)
    try:
        switcher = root.property("switcherRef")
        switcher.forceActiveFocus()
        qapp.processEvents()

        # Must not raise/warn when activated via keyboard.
        QTest.keyClick(root, Qt.Key.Key_Return)
        qapp.processEvents()

        relevant = [m for m in messages if "ReferenceError" in m or "TypeError" in m]
        assert relevant == []
    finally:
        _teardown(previous_handler, root, qapp)
