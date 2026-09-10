from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from PySide6.QtCore import QObject, QMetaObject, Qt, QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


VIEWPORTS = (
    (1024, 640),
    (1280, 720),
    (1366, 768),
    (1440, 900),
    (1920, 1080),
)
DIALOG_ROOT = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs"
).resolve()
MANUAL_DIALOG = (DIALOG_ROOT / "ManualActualEditorDialog.qml").as_uri()
LIFECYCLE_DIALOG = (DIALOG_ROOT / "ActualLifecycleDialog.qml").as_uri()
HOST_DIALOG = (DIALOG_ROOT / "FinancialsDialogHost.qml").as_uri()
ACTUALS_SECTION = (
    DIALOG_ROOT.parent / "sections" / "FinancialsActualsSection.qml"
).as_uri()
REJECTED_QML_WARNINGS = (
    "managed by a layout",
    "binding loop",
    "ReferenceError",
    "TypeError",
    "Cannot read property",
    "is not a function",
    "destroyed",
)


def _wait(qapp, predicate, *, attempts: int = 40) -> bool:
    for _ in range(attempts):
        qapp.processEvents()
        if predicate():
            return True
        QTest.qWait(25)
    return False


def _component(engine, source: str, name: str) -> QQmlComponent:
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), QUrl(name))
    return component


def _manual_window_source(
    width: int,
    height: int,
    *,
    initial_project: bool = True,
    mode: str = "create",
) -> str:
    project_id = '"project-1"' if initial_project else '""'
    cost_code_id = '"code-1"' if initial_project else '""'
    entry = (
        '{"id": "entry-a", "state": {'
        '"entryId": "entry-a", "rowVersion": 3, '
        '"description": "Travel adjustment", "amount": "10000", '
        '"transactionDate": "2026-09-10", "entryKind": "actual", '
        '"taskId": "task-1", "resourceId": "resource-1", '
        '"costCodeId": "code-1"}}'
        if mode == "edit"
        else "null"
    )
    return f"""
        import QtQuick
        import QtQuick.Controls

        ApplicationWindow {{
            id: testWindow
            width: {width}
            height: {height}
            visible: true
            property int submittedCount: 0
            readonly property var actualDialog: dialogLoader.item

            Button {{
                id: opener
                objectName: "actualDialogOpener"
                text: "Open Actual"
            }}
            Button {{
                id: fallback
                objectName: "actualDialogFallback"
                text: "Finance Project"
                y: 52
            }}
            QtObject {{
                id: controller
                property bool isBusy: false
                function resolveManualActualProject(projectId) {{
                    return {{"ok": true, "item": {{"value": projectId, "label": "Project One"}}}}
                }}
                function loadManualActualDefaults(projectId) {{
                    return {{"ok": true, "currencyCode": "XAF", "entryKinds": [{{"label": "Actual", "value": "actual"}}]}}
                }}
                function resolveManualActualTask(projectId, taskId) {{
                    return {{"ok": true, "item": {{"value": taskId, "label": "Task One"}}}}
                }}
                function resolveManualActualResource(projectId, resourceId) {{
                    return {{"ok": true, "item": {{"value": resourceId, "label": "Resource One"}}}}
                }}
                function resolveManualActualCostCode(projectId, codeId, effectiveOn) {{
                    return {{"ok": true, "item": {{"value": codeId, "label": "CC-001 - Labor"}}}}
                }}
                function searchManualActualProjects(query, page, pageSize) {{
                    return {{"ok": true, "items": [{{"value": "project-1", "label": "Project One"}}], "page": page, "total": 1, "hasMore": false}}
                }}
                function searchManualActualTasks(projectId, query, page, pageSize) {{
                    return {{"ok": true, "items": [{{"value": "task-1", "label": "Task One"}}], "page": page, "total": 1, "hasMore": false}}
                }}
                function searchManualActualResources(projectId, query, page, pageSize) {{
                    return {{"ok": true, "items": [{{"value": "resource-1", "label": "Resource One"}}], "page": page, "total": 1, "hasMore": false}}
                }}
                function searchManualActualCostCodes(projectId, query, page, pageSize, effectiveOn) {{
                    return {{"ok": true, "items": [{{"value": "code-1", "label": "CC-001 - Labor"}}], "page": page, "total": 1, "hasMore": false}}
                }}
            }}
            Loader {{
                id: dialogLoader
                source: "{MANUAL_DIALOG}"
                onLoaded: {{
                    item.workspaceController = controller
                    item.mode = "{mode}"
                    item.entry = {entry}
                    item.initialProjectId = {project_id}
                    item.initialTaskId = "task-1"
                    item.initialCostCodeId = {cost_code_id}
                    item.commandId = "command-1"
                    item.focusReturnTarget = opener
                    item.focusFallbackTarget = fallback
                    item.submitted.connect(function(payload) {{ testWindow.submittedCount += 1 }})
                    opener.forceActiveFocus()
                    item.open()
                }}
            }}
        }}
    """


def _lifecycle_window_source(width: int, height: int, mode: str) -> str:
    return f"""
        import QtQuick
        import QtQuick.Controls

        ApplicationWindow {{
            id: testWindow
            width: {width}
            height: {height}
            visible: true
            property int decisionCount: 0
            readonly property var actualDialog: dialogLoader.item

            Button {{
                id: opener
                objectName: "actualDialogOpener"
                text: "Open Decision"
            }}
            Button {{
                id: fallback
                objectName: "actualDialogFallback"
                text: "Finance Project"
                y: 52
            }}
            Loader {{
                id: dialogLoader
                source: "{LIFECYCLE_DIALOG}"
                onLoaded: {{
                    item.mode = "{mode}"
                    item.entryId = "entry-a"
                    item.rowVersion = 3
                    item.commandId = "command-1"
                    item.focusReturnTarget = opener
                    item.focusFallbackTarget = fallback
                    item.decided.connect(function(action, payload) {{ testWindow.decisionCount += 1 }})
                    opener.forceActiveFocus()
                    item.open()
                }}
            }}
        }}
    """


def _assert_footer_is_reachable(window, dialog) -> None:
    footer = dialog.findChild(QObject, "dialogActionFooter")
    assert footer is not None and bool(footer.property("visible"))
    assert 0 < float(footer.property("width")) <= float(dialog.property("width"))
    assert 0 < float(footer.property("height")) <= float(dialog.property("height"))
    assert float(footer.property("y")) >= 0
    assert (
        float(footer.property("y")) + float(footer.property("height"))
        <= float(dialog.property("height")) + 1
    )
    for object_name in ("dialogCancelButton", "dialogSubmitButton"):
        button = dialog.findChild(QObject, object_name)
        assert button is not None and bool(button.property("visible"))
        assert 0 < float(button.property("width")) <= float(footer.property("width"))
        assert 0 < float(button.property("height")) <= float(footer.property("height"))


def _assert_no_rejected_warnings(messages: list[str]) -> None:
    lowered = [message.lower() for message in messages]
    assert not any(
        rejected.lower() in message
        for rejected in REJECTED_QML_WARNINGS
        for message in lowered
    ), messages


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
def test_actuals_table_surface_is_usable_at_supported_viewports(
    qapp, width: int, height: int
) -> None:
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(
        lambda _message_type, _context, message: messages.append(str(message))
    )
    window = None
    try:
        engine = create_qml_engine()
        component = _component(
            engine,
            f"""
                import QtQuick
                import QtQuick.Controls

                ApplicationWindow {{
                    width: {width}
                    height: {height}
                    visible: true
                    ListModel {{
                        id: actualRows
                        ListElement {{
                            rowId: "entry-a"
                            title: "ACT-0001"
                            subtitle: "Manual Actual / Draft"
                            statusLabel: "10,000 XAF"
                            supportingText: "Task One / Resource One"
                            metaText: "10 Sep 2026 / Manual"
                        }}
                    }}
                    Loader {{
                        anchors.fill: parent
                        source: "{ACTUALS_SECTION}"
                        onLoaded: {{
                            item.ledgerModel = {{
                                "items": [{{"id": "entry-a"}}],
                                "page": 1,
                                "pageSize": 50,
                                "total": 51
                            }}
                            item.ledgerTableModel = actualRows
                        }}
                    }}
                }}
            """,
            f"r6dc1-actuals-surface-{width}x{height}.qml",
        )
        window = component.create()
        assert window is not None, "\n".join(
            error.toString() for error in component.errors()
        )
        assert _wait(
            qapp,
            lambda: window.findChild(QObject, "financialsActualsTable") is not None,
        )

        section = window.findChild(QObject, "financialsActualsSection")
        toolbar = window.findChild(QObject, "financialsActualsFilterToolbar")
        table = window.findChild(QObject, "financialsActualsTable")
        status_filter = window.findChild(QObject, "financialsActualsStatusFilter")
        source_filter = window.findChild(QObject, "financialsActualsSourceFilter")
        pagination = window.findChild(QObject, "financialsActualsPagination")
        assert all(
            item is not None
            for item in (section, toolbar, table, status_filter, source_filter, pagination)
        )
        assert 0 < float(section.property("width")) <= width
        assert 0 < float(toolbar.property("width")) <= width
        assert 0 < float(table.property("width")) <= width
        assert 0 < float(table.property("height")) < height
        assert table.property("sortingMode") == "server"
        assert 0 < float(status_filter.property("width")) <= float(toolbar.property("width"))
        assert 0 < float(source_filter.property("width")) <= float(toolbar.property("width"))
        assert bool(pagination.property("visible"))
        assert 0 < float(pagination.property("width")) <= width
    finally:
        if window is not None:
            window.close()
            window.deleteLater()
        qapp.processEvents()
        qInstallMessageHandler(previous_handler)

    _assert_no_rejected_warnings(messages)


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
@pytest.mark.parametrize("mode", ("create", "edit"))
def test_manual_actual_dialog_is_operable_at_supported_viewports(
    qapp, width: int, height: int, mode: str
) -> None:
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(
        lambda _message_type, _context, message: messages.append(str(message))
    )
    window = None
    try:
        engine = create_qml_engine()
        component = _component(
            engine,
            _manual_window_source(width, height, mode=mode),
            f"r6dc1-manual-{mode}-{width}x{height}.qml",
        )
        window = component.create()
        assert window is not None, "\n".join(
            error.toString() for error in component.errors()
        )
        assert _wait(
            qapp,
            lambda: window.property("actualDialog") is not None
            and bool(window.property("actualDialog").property("opened")),
        )
        dialog = window.property("actualDialog")

        assert 0 < float(dialog.property("width")) <= width
        assert 0 < float(dialog.property("height")) <= height
        assert float(dialog.property("x")) >= 0
        assert float(dialog.property("y")) >= 0
        assert float(dialog.property("x")) + float(dialog.property("width")) <= width
        assert float(dialog.property("y")) + float(dialog.property("height")) <= height
        _assert_footer_is_reachable(window, dialog)

        controls = (
            "manualActualProjectSelector",
            "manualActualDescriptionField",
            "manualActualResourceSelector",
            "manualActualEntryKindField",
            "manualActualTaskSelector",
            "manualActualCostCodeSelector",
            "manualActualAmountField",
            "manualActualCurrencyField",
            "manualActualTransactionDateField",
        )
        for object_name in controls:
            control = dialog.findChild(QObject, object_name)
            assert control is not None and bool(control.property("visible"))
            assert 0 < float(control.property("width")) <= float(dialog.property("width"))

        for object_name in (
            "manualActualTaskSelector",
            "manualActualCostCodeSelector",
            "manualActualResourceSelector",
        ):
            selector = dialog.findChild(QObject, object_name)
            assert QMetaObject.invokeMethod(selector, "openPopup")
            assert _wait(
                qapp,
                lambda: any(
                    child.property("opened") is True
                    for child in selector.findChildren(QObject)
                ),
            )
            QTest.keyClick(window, Qt.Key.Key_Escape)
            qapp.processEvents()
            assert bool(dialog.property("opened"))
        if mode == "create":
            selector = dialog.findChild(QObject, "manualActualProjectSelector")
            assert QMetaObject.invokeMethod(selector, "openPopup")
            assert _wait(
                qapp,
                lambda: any(
                    child.property("opened") is True
                    for child in selector.findChildren(QObject)
                ),
            )
            QTest.keyClick(window, Qt.Key.Key_Escape)
            qapp.processEvents()
            assert bool(dialog.property("opened"))
    finally:
        if window is not None:
            window.close()
            window.deleteLater()
        qapp.processEvents()
        qInstallMessageHandler(previous_handler)

    _assert_no_rejected_warnings(messages)


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
@pytest.mark.parametrize("mode", ("delete", "reject", "post", "reverse"))
def test_actual_lifecycle_dialogs_keep_actions_reachable(
    qapp, width: int, height: int, mode: str
) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _lifecycle_window_source(width, height, mode),
        f"r6dc1-{mode}-{width}x{height}.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        assert _wait(
            qapp,
            lambda: window.property("actualDialog") is not None
            and bool(window.property("actualDialog").property("opened")),
        )
        dialog = window.property("actualDialog")
        assert 0 < float(dialog.property("width")) <= width
        assert 0 < float(dialog.property("height")) <= height
        assert float(dialog.property("x")) >= 0
        assert float(dialog.property("y")) >= 0
        assert float(dialog.property("x")) + float(dialog.property("width")) <= width
        assert float(dialog.property("y")) + float(dialog.property("height")) <= height
        _assert_footer_is_reachable(window, dialog)
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_manual_actual_keyboard_validation_and_safe_enter(qapp) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _manual_window_source(1024, 640),
        "r6dc1-manual-keyboard.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        assert _wait(qapp, lambda: window.property("actualDialog") is not None)
        dialog = window.property("actualDialog")
        description = dialog.findChild(QObject, "manualActualDescriptionField")
        amount = dialog.findChild(QObject, "manualActualAmountField")
        assert _wait(qapp, lambda: bool(description.property("activeFocus")))

        QTest.keyClick(window, Qt.Key.Key_Return)
        qapp.processEvents()
        assert window.property("submittedCount") == 0
        assert bool(dialog.property("opened"))

        QTest.keyClick(window, Qt.Key.Key_Tab)
        qapp.processEvents()
        assert not bool(description.property("activeFocus"))
        QTest.keyClick(window, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier)
        qapp.processEvents()
        assert bool(description.property("activeFocus"))

        assert QMetaObject.invokeMethod(dialog, "submitDialog")
        qapp.processEvents()
        assert dialog.property("errorMessage") == "Description is required."
        assert bool(description.property("activeFocus"))

        description.setProperty("text", "Travel adjustment")
        assert QMetaObject.invokeMethod(dialog, "submitDialog")
        qapp.processEvents()
        assert dialog.property("errorMessage") == "Amount is required."
        assert bool(amount.property("activeFocus"))

        opener = window.findChild(QObject, "actualDialogOpener")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        assert _wait(qapp, lambda: not bool(dialog.property("opened")))
        assert _wait(qapp, lambda: bool(opener.property("activeFocus")))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("mode", ("delete", "reject", "post", "reverse"))
def test_actual_lifecycle_enter_is_never_a_mutating_default(qapp, mode: str) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _lifecycle_window_source(1024, 640, mode),
        f"r6dc1-{mode}-safe-enter.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        assert _wait(qapp, lambda: window.property("actualDialog") is not None)
        dialog = window.property("actualDialog")
        assert _wait(
            qapp,
            lambda: bool(
                dialog.findChild(
                    QObject,
                    "dialogCancelButton"
                    if mode == "delete"
                    else (
                        "actualDecisionNotesField"
                        if mode == "reject"
                        else "actualPostingDateFieldInput"
                    ),
                ).property("activeFocus")
            ),
        )
        QTest.keyClick(window, Qt.Key.Key_Return)
        qapp.processEvents()
        assert window.property("decisionCount") == 0
        if mode != "delete":
            assert bool(dialog.property("opened"))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("mode", ("delete", "reject", "post", "reverse"))
def test_actual_lifecycle_tab_and_shift_tab_reverse_logically(qapp, mode: str) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _lifecycle_window_source(1024, 640, mode),
        f"r6dc1-{mode}-tab-order.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        assert _wait(qapp, lambda: window.property("actualDialog") is not None)
        dialog = window.property("actualDialog")
        initial = dialog.findChild(
            QObject,
                "dialogCancelButton"
                if mode == "delete"
                else (
                    "actualDecisionNotesField"
                    if mode == "reject"
                    else "actualPostingDateFieldInput"
                ),
            )
        assert _wait(qapp, lambda: bool(initial.property("activeFocus")))

        QTest.keyClick(window, Qt.Key.Key_Tab)
        qapp.processEvents()
        assert not bool(initial.property("activeFocus"))
        for _ in range(4):
            QTest.keyClick(window, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier)
            qapp.processEvents()
            if bool(initial.property("activeFocus")):
                break
        assert bool(initial.property("activeFocus"))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_reversal_validation_focuses_each_missing_required_field(qapp) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _lifecycle_window_source(1024, 640, "reverse"),
        "r6dc1-reversal-validation.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        assert _wait(qapp, lambda: window.property("actualDialog") is not None)
        dialog = window.property("actualDialog")
        posting_date = dialog.findChild(QObject, "actualPostingDateField")
        posting_date_input = dialog.findChild(QObject, "actualPostingDateFieldInput")
        reason = dialog.findChild(QObject, "actualDecisionNotesField")

        posting_date.setProperty("text", "")
        assert QMetaObject.invokeMethod(dialog, "submitDialog")
        qapp.processEvents()
        assert dialog.property("errorMessage") == "Posting date is required."
        assert bool(posting_date_input.property("activeFocus"))

        posting_date.setProperty("text", "2026-09-10")
        assert QMetaObject.invokeMethod(dialog, "submitDialog")
        qapp.processEvents()
        assert dialog.property("errorMessage") == "A reversal reason is required."
        assert bool(reason.property("activeFocus"))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("mode", ("delete", "reject", "post", "reverse"))
@pytest.mark.parametrize("hide_opener", (False, True))
def test_actual_dialog_escape_restores_preferred_or_stable_fallback_focus(
    qapp, hide_opener: bool, mode: str
) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _lifecycle_window_source(1024, 640, mode),
        f"r6dc1-{mode}-focus-restore.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        dialog = None
        assert _wait(
            qapp,
            lambda: window.property("actualDialog") is not None
            and bool(window.property("actualDialog").property("opened")),
        )
        dialog = window.property("actualDialog")
        opener = window.findChild(QObject, "actualDialogOpener")
        fallback = window.findChild(QObject, "actualDialogFallback")
        if hide_opener:
            opener.setProperty("visible", False)

        QTest.keyClick(window, Qt.Key.Key_Escape)
        assert _wait(qapp, lambda: not bool(dialog.property("opened")))
        expected = fallback if hide_opener else opener
        assert _wait(qapp, lambda: bool(expected.property("activeFocus")))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


def _host_window_source(open_expression: str) -> str:
    return f"""
        import QtQuick
        import QtQuick.Controls

        ApplicationWindow {{
            id: testWindow
            width: 1024
            height: 640
            visible: true
            property string selectedProjectId: "project-a"
            property string selectedEntryId: "entry-a"

            Button {{ id: opener; objectName: "actualDialogOpener"; text: "Actual action" }}
            Button {{ id: fallback; objectName: "actualDialogFallback"; text: "Finance project"; y: 52 }}
            QtObject {{
                id: controller
                property bool isBusy: false
                function newFinancialCommandId() {{ return "command-1" }}
                function resolveManualActualProject(projectId) {{
                    return {{"ok": true, "item": {{"value": projectId, "label": "Project One"}}}}
                }}
                function loadManualActualDefaults(projectId) {{
                    return {{"ok": true, "currencyCode": "XAF", "entryKinds": [{{"label": "Actual", "value": "actual"}}]}}
                }}
                function resolveManualActualTask(projectId, taskId) {{ return {{"ok": true, "item": null}} }}
                function resolveManualActualResource(projectId, resourceId) {{ return {{"ok": true, "item": null}} }}
                function resolveManualActualCostCode(projectId, codeId, effectiveOn) {{
                    return {{"ok": true, "item": codeId ? {{"value": codeId, "label": "CC-001 - Labor"}} : null}}
                }}
                function createManualActual(payload) {{ return {{"ok": true}} }}
                function updateActualDraft(payload) {{ return {{"ok": true}} }}
                function postActual(payload) {{ return {{"ok": true}} }}
                function reverseActual(payload) {{ return {{"ok": true}} }}
                function deleteActualDraft(payload) {{ return {{"ok": true}} }}
                function rejectActual(payload) {{ return {{"ok": true}} }}
            }}
            Loader {{
                id: hostLoader
                source: "{HOST_DIALOG}"
                onLoaded: {{
                    item.workspaceController = controller
                    item.selectedProjectId = Qt.binding(function() {{ return testWindow.selectedProjectId }})
                    item.selectedActualEntryId = Qt.binding(function() {{ return testWindow.selectedEntryId }})
                    item.focusFallbackTarget = fallback
                    opener.forceActiveFocus()
                    {open_expression}
                }}
            }}
        }}
    """


@pytest.mark.parametrize(
    ("open_expression", "dialog_name", "switch_property", "switch_value"),
    (
        (
            'item.openActualDecisionDialog("post", "entry-a", 2)',
            "actualLifecycleDialog",
            "selectedEntryId",
            "entry-b",
        ),
        (
            'item.openEditManualActualDialog({"id": "entry-a", "state": {"entryId": "entry-a", "rowVersion": 2}})',
            "manualActualEditorDialog",
            "selectedEntryId",
            "entry-b",
        ),
        (
            "item.openCreateManualActualDialog()",
            "manualActualEditorDialog",
            "selectedProjectId",
            "project-b",
        ),
    ),
)
def test_entry_or_project_switch_closes_stale_actual_dialog_and_restores_fallback(
    qapp,
    open_expression: str,
    dialog_name: str,
    switch_property: str,
    switch_value: str,
) -> None:
    engine = create_qml_engine()
    component = _component(
        engine,
        _host_window_source(open_expression),
        "r6dc1-context-switch.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        dialog = window.findChild(QObject, dialog_name)
        assert _wait(qapp, lambda: dialog is not None and bool(dialog.property("opened")))
        opener = window.findChild(QObject, "actualDialogOpener")
        fallback = window.findChild(QObject, "actualDialogFallback")
        opener.setProperty("visible", False)
        window.setProperty(switch_property, switch_value)

        assert _wait(qapp, lambda: not bool(dialog.property("opened")))
        assert _wait(qapp, lambda: bool(fallback.property("activeFocus")))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_successful_actual_edit_closes_through_host_and_restores_focus(qapp) -> None:
    entry = (
        '{"id": "entry-a", "state": {'
        '"entryId": "entry-a", "rowVersion": 3, '
        '"description": "Travel adjustment", "amount": "10000", '
        '"transactionDate": "2026-09-10", "entryKind": "actual", '
        '"taskId": "", "resourceId": "", "costCodeId": "code-1"}}'
    )
    engine = create_qml_engine()
    component = _component(
        engine,
        _host_window_source(f"item.openEditManualActualDialog({entry})"),
        "r6dc1-successful-edit.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        dialog = window.findChild(QObject, "manualActualEditorDialog")
        assert _wait(qapp, lambda: dialog is not None and bool(dialog.property("opened")))
        submit = dialog.findChild(QObject, "dialogSubmitButton")
        opener = window.findChild(QObject, "actualDialogOpener")
        assert submit is not None and bool(submit.property("enabled"))
        assert QMetaObject.invokeMethod(submit, "click")
        assert _wait(qapp, lambda: not bool(dialog.property("opened")))
        assert _wait(qapp, lambda: bool(opener.property("activeFocus")))
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
