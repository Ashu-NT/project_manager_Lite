import pytest
from PySide6.QtCore import QObject, Qt, QUrl, Slot
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QSignalSpy, QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


class SourceController(QObject):
    def __init__(self):
        super().__init__()
        self.requests = []
        self.fail = False

    @Slot(str, str, str, int, int, result="QVariantMap")
    def searchEligibleBillingSources(self, project, preparation, search, page, size):
        self.requests.append((project, preparation, search, page, size))
        if self.fail:
            return {"ok": False, "message": "Lookup unavailable."}
        return {
            "ok": True, "page": page, "pageSize": size, "total": 101,
            "items": [{"value": f"source-{page}", "label": "Source", "sourceType": "schedule_line", "amount": "125.00", "currencyCode": "XAF"}],
        }


@pytest.mark.parametrize("width,height", [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)])
def test_source_picker_pages_failure_escape_and_viewport(qapp, width, height):
    engine = create_qml_engine()
    controller = SourceController()
    engine.rootContext().setContextProperty("sourceController", controller)
    component = QQmlComponent(engine)
    component.setData(b'''
import QtQuick
import workspaces.financials.dialogs 1.0
Window {
    visible: true
    BillingSourcePickerDialog {
        objectName: "picker"
        projectId: "project"
        preparationId: "preparation"
        preparationVersion: 7
        workspaceController: sourceController
    }
}
''', QUrl())
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None
    try:
        window.setWidth(width)
        window.setHeight(height)
        window.show()
        picker = window.findChild(QObject, "picker")
        picker.open()
        QTest.qWait(100)
        assert picker.property("opened")
        assert controller.requests[-1] == ("project", "preparation", "", 1, 50)
        assert 0 < picker.property("height") <= height
        assert 0 <= picker.property("y") <= height - picker.property("height")
        assert 0 <= picker.property("x") <= width - picker.property("width")
        picker.setProperty("sourcePage", 2)
        picker.loadSources()
        assert controller.requests[-1][3] == 2
        assert picker.property("sourceTotal") == 101
        picker.setProperty("selectedSourceId", "source-2")
        picker.setProperty("selectedSourceType", "schedule_line")
        assert picker.property("primaryEnabled")
        controller.fail = True
        picker.loadSources()
        assert not picker.property("primaryEnabled")
        assert picker.property("sourceTotal") == 0
        assert picker.property("errorMessage") == "Lookup unavailable."
        QTest.keyClick(window, Qt.Key_Escape)
        QTest.qWait(100)
        assert not picker.property("opened")
        count = len(controller.requests)
        QTest.qWait(350)
        assert len(controller.requests) == count
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("width,height", [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)])
@pytest.mark.parametrize("dialog_type", ["BillingProfileDialog", "BillingScheduleLineDialog", "BillingPreparationDialog", "BillingDecisionDialog"])
def test_billing_forms_viewport_keyboard_validation_reset(qapp, width, height, dialog_type):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    properties = ('action: "reject"; preparation: ({id: "prep", state: {canReject: true}})'
                  if dialog_type == "BillingDecisionDialog" else 'projectId: "project"')
    if dialog_type == "BillingPreparationDialog":
        properties += '; commandId: "command"'
    component.setData(f'''
import QtQuick
import QtQuick.Controls
import workspaces.financials.dialogs 1.0
Window {{
    visible: true
    Button {{ id: opener; objectName: "opener"; text: "Open" }}
    {dialog_type} {{ objectName: "dialog"; {properties}; focusFallbackTarget: opener }}
}}
'''.encode(), QUrl())
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None
    try:
        window.setWidth(width)
        window.setHeight(height)
        window.show()
        opener = window.findChild(QObject, "opener")
        opener.forceActiveFocus()
        dialog = window.findChild(QObject, "dialog")
        spy = QSignalSpy(dialog.submitted)
        dialog.open()
        QTest.qWait(100)
        assert dialog.property("opened")
        assert 0 < dialog.property("height") <= height
        assert 0 <= dialog.property("y") <= height - dialog.property("height")
        assert 0 <= dialog.property("x") <= width - dialog.property("width")
        initial = window.property("activeFocusItem")
        assert isinstance(initial, QQuickItem) and initial != opener
        QTest.keyClick(window, Qt.Key_Tab)
        assert window.property("activeFocusItem") != initial
        QTest.keyClick(window, Qt.Key_Backtab)
        assert window.property("activeFocusItem") == initial
        QTest.keyClick(window, Qt.Key_Return)
        assert spy.count() == 0
        dialog.submitDialog()
        assert spy.count() == 0
        assert dialog.property("errorMessage")
        assert window.property("activeFocusItem") == initial
        initial.setProperty("text", "Unsubmitted value")
        QTest.keyClick(window, Qt.Key_Escape)
        QTest.qWait(100)
        assert not dialog.property("opened")
        assert window.property("activeFocusItem") == opener
        dialog.open()
        QTest.qWait(100)
        assert initial.property("text") == ""
        assert dialog.property("errorMessage") == ""
        dialog.close()
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
