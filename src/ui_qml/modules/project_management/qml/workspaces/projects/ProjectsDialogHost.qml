import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
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

    Dialog {
        id: deleteDialog

        modal: true
        title: "Delete Project"
        standardButtons: Dialog.Cancel | Dialog.Ok
        closePolicy: Popup.CloseOnEscape

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: root.deleteTarget && root.deleteTarget.title
                    ? "Delete " + root.deleteTarget.title + " and its related planning data?"
                    : "Delete the selected project and its related planning data?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This action removes the project record, related tasks, and dependent planning data."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.projectId) {
                root.deleteRequested(String(state.projectId))
            }
        }
    }
}
