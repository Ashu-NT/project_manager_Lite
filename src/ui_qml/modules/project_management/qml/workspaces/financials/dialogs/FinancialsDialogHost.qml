import QtQuick

Item {
    id: root

    property var workspaceController: null
    property string selectedProjectId: ""
    property var taskOptions: []
    property var manualActualOptions: ({ "currencyCode": "", "costCodes": [], "entryKinds": [] })

    function _handleResult(dialog, result) {
        if (result && result.ok) {
            dialog.close()
        } else {
            dialog.errorMessage = (result && result.message) || "An unexpected error occurred."
        }
    }

    function openCreateManualActualDialog() {
        editorDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openCreateCostCodeDialog() {
        costCodeEditorDialog.errorMessage = ""
        costCodeEditorDialog.open()
    }

    // Opens the shared reject/post/reverse decision dialog for the given
    // canonical ProjectCostEntry. Submit and approve need no extra fields
    // and are dispatched directly by the caller without a dialog.
    function openActualDecisionDialog(mode, entryId, rowVersion) {
        actualLifecycleDialog.mode = String(mode || "reject")
        actualLifecycleDialog.entryId = String(entryId || "")
        actualLifecycleDialog.rowVersion = Number(rowVersion || 0)
        actualLifecycleDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        actualLifecycleDialog.errorMessage = ""
        actualLifecycleDialog.open()
    }

    ManualActualEditorDialog {
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

    CostCodeEditorDialog {
        id: costCodeEditorDialog

        selectedProjectId: root.selectedProjectId
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = root.workspaceController.createCostCode(payload)
            root._handleResult(costCodeEditorDialog, result)
        }
    }

    ActualLifecycleDialog {
        id: actualLifecycleDialog

        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onDecided: function(mode, payload) {
            if (!root.workspaceController) return
            let result
            if (mode === "post") {
                result = root.workspaceController.postActual(payload)
            } else if (mode === "reverse") {
                result = root.workspaceController.reverseActual(payload)
            } else {
                result = root.workspaceController.rejectActual(payload)
            }
            root._handleResult(actualLifecycleDialog, result)
        }
    }
}
