import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var workerTypeOptions: []
    property var categoryOptions: []
    property var employeeOptions: []
    property var editTarget: ({})
    property var deleteTarget: ({})

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string resourceId)

    function openCreateDialog() {
        root.editTarget = {
            "state": {
                "workerType": "EXTERNAL",
                "costType": "LABOR",
                "isActive": true,
                "capacityPercent": "100.0"
            }
        }
        editorDialog.modeTitle = "Create Resource"
        editorDialog.resourceData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(resourceData) {
        root.editTarget = resourceData || ({})
        editorDialog.modeTitle = "Edit Resource"
        editorDialog.resourceData = root.editTarget
        editorDialog.open()
    }

    function openDeleteDialog(resourceData) {
        root.deleteTarget = resourceData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.ResourceEditorDialog {
        id: editorDialog

        workerTypeOptions: root.workerTypeOptions
        categoryOptions: root.categoryOptions
        employeeOptions: root.employeeOptions

        onSubmitted: function(payload) {
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            if (state.resourceId) {
                payload.resourceId = state.resourceId
                payload.expectedVersion = state.version
                root.updateRequested(payload)
            } else {
                root.createRequested(payload)
            }
            editorDialog.close()
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteDialog
        title: "Delete Resource"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Resource"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.deleteTarget && root.deleteTarget.title
            ? "Delete " + root.deleteTarget.title + " and its related assignments?"
            : "Delete the selected resource and its related assignments?"
        supportingText: "This action removes the resource record and any PM assignments or linked allocation history that depends on it."

        onConfirmed: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.resourceId) {
                root.deleteRequested(String(state.resourceId))
            }
        }
    }
}

