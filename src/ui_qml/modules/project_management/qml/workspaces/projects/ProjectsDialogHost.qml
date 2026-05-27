import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var statusOptions: []
    property var editTarget: ({})
    property var statusTarget: ({})
    property var deleteTarget: ({})

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal statusChangeRequested(string projectId, string statusValue)
    signal deleteRequested(string projectId)

    function openCreateDialog() {
        root.editTarget = { "state": { "status": "PLANNED" } }
        editorDialog.modeTitle = "Create Project"
        editorDialog.projectData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(projectData) {
        root.editTarget = projectData || ({})
        editorDialog.modeTitle = "Edit Project"
        editorDialog.projectData = root.editTarget
        editorDialog.open()
    }

    function openStatusDialog(projectData) {
        root.statusTarget = projectData || ({})
        statusDialog.projectData = root.statusTarget
        statusDialog.open()
    }

    function openDeleteDialog(projectData) {
        root.deleteTarget = projectData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.ProjectEditorDialog {
        id: editorDialog

        statusOptions: root.statusOptions

        onSubmitted: function(payload) {
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            if (state.projectId) {
                payload.projectId = state.projectId
                payload.expectedVersion = state.version
                root.updateRequested(payload)
            } else {
                root.createRequested(payload)
            }
            editorDialog.close()
        }
    }

    ProjectManagementDialogs.ProjectStatusDialog {
        id: statusDialog

        statusOptions: root.statusOptions

        onSubmitted: function(statusValue) {
            var state = root.statusTarget && root.statusTarget.state ? root.statusTarget.state : (root.statusTarget || {})
            if (state.projectId) {
                root.statusChangeRequested(String(state.projectId), statusValue)
            }
            statusDialog.close()
        }
    }

    AppControls.ConfirmationDialog {
        id: deleteDialog
        title: "Delete Project"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Project"
        confirmIcon: "delete"
        confirmDanger: true
        message: root.deleteTarget && root.deleteTarget.title
            ? "Delete " + root.deleteTarget.title + " and its related planning data?"
            : "Delete the selected project and its related planning data?"
        supportingText: "This action removes the project record, related tasks, and dependent planning data."

        onConfirmed: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.projectId) {
                root.deleteRequested(String(state.projectId))
            }
        }
    }
}

