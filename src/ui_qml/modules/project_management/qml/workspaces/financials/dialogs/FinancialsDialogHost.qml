import QtQuick
import QtQuick.Controls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var workspaceController: null
    property string selectedProjectId: ""
    property var taskOptions: []
    property var manualActualOptions: ({ "currencyCode": "", "costCodes": [], "entryKinds": [] })

    function _handleResult(dialog, result) {
        if (!result || result.success) {
            dialog.close()
        } else {
            dialog.errorMessage = result.error || "An unexpected error occurred."
        }
    }

    function openCreateManualActualDialog() {
        editorDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    ProjectManagementDialogs.ManualActualEditorDialog {
        id: editorDialog

        selectedProjectId: root.selectedProjectId
        taskOptions: root.taskOptions
        actualOptions: root.manualActualOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = root.workspaceController.createManualActual(payload)
            root._handleResult(editorDialog, result)
        }
    }
}
