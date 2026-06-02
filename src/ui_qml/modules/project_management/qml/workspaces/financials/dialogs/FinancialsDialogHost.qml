import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var workspaceController: null
    property string selectedProjectId: ""
    property var taskOptions: []
    property var costTypeOptions: []
    property var editTarget: ({})
    property var deleteTarget: ({})

    signal deleteRequested(string costId)

    function _handleResult(dialog, result) {
        if (!result || result.success) {
            dialog.close()
        } else {
            dialog.errorMessage = result.error || "An unexpected error occurred."
        }
    }

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "costType": "OVERHEAD",
                "plannedAmount": "0.00",
                "committedAmount": "0.00",
                "actualAmount": "0.00"
            }
        }
        editorDialog.modeTitle = "Create Cost Item"
        editorDialog.costData = root.editTarget
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openEditDialog(costData) {
        root.editTarget = costData || ({})
        editorDialog.modeTitle = "Edit Cost Item"
        editorDialog.costData = root.editTarget
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openDeleteDialog(costData) {
        root.deleteTarget = costData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.CostItemEditorDialog {
        id: editorDialog

        workspaceController: root.workspaceController
        selectedProjectId: root.selectedProjectId
        taskOptions: root.taskOptions
        costTypeOptions: root.costTypeOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            var result
            if (state.costId) {
                payload.costId = state.costId
                payload.expectedVersion = state.version
                result = root.workspaceController.updateCostItem(payload)
            } else {
                payload.projectId = root.selectedProjectId
                result = root.workspaceController.createCostItem(payload)
            }
            root._handleResult(editorDialog, result)
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteDialog
        title: "Delete Cost Item"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Cost Item"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.deleteTarget && root.deleteTarget.title
            ? "Delete " + root.deleteTarget.title + " from the selected project?"
            : "Delete the selected cost item from the selected project?"
        supportingText: "This removes the financial line from cost control, finance snapshots, and related project reporting."

        onConfirmed: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.costId) {
                root.deleteRequested(String(state.costId))
            }
        }
    }
}
