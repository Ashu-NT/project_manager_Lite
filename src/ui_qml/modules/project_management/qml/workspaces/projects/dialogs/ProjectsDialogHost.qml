import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property var statusOptions: []
    property var workspaceController: null
    property var editTarget: ({})
    property var statusTarget: ({})
    property var deleteTarget: ({})

    signal deleteRequested(string projectId)

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

    function openImportDialog() {
        importDialog.open()
    }

    function openCreateDialog() {
        root.editTarget = { "state": { "status": "PLANNED" } }
        editorDialog.modeTitle = "Create Project"
        editorDialog.projectData = root.editTarget
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openEditDialog(projectData) {
        root.editTarget = projectData || ({})
        editorDialog.modeTitle = "Edit Project"
        editorDialog.projectData = root.editTarget
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openStatusDialog(projectData) {
        root.statusTarget = projectData || ({})
        statusDialog.projectData = root.statusTarget
        statusDialog.errorMessage = ""
        statusDialog.open()
    }

    function openDeleteDialog(projectData) {
        root.deleteTarget = projectData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.ProjectsImportDialog {
        id: importDialog
        workspaceController: root.workspaceController
    }

    ProjectManagementDialogs.ProjectEditorDialog {
        id: editorDialog
        statusOptions: root.statusOptions
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (root.workspaceController === null) return
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            var result
            if (state.projectId) {
                payload.projectId = state.projectId
                payload.expectedVersion = state.version
                result = root.workspaceController.updateProject(payload)
            } else {
                result = root.workspaceController.createProject(payload)
            }
            root._handleResult(editorDialog, result)
        }
    }

    ProjectManagementDialogs.ProjectStatusDialog {
        id: statusDialog
        statusOptions: root.statusOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(statusValue) {
            if (root.workspaceController === null) return
            var state = root.statusTarget && root.statusTarget.state ? root.statusTarget.state : (root.statusTarget || {})
            if (!state.projectId) return
            const result = root.workspaceController.setProjectStatus(String(state.projectId), statusValue)
            root._handleResult(statusDialog, result)
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
