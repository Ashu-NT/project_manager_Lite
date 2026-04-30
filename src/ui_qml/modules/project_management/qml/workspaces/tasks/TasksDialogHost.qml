import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Dialogs 1.0 as ProjectManagementDialogs

Item {
    id: root

    property string selectedProjectId: ""
    property var statusOptions: []
    property var editTarget: ({})
    property var progressTarget: ({})
    property var deleteTarget: ({})

    signal createRequested(var payload)
    signal updateRequested(var payload)
    signal progressRequested(var payload)
    signal deleteRequested(string taskId)

    function openCreateDialog() {
        root.editTarget = { "state": { "status": "TODO" } }
        editorDialog.modeTitle = "Create Task"
        editorDialog.taskData = root.editTarget
        editorDialog.open()
    }

    function openEditDialog(taskData) {
        root.editTarget = taskData || ({})
        editorDialog.modeTitle = "Edit Task"
        editorDialog.taskData = root.editTarget
        editorDialog.open()
    }

    function openProgressDialog(taskData) {
        root.progressTarget = taskData || ({})
        progressDialog.taskData = root.progressTarget
        progressDialog.open()
    }

    function openDeleteDialog(taskData) {
        root.deleteTarget = taskData || ({})
        deleteDialog.open()
    }

    ProjectManagementDialogs.TaskEditorDialog {
        id: editorDialog

        statusOptions: root.statusOptions

        onSubmitted: function(payload) {
            var state = root.editTarget && root.editTarget.state ? root.editTarget.state : (root.editTarget || {})
            payload.projectId = String(state.projectId || root.selectedProjectId || "")
            if (state.taskId) {
                payload.taskId = String(state.taskId)
                payload.expectedVersion = state.version
                root.updateRequested(payload)
            } else {
                root.createRequested(payload)
            }
            editorDialog.close()
        }
    }

    ProjectManagementDialogs.TaskProgressDialog {
        id: progressDialog

        statusOptions: root.statusOptions

        onSubmitted: function(payload) {
            root.progressRequested(payload)
            progressDialog.close()
        }
    }

    Dialog {
        id: deleteDialog

        modal: true
        title: "Delete Task"
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
                    ? "Delete " + root.deleteTarget.title + " and its dependent planning data?"
                    : "Delete the selected task and its dependent planning data?"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "This action removes the task record plus related dependencies, assignments, and linked planning items."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        onAccepted: {
            var state = root.deleteTarget && root.deleteTarget.state ? root.deleteTarget.state : (root.deleteTarget || {})
            if (state.taskId) {
                root.deleteRequested(String(state.taskId))
            }
        }
    }
}
